# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import os
from reportlab.pdfbase import pdfmetrics, ttfonts

FONT_ALIASES = {
    "sans-serif": "Helvetica",
    "serif": "Times-Roman",
    "monospace": "Courier",
}

DEFAULT_FONT = 'Helvetica'

__all__ = [
    'FONT_ALIASES',
    'DEFAULT_FONT',
]
