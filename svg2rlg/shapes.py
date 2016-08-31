# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import base64
import hashlib
import logging
import os
import re
from os.path import dirname
from xml.dom.minidom import Element

from reportlab.graphics.shapes import Line, Rect, Circle, Ellipse, Group, Polygon, PolyLine, String, Path, Image, Shape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from . import utils, attributes

_logger = logging.getLogger(__name__)

OP_MOVETO, OP_LINETO, OP_CURVETO, OP_CLOSEPATH = list(range(4))


# [
#   { code:'M', command:'moveto', x:3, y:7 },
#   { code:'L', command:'lineto', x:5, y:-6 },
#   { code:'L', command:'lineto', x:1, y:7 },
#   { code:'L', command:'lineto', x:100, y:-0.4 },
#   { code:'m', command:'moveto', relative:true, x:-10, y:10 },
#   { code:'l', command:'lineto', relative:true, x:10, y:0 },
#   { code:'V', command:'vertical lineto', y:27 },
#   { code:'V', command:'vertical lineto', y:89 },
#   { code:'H', command:'horizontal lineto', x:23 },
#   { code:'v', command:'vertical lineto', relative:true, y:10 },
#   { code:'h', command:'horizontal lineto', relative:true, x:10 },
#   { code:'C', command:'curveto',          x1:33,  y1:43, x2:38, y2:47, x:43, y:47 },
#   { code:'c', command:'curveto',          x1:0,   y1:5,  x2:5,  y2:10, x:10, y:10, relative:true },
#   { code:'S', command:'smooth curveto',   x2:63,  y2:67, x:63, y:67 },
#   { code:'s', command:'smooth curveto',   x2:-10, y2:10, x:10, y:10, relative:true },
#   { code:'Q', command:'quadratic curveto', x1:50, y1:50, x:73, y:57 },
#   { code:'q', command:'quadratic curveto', relative:true, x1:20, y1:-5, x:0, y:-10 },
#   { code:'T', command:'smooth quadratic curveto', x:70, y:40 },
#   { code:'t', command:'smooth quadratic curveto', relative:true, x:0, y:-15 },
#   { code:'A', command:'elliptical arc', rx:5, ry:5, xAxisRotation:45, largeArc:true, sweep:false, x:40, y:20 },
#   { code:'a', command:'elliptical arc', relative:true, rx:5, ry:5, xAxisRotation:20, largeArc:false, sweep:true, x:-10, y:-10 },
#   { code:'Z', command:'closepath' }
# ]


class ShapeConverter(object):
    """
    Converter from SVG shapes to RLG (ReportLab Graphics) shapes.
    """

    def __init__(self):
        self.svgSourceFile = ''

    def get_handled_shapes(self):
        """
        Determine a list of handled shape elements
        """
        keys = [getattr(self, i) for i in self.__class__.__dict__.keys()]
        keys = [k.__name__.lower() for k in keys if callable(k)]
        # this only works because all the things we are converting are only one word (convert_line, etc)
        # otherwise we would need to map convert camelCase for the svg internal names
        return [k[8:].lower() for k in keys if k.startswith("convert_")]

    def _get_length(self, node, attribute):
        return attributes.convert_length(node.getAttribute(attribute))

    def _length_attrs(self, node, *args):
        return tuple(self._get_length(node, v) for v in args)

    def _length_attrs_dict(self, node, *args):
        return {v: self._get_length(node, v) for v in args}

    def convert_line(self, node):
        return Line(
            *self._length_attrs(node, "x1", "y1", "x2", "y2")
        )

    def convert_rect(self, node):
        return Rect(
            *self._length_attrs(node, "x", "y", "width", "height"),
            **self._length_attrs_dict(node, "rx", "ry")
        )

    def convert_circle(self, node):
        return Circle(
            *self._length_attrs(node, "cx", "cy", "r")
        )

    def convert_ellipse(self, node):
        return Ellipse(
            *self._length_attrs(node, "cx", "cy", "rx", "ry")
        )

    def convert_polyline(self, node):
        points = attributes.convert_length_list(node.getAttribute("points"))

        # Need to use two shapes, because standard RLG polylines do not support filling...
        gr = Group()
        shape = Polygon(points)
        self.apply_style(shape, node)
        shape.strokeColor = None
        gr.add(shape)
        shape = PolyLine(points)
        self.apply_style(shape, node)
        gr.add(shape)

        return gr

    def convert_polygon(self, node):
        points = attributes.convert_length_list(node.getAttribute("points"))
        return Polygon(points)

    def convert_text_0(self, node):
        text = ''
        if node.firstChild.nodeValue:
            try:
                text = utils.enc(node.firstChild.nodeValue)
            except:
                text = "Unicode"

        x, y = (attributes.convert_length(node.getAttribute(v) or '0') for v in ['x', 'y'])
        shape = String(x, y, text)
        self.apply_style(shape, node)
        gr = Group()
        gr.add(shape)
        gr.scale(1, -1)
        gr.translate(0, -2 * y)

        return gr

    def convert_text(self, node):
        """
        Converts a <text> element
        :type node: Element
        """
        x, y = self._length_attrs(node, 'x', 'y')

        gr = Group()
        frags = []
        frag_lengths = []

        dx0, dy0 = 0, 0
        x1, y1 = 0, 0

        ff = attributes.convert_font_family(attributes.find(node, "font-family") or "Helvetica")
        fs = attributes.convert_length(attributes.find(node, "font-size") or "12")

        for c in node.childNodes:
            base_line_shift = 0

            if c.nodeType == c.TEXT_NODE:
                frags.append(c.nodeValue)
                try:
                    tx = ''.join(frags)
                except:
                    tx = ""

            elif c.nodeType == c.ELEMENT_NODE and c.nodeName == "tspan":
                frags.append(c.firstChild.nodeValue)
                tx = ''.join([chr(ord(f)) for f in frags[-1]])
                y1, dx, dy = self._length_attrs(node, 'y', 'dx', 'dy')
                dx0 = dx0 + dx
                dy0 = dy0 + dy
                base_line_shift = node.getAttribute("baseline-shift") or "0"

                if base_line_shift in ("sub", "super", "baseline"):
                    base_line_shift = {"sub": -fs / 2, "super": fs / 2, "baseline": 0}[base_line_shift]
                else:
                    base_line_shift = attributes.convert_length(base_line_shift, fs)

            elif c.nodeType == c.ELEMENT_NODE and c.nodeName != "tspan":
                continue
            else:
                raise Exception("Unexpected node, type=%s, name=%s" % (c.nodeType, c.nodeName))

            frag_lengths.append(stringWidth(tx, ff, fs))
            rl = sum(frag_lengths[:-1])

            try:
                text = ''.join(frags)
            except ValueError:
                text = "Unicode"

            shape = String(x + rl, y - y1 - dy0 + base_line_shift, text)

            self.apply_style(shape, node)

            if c.nodeType == c.ELEMENT_NODE and c.nodeName == "tspan":
                self.apply_style(shape, c)

            gr.add(shape)

        gr.scale(1, -1)
        gr.translate(0, -2 * y)

        return gr

    def convert_path(self, node):
        """
        Converts a <path> element's "d" property into an RLG group
        :type node: Element
        :rtype Group
        """
        assert isinstance(node, Element)

        norm_path = utils.normalize_svg_path(node.getAttribute('d'))
        pts, ops = [], []
        last_move_to_op = None

        for op, nums in utils.pairwise(norm_path):

            # moveto, lineto absolute
            if op in ('M', 'L'):
                xn, yn = nums
                pts += [xn, yn]
                if op == 'M':
                    ops.append(OP_MOVETO)
                    last_move_to_op = (op, xn, yn)
                elif op == 'L':
                    ops.append(OP_LINETO)

            # moveto, lineto relative
            elif op == 'm':
                xn, yn = nums
                if len(pts) >= 2:
                    pts = pts + [pts[-2] + xn] + [pts[-1] + yn]
                else:
                    pts += [xn, yn]
                if norm_path[-2] in ('z', 'Z') and last_move_to_op:
                    pts[-2] = xn + last_move_to_op[-2]
                    pts[-1] = yn + last_move_to_op[-1]
                    last_move_to_op = (op, pts[-2], pts[-1])
                if not last_move_to_op:
                    last_move_to_op = (op, xn, yn)
                ops.append(OP_MOVETO)
            elif op == 'l':
                xn, yn = nums
                pts = pts + [pts[-2] + xn] + [pts[-1] + yn]
                ops.append(1)

            # horizontal/vertical line absolute
            elif op in ('H', 'V'):
                k = nums[0]
                if op == 'H':
                    pts = pts + [k] + [pts[-1]]
                elif op == 'V':
                    pts = pts + [pts[-2]] + [k]
                ops.append(OP_LINETO)

            # horizontal/vertical line relative
            elif op in ('h', 'v'):
                k = nums[0]
                if op == 'h':
                    pts = pts + [pts[-2] + k] + [pts[-1]]
                elif op == 'v':
                    pts = pts + [pts[-2]] + [pts[-1] + k]
                ops.append(OP_LINETO)

            # cubic bezier, absolute
            elif op == 'C':
                x1, y1, x2, y2, xn, yn = nums
                pts += [x1, y1, x2, y2, xn, yn]
                ops.append(OP_CURVETO)
            elif op == 'S':
                x2, y2, xn, yn = nums
                xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                # pts = pts + [xcp2, ycp2, x2, y2, xn, yn]
                pts += [xi, yi, x2, y2, xn, yn]
                ops.append(OP_CURVETO)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = pts[-2:]
                x1, y1, x2, y2, xn, yn = nums
                pts += [xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn]
                ops.append(OP_CURVETO)
            elif op == 's':
                xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                x2, y2, xn, yn = nums
                pts += [xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn]
                ops.append(OP_CURVETO)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = pts[-2:]
                x1, y1, xn, yn = nums
                xcp, ycp = x1, y1
                (_, _), (x1, y1), (x2, y2), (xn, yn) = utils.convert_quadratic_path_to_cubic(
                    (x0, y0),
                    (x1, y1),
                    (xn, yn)
                )
                pts += [x1, y1, x2, y2, xn, yn]
                ops.append(OP_CURVETO)
            elif op == 'T':
                xp, yp, x0, y0 = pts[-4:]
                xi, yi = x0 + (x0 - xcp), y0 + (y0 - ycp)
                xcp, ycp = xi, yi
                xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (xi, yi), (xn, yn))
                pts += [x1, y1, x2, y2, xn, yn]
                ops.append(OP_CURVETO)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = pts[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                xcp, ycp = x1, y1
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (x1, y1), (xn, yn))
                pts += [x1, y1, x2, y2, xn, yn]
                ops.append(OP_CURVETO)
            elif op == 't':
                x0, y0 = pts[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xcp), y0 + (y0 - ycp)
                xcp, ycp = xi, yi
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (xi, yi), (xn, yn))
                pts += [x1, y1, x2, y2, xn, yn]
                ops.append(OP_CURVETO)

            elif op in ('Z', 'z'):
                # close path
                ops.append(OP_CLOSEPATH)

            else:
                # arcs
                if op in ('A', 'a'):
                    pts = pts + nums[-2:]
                    ops.append(OP_LINETO)
                else:
                    print("Unknown Path Operator:", op)

        # hack because RLG has no "semi-closed" paths...
        gr = Group()
        if ops[-1] == OP_CLOSEPATH:  # if ends with a close path...
            shape1 = Path(pts, ops)
            self.apply_style(shape1, node, defaults={"fill": colors.black, "stroke": None})
            if not attributes.find(node, "fill"):
                shape1.fillColor = colors.black

            if not attributes.find(node, "stroke"):
                shape1.strokeColor = None

            gr.add(shape1)
        else:
            shape1 = Path(pts, ops + [OP_CLOSEPATH])
            self.apply_style(shape1, node)

            shape1.strokeColor = None
            if not attributes.find(node, "fill"):
                shape1.fillColor = colors.black
            gr.add(shape1)

            shape2 = Path(pts, ops)
            self.apply_style(shape2, node)
            shape2.fillColor = None

            if not attributes.find(node, "stroke"):
                shape2.strokeColor = None
            gr.add(shape2)

        # debugging in case we try to replace this path parsing with a better version that doesn't crash so much
        # from svg.path import parse_path
        # print("-" * 200)
        # print("original :", node.getAttribute('d'))
        # print("parsed   :", parse_path(node.getAttribute('d')).d())
        # print("  ops    :", ops)
        # print("  pts    :", pts)
        # original: M 63.223676,253.416 A 135,135 0 0 1 63.223675, 46.583998 L 150,150 z
        # parsed  : M 63.2237,  253.416 A 135,135 0 0,1 63.2237,   46.584 L 150,150 Z

        return gr

    def convert_image(self, node):
        _logger.debug("Adding box instead of image")

        x, y, width, height = self._length_attrs(node, 'x', 'y', 'width', 'height')

        xlink_href = utils.enc(node.getAttributeNS("http://www.w3.org/1999/xlink", "href"))
        xlink_href = os.path.join(os.path.dirname(self.svgSourceFile), xlink_href)

        magic = "data:image/jpeg;base64"

        if xlink_href[:len(magic)] == magic:
            pat = "data:image/(\w+?);base64"
            ext = re.match(pat, magic).groups()[0]
            jpeg_data = base64.decodestring(xlink_href[len(magic):])
            hash_val = hashlib.md5(jpeg_data).hexdigest()
            name = "images/img%s.%s" % (hash_val, ext)
            path = os.path.join(dirname(self.svgSourceFile), name)
            open(path, "wb").write(jpeg_data)
            img = Image(x, y + height, width, -height, path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(dirname(self.svgSourceFile), xlink_href)
            img = Image(x, y + height, width, -height, xlink_href)

        return img

    @staticmethod
    def apply_transform(transform, group):
        """
        Apply an SVG transformation to a RL Group shape.

        The transformation is the value of an SVG transform attribute
        like transform="scale(1, -1) translate(10, 30)".

        rotate(<angle> [<cx> <cy>]) is equivalent to:
          translate(<cx> <cy>) rotate(<angle>) translate(-<cx> -<cy>)
        """

        assert isinstance(group, Group), "group parameter must be an RLG Group object"

        tr = attributes.convert_transform(transform)
        for op, values in tr:
            if op == "scale":
                if not isinstance(values, tuple):
                    values = (values, values)
                group.scale(*values)
            elif op == "translate":
                try:
                    values = values[0], values[1]
                except TypeError:
                    return
                group.translate(*values)
            elif op == "rotate":
                if not isinstance(values, tuple) or len(values) == 1:
                    group.rotate(values)
                elif len(values) == 3:
                    angle, cx, cy = values
                    group.translate(cx, cy)
                    group.rotate(angle)
                    group.translate(-cx, -cy)
            elif op == "skewX":
                group.skew(values, 0)
            elif op == "skewY":
                group.skew(0, values)
            elif op == "matrix":
                group.transform = values
            else:
                _logger.debug("Ignoring unknown transform: %s %s" % (op, values))

    @staticmethod
    def apply_style(to_shape, from_node, defaults=None):
        """
        Apply styles from SVG elements to an RLG shape.
        """

        assert isinstance(to_shape, Shape), "to_shape must be a RLG shape instance (line, polygon, circle, etc...)"

        # tuple format: (svgAttr, rlgAttr, converter, default)
        mapping_n = (
            ("fill", "fillColor", "convert_color", "none"),
            ("fill-opacity", "fillOpacity", "convert_opacity", 1),
            ("stroke", "strokeColor", "convert_color", "none"),
            ("stroke-width", "strokeWidth", "convert_length", "0"),
            ("stroke-linejoin", "strokeLineJoin", "convert_line_join", "0"),
            ("stroke-linecap", "strokeLineCap", "convert_line_cap", "0"),
            ("stroke-dasharray", "strokeDashArray", "convert_dash_array", "none"),
        )
        mapping_f = (
            ("font-family", "fontName", "convert_font_family", "Helvetica"),
            ("font-size", "fontSize", "convert_length", "12"),
            ("text-anchor", "textAnchor", "identity", "start"),
        )

        ac = attributes

        for mapping in (mapping_n, mapping_f):
            # values in mapping_f ONLY apply to strings, so skip if other shape
            if to_shape.__class__ != String and mapping == mapping_f:
                continue

            for (svgAttrName, rlgAttr, func, default) in mapping:
                try:
                    value = attributes.find(from_node, svgAttrName) or default
                    if value == "currentColor":
                        value = attributes.find(from_node.parentNode, "color") or default
                    method = getattr(ac, func)
                    setattr(to_shape, rlgAttr, method(value))
                except:
                    pass

        if to_shape.__class__ == String:
            svg_attr = attributes.find(from_node, "fill") or "black"
            setattr(to_shape, "fillColor", attributes.convert_color(svg_attr))
