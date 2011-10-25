#!/usr/bin/env python
from setuptools import setup, find_packages
from distutils.version import LooseVersion
from matplotlib import __version__ as mpl_version
import sys
import os.path

if LooseVersion(mpl_version) < LooseVersion("0.99.1.1"):
    print "The HTML5 Canvas Backend requires matplotlib 0.99.1.1 or newer. " \
          "Your version (%s) appears older than this. Unable to continue..." % (mpl_version,)
    sys.exit(0)

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
INSTALL = open(os.path.join(here, 'INSTALL.rst')).read()

setup (
    name="mplh5canvas",
    version="0.6",
    author="Simon Ratcliffe, Ludwig Schwardt",
    author_email="sratcliffe@ska.ac.za, ludwig@ska.ac.za",
    url="http://code.google.com/p/mplh5canvas/",
    description="A matplotlib backend based on HTML5 Canvas.",
    long_description=README + "\n\n" + INSTALL,
    license="BSD",
    classifiers=["Environment :: Console",
                 "Intended Audience :: Developers",
                 "Intended Audience :: End Users/Desktop",
                 "License :: OSI Approved :: BSD License",
                 "Operating System :: OS Independent",
                 "Programming Language :: Python :: 2",
                 "Topic :: Software Development :: Libraries :: Python Modules",
                ],
    packages = find_packages(),
    scripts = [],
    install_requires = ['mod_pywebsocket'],
    zip_safe = False,
)
