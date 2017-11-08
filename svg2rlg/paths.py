# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import copy
import logging

from reportlab.graphics.shapes import Path

_logger = logging.getLogger(__name__)


class NoStrokePath(Path):
    """
    This path object never gets a stroke width whatever the properties it's
    getting assigned.
    """

    def __init__(self, *args, **kwargs):
        copy_from = kwargs.pop(b'copy_from', None)
        Path.__init__(self, *args, **kwargs)  # we're old-style class on PY2
        if copy_from:
            self.__dict__.update(copy.deepcopy(copy_from.__dict__))

    def getProperties(self, *args, **kwargs):
        # __getattribute__ wouldn't suit, as RL is directly accessing self.__dict__
        props = Path.getProperties(self, *args, **kwargs)
        if 'strokeWidth' in props:
            props['strokeWidth'] = 0
        if 'strokeColor' in props:
            props['strokeColor'] = None
        return props


class ClippingPath(Path):
    """
    Should clip the contents, but doesn't right now
    """

    def __init__(self, *args, **kwargs):
        copy_from = kwargs.pop(b'copy_from', None)
        Path.__init__(self, *args, **kwargs)
        if copy_from:
            self.__dict__.update(copy.deepcopy(copy_from.__dict__))
        self.isClipPath = 1

    def getProperties(self, *args, **kwargs):
        props = Path.getProperties(self, *args, **kwargs)
        if 'fillColor' in props:
            props['fillColor'] = None
        return props
