# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

from .api import data_to_rlg, file_to_rlg

__version__ = "1.1.2"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2010-03-01"

VERISON = __version__

__all__ = [
    'data_to_rlg',
    'file_to_rlg',
    'VERSION'
]
