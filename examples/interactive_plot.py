#!/usr/bin/python
"""Test of interactive features, including a button widget."""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

def onclick(ev):
    """Callback when mouse button is released."""
    print "Received click. X: %i, Y: %i" % (ev.x, ev.y)
    if ev.inaxes is not None:
        print "Data X: %f, Data Y: %f" % (ev.xdata, ev.ydata)
    else:
        print "Click was not over active axes."

def next_data(ax):
    """Shift data along x-axis."""
    t = ax.lines[0].get_xdata() + 0.2
    s = sin(2*pi*t)
    ax.lines[0].set_xdata(t)
    ax.lines[0].set_ydata(s)
    ax.set_xlim(t[0], t[-1])

t = arange(0.0, 2.0, 0.01)
s = sin(2*pi*t)
plot(t, s, linewidth=1.0)
xlabel('time (s)')
ylabel('voltage (mV)')
title('Interactive widgets')
f = gcf()
f.canvas.mpl_connect('button_release_event', onclick)
ax = f.gca()

next_target_button = matplotlib.widgets.Button(axes([0.1, 0.05, 0.06, 0.04]), 'Next')
def next_target_callback(event):
    next_data(ax)
    f.canvas.draw()
    print "Next was called..."
next_target_button.on_clicked(next_target_callback)

show()
