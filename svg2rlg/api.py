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

from . import utils, render
from lxml import etree

_logger = logging.getLogger(__name__)


def file_to_rlg(path_or_file):
    """
    Converts an SVG file to an RLG Drawing object.
    :rtype: reportlab.graphics.shapes.Drawing
    """

    data = utils.read_any(path_or_file)
    return data_to_rlg(data, file_path=path_or_file)


def data_to_rlg(data, file_path=None):
    """
    Converts a string representation of an xml svg document to a RLG Drawing object.
    :rtype: reportlab.graphics.shapes.Drawing
    """
    # noinspection PyUnresolvedReferences

    try:
        parser = etree.XMLParser(remove_comments=True, recover=True)
        svg = etree.fromstring(data, parser=parser)
    except Exception as exc:
        _logger.error("Failed to load input file! (%s)" % file_path)
        raise

    renderer = render.SvgRenderer(file_path=file_path)
    return renderer.render(svg)


def __minidom_parser():
    """
    This is the old minidom parser, which doesn't quite work yet
    since minidom doesn't support a lot of things like <use> resolution.
    If that is fixed, then we can bring this back and drop lxml
    """
    pass
    # renderer = SvgRenderer()
    # renderer.render_node(
    #     parseString(data).documentElement
    # )
    # return renderer.finish()
