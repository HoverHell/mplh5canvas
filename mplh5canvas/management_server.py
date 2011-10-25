"""A base for handling management of the h5 canvas backend.

Its jobs are as follows:
- Provide a standardised base port for clients to connect to
- Serve up the html wrapper page
- Provide a list of currently available plots (perhaps with a thumbnail)
- Manage the list of plots as time goes by

Simon Ratcliffe (sratcliffe@ska.ac.za)
Ludwig Schwardt (ludwig@ska.ac.za)

Copyright (c) 2010-2011, SKA South Africa
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of SKA South Africa nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

import BaseHTTPServer
import simple_server
import base_page
import thread
import sys
import re
import socket
import time
import logging

logger = logging.getLogger("mplh5canvas.management_server")

try:
    import netifaces
except:
    netifaces = None

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    base_html = base_page.base_html
    base_html_decoration = base_page.base_html_decoration
    base_html_canvii = base_page.base_html_canvii
    thumb_html = base_page.thumb_html
    thumb_inner = base_page.thumb_inner
    h5m = None
    server_port = ""
    custom_content = None
    def do_GET(self):
        server_ip = self.connection.getsockname()[0]
        logger.info("Server ip for connection: %s " % server_ip)
        match = re.compile("\/(\d*)$").match(self.path)
        ports = self.h5m._figures.keys()
        ports.sort()
        if match is not None:
            req_layout = match.groups()[0]
            for port in ports:
                canvas = self.h5m._figures[port]
            req_layout = (req_layout == '' and "" or "set_layout(" + str(req_layout) + ");")
            bh = self.base_html + self.base_html_decoration + self.base_html_canvii
            self.wfile.write(bh.replace('<!--requested_layout-->',req_layout).replace('<!--server_ip-->',server_ip).replace('<!--server_port-->',self.server_port).replace('<!--canvas_top-->','105').replace('<!--canvas_left-->','10').replace('<!--canvas_position-->','absolute'))
        elif self.path.startswith("/figure"):
            try:
                fig_no = int(self.path[7:]) - 1
            except ValueError:
                fig_no = 0
            if fig_no < 0: fig_no = 0
             # get the first figure by default
            try:
                port = ports[fig_no]
                custom_content = self.h5m._figures[port]._custom_content
                bh = self.base_html + self.base_html_canvii
                req_layout = "plot_if_possible(" + str(port)  + ");"
                content = bh.replace('<!--requested_layout-->',req_layout).replace('<!--server_ip-->',server_ip).replace('<!--server_port-->',self.server_port).replace('<!--canvas_top-->','10').replace('<!--canvas_left-->','10').replace('<!--canvas_position-->','absolute')
                if custom_content is not None:
                    content = custom_content.replace("<!--figure-->", content)
                self.wfile.write(content)

            except IndexError:
                self.wfile.write("Invalid Figure number (" + str(fig_no+1) + ") specified.")
        elif self.path == "/thumbs":
             # for each figure, create a thumbnail snippet and slipstream the js for the preview
            figure_count = 0
            thumbs = ""
            for port in ports:
                canvas = self.h5m._figures[port]
                t = self.thumb_inner.replace("<id>",str(figure_count))
                t = t.replace("<!--thumbnail_port-->",str(port))
                t = t.replace("<!--width-->",str(canvas._width)).replace("<!--height-->",str(canvas._height))
                frame = str(canvas._frame).replace("\n","").replace(";c.",";c_t_" + str(figure_count) + ".").replace("{ c", "{ c_t_" + str(figure_count))
                header = str(canvas._header).replace("\n","")
                if frame.startswith("c."): frame = "c_t_" + str(figure_count) + frame[1:]
                thumbs += t.replace('<!--thumbnail_content-->',header + frame) + "\n"
                figure_count += 1
             # insert thumbnail code into base page 
            self.wfile.write(self.thumb_html.replace("<!--thumbnail_body-->",thumbs))
        else:
            self.wfile.write("Not found...")

class H5Manager(object):
    """An H5 Canvas Manager.
    
    Parameters
    ----------
    port : integer
        The base port on which to serve the managers web interface
    """
    def __init__(self, base_port, limit):
        self.ip = self._external_ip()
         # find the next available port in multiples of 100 from base port
        self._figures = {}
        for x in range(limit):
            port_to_try = base_port + x*100
            try:
                self._server = BaseHTTPServer.HTTPServer(('', port_to_try), RequestHandler)
                self._thread = thread.start_new_thread(self._server.serve_forever, ())
                self._wsserver = simple_server.WebSocketServer(('', port_to_try+1), self.management_request, simple_server.WebSocketRequestHandler)
                self._wsthread = thread.start_new_thread(self._wsserver.serve_forever, ())
                break
            except Exception, e:
                if x == limit - 1:
                    logger.error("Tried to find an available port pair from %i to %i, but none seemed available. You can only spawn %i python mplh5 instances on this machine.\nThis limit can be changed in init.py." % (base_port, base_port + (x-1)*100, limit))
                    sys.exit(1)
                else:
                    logger.error("Failed to start management servers on ports (%i, %i). Trying another pair..." % (port_to_try, port_to_try+1))
                    logger.error(e)
                    time.sleep(0.05)
         # we have a port :)
        self.port = port_to_try
        RequestHandler.h5m = self
        RequestHandler.server_port = str(self.port)
        self.url = "http://%s:%i" % (self.ip, self.port)
        self._request_handlers = {}
        print "===================================================================================="
        print "Management interface active. Browse to %s to view plots." % self.url
        print "===================================================================================="
        sys.stdout.flush()

    def _external_ip(self, preferred_prefixes=('eth', 'en')):
        """Return the external IPv4 address of this machine.

        Attempts to use netifaces module if available, otherwise
        falls back to socket.

        Parameters
        ----------
        preferred_prefixes : tuple
            A tuple of string prefixes for network interfaces to match. e.g. ('eth','en') matches ethX and enX
            with a preference for lowest number first (eth0 over eth3).

        Returns
        -------
        ip : str or None
            IPv4 address string (dotted quad). Returns None if
            ip address cannot be guessed.
        """
        if netifaces is None:
            ips = [socket.gethostbyname(socket.gethostname())]
        else:
            preferred_ips = []
            other_ips = []
            for iface in netifaces.interfaces():
                for addr in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
                    if 'addr' in addr:
                        for prefix in preferred_prefixes:
                            if iface.startswith(prefix): preferred_ips.append(addr['addr'])
                        other_ips.append(addr['addr'])
                         # will duplicate those in preferred_ips but this doesn't matter as we only
                         # use other_ips if preferred is empty.
            ips = preferred_ips + other_ips
        if ips:
            return ips[0]
        else:
            return "127.0.0.1"

    def management_request(self, request):
        self._request_handlers[request] = request.connection.remote_addr[0]
        while True:
            try:
                line = request.ws_stream.receive_message()
                request.ws_stream.send_message("update_thumbnails();".decode('utf-8'))
            except Exception, e:
                logger.debug("Removing registered management handler (%s)" % e)
                if self._request_handlers.has_key(request): del self._request_handlers[request]
                return

    def tell(self):
        recipients = ""
        for r in self._request_handlers.keys():
            try:
                recipients += str(r.connection.remote_addr[0]) + " "
                r.ws_stream.send_message("update_thumbnails();".decode('utf-8'))
            except AttributeError:
                logger.debug("Connection %s has gone. Closing..." % r.connection.remote_addr[0])
                del self._request_handlers[request]


    def add_figure(self, port, canvas):
        """Add a figure to the manager"""
        self._figures[port] = canvas
        self.tell()

    def remove_figure(self, port):
        """Remove a figure from the manager"""
        self._figures.pop(port)
        self.tell()

    def handle_base(self):
        pass

    def parse_web_cmd(self, s):
        action = s[1:s.find(" ")]
        args = s[s.find("args='")+6:-2].split(",")
        method = getattr(self, "handle_%s" % action)
        if method:
            method(*args)
        else:
            self.handle_base()
