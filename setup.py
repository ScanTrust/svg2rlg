# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import os.path
import sys

import re
from setuptools import setup, find_packages


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


install_requires = open('requirements.txt').read().strip().split()
v = sys.version_info
if (v.major, v.minor) < (2, 7):
    install_requires.append('argparse')


def get_version():
    """Parses the __version__ so we don't have to maintain in 2 locations"""
    for m in re.findall("__version__\s*=\s*\"(\d+.\d+.\d+)\"", read("svg2rlg/__init__.py")):
        return m


setup(
    name='svg2rlg',
    version=get_version(),
    install_requires=install_requires,
    author='Sebastian Wehrmann, Dinu Gherman, Deeplook, ScanTrust',
    author_email='sebastian.wehrmann@icloud.com, gherman@darwin.in-berlin.de, andrew.backer@scantrust.com',
    url='https://github.com/ScanTrust/svg2rlg',
    packages=find_packages(include=('svg2rlg',)),
    keywords='',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Documentation',
        'Topic :: Utilities',
        'Topic :: Printing',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: XML',
    ],
    description="An experimental library for reading and converting SVG. Python 3 compatible.",
    long_description=open('README.rst').read(),
    include_package_data=True,
    data_files=[
        ('svg2rlg', ['README.rst', 'CONTRIBUTORS.rst']),
    ],
    zip_safe=False,
)
