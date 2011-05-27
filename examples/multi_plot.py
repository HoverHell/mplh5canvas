#!/usr/bin/python
"""Testbed for the animation functionality of the backend, with multiple figures.

It basically produces an long series of frames that get animated on the client
browser side, this time with two figures.

"""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

def refresh_data(ax):
    t = arange(0.0 + count, 2.0 + count, 0.01)
    s = sin(2*pi*t)
    ax.lines[0].set_xdata(t)
    ax.lines[0].set_ydata(s)
    ax.set_xlim(t[0],t[-1])

t = arange(0.0, 2.0, 0.01)
s = sin(2*pi*t)
plot(t, s, linewidth=1.0)
xlabel('time (s)')
ylabel('voltage (mV)')
title('Frist Post')
f = gcf()
ax = f.gca()
count = 0

f2 = figure()
ax2 = f2.gca()
ax2.set_xlabel('IMDB rating')
ax2.set_ylabel('South African Connections')
ax2.set_title('Luds chart...')
ax2.plot(arange(0.0, 5 + count, 0.01), arange(0.0, 5 + count, 0.01))

show(block=False, layout=2)
 # show the figure manager but don't block script execution so animation works..
 # layout=2 overrides the default layout manager which only shows a single plot in the browser window

while True:
    refresh_data(ax)
    d = arange(0.0, 5 + count, 0.01)
    ax2.lines[0].set_xdata(d)
    ax2.lines[0].set_ydata(d)
    ax2.set_xlim(d[0],d[-1])
    ax2.set_ylim(d[0],d[-1])
    f.canvas.draw()
    f2.canvas.draw()
    count += 0.01
    time.sleep(1)
