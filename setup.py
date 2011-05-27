#!/usr/bin/env python
from setuptools import setup, find_packages
from matplotlib import __version__
import sys
import os.path

if tuple([int(x) for x in __version__.split(".")[:3]]) < (0, 99, 1):
    print "The HTML5 Canvas Backend requires matplotlib 0.99.1.1 or newer. Your version (%s) appears older than this. Unable to continue..." % __version__
    sys.exit(0)

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
INSTALL = open(os.path.join(here, 'INSTALL.rst')).read()

VERSION = "trunk"
DESCRIPTION = "A matplotlib backend based on HTML5 Canvas."
LONG_DESCRIPTION = README + "\n\n" + INSTALL
CLASSIFIERS = [
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

setup (
    name="mplh5canvas",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    author="Simon Ratcliffe, Ludwig Schwardt",
    author_email="sratcliffe@ska.ac.za, ludwig.schwardt@gmail.com",
    url="http://code.google.com/p/mplh5canvas/",
    license="BSD",
    packages = find_packages(),
    scripts = [],
    zip_safe = False,
)
