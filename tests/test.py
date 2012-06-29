#!/usr/bin/python

# The MPLH5Canvas test suite.
#
# Basically this runs against a directory of matplotlib examples (try examples/api or examples/pylab in the matplotlib source tree)
# and produces a test.html file in ./output that when shown in a browser displays a MPLH5Canvas, PNG and SVG rendering for each
# example in the test set.
#
# This allows rapid fault finding through direct comparisons with known good backends...

from optparse import OptionParser
import os
import sys

parser = OptionParser()
parser.add_option("-d", "--dir", type="string", default=".",help="Specify the directory containing examples to be tested. [default=%default]")
parser.add_option("-f", "--file", type="string", default=None, help="Specify a single file to test. Overrides any directory specified. [default=%default]")
parser.add_option("-w","--wildcard", type="string", default="*", help="Match the filenames to use. e.g. * for all, image_ for all image demos. [default=%default]")
parser.add_option("-c", "--crash", action="store_true", default=False, help="Do not catch script exceptions. [default=%default]")
(options, args) = parser.parse_args()

# Matplotlib examples that should be excluded as they bork things.
exclusions = [# mpl_examples/pylab_examples
              '__init__.py', 'customize_rc.py', 'to_numeric.py',
              'dannys_example.py', # uses TeX - which borks matplotlib if you don't have TeX installed
              'demo_tight_layout.py', # expects Canvas.get_renderer method, then falls back to Agg backend at very inopportune moment
              'hexbin_demo.py', 'hexbin_demo2.py', # seems to create an infinite length polygon...
              'pcolor_demo.py', 'pcolor_log.py', # what the heck is this rubbish. imshow ftw...
              'scatter_profile.py','quadmesh_demo.py', # very slow for now
              'tex_unicode_demo.py','tex_demo.py', # uses TeX
              'usetex_fonteffects.py','usetex_demo.py','usetex_baseline_test.py', # uses TeX
             ]

files = []
p = os.listdir(options.dir+"/")
if options.wildcard == "*": options.wildcard = ""
while p:
    x = p.pop()
    if x != sys.argv[0] and x.endswith(".py") and x not in exclusions and x.startswith(options.wildcard):
        files.append(x)

if options.file:
    options.dir = options.file[:options.file.rfind("/")]
    files = [options.file[options.file.rfind("/")+1:]]
    print "Dir:",options.dir,",Files:",files

if files == []:
    print "No .py files found in the specified directory (%s)" % options.dir
    sys.exit(0)

import matplotlib
import mplh5canvas.backend_h5canvas

mplh5canvas.backend_h5canvas._test = True
mplh5canvas.backend_h5canvas._quiet = True
# The 'use' command has to happen *before* pylab is touched 
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import savefig, gcf, switch_backend

html = "<html><head><script>function resize_canvas(id, w, h) { } var id=-1; var ax_bb = new Array(); var native_w = new Array(); var native_h = new Array();</script></head><body><table>"
html += "<tr><th>File<th>H5 Canvas<th>PNG<th>SVG</tr>"
thtml = "<html><head><body><table><tr><th>File<th>H5 Canvas (PNG from Chrome 4.0 OSX)<th>PNG</tr>"
files.sort()
for count, filename in enumerate(files):
    print "Running %s\n" % filename
    html += "<tr><th id='name_" + str(count) + "'>" + filename
    thtml += "<tr><th id='name_" + str(count) + "'>" + filename
    try:
        execfile(options.dir + "/" + filename)
        f = gcf()
        f.canvas.draw()
    except Exception, e:
        print "Failed to run script %s. (%s)" % (filename, str(e))
        html += "<td>Failed to execute script.<td>Failed to execute script.<td>Failed to execute script.</tr>"
        thtml += "<td>Failed to execute script.<td>Failed to execute script.<td>Failed to execute script.</tr>"
        if options.crash:
            raise
        else:
            continue
    f = gcf()
    f.canvas.draw(ctx_override="c_" + str(count))
    w, h = f.get_size_inches() * f.get_dpi()
    png_filename = filename[:-2] + "png"
    try:
        html += "<td><canvas width='%dpx' height='%dpx' id='canvas_%d'>" % (w, h, count,)
        html += "\n<script>var c_%d = document.getElementById('canvas_%d').getContext('2d');\n" % (count, count)
        html += f.canvas._frame_extra + "\n" + f.canvas._header + "\n" + f.canvas._frame
        html += "\nframe_header();\n"
        html += "\n</script></canvas>"
        thtml += "<td><img src='%s' width='%dpx' height='%dpx' />" % ("h5canvas_" + png_filename, w, h)
    except Exception, e:
        print "Failed to create Canvas for %s. (%s)" % (filename, str(e))
        html += "<td>Failed to create Canvas"
        thtml += "<td>Failed to create Canvas"
        if options.crash:
            raise

    try:
        f.canvas.print_png("./output/" + png_filename, dpi=f.dpi)
        html += "<td><img src='%s' width='%dpx' height='%dpx' />" % (png_filename, w, h)
        thtml += "<td><img src='%s' width='%dpx' height='%dpx' />" % (png_filename, w, h)
    except Exception, e:
        print "Failed to create PNG for %s. (%s)" % (filename, str(e))
        html += "<td>Failed to create PNG"
        thtml += "<td>Failed to create PNG"
        if options.crash:
            raise

    try:
        svg_filename = filename[:-2] + "svg"
        f.canvas.print_svg("./output/" + svg_filename, dpi=f.dpi)
        html += "<td><img src='%s' width='%dpx' height='%dpx' />" % (svg_filename, w, h)
    except Exception, e:
        print "Failed to create SVG for %s. (%s)" % (filename, str(e))
        html += "<td>Failed to create SVG"
        if options.crash:
            raise
    switch_backend('module://mplh5canvas.backend_h5canvas')
    html += "</tr>"
    thtml += "</tr>"

print "Finished processing files..."
html += "</table><script> var total_plots = " + str(count) + "; "
pi = """
function connect() {
  s = new WebSocket("ws://192.168.184.1:8123");
}

function put_images() {
  for (var i=0; i<total_plots+1;i++) { 
   try {
   s.send(document.getElementById("name_"+i).innerText.split(".py")[0] + ".png " + document.getElementById("canvas_"+i).toDataURL());
   } catch (err) {}
 }
}"""
html += pi +"</script><input type='button' onclick='put_images()' value='Put Images to server'>"
html += "<input type='button' onclick='connect()' value='Connect'></body></html>"
thtml += "</table></body></html>"
f = open("output/test.html","w")
f.write(html)
f.close()
f = open("output/test_rendered.html","w")
f.write(thtml)
f.close()
