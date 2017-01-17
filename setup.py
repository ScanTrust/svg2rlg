# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

from setuptools import setup, find_packages
import glob
import os.path
import sys


def project_path(*names):
    return os.path.join(os.path.dirname(__file__), *names)


def read(path):
    if sys.version_info < (3,):
        f = open(path)
    else:
        f = open(path, encoding='UTF-8')
    text = f.read()
    f.close()
    return text


setup(
    name='svg2rlg',
    version='1.1.0',
    install_requires=[
        'reportlab>=3.0.0',
    ],
    author='ScanTrust, Sebastian Wehrmann, Dinu Gherman',
    author_email='andrew.backer@scantrust.com, sebastian.wehrmann@icloud.com, gherman@darwin.in-berlin.de',
    url='https://github.com/ScanTrust/svglib',
    packages=find_packages(include=('svg2rlg',)),
    keywords='',
    classifiers="""\
        Development Status :: 4 - Beta
        Environment :: Console
        Intended Audience :: Developers
        Natural Language :: English
        Operating System :: MacOS :: MacOS X
        Operating System :: Microsoft :: Windows
        Operating System :: POSIX
        Programming Language :: Python
        Programming Language :: Python :: 2.7
        Programming Language :: Python :: 3.4
        Programming Language :: Python :: 3.5
        Topic :: Documentation
        Topic :: Multimedia :: Graphics :: Graphics Conversion
        Topic :: Printing
        Topic :: Software Development :: Libraries :: Python Modules
        Topic :: Text Processing :: Markup :: XML
        Topic :: Utilities
"""[:-1].split('\n'),
    description="An experimental library for reading and converting SVG. Python 3 compatible.",
    long_description='\n\n'.join(read(project_path(name)) for name in (
        'README.txt',
        'CHANGES.txt'
    )),

    include_package_data=True,
    data_files=[('', glob.glob(project_path('*.txt')))],
    zip_safe=False,
)
