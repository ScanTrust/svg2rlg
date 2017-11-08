# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import base64
import hashlib
import logging
import os
import re
import tempfile
from functools import partial
from os.path import dirname
from xml.dom.minidom import Element

import itertools
from reportlab.graphics.shapes import Line, Rect, Circle, Ellipse, Group, Polygon, PolyLine, String, Path, Image, Shape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import FILL_NON_ZERO, FILL_EVEN_ODD
from reportlab.pdfgen.pdfimages import PDFImage

from svg2rlg.paths import NoStrokePath
from svg2rlg.utils import node_name, node_attr
from . import utils, attributes, settings

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

    def __init__(self, file_path):
        """
        :param file_path: Path to the original file, used to resolve images/external files
        :type file_path: str| None
        """
        self.preserve_space = False
        self.svg_source_file = file_path

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
        return attributes.convert_length(node_attr(node, attribute))

    def _length_attrs(self, node, *args):
        return tuple(self._get_length(node, v) for v in args)

    def _length_attrs_dict(self, node, *args):
        return {v: self._get_length(node, v) for v in args}

    def convert(self, node, clipping=None):
        """
        Converts any supported node to a reportlab shape.

        :type node: reportlab.shapes.Shape
        :type clipping: svg2rlg.paths.ClippingPath
        """
        name = node_name(node).lower()
        method_name = "convert_%s" % name.lower()
        shape = getattr(self, method_name)(node)
        if not shape:
            return

        if name not in ('path', 'polyline', 'text'):
            # Only apply style where the convert method did not apply it.
            self.apply_style(shape, node)

        transform = node_attr(node, "transform")
        if not (transform or clipping):
            return shape
        else:
            group = Group()
            if transform:
                self.apply_transform(transform, group)
            if clipping:
                group.add(clipping)
            group.add(shape)
            return group

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
            # rx = width, ry = height
            *self._length_attrs(node, "cx", "cy", "rx", "ry")
        )

    def convert_polyline(self, node):
        points = attributes.convert_length_list(node_attr(node, "points"))
        has_fill = node_attr(node, 'fill') not in ('', 'none')

        if len(points) % 2 != 0 or len(points) == 0:
            _logger.warn("Invalid Polyline points: %s" % points)
            return None

        polyline = PolyLine(points)
        self.apply_style(polyline, node)

        if has_fill:
            # Need to use two shapes, because standard RLG polylines do not support filling...
            # Polygon is the same as the polyline but without a border (stroke)
            gr = Group()
            polygon = Polygon(points)
            self.apply_style(polygon, node)
            polygon.strokeColor = None
            gr.add(polygon)
            gr.add(polyline)
            return gr
        else:
            return polyline

    def convert_polygon(self, node):
        points = attributes.convert_length_list(node_attr(node, "points"))
        if len(points) % 2 != 0 or len(points) == 0:
            _logger.warn("Invalid Polygon points: %s" % points)
            return None

        return Polygon(points)

    def clean_text(self, text, preserve_space):
        """
        Text cleaning as per https://www.w3.org/TR/SVG/text.html#WhiteSpace
        """
        if text is None:
            return

        # todo: this doesn't seem quite right, this replacement logic
        if preserve_space:
            text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\t', ' ')
        else:
            text = text.replace('\r\n', '').replace('\n', '').replace('\t', ' ')
            text = text.strip()
            while '  ' in text:
                text = text.replace('  ', ' ')
        return text

    def convert_text(self, node):
        """
        Converts a <text> element
        """

        x, y = self._length_attrs(node, 'x', 'y')
        preserve_space = utils.node_preserve_space(node, self.preserve_space)

        gr = Group()
        frag_lengths = []

        dx0, dy0 = 0, 0
        x1, y1 = 0, 0

        ff = attributes.convert_font_family(attributes.find(node, "font-family"))  # default is set inside convert_...
        fs = attributes.convert_length(attributes.find(node, "font-size") or "12")
        convert_len = partial(attributes.convert_length, em_base=fs)

        for c in itertools.chain([node], node.getchildren()):
            has_x, has_y = False, False
            dx, dy = 0, 0
            baseline_shift = 0
            if node_name(c) == 'text':
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
            elif node_name(c) == 'tspan':
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
                x1, y1, dx, dy = [c.attrib.get(name, '') for name in ("x", "y", "dx", "dy")]
                has_x, has_y = (x1 != '', y1 != '')
                x1, y1, dx, dy = map(convert_len, (x1, y1, dx, dy))
                dx0 = dx0 + dx
                dy0 = dy0 + dy
                baseline_shift = c.attrib.get("baseline-shift", '0')
                if baseline_shift in ("sub", "super", "baseline"):
                    baseline_shift = {"sub": -fs / 2, "super": fs / 2, "baseline": 0}[baseline_shift]
                else:
                    baseline_shift = convert_len(baseline_shift, fs)
            else:
                continue

            frag_lengths.append(stringWidth(text, ff, fs))
            new_x = (x1 + dx) if has_x else (x + dx0 + sum(frag_lengths[:-1]))
            new_y = (y1 + dy) if has_y else (y + dy0)
            shape = String(new_x, -(new_y - baseline_shift), text)
            self.apply_style(to_shape=shape, from_node=node)
            if node_name(c) == 'tspan':
                self.apply_style(to_shape=shape, from_node=c)

            gr.add(shape)

        gr.scale(1, -1)

        return gr

    def convert_opacity(self, value):
        return float(value)

    def convert_fill_rule(self, value):
        return {
            'nonzero': FILL_NON_ZERO,
            'evenodd': FILL_EVEN_ODD,
        }.get(value, '')

    # noinspection PyUnusedLocal
    def convert_path(self, node):
        normalized_path = utils.normalize_svg_path(node_attr(node, 'd'))

        path = Path()
        points = path.points

        # Track subpaths needing to be closed later
        unclosed_subpath_pointers = []
        subpath_start = []
        last_op = ''

        for op, nums in utils.pairwise(normalized_path):

            if op in ('m', 'M') and last_op != '' and path.operators[-1] != OP_CLOSEPATH:
                unclosed_subpath_pointers.append(len(path.operators))

            # moveto absolute
            if op == 'M':
                path.moveTo(*nums)
                subpath_start = points[-2:]

            # lineto absolute
            elif op == 'L':
                path.lineTo(*nums)

            # moveto relative
            elif op == 'm':
                if len(points) >= 2:
                    if last_op in ('Z', 'z'):
                        starting_point = subpath_start
                    else:
                        starting_point = points[-2:]
                    xn, yn = starting_point[0] + nums[0], starting_point[1] + nums[1]
                    path.moveTo(xn, yn)
                else:
                    path.moveTo(*nums)
                subpath_start = points[-2:]

            # lineto relative
            elif op == 'l':
                xn, yn = points[-2] + nums[0], points[-1] + nums[1]
                path.lineTo(xn, yn)

            # horizontal/vertical line absolute
            elif op == 'H':
                path.lineTo(nums[0], points[-1])
            elif op == 'V':
                path.lineTo(points[-2], nums[0])

            # horizontal/vertical line relative
            elif op == 'h':
                path.lineTo(points[-2] + nums[0], points[-1])
            elif op == 'v':
                path.lineTo(points[-2], points[-1] + nums[0])

            # cubic bezier, absolute
            elif op == 'C':
                path.curveTo(*nums)
            elif op == 'S':
                x2, y2, xn, yn = nums
                if len(points) < 4 or last_op not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x2, y2, xn, yn)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = points[-2:]
                x1, y1, x2, y2, xn, yn = nums
                path.curveTo(xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn)
            elif op == 's':
                x2, y2, xn, yn = nums
                if len(points) < 4 or last_op not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (x1, y1), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            elif op == 'T':
                if len(points) < 4:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (xi, yi), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (x1, y1), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 't':
                if len(points) < 4:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                x0, y0 = points[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    utils.convert_quadratic_path_to_cubic((x0, y0), (xi, yi), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # elliptical arc
            elif op in ('A', 'a'):
                rx, ry, phi, fA, fS, x2, y2 = nums
                x1, y1 = points[-2:]
                if op == 'a':
                    x2 += x1
                    y2 += y1
                if abs(rx) <= 1e-10 or abs(ry) <= 1e-10:
                    path.lineTo(x2, y2)
                else:
                    bp = utils.bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2)
                    for _, _, x1, y1, x2, y2, xn, yn in bp:
                        path.curveTo(x1, y1, x2, y2, xn, yn)

            # close path
            elif op in ('Z', 'z'):
                path.closePath()

            else:
                _logger.debug("Suspicious path operator: %s" % op)
            last_op = op

        gr = Group()
        self.apply_style(path, node)

        if path.operators[-1] != OP_CLOSEPATH:
            unclosed_subpath_pointers.append(len(path.operators))

        if unclosed_subpath_pointers and path.fillColor is not None:
            # ReportLab doesn't fill unclosed paths, so we are creating a copy
            # of the path with all subpaths closed, but without stroke.
            # https://bitbucket.org/rptlab/reportlab/issues/99/
            closed_path = NoStrokePath(copy_from=path)
            for pointer in reversed(unclosed_subpath_pointers):
                closed_path.operators.insert(pointer, OP_CLOSEPATH)
            gr.add(closed_path)
            path.fillColor = None

        gr.add(path)
        return gr

    def convert_image(self, node):
        _logger.warn("Adding box instead of image.")

        x, y, width, height = self._length_attrs(node, ('x', 'y', "width", "height"))
        xlink_href = utils.node_xlink_href(node)

        magic = "data:image/jpeg;base64"
        if xlink_href[:len(magic)] == magic:
            pat = "data:image/(\w+?);base64"
            ext = re.match(pat, magic).groups()[0]
            jpeg_data = base64.decodestring(xlink_href[len(magic):].encode('ascii'))
            _, path = tempfile.mkstemp(suffix='.%s' % ext)
            with open(path, b'wb') as fh:
                fh.write(jpeg_data)
            img = Image(int(x), int(y + height), int(width), int(-height), path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(os.path.dirname(self.svg_source_file), xlink_href)
            img = Image(int(x), int(y + height), int(width), int(-height), xlink_href)
            try:
                # this will catch invalid image
                PDFImage(xlink_href, 0, 0)
            except IOError:
                _logger.error("Unable to read the image %s. Skipping..." % img.path)
                return None
        return img

    def apply_transform(self, transform, group):
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
                if isinstance(values, (int, float)):
                    # From the SVG spec: If <ty> is not provided, it is assumed to be zero.
                    values = values, 0
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

    def apply_style(self, to_shape, from_node, only_explicit=False):
        """
        Apply styles from SVG elements to an RLG shape.
        """

        assert isinstance(to_shape, Shape), "to_shape must be a RLG shape instance (line, polygon, circle, etc...)"

        # tuple format: (svgAttr, rlgAttr, converter, default)
        mapping_n = (
            ("fill", "fillColor", "convert_color", "black"),
            ("fill-opacity", "fillOpacity", "convert_opacity", 1),
            ("stroke", "strokeColor", "convert_color", "none"),
            ("fill-rule", "_fillRule", "convert_fill_rule", "nonzero"),
            ("stroke", "strokeColor", "convert_color", "none"),
            ("stroke-width", "strokeWidth", "convert_length", "1"),
            ("stroke-opacity", "strokeOpacity", "convert_opacity", 1),
            ("stroke-linejoin", "strokeLineJoin", "convert_line_join", "0"),
            ("stroke-linecap", "strokeLineCap", "convert_line_cap", "0"),
            ("stroke-dasharray", "strokeDashArray", "convert_dash_array", "none"),
        )
        mapping_f = (
            ("font-family", "fontName", "convert_font_family", "Helvetica"),
            ("font-size", "fontSize", "convert_length", "12"),
            ("text-anchor", "textAnchor", "identity", "start"),
        )

        if to_shape.__class__ == Group:
            # Recursively apply style on Group subelements
            for subshape in to_shape.contents:
                self.apply_style(subshape, from_node, only_explicit=only_explicit)
            return

        for mapping in (mapping_n, mapping_f):
            # values in mapping_f ONLY apply to strings, so skip if other shape
            if to_shape.__class__ != String and mapping == mapping_f:
                continue

            for (svg_attr_name, rlg_attr, func, default) in mapping:
                value = attributes.find(from_node, svg_attr_name)
                if value == '':
                    if only_explicit:
                        continue
                    value = default

                if value == "currentColor":
                    value = attributes.find(from_node.parentNode, "color") or default

                try:
                    conversion_func = getattr(attributes, func)
                    setattr(to_shape, rlg_attr, conversion_func(value))
                except (AttributeError, KeyError, ValueError):
                    pass

        if getattr(to_shape, 'fillOpacity', None):
            if getattr(to_shape, 'fillColor', None):
                to_shape.fillColor.alpha = to_shape.fillOpacity
