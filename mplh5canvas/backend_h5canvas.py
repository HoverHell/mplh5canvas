"""An HTML5 Canvas backend for matplotlib.

Simon Ratcliffe (sratcliffe@ska.ac.za)
Ludwig Schwardt (ludwig@ska.ac.za)

Copyright (c) 2010, SKA South Africa
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of SKA South Africa nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

from __future__ import division

import sys
import math
import webbrowser
import time
import thread

import numpy as np
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import RendererBase, GraphicsContextBase, FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.transforms import Affine2D
from matplotlib.path import Path
from matplotlib.colors import colorConverter, rgb2hex
from matplotlib.cbook import maxdict
from matplotlib.ft2font import FT2Font, LOAD_NO_HINTING
from matplotlib.font_manager import findfont
from matplotlib.mathtext import MathTextParser
from matplotlib import _png

import simple_server
import msgutil
import management_server
import uuid

_capstyle_d = {'projecting' : 'square', 'butt' : 'butt', 'round': 'round',}
 # mapping from matplotlib style line caps to H5 canvas

BASE_PORT = 4566
figure_number = 0

_figure_ports = {}
#_request_handlers = {}
_frame = ""
_test = False
_quiet = True
_metrics = False

h5m = management_server.H5Manager(8080)
 # start a new management server...

def new_web_port():
    if _figure_ports.has_key('count'): _figure_ports['count'] += 1
    else: _figure_ports['count'] = 1
    return BASE_PORT + _figure_ports['count']

def register_web_server(port, canvas):
    h5m.add_figure(port, canvas)
    _figure_ports[port] = canvas

def deregister_web_server(port):
    h5m.remove_figure(port)
    _figure_ports.pop(port)
     # not particularly intelligent as we can't reuse ports. some form of map required.

def mpl_to_css_color(color, alpha=None, isRGB=True):
    """Convert Matplotlib color spec (or rgb tuple + alpha) to CSS color string."""
    if not isRGB:
        r, g, b, alpha = colorConverter.to_rgba(color)
        color = (r, g, b)
    if alpha is None and len(color) == 4:
        alpha = color[3]
    if alpha is None:
        return rgb2hex(color[:3])
    else:
        return 'rgba(%d, %d, %d, %.3g)' % (color[0] * 255, color[1] * 255, color[2] * 255, alpha)

class WebPNG(object):
    """Very simple file like object for use with the write_png method.
    Used to grab the output that would have headed to a standard file, and allow further manipulation
    such as base 64 encoding."""
    def __init__(self):
        self.buffer = ""
    def write(self, s):
        self.buffer += s
    def get_b64(self):
        import base64
        return base64.b64encode(self.buffer)

class H5Frame(object):
    def __init__(self, frame_number=0, context_name='c'):
        self._frame_number = frame_number
         # the frame number in the current animated sequence
        self._context_name = context_name
         # the name of the context to use for drawing
        self._content = ""
         # a full frame of script ready for rendering
        self._extra = ""
        self._header = "frame_body_%s();" % self._context_name
        self._custom_header = False

    def _convert_obj(self, obj):
        return (isinstance(obj, unicode) and repr(obj.replace("'","`"))[1:] or (isinstance(obj, float) and '%.2f' % obj or repr(obj)))

    def __getattr__(self, method_name):
         # when frame is called in .<method_name>(<argument>) context
        def h5_method(*args):
            self._content += '%s.%s(%s);\n' % (self._context_name, method_name, ','.join([self._convert_obj(obj) for obj in args]))
        return h5_method

    def __setattr__(self, prop, value):
         # when frame properties are assigned to .<prop> = <value>
        if prop.startswith('_'):
            self.__dict__[prop] = value
            return
        self._content += '%s.%s=%s;\n' % (self._context_name, prop, self._convert_obj(value))

    def moveTo(self, x, y):
        self._content += '%s.%s(%.2f,%.2f);\n' % (self._context_name, "moveTo", x, y)

    def lineTo(self, x, y):
        self._content += '%s.%s(%.2f,%.2f);\n' % (self._context_name, "lineTo", x, y)
        #self._content = self._content + self._context_name + ".lineTo(" + str(x) + "," + str(y) + ");\n"
         # options for speed...

    def dashedLine(self, x1, y1, x2, y2, dashes):
        """Draw dashed line from (x1, y1) to (x2, y2), given dashes structure, and return new dash offset."""
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length <= 0.0:
            return dashes[0]
        dash_length = np.sum(dashes[1])
        # Wrap offset to fall in interval [-dash_length..0], and do one dash period extra to ensure dashed line has no gaps
        offset, num_periods = -(dashes[0] % dash_length), int(length // dash_length) + 2
        unit_x, unit_y = (x2 - x1) / length, (y2 - y1) / length
        # The rest of the function can be implemented in Javascript instead, to compress the string being sent across the network
        self.moveTo(x1, y1)
        for n in xrange(num_periods):
            for m, dash_step in enumerate(dashes[1]):
                # Clip start of dash segment if it straddles (x1, y1)
                if offset < 0.0 and (offset + dash_step) > 0.0:
                    dash_step += offset
                    offset = 0.0
                # Clip end of dash segment if it straddles (x2, y2)
                if offset < length and (offset + dash_step) > length:
                    dash_step = length - offset
                # Advance to end of current dash segment
                offset += dash_step
                if offset >= 0.0 and offset <= length:
                    # Alternately draw dash and move to start of next dash
                    if m % 2 == 0:
                        self.lineTo(x1 + unit_x * offset, y1 + unit_y * offset)
                    else:
                        self.moveTo(x1 + unit_x * offset, y1 + unit_y * offset)
        return dashes[0] + (length % dash_length)

    def beginPath(self):
        self._content += '%s.%s();\n' % (self._context_name, "beginPath")

    def stroke(self):
        self._content += '%s.%s();\n' % (self._context_name, "stroke")

    def closePath(self):
        self._content += '%s.%s();\n' % (self._context_name, "closePath")

    def add_header(self, s, start=False):
        if not self._custom_header:
            self._custom_header = True
            self._header = ""
        if start: self._header = "%s\n" % s + self._header
        else: self._header += "%s\n" % s

    def write_extra(self, s):
        self._extra += '%s\n' % s

    def write(self, s):
        self._content += '%s\n' % s

    def get_frame(self):
        return "function frame_body_%s() { %s }\n" % (self._context_name, self._content)

    def get_frame_extra(self):
        return "function frame_body_%s() { %s\n%s }\n" % (self._context_name, self._extra, self._content)

    def get_header(self):
        return "function frame_header() { %s }\n" % self._header

    def get_extra(self):
        return self._extra

class RendererH5Canvas(RendererBase):
    """The renderer handles drawing/rendering operations."""
    fontd = maxdict(50)

    def __init__(self, width, height, ctx, dpi=72):
        self.width = width
        self.height = height
        self.dpi = dpi
        #print "Canvas Width:",width,",Height:",height,",DPI:",dpi
        self.ctx = ctx
        self._image_count = 0
         # used to uniquely label each image created in this figure...
         # define the js context
        self.ctx.width = width
        self.ctx.height = height
        #self.ctx.textAlign = "center";
        self.ctx.textBaseline = "alphabetic"
        self.flip = Affine2D().scale(1, -1).translate(0, height)
        self.mathtext_parser = MathTextParser('bitmap')
        self._path_time = 0
        self._text_time = 0
        self._marker_time = 0
        self._sub_time = 0
        self._last_clip = None
        self._last_clip_path = None
        self._clip_count = 0

    def _set_style(self, gc, rgbFace=None):
        ctx = self.ctx
        if rgbFace is not None:
            ctx.fillStyle = mpl_to_css_color(rgbFace, gc.get_alpha())
        ctx.strokeStyle = mpl_to_css_color(gc.get_rgb(), gc.get_alpha())
        if gc.get_capstyle():
            ctx.lineCap = _capstyle_d[gc.get_capstyle()]
        ctx.lineWidth = self.points_to_pixels(gc.get_linewidth())

    def _path_to_h5(self, ctx, path, transform, clip=None, stroke=True, dashes=(None, None)):
        """Iterate over a path and produce h5 drawing directives."""
        transform = transform + self.flip
        ctx.beginPath()
        current_point = None
        dash_offset, dash_pattern = dashes
        if dash_pattern is not None:
            dash_offset = self.points_to_pixels(dash_offset)
            dash_pattern = tuple([self.points_to_pixels(dash) for dash in dash_pattern])
        for points, code in path.iter_segments(transform, clip=clip):
            # Shift all points by half a pixel, so that integer coordinates are aligned with pixel centers instead of edges
            # This prevents lines that are one pixel wide and aligned with the pixel grid from being rendered as a two-pixel wide line
            # This happens because HTML Canvas defines (0, 0) as the *top left* of a pixel instead of the center,
            # which causes all integer-valued coordinates to fall exactly between pixels
            points += 0.5
            # Ignore directives with negative coordinates (sanity check that gets rid of some drawing artifacts)
            if (points < 0).any():
                continue
            if code == Path.MOVETO:
                ctx.moveTo(points[0], points[1])
                current_point = (points[0], points[1])
            elif code == Path.LINETO:
                t = time.time()
                if (dash_pattern is None) or (current_point is None):
                    ctx.lineTo(points[0], points[1])
                else:
                    dash_offset = ctx.dashedLine(current_point[0], current_point[1], points[0], points[1], (dash_offset, dash_pattern))
                self._sub_time += time.time() - t
                current_point = (points[0], points[1])
            elif code == Path.CURVE3:
                ctx.quadraticCurveTo(*points)
                current_point = (points[2], points[3])
            elif code == Path.CURVE4:
                ctx.bezierCurveTo(*points)
                current_point = (points[4], points[5])
            else:
                pass
        if stroke: ctx.stroke()

    def _do_path_clip(self, ctx, clip):
        self._clip_count += 1
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(clip[0],clip[1])
        ctx.lineTo(clip[2],clip[1])
        ctx.lineTo(clip[2],clip[3])
        ctx.lineTo(clip[0],clip[3])
        ctx.clip()

    def draw_path(self, gc, path, transform, rgbFace=None):
        t = time.time()
        self._set_style(gc, rgbFace)
        clip = self._get_gc_clip_svg(gc)
        clippath, cliptrans = gc.get_clip_path()
        ctx = self.ctx
        if clippath is not None and self._last_clip_path != clippath:
            ctx.restore()
            ctx.save()
            self._path_to_h5(ctx, clippath, cliptrans, None, stroke=False)
            ctx.clip()
            self._last_clip_path = clippath
        if self._last_clip != clip and clip is not None and clippath is None:
            ctx.restore()
            self._do_path_clip(ctx, clip)
            self._last_clip = clip
        if clip is None and clippath is None and (self._last_clip is not None or self._last_clip_path is not None): self._reset_clip()
        self._path_to_h5(ctx, path, transform, None, dashes=gc.get_dashes())
        if rgbFace is not None:
            ctx.fill()
            ctx.fillStyle = '#000000'
        self._path_time += time.time() - t

    def _get_gc_clip_svg(self, gc):
        cliprect = gc.get_clip_rectangle()
        if cliprect is not None:
            x, y, w, h = cliprect.bounds
            y = self.height-(y+h)
            return (x,y,x+w,y+h)
        return None

    def draw_markers(self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
    #    print "Draw markers called: marker_path=",marker_path,",marker_trans=",marker_trans,",path=",path,",trans=",trans
        t = time.time()
        for vertices, codes in path.iter_segments(trans, simplify=False):
            if len(vertices):
                x,y = vertices[-2:]
                self._set_style(gc, rgbFace)
                clip = self._get_gc_clip_svg(gc)
                ctx = self.ctx
                self._path_to_h5(ctx, marker_path, marker_trans + Affine2D().translate(x, y), clip) 
                if rgbFace is not None:
                    ctx.fill()
                    ctx.fillStyle = '#000000'
        self._marker_time += time.time() - t

    def _slipstream_png(self, x, y, im_buffer, width, height):
        """Insert image directly into HTML canvas as base64-encoded PNG."""
        # Shift x, y (top left corner) to the nearest CSS pixel edge, to prevent resampling and consequent image blurring
        x = math.floor(x + 0.5)
        y = math.floor(y + 1.5)
        # Write the image into a WebPNG object
        f = WebPNG()
        _png.write_png(im_buffer, width, height, f)
        # Write test PNG as file as well
        #_png.write_png(im_buffer, width, height, 'canvas_image_%d.png' % (self._image_count,))
        # Extract the base64-encoded PNG and send it to the canvas
        uname = str(uuid.uuid1()).replace("-","") #self.ctx._context_name + str(self._image_count)
         # try to use a unique image name
        enc = "var canvas_image_%s = 'data:image/png;base64,%s';" % (uname, f.get_b64())
        s = "function imageLoaded_%s(ev) {\nim = ev.target;\nim_left_to_load_%s -=1;\nif (im_left_to_load_%s == 0) frame_body_%s();\n}\ncanv_im_%s = new Image();\ncanv_im_%s.onload = imageLoaded_%s;\ncanv_im_%s.src = canvas_image_%s;\n" % \
            (uname, self.ctx._context_name, self.ctx._context_name, self.ctx._context_name, uname, uname, uname, uname, uname)
        self.ctx.add_header(enc)
        self.ctx.add_header(s)
         # Once the base64 encoded image has been received, draw it into the canvas
        self.ctx.write("%s.drawImage(canv_im_%s, %g, %g, %g, %g);" % (self.ctx._context_name, uname, x, y, width, height))
         # draw the image as loaded into canv_im_%d...
        self._image_count += 1
        #print "Placed image with w=%g h=%g at x=%g y=%g" % (width, height, x, y)

    def _reset_clip(self):
        self.ctx.restore()
        self._last_clip = None
        self._last_clip_path = None

    def draw_image(self, x, y, im, bbox, clippath=None, clippath_trans=None):
        if self._last_clip is not None or self._last_clip_path is not None: self._reset_clip()
        h,w = im.get_size_out()
        if clippath is not None:
            self._path_to_h5(self.ctx,clippath, clippath_trans, stroke=False)
            self.ctx.save()
            self.ctx.clip()
        (x,y) = self.flip.transform((x,y))
        im.flipud_out()
        rows, cols, im_buffer = im.as_rgba_str()
        self._slipstream_png(x, (y-h), im_buffer, cols, rows)
        if clippath is not None:
            self.ctx.restore()

    def _get_font(self, prop):
        key = hash(prop)
        font = self.fontd.get(key)
        if font is None:
            fname = findfont(prop)
            font = self.fontd.get(fname)
            if font is None:
                #print "Using font",str(fname)
                #print type(prop)
                font = FT2Font(str(fname))
                self.fontd[fname] = font
            self.fontd[key] = font
        font.clear()
        font.set_size(prop.get_size_in_points(), self.dpi)
        return font

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        if self._last_clip is not None or self._last_clip_path is not None: self._reset_clip()
        t = time.time()
        #print "Draw", s, "at x:" ,x, "y:" , y, "angle", angle
        if ismath:
            self._draw_mathtext(gc, x, y, s, prop, angle)
            return
        angle = math.radians(angle)
        width, height, descent = self.get_text_width_height_descent(s, prop, ismath)
        x -= math.sin(angle) * descent
        y -= math.cos(angle) * descent
        ctx = self.ctx
        if angle != 0:
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(-angle)
            ctx.translate(-x, -y)
        #print "Font property: ", prop
        font_size = self.points_to_pixels(prop.get_size_in_points())
        font_str = '%s %s %.3gpx %s, %s' % (prop.get_style(), prop.get_weight(), font_size, prop.get_name(), prop.get_family()[0])
        ctx.font = font_str
        # Set the text color, draw the text and reset the color to black afterwards
        ctx.fillStyle = mpl_to_css_color(gc.get_rgb(), gc.get_alpha())
        ctx.fillText(unicode(s), x, y)
        ctx.fillStyle = '#000000'
        if angle != 0:
            ctx.restore()
        self._text_time = time.time() - t

    def _draw_mathtext(self, gc, x, y, s, prop, angle):
        """Draw math text using matplotlib.mathtext."""
        # Render math string as an image at the configured DPI, and get the image dimensions and baseline depth
        rgba, descent = self.mathtext_parser.to_rgba(s, color=gc.get_rgb(), dpi=self.dpi, fontsize=prop.get_size_in_points())
        height, width, tmp = rgba.shape
        angle = math.radians(angle)
        # Shift x, y (top left corner) to the nearest CSS pixel edge, to prevent resampling and consequent image blurring
        x = math.floor(x + 0.5)
        y = math.floor(y + 1.5)
        ctx = self.ctx
        if angle != 0:
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(-angle)
            ctx.translate(-x, -y)
        # Insert math text image into stream, and adjust x, y reference point to be at top left of image
        self._slipstream_png(x, y - height, rgba.tostring(), width, height)
        if angle != 0:
            ctx.restore()

    def flipy(self):
        return True

    def get_canvas_width_height(self):
        return self.width, self.height

    def get_text_width_height_descent(self, s, prop, ismath):
        if ismath:
            image, d = self.mathtext_parser.parse(s, self.dpi, prop)
            w, h = image.get_width(), image.get_height()
        else:
            font = self._get_font(prop)
            font.set_text(s, 0.0, flags=LOAD_NO_HINTING)
            w, h = font.get_width_height()
            w /= 64.0  # convert from subpixels
            h /= 64.0
            d = font.get_descent() / 64.0
        #print "String '%s' has dimensions w=%g h=%g d=%g" % (s, w, h, d)
        return w, h, d

    def new_gc(self):
        return GraphicsContextH5Canvas()

    def points_to_pixels(self, points):
        # The standard desktop-publishing (Postscript) point is 1/72 of an inch
        return points/72.0 * self.dpi


class GraphicsContextH5Canvas(GraphicsContextBase):
    """
    The graphics context provides the color, line styles, etc...  See the gtk
    and postscript backends for examples of mapping the graphics context
    attributes (cap styles, join styles, line widths, colors) to a particular
    backend.  In GTK this is done by wrapping a gtk.gdk.GC object and
    forwarding the appropriate calls to it using a dictionary mapping styles
    to gdk constants.  In Postscript, all the work is done by the renderer,
    mapping line styles to postscript calls.

    If it's more appropriate to do the mapping at the renderer level (as in
    the postscript backend), you don't need to override any of the GC methods.
    If it's more appropriate to wrap an instance (as in the GTK backend) and
    do the mapping here, you'll need to override several of the setter
    methods.

    The base GraphicsContext stores colors as a RGB tuple on the unit
    interval, eg, (0.5, 0.0, 1.0). You may need to map this to colors
    appropriate for your backend.
    """
    pass



########################################################################
#
# The following functions and classes are for pylab and implement
# window/figure managers, etc...
#
########################################################################

def draw_if_interactive():
    """
    For image backends - is not required
    For GUI backends - this should be overriden if drawing should be done in
    interactive python mode
    """
    #print "In interactive..."

def show(block=True, layout=''):
    """
    This show is typically called via pyplot.show.
    In general usage a script will have a sequence of figure creation followed by a pyplot.show which
    effectively blocks and leaves the figures open for the user.
    We suspect this blocking is because the mainloop thread of the GUI is not setDaemon and thus halts
    python termination.
    To simulate this we create a non daemon dummy thread and instruct the user to use Ctrl-C to finish...
    """
    Gcf.get_active().canvas.draw()
     # update the current figure
     # open the browser with the current active figure shown...
    if not _test:
        try:
            webbrowser.open_new_tab(h5m.url + "/" + str(layout))
        except:
            print "Failed to open figure page in your browser. Please browse to " + h5m.url + "/" + str(Gcf.get_active().canvas.figure.number)
    if block and not _test:
        print "Showing figures. Hit Ctrl-C to finish script and close figures..."
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print "Shutting down..."

def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    # if a main-level app must be created, this is the usual place to
    # do it -- see backend_wx, backend_wxagg and backend_tkagg for
    # examples.  Not all GUIs require explicit instantiation of a
    # main-level app (egg backend_gtk, backend_gtkagg) for pylab
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    canvas = FigureCanvasH5Canvas(thisFig)
    manager = FigureManagerH5Canvas(canvas, num)
    #print "New figure created..."
    thisFig.__dict__['show'] = canvas.draw
    thisFig.__dict__['close'] = canvas.close
    thisFig.__dict__['show_browser'] = canvas.show_browser
     # provide a show that is basically just a canvas refresh...
    return manager


class FigureCanvasH5Canvas(FigureCanvasBase):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc...

    Public attribute

      figure - A Figure instance

    Note GUI templates will want to connect events for button presses,
    mouse movements and key presses to functions that call the base
    class methods button_press_event, button_release_event,
    motion_notify_event, key_press_event, and key_release_event.  See,
    eg backend_gtk.py, backend_wx.py and backend_tkagg.py
    """

    def __init__(self, figure):
        FigureCanvasBase.__init__(self, figure)
        #print "Init of Canvas called....",figure
        self.frame_count = 0
        self._server_port = new_web_port()
        self._request_handlers = {}
        self._frame = None
        self._header = ""
        self._home_x = {}
        self._home_y = {}
        self._zoomed = False
        self._first_frame = True
        self._width, self._height = self.get_width_height()
        self.flip = Affine2D().scale(1, -1).translate(0, self._height)
        #print "Figure Width:",self._width,",Height:",self._height
        if not _quiet: print "Creating canvas web server on port %i" % self._server_port
        try:
            self._server = simple_server.WebSocketServer(('', self._server_port), self.web_socket_transfer_data, simple_server.WebSocketRequestHandler)
            self._thread = thread.start_new_thread(self._server.serve_forever, ())
            register_web_server(self._server_port, self)
        except Exception, e:
            print "Failed to create webserver. (%s)" % str(e)
            sys.exit(1)

    def register_request_handler(self, request):
        self._request_handlers[request] = request.connection.remote_addr[0]
         # if we have a lurking frame, send it on
        if self._frame is not None:
            self.send_frame(self._header + self._frame_extra)

    def parse_web_cmd(self, s):
        action = s[1:s.find(" ")]
        args = s[s.find("args='")+6:-2].split(",")
        method = getattr(self, "handle_%s" % action)
        if method:
            method(*args)
        else:
            print "Cannot find request method handle_%s" % action

    def show_browser(self):
        self.draw()
        webbrowser.open_new_tab(h5m.url + "/" + str(self.figure.number))

    def handle_click(self, x, y, button):
        self.button_release_event(float(x),float(y),int(button))
        self.button_press_event(float(x), float(y), int(button))
         # currently we do not distinguish between press and release on the javascript side. So call both :)

    def handle_resize(self, width, height):
        width_in = float(width) / self.figure.dpi
        height_in = float(height) / self.figure.dpi
        self.figure.set_size_inches(width_in, height_in)
        self.draw()
         # set the figure and force a redraw...

    def handle_close(self, *args):
        self.figure.close()
        self._stop_server()

    def handle_home(self, *args):
         # reset the plot to it's home coordinates
        for i in self._home_x.keys():
            self.figure.axes[i].set_xlim(self._home_x[i][0], self._home_x[i][1])
            self.figure.axes[i].set_ylim(self._home_y[i][0], self._home_y[i][1])
        self._zoomed = False
        self.draw()

    def handle_zoom(self, ax, x0, y0, x1, y1):
         # these coordinates should be the bottom left and top right of the zoom bounding box
         # in figure pixels..
        ax = int(ax)
        if not self._zoomed:
            self._home_x[ax] = self.figure.axes[ax].get_xlim()
            self._home_y[ax] = self.figure.axes[ax].get_ylim()
        self._zoomed = True
        inverse = self.figure.axes[ax].transData.inverted()
        lastx, lasty = inverse.transform_point((float(x0), float(y0)))
        x, y = inverse.transform_point((float(x1), float(y1)))
        x0, y0, x1, y1 = self.figure.axes[ax].viewLim.frozen().extents

        Xmin,Xmax=self.figure.axes[ax].get_xlim()
        Ymin,Ymax=self.figure.axes[ax].get_ylim()
        twinx, twiny = False, False
         # need to figure out how to detect twin axis here TODO

        if twinx:
            x0, x1 = Xmin, Xmax
        else:
            if Xmin < Xmax:
                if x<lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 < Xmin: x0=Xmin
                if x1 > Xmax: x1=Xmax
            else:
                if x>lastx:  x0, x1 = x, lastx
                else: x0, x1 = lastx, x
                if x0 > Xmin: x0=Xmin
                if x1 < Xmax: x1=Xmax

        if twiny:
            y0, y1 = Ymin, Ymax
        else:
            if Ymin < Ymax:
                if y<lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 < Ymin: y0=Ymin
                if y1 > Ymax: y1=Ymax
            else:
                if y>lasty:  y0, y1 = y, lasty
                else: y0, y1 = lasty, y
                if y0 > Ymin: y0=Ymin
                if y1 < Ymax: y1=Ymax
        self.figure.axes[ax].set_xlim((x0, x1))
        self.figure.axes[ax].set_ylim((y0, y1))
        print "Set limits to ",(x0, x1),",",(y0, y1)
        self.draw()

    def deregister_request_handler(self, request):
        del self._request_handlers[request]

    def web_socket_transfer_data(self, request):
        self.register_request_handler(request)
        while True:
            try:
                line = msgutil.receive_message(request).encode('utf-8')
                self.parse_web_cmd(line)
                #msgutil.send_message(request, str(_figure_ports.keys())[1:-1].decode('utf-8'))
                #msgutil.send_message(request, _frame.decode('utf-8'))
            except Exception, e:
                #print "\nCaught exception. Removing registered handler",e
                self.deregister_request_handler(request)
                return

    def close(self):
        self._stop_server()

    def _stop_server(self):
        if not _quiet: print "Stopping canvas web server..."
        self._server.shutdown()
        deregister_web_server(self._server_port)

    def draw(self, ctx_override='c', *args, **kwargs):
        """
        Draw the figure using the renderer
        """
        ts = time.time()
        width, height = self.get_width_height()
        ctx = H5Frame(context_name=ctx_override)
         # the context to write the js in...
        renderer = RendererH5Canvas(width, height, ctx, dpi=self.figure.dpi)
        ctx.write_extra("resize_canvas(id," + str(width) + "," + str(height) + ");")
        ctx.write_extra("native_w[id] = " + str(width) + ";")
        ctx.write_extra("native_h[id] = " + str(height) + ";")
        #ctx.write("// Drawing frame " + str(self.frame_count))
        #ctx.write(ctx_override + ".width = " + ctx_override + ".width;")
         # clear the canvas...  
        t = time.time()
        self.figure.draw(renderer)
        if _metrics:
            print "Render took %s s" % (time.time() - t)
            print "Path time: %s, Text time: %s, Marker time: %s, Sub time: %s" % (renderer._path_time, renderer._text_time, renderer._marker_time, renderer._sub_time)
        self.frame_count+=1
        for i,ax in enumerate(self.figure.axes):
            corners = self.flip.transform(ax.bbox.corners())
            bb_str = ""
            for corner in corners: bb_str += str(corner[0]) + "," + str(corner[1]) + ","
            ctx.add_header("ax_bb[" + str(i) + "] = [" + bb_str[:-1] + "];")
        if renderer._image_count > 0:
            ctx.add_header("var im_left_to_load_%s = %i;" % (ctx._context_name, renderer._image_count), start=True)
        else:
            ctx.add_header("frame_body_%s();" % ctx._context_name)
             # if no image we can draw the frame body immediately..
        self._header = ctx.get_header()
        self._frame = ctx.get_frame()
        self._frame_extra = ctx.get_frame_extra()
         # additional script commands needed for handling functions other than drawing
        self._width, self._height = self.get_width_height()
         # redo my height and width...
        self.send_frame(self._header + self._frame_extra)
         # if we have a frame ready, send it on...
        if self._first_frame:
            h5m.tell()
            self._first_frame = False
        if _metrics: print "Overall draw took %s s, with %i clipcount" % ((time.time() - ts), renderer._clip_count)

    def send_frame(self, frame):
        recipients = ""
        for r in self._request_handlers.keys():
            try:
                recipients += str(r.connection.remote_addr[0]) + " "
                msgutil.send_message(r, frame.decode('utf-8'))
            except AttributeError:
                 # connection has gone
                print "Connection",r.connection.remote_addr[0],"has gone. Closing..."
            except Exception, e:
                print "Failed to send message",e

    def show(self):
        print "Show called... Not implemented in this function..."

    # You should provide a print_xxx function for every file format
    # you can write.

    # If the file type is not in the base set of filetypes,
    # you should add it to the class-scope filetypes dictionary as follows:
    filetypes = {'js': 'HTML5 Canvas'}

    def print_js(self, filename, *args, **kwargs):
        print "Print js called with args",args,"and **kwargs",kwargs
        width, height = self.get_width_height()
        writer = open(filename, 'w')
        renderer = RendererH5Canvas(width, height, writer, dpi=self.figure.dpi)
        self.figure.draw(renderer)

    def get_default_filetype(self):
        return 'js'

    def print_foo(self, filename, *args, **kwargs):
        """
        Write out format foo.  The dpi, facecolor and edgecolor are restored
        to their original values after this call, so you don't need to
        save and restore them.
        """
        pass

class FigureManagerH5Canvas(FigureManagerBase):
    """
    Wrap everything up into a window for the pylab interface

    For non interactive backends, the base class does all the work
    """
    def __init__(self, canvas, num):
        self.canvas = canvas
        FigureManagerBase.__init__(self, canvas, num)
        #print "Called init on figure manager",canvas,num

    def destroy(self, *args):
        self.canvas._stop_server()
        if not _quiet: print "Destroy called on figure manager",args

    def show(self):
        print "Show called for figure manager"

########################################################################
#
# Now just provide the standard names that backend.__init__ is expecting
#
########################################################################


FigureManager = FigureManagerH5Canvas

