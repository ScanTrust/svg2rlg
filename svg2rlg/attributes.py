# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import logging
import re

from reportlab.lib import colors, units
from reportlab.pdfgen.canvas import FILL_NON_ZERO, FILL_EVEN_ODD

from svg2rlg.utils import pad_list, enc, node_name
from . import utils, settings

_logger = logging.getLogger(__name__)


def find(node, name):
    """
    Search an attribute with some name in some node OR ABOVE.

    First the node is searched, then its style attribute, then
    the search continues in the node's parent node. If no such
    attribute is found, '' is returned.
    """

    # This needs also to lookup values like "url(#SomeName)"...
    attr_value = node.attrib.get(name, '').strip()

    if attr_value and attr_value != "inherit":
        return attr_value
    elif node.attrib.get("style"):
        styles = parse_multi_attribute_string(node.attrib.get("style"))
        if name in styles:
            return styles[name]
    elif node.getparent() is not None:
        # recursively search up the tree for the attribute
        return find(node.getparent(), name)

    return ''


def get_all(node):
    values = {}
    if node_name(node.getparent()) == 'g':
        values.update(get_all(node.getparent()))

    style = node.attrib.get("style")
    if style:
        values.update(parse_multi_attribute_string(style))

    for key, value in node.attrib.items():
        if key != "style":
            values[key] = value

    return values


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
        if ',' in subline:
            indices.append(tuple(float(num) for num in subline.split(',')))
        else:
            indices.append(float(subline))
        ops = ops[:bi] + ' ' * (bj - bi + 1) + ops[bj + 1:]

    ops = ops.replace(',', ' ').split()

    assert len(ops) == len(indices)

    return list(zip(ops, indices))


def convert_length(value, percent_of=100, em_base=12):
    """
    Convert length to points
    """

    text = value
    if not text:
        return 0.0

    if ' ' in text.replace(',', ' ').strip():
        _logger.debug("Only getting first value of %s" % text)
        text = text.replace(',', ' ').split()[0]

    if text[-1] == '%':
        _logger.debug("Fiddling length unit: %")
        return float(text[:-1]) / 100 * percent_of
    elif text[-2:] == "pc":
        return float(text[:-2]) * units.pica
    elif text.endswith("pt"):
        return float(text[:-2]) * 1.25
    elif text.endswith("em"):
        return float(text[:-2]) * em_base
    elif text.endswith("px"):
        return float(text[:-2])

    if "ex" in text:
        _logger.warn("Ignoring unit ex in '%s'" % value)
        text = text.replace("ex", '')

    text = text.strip()
    length = units.toLength(text)

    return length


def convert_length_list(value):
    """
    Convert a list of comma or space separated lengths
    """
    return [convert_length(v) for v in value.replace(',', ' ').split()]  # split ignores empty elements this way


def convert_opacity(value):
    return float(value)


def convert_fill_rule(value):
    return {
        'nonzero': FILL_NON_ZERO,
        'evenodd': FILL_EVEN_ODD,
    }.get(value, '')


def convert_color(value):
    """
    Convert string to a RL color object.
    :type value: str | unicode
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
        return getattr(colors, text)  # ??
    elif text == "currentColor":
        return "currentColor"
    elif len(text) == 7 and text[0] == '#':
        return colors.HexColor(text)
    elif len(text) == 4 and text[0] == '#':
        return colors.HexColor('#%s%s%s' % (text[1] * 2, text[2] * 2, text[3] * 2))
    elif text.startswith('rgb') and '%' not in text:
        t = text[3:].strip('()')
        hex_values = [hex(int(num))[2:] for num in t.split(',')]
        hex_values = [h.zfill(2) for h in hex_values]
        return colors.HexColor("#%s%s%s" % tuple(hex_values))
    elif text.startswith('rgb') and '%' in text:
        t = text[3:].replace('%', '').strip('()')
        tup = (int(val) / 100.0 for val in t.split(','))
        return colors.Color(*tup)

    _logger.debug("Can't handle color: %s" % text)

    return None


def convert_line_join(value):
    return {"miter": 0, "round": 1, "bevel": 2}[value]


def convert_line_cap(value):
    return {"butt": 0, "round": 1, "square": 2}[value]


def convert_dash_array(value):
    return convert_length_list(value)


def convert_dash_offset(value):
    return convert_length(value)


def convert_font_family(value):
    """
    Converts a font-family to a standard font name, or returns the value unmodified.  PDFs are
    expected to register their own font names, and the SVG must use this exact font name as well if it
    is to be recognized later.  Verifying these names is beyond the scope of this function.

    > f("Arial")        == "Arial"
    > f("'Arial-Bold'") == "Arial-Bold"
    > f("sans-serif")   == "Helvetica" (unless overidden in settings)
    > f("")             == "Helvetica" (unless overidden in settings)
    """
    # in svg-land, *Arial* is == 'Arial-Bold' (with the quotes)!
    # <text fill="#000000" font-family="'Arial-Bold'" font-size="14">My Bold!</text>
    if not value:
        return ''

    # try to get the mapping, in case they used a built-in shortcut (e.g. sans-serif)
    font_name = settings.FONT_MAP.get(value, value)

    # ensure that the font name is one of the valid names from the map
    if font_name not in settings.FONT_MAP.values():
        font_name = settings.DEFAULT_FONT

    return font_name


def parse_multi_attribute_string(line):
    """
    Parse an attribute string in the format "name:value;name2:value2;name3:value3..." into a dict
    """
    line = enc(line)
    pairs = [a.strip() for a in line.split(';') if a]
    pairs = [[e.strip() for e in a.split(':')] for a in pairs]
    return {k: v for k, v in pairs}
