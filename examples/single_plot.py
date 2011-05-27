#!/usr/bin/python
"""Simple static plot, mostly for testing zooming..."""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time


t = arange(0, 100, 1)
s = sin(2*pi*t/10) * 10
plot(t, s, linewidth=1.0)
xlabel('time (s)')
ylabel('voltage (mV)')
title('Frist Post')
f = gcf()
show()
