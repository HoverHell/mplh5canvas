Matplotlib HTML5 Canvas Backend
===============================

This provides a web-delivered interactive matplotlib backend using HTML5
technologies including `WebSocket`_ and the `Canvas`_ element.

Our main goal is to have a backend that is consistent across multiple platforms,
has no installation dependencies, is easy and fast to animate, and retains
compatibility with current matplotlib usage scenarios.

Installation instructions can be found below or on the project's `Wiki`_ page.

Features
--------

- Pure Python with no installation dependencies (apart from matplotlib itself)
- Requires web browser with Canvas and WebSocket support (Chrome 4+ and Safari 5+
  works out of the box, Firefox 4+ and Opera 11+ works after enabling WebSockets
  in their preferences, but Internet Explorer is not supported)
- Designed with animation and interactivity in mind (resizable, zoomable,
  clickable regions, etc)
- Simple plots (e.g. a 2048-point line plot) can be animated at around 60 frames
  per second
- Allows proper remote access to plots
- Allows multiple concurrent access to plots
- Thumbnail window allows quick cycling between plots on a single page

Screenshot
----------

.. image:: http://mplh5canvas.googlecode.com/files/screenshot.png
   :height: 600px

.. _WebSocket: http://en.wikipedia.org/wiki/WebSockets
.. _Canvas: http://en.wikipedia.org/wiki/Canvas_element
.. _Wiki: http://code.google.com/p/mplh5canvas/wiki/Installation
