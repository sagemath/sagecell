#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

from distribute_setup import use_setuptools; use_setuptools()
from setuptools import setup, find_packages


rel_file = lambda *args: os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)

def read_from(filename):
    fp = open(filename)
    try:
        return fp.read()
    finally:
        fp.close()

def get_version():
    data = read_from(rel_file('src', 'cssmin.py'))
    return re.search(r"__version__ = '([^']+)'", data).group(1)


setup(
    name             = 'cssmin',
    version          = get_version(),
    author           = "Zachary Voase",
    author_email     = "zacharyvoase@me.com",
    url              = 'http://github.com/zacharyvoase/cssmin',
    description      = "A Python port of the YUI CSS compression algorithm.",
    py_modules       = ['cssmin'],
    package_dir      = {'': 'src'},
    entry_points     = {'console_scripts': ['cssmin = cssmin:main']},
)
