# Modifications 2010 by Simon Ratcliffe (sratcliffe@ska.ac.za)
#
# Original copyright notice below:
#
# Copyright 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Simplistic WebSocket server.
"""

import BaseHTTPServer
import CGIHTTPServer
import SimpleHTTPServer
import SocketServer
import logging
import logging.handlers
import optparse
import os
import re
import socket
import sys

import traceback
import handshake
import memorizingfile
import threading
import select

# 1024 is practically large enough to contain WebSocket handshake lines.
_MAX_MEMORIZED_LINES = 1024

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

class _StandaloneConnection(object):
    """Mimic mod_python mp_conn."""

    def __init__(self, request_handler):
        """Construct an instance.

        Args:
            request_handler: A WebSocketRequestHandler instance.
        """
        self._request_handler = request_handler

    def get_local_addr(self):
        """Getter to mimic mp_conn.local_addr."""
        return (self._request_handler.server.server_name,
                self._request_handler.server.server_port)
    local_addr = property(get_local_addr)

    def get_remote_addr(self):
        """Getter to mimic mp_conn.remote_addr.

        Setting the property in __init__ won't work because the request
        handler is not initialized yet there."""
        return self._request_handler.client_address
    remote_addr = property(get_remote_addr)

    def write(self, data):
        """Mimic mp_conn.write()."""
        return self._request_handler.wfile.write(data)

    def read(self, length):
        """Mimic mp_conn.read()."""
        return self._request_handler.rfile.read(length)

    def get_memorized_lines(self):
        """Get memorized lines."""
        return self._request_handler.rfile.get_memorized_lines()


class _StandaloneRequest(object):
    """Mimic mod_python request."""

    def __init__(self, request_handler, use_tls):
        """Construct an instance.

        Args:
            request_handler: A WebSocketRequestHandler instance.
        """
        self._request_handler = request_handler
        self.connection = _StandaloneConnection(request_handler)
        self._use_tls = use_tls

    def get_uri(self):
        """Getter to mimic request.uri."""
        return self._request_handler.path
    uri = property(get_uri)

    def get_method(self):
        """Getter to mimic request.method."""
        return self._request_handler.command
    method = property(get_method)

    def get_headers_in(self):
        """Getter to mimic request.headers_in."""
        return self._request_handler.headers
    headers_in = property(get_headers_in)

    def is_https(self):
        """Mimic request.is_https()."""
        return self._use_tls


class WebSocketServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """HTTPServer specialized for Web Socket."""

    SocketServer.ThreadingMixIn.daemon_threads = True

    def __init__(self, server_address, handler, RequestHandlerClass):
        """Override SocketServer.BaseServer.__init__."""

        SocketServer.BaseServer.__init__(
                self, server_address, RequestHandlerClass)
        self._handler = handler
        self.socket = self._create_socket()
        self.server_bind()
        self.server_activate()
         # python 2.5 fixes
        self.__is_shut_down = threading.Event()
        self.__serving = False

     # from python 2.6 to handle python 2.5 :)
    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            r, w, e = select.select([self], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
        self.__is_shut_down.set()

    def shutdown(self):
        """Stops the serve_forever loop.

        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__serving = False
        self.__is_shut_down.wait()

    def handle_request(self):
        """Handle one request, possibly blocking.

        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = select.select([self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.close_request(request)

    def handle_timeout(self):
        """Called if no new request arrives within self.timeout.

        Overridden by ForkingMixIn.
        """
        pass

    def _create_socket(self):
        socket_ = socket.socket(self.address_family, self.socket_type)
        return socket_

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, handler=self._handler)

    def handle_error(self, rquest, client_address):
        """Override SocketServer.handle_error."""

        logging.error(
            ('Exception in processing request from: %r' % (client_address,)) +
            '\n' + traceback.format_exc())
        # Note: client_address is a tuple. To match it against %r, we need the
        # trailing comma.


class WebSocketRequestHandler(CGIHTTPServer.CGIHTTPRequestHandler):
    """CGIHTTPRequestHandler specialized for Web Socket."""

    def setup(self):
        """Override SocketServer.StreamRequestHandler.setup."""

        self.connection = self.request
        self.rfile = memorizingfile.MemorizingFile(
                socket._fileobject(self.request, 'rb', self.rbufsize),
                max_memorized_lines=1024)
        self.wfile = socket._fileobject(self.request, 'wb', self.wbufsize)

    def __init__(self, *args, **keywords):
        self._request = _StandaloneRequest(
                self, False)
        self._handler = keywords.pop('handler') #WebSocketRequestHandler._handlers
        self._handshaker = handshake.Handshaker(self._request, allowDraft75=True, strict=False)
        CGIHTTPServer.CGIHTTPRequestHandler.__init__(
                self, *args, **keywords)

    def parse_request(self):
        """Override BaseHTTPServer.BaseHTTPRequestHandler.parse_request.

        Return True to continue processing for HTTP(S), False otherwise.
        """
        result = CGIHTTPServer.CGIHTTPRequestHandler.parse_request(self)
        #print "CGI Result: ",result
        if result:
            try:
                self._handshaker.do_handshake()
                self._handler(self._request)
                return False
            except handshake.HandshakeError, e:
                # Handshake for ws(s) failed. Assume http(s).
                logging.info('mod_pywebsocket: %s' % e)
                return True
            except Exception, e:
                logging.warning('mod_pywebsocket: %s' % e)
                logging.info('mod_pywebsocket: %s' % traceback.format_exc())
                return False
        return result

    def log_request(self, code='-', size='-'):
        """Override BaseHTTPServer.log_request."""

        logging.info('"%s" %s %s',
                     self.requestline, str(code), str(size))

    def log_error(self, *args):
        """Override BaseHTTPServer.log_error."""

        # Despite the name, this method is for warnings than for errors.
        # For example, HTTP status code is logged by this method.
        logging.warn('%s - %s' % (self.address_string(), (args[0] % args[1:])))

    def is_cgi(self):
        return False

# vi:sts=4 sw=4 et
