#!/usr/bin/env python

from setuptools import setup, find_packages

long_desc = '''
This package contains the sage cell server Sphinx extension.

The extension defines a directive, "sagecellserver", for embedding sage cell.
'''

requires = ['Sphinx>=0.6', 'setuptools']


setup(name='icsecontrib-sagecellserver',
      version='1.1',
      description='Sphinx sagecellserver extension',
      author='Krzysztof Kajda',
      author_email='kajda.krzysztof@gmail.com',
      packages=find_packages(),
      include_package_data=True,
      install_requires=requires,
      namespace_packages=['icsecontrib'],
     )
