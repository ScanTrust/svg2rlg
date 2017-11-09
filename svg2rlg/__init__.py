# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

from svg2rlg.utils import monkeypatch_reportlab
from .api import data_to_rlg, file_to_rlg

__version__ = "1.2.2"
__license__ = "LGPL 3"
__author__ = "Dinu Gherman"
__date__ = "2017-11-08"

VERISON = __version__

__all__ = [
    'data_to_rlg',
    'file_to_rlg',
    'VERSION'
]

monkeypatch_reportlab()
