#!/usr/bin/python
"""Plot embedded in HTML wrapper with custom user events..."""

import matplotlib
matplotlib.use('module://mplh5canvas.backend_h5canvas')
from pylab import *
import time

sensor_list = ['enviro.wind_speed','enviro.wind_direction','enviro.ambient_temperature','enviro.humidity']

def user_cmd_ret(*args):
    """Handle any data returned from calls to canvas.send_cmd()"""
    print "Got return from user event:",args

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
    f.canvas.send_cmd("alert('Server says: Plot updated...'); document.documentURI;")
     # send a command back to the browser on completion of the event
     # output of this command (in this case the documentURI is returned to the server if user_cmd_ret is set

# show a plot
title('No sensors selected')
f = gcf()
ax = gca()

# some sensors
sensor_select = "".join(['<option value="'+x+'">'+x+'</option>' for x in sensor_list])

f.canvas._user_event = user_event
 # register handler for client side javascript calls to user_event

f.canvas._user_cmd_ret = user_cmd_ret
 # register handler for any returns from send_cmd

html_wrap_file = open("./examples/monitor_plot.html")
cc = html_wrap_file.read().replace("<!--sensor-list-->",sensor_select)
 # read in a custom HTML wrapper and populate dynamic content

f.canvas._custom_content = cc
 # specify a custom HTML wrapper to use in place of default (thumbnail view)

html_wrap_file.close()
f.canvas.draw()

show(layout='figure1')
