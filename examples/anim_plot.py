#!/usr/bin/python

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

"""This script serves as a testbed for the animatable functionality of the backend.
It basically produces an long series of frames that get animated on the client browser side.
"""

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

show(block=False)
 # show the figure manager but don't block script execution so animation works..
while True:
    refresh_data(ax)
    f.canvas.draw()
    count += 0.01
    time.sleep(0.5)
