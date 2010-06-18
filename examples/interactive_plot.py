#!/usr/bin/python

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

"""Test of interactive features.
"""

def onclick(ev):
    print "Received click. X: %i, Y: %i" % (ev.x, ev.y)
    if ev.inaxes is not None:
        print "Data X: %f, Data Y: %f" % (ev.xdata, ev.ydata)
    else:
        print "Click was not over active axes."

t = arange(0, 100, 1)
s = sin(2*pi*t/10) * 10
plot(t, s, linewidth=1.0)
xlabel('time (s)')
ylabel('voltage (mV)')
title('Frist Post')
f = gcf()
f.canvas.mpl_connect('button_release_event',onclick)

next_target_button = matplotlib.widgets.Button(axes([0.1, 0.05, 0.06, 0.04]), 'Next')
def next_target_callback(event):
    print "Next was called..."
next_target_button.on_clicked(next_target_callback)

show()
