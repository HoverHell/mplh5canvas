#!/usr/bin/python
"""Plots of two different sizes!"""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

t = arange(0.0, 2.0, 0.01)
s = sin(2*pi*t)
f = figure(figsize=(10,6))
ax = f.gca()
ax.plot(t, s, linewidth=1.0)
ax.set_xlabel('time (s)')
ax.set_ylabel('voltage (mV)')
ax.set_title('Frist Post')
count = 0
f.show()

f2 = figure(figsize=(12,4))
ax2 = f2.gca()
ax2.set_xlabel('IMDB rating')
ax2.set_ylabel('South African Connections')
ax2.set_title('Luds chart...')
ax2.plot(arange(0.0, 5 + count, 0.01), arange(0.0, 5 + count, 0.01))

show()
