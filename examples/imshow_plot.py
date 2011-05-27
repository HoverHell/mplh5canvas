#!/usr/bin/python
"""Used for testing image show."""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

fig = figure()
ax = fig.add_subplot(111)
img = standard_normal((50,100))
image = ax.imshow(img,interpolation='nearest',animated=False,label="blah")
xlabel('time (s)')
ylabel('voltage (mV)')
title('Another test')
show(block=False)
 # show the figure manager but don't block script execution so animation works..
print "Animating... Ctrl-C to stop"
while True:
    img = standard_normal((50,100))
    image.set_data(img)
    fig.canvas.draw()
    time.sleep(0.1)
