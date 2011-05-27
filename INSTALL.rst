Requirements
------------

We have tried to keep this module as free of dependencies as possible in order
to open up the widest possible installation base. It may, however, be more
practical to include some external dependencies in the future. For example, we
pull in and modify the excellent `pywebsocket`_ code for handling our browser
communications. As the standard emerges, it may be better to depend on this
directly.

The current base system requirements prior to installation are:

* Python 2.5 or newer (2.4 should also be OK, but has not been tested)
* `Matplotlib`_ 0.99.1.1 or newer

The web browser must support Canvas and WebSockets (see
http://caniuse.com/#feat=websockets for current support). The target browser is
Chrome 9.0+, while Safari 5.0+ is also supported. Opera 11.0+ and Firefox 4.0+
support WebSocket too, but it is disabled by default. It can be enabled by
browsing to the ``about:config`` page in Firefox and the ``opera:config`` page
in Opera, respectively. There is currently no support for Internet Explorer.

The code now supports both draft-75 and draft-76 websockets and so should be
reasonably future proof (until they change the standard again).

Netifaces
^^^^^^^^^

It is surprisingly difficult to make a good guess of the IP address of a user's
primary network interface across a range of operating systems. The code uses
``socket.gethostbyname`` by default, which does a reasonable job but is
completely borked if you have VMware installed.

If available it will use the `netifaces`_ module which generally does a better
job. It is recommended that you install this by running::

  easy_install netifaces

Installation
------------

Since this package is available on `PyPI`_ the simplest way to install it is to do::

  easy_install mplh5canvas

Alternatively, download the latest tarball or check out the source code from
Google Code and do::

  python setup.py install

It is assumed that you have the proper permissions to install Python packages on
your system (if not, you can make use of `virtualenv`_ instead).

Testing
-------

We provide a number of example scripts for initial testing. Surprisingly these
are found in the ``examples`` directory of the source code.

The script names are self-explanatory. The URL of the management server should be
printed out by the script, and if a web browser is installed and available a new
tab should be opened in your browser. If not, then just copy and paste the
management URL into a browser window.

Conformance Testing
^^^^^^^^^^^^^^^^^^^

To try and reach a level of reasonable conformance we have a crude test suite
that will run against a directory of matplotlib examples and produce a web page
for side-by-side comparison::

  cd tests
  python test.py -d <matplotlib source tree>/lib/mpl_examples/pylab_examples

This produces output files in the ``tests/output`` directory. The file ``test.html``
when viewed in a web browser will show the mplh5canvas implementation alongside a
PNG and SVG for each file in the target directory. 

Be aware that these test results can be pretty massive and may well lead to
browser instability. You can run on a restricted set of tests by using a wildcard
parameter (see ``test.py --help``).

There is also the option of rendering each canvas on the page to a PNG for easier
side-by-side comparison. To do this, run::

  python rec.py

once you have a completed test run. At the bottom of the test.html page click
the "Connect" button. Then click the "Put Images to Server" button.
The ``rec.py`` instance should indicate a variety of files being written to disk.
Then open the ``test_rendered.html`` page which will have a side-by-side column
of PNGs.

.. _pywebsocket: http://code.google.com/p/pywebsocket/
.. _Matplotlib: http://matplotlib.sourceforge.net/
.. _netifaces: http://alastairs-place.net/netifaces/
.. _PyPI: http://pypi.python.org/pypi/mplh5canvas
.. _virtualenv: http://pypi.python.org/pypi/virtualenv
