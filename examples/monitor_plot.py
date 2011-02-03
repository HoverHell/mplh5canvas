#!/usr/bin/python

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

"""Plot embedded in HTML wrapper with custom user events...
"""

sensor_list = ['enviro.wind_speed','enviro.wind_direction','enviro.ambient_temperature','enviro.humidity']

def user_event(figure_id, *args):
    f = figure(int(figure_id)+1)
     # make the specified figure active for the rest of the calls in this method
    sensors = args[:-1]
    clf()
    xlabel('time (s)')
    ylabel('value')
    count = 1
    for sensor in sensors:
        t = arange(0, 100, 1)
        s = sin(count*pi*t/10) * 10
        plot(t,s,linewidth=1.0,label=sensor)
        count+=0.5
    legend()
    f.canvas.draw()

# show a plot
title('No sensors selected')
f = gcf()
ax = gca()

# some sensors
sensor_select = "".join(['<option value="'+x+'">'+x+'</option>' for x in sensor_list])

# setup custom events and html wrapper
f.canvas._user_event = user_event
html_wrap_file = open("./examples/monitor_plot.html")
cc = html_wrap_file.read().replace("<!--sensor-list-->",sensor_select)
f.canvas._custom_content = cc
html_wrap_file.close()
f.canvas.draw()

show(layout='figure1')
