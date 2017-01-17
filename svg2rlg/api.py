# -*- coding: UTF-8 -*-
"""
Contains the PUBLIC api for svg2rlg.  This should be imported & reexported in __init__.py and the entire svg2rlg module
can be imported (or just one function)

>>> import svg2rlg
>>> svg2rlg.file_to_rlg(...)

or

>>> from svg2rlg import file_to_rlg

"""

from __future__ import print_function, absolute_import, unicode_literals

import logging
from xml.dom.minidom import parseString

from .render import SvgRenderer
from . import utils

_logger = logging.getLogger(__name__)


def file_to_rlg(path_or_file):
    """
    Converts an SVG file to an RLG Drawing object.
    :rtype: reportlab.graphics.shapes.Drawing
    """

    data = utils.read_any(path_or_file)
    return data_to_rlg(data)


def data_to_rlg(data):
    """
    Converts a string representation of an xml svg document to a RLG Drawing object.
    :rtype: reportlab.graphics.shapes.Drawing
    """

    renderer = SvgRenderer()
    renderer.render(
        parseString(data).documentElement
    )

    return renderer.finish()
