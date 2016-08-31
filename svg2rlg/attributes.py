# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import re
import logging
from reportlab.lib import colors, units

from . import utils

_logger = logging.getLogger(__name__)


def find(node, name):
    """
    Search an attribute with some name in some node or above.

    First the node is searched, then its style attribute, then
    the search continues in the node's parent node. If no such
    attribute is found, '' is returned.
    """

    # This needs also to lookup values like "url(#SomeName)"...

    try:
        value = node.getAttribute(name)
    except:
        return ''

    if value and value != "inherit":
        return value
    elif node.getAttribute("style"):
        attrs = utils.parse_multi_attribute_string(node.getAttribute("style"))
        if name in attrs:
            return attrs[name]
    else:
        if node.parentNode:
            return find(node.parentNode, name)

    return ''


def identity(value):
    """
    Null transform, returns the same value sent
    """

    return value


def convert_transform(value):
    """
    Parse transform attribute string.

    E.g. "scale(2) translate(10,20)"
         -> [("scale", 2), ("translate", (10,20))]
    """

    line = utils.enc(value).strip()
    ops = line[:]
    brackets = [i for i, c in enumerate(line) if c in '()']
    indices = []

    for bi, bj in utils.pairwise(brackets):
        subline = line[bi + 1:bj].strip().replace(',', ' ')
        subline = re.sub("[ ]+", ',', subline)
        indices.append(eval(subline))
        ops = ops[:bi] + ' ' * (bj - bi + 1) + ops[bj + 1:]

    ops = ops.split()

    assert len(ops) == len(indices)

    return list(zip(ops, indices))


def convert_length(svg_attr, percent_of=100):
    """
    Convert length to points
    """

    text = svg_attr
    if not text:
        return 0.0

    if text[-1] == '%':
        _logger.debug("Fiddling length unit: %")
        return float(text[:-1]) / 100 * percent_of
    elif text[-2:] == "pc":
        return float(text[:-2]) * units.pica

    new_size = text[:]
    for u in "em ex px".split():
        if new_size.find(u) >= 0:
            _logger.debug("Ignoring unit: %s" % u)
            new_size = new_size.replace(u, '')

    new_size = new_size.strip()
    length = units.toLength(new_size)

    return length


def convert_length_list(value):
    """
    Convert a list of comma or space separated lengths
    """
    return [convert_length(v) for v in value.replace(',', ' ').split()]  # split ignores empty elements this way


def convert_opacity(value):
    return float(value)


def convert_color(value):
    """
    Convert string to a RL color object.
    """

    # fix it: most likely all "web colors" are allowed
    predefined = "aqua black blue fuchsia gray green lime maroon navy "
    predefined += "olive orange purple red silver teal white yellow "
    predefined += "lawngreen indianred aquamarine lightgreen brown"

    # This needs also to lookup values like "url(#SomeName)"...

    text = value
    if not text or text == "none":
        return None

    text = utils.enc(text)

    if text in predefined.split():
        return getattr(colors, text)
    elif text == "currentColor":
        return "currentColor"
    elif len(text) == 7 and text[0] == '#':
        return colors.HexColor(text)
    elif len(text) == 4 and text[0] == '#':
        return colors.HexColor('#%s%s%s' % (text[1] * 2, text[2] * 2, text[3] * 2))
    elif text[:3] == "rgb" and text.find('%') < 0:
        t = text[:][3:]
        t = t.replace('%', '')
        tup = eval(t)
        tup = tuple(map(lambda h: h[2:], map(hex, tup)))
        tup = tuple(map(lambda h: (2 - len(h)) * '0' + h, tup))
        col = "#%s%s%s" % tup
        return colors.HexColor(col)
    elif text[:3] == 'rgb' and text.find('%') >= 0:
        t = text[:][3:]
        t = t.replace('%', '')
        tup = eval(t)
        tup = tuple(map(lambda c: c / 100.0, tup))
        c = colors.Color(*tup)
        return c

    _logger.debug("Can't handle color: %s" % text)

    return None


def convert_line_join(value):
    return {"miter": 0, "round": 1, "bevel": 2}[value]


def convert_line_cap(value):
    return {"butt": 0, "round": 1, "square": 2}[value]


def convert_dash_array(value):
    stroke_dash_array = convert_length_list(value)
    return stroke_dash_array


def convert_dash_offset(value):
    stroke_dash_offset = convert_length(value)
    return stroke_dash_offset


def convert_font_family(value):
    # very hackish
    font_mapping = {
        "sans-serif": "Helvetica",
        "serif": "Times-Roman",
        "monospace": "Courier",
    }
    font_name = value
    if not font_name:
        return ''
    try:
        font_name = font_mapping[font_name]
    except KeyError:
        pass
    if font_name not in ("Helvetica", "Times-Roman", "Courier"):
        font_name = "Helvetica"

    return font_name
