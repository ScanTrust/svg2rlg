# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import copy
import logging
import re
from collections import defaultdict, namedtuple

from reportlab.graphics.shapes import Group, Drawing, Rect

from svg2rlg.paths import ClippingPath
from svg2rlg.shapes import ShapeConverter
from svg2rlg.utils import node_name, node_attr, node_attrs, node_xlink_href
from . import attributes

_logger = logging.getLogger(__name__)

XML_NS = 'http://www.w3.org/XML/1998/namespace'
Box = namedtuple('Box', ['x', 'y', 'width', 'height'])


class SvgRenderer:
    """Renderer that renders an SVG file on a ReportLab Drawing instance.
    This is the base class for walking over an SVG DOM document and
    transforming it into a ReportLab Drawing instance.
    """

    def __init__(self, file_path=None):
        self.shape_converter = ShapeConverter(file_path=file_path)
        self.handled_shapes = self.shape_converter.get_handled_shapes()
        self.definitions = {}
        self.waiting_use_nodes = defaultdict(list)
        self.box = Box(x=0, y=0, width=0, height=0)

    def render(self, svg_node):
        main_group = self.render_node(svg_node)
        for xlink in self.waiting_use_nodes.keys():
            _logger.debug("Ignoring unavailable object width ID '%s'." % xlink)

        main_group.scale(1, -1)
        main_group.translate(0 - self.box.x, -self.box.height - self.box.y)
        drawing = Drawing(self.box.width, self.box.height)
        drawing.add(main_group)
        return drawing

    def render_node(self, node, parent=None):
        nid = node_attr(node, "id")
        ignored = False
        item = None
        name = node_name(node)

        clipping = self.get_clippath(node)

        if name == "svg":
            if node_attr(node, "{%s}space" % XML_NS) == 'preserve':
                self.shape_converter.preserve_space = True
            return self.render_svg(node)

        elif name == "defs":
            item = self.render_g(node)

        elif name == 'a':
            item = self.render_a(node)
            parent.add(item)

        elif name == 'g':
            display = node_attr(node, "display")
            item = self.render_g(node, clipping=clipping)
            if display != "none":
                parent.add(item)

        elif name == "symbol":
            item = self.render_symbol(node)
            parent.add(item)

        elif name == "use":
            item = self.render_use(node, clipping=clipping)
            parent.add(item)

        elif name == "clipPath":
            item = self.render_g(node)

        elif name in self.handled_shapes:
            display = node_attr(node, "display")
            item = self.shape_converter.convert(node, clipping)
            if item and display != "none":
                parent.add(item)
        else:
            ignored = True
            _logger.debug("Ignoring node: %s" % name)

        if not ignored:
            if nid and item and nid not in self.definitions:
                self.definitions[nid] = node

            if nid in self.waiting_use_nodes.keys():
                to_render = self.waiting_use_nodes.pop(nid)
                for use_node, group in to_render:
                    self.render_use(use_node, group=group)

    def get_definition(self, ref):
        return self.definitions.get(ref.replace("#", ""), None)

    def get_clippath(self, node):
        """
        Return the clipping Path object referenced by the node 'clip-path'
        attribute, if any.
        """

        def get_path_from_node(innernode):
            """
            Get the path from any acceptable node in the chain.  This automatically
            resolves all `use` and so on.
            """
            for child in innernode.getchildren():
                if node_name(child) == 'path':
                    group = self.shape_converter.convert(child)
                    return group.contents[-1]
                if node_name(child) == 'rect':
                    # convert a rect into a path and apply the rect's styles
                    rect = self.shape_converter.convert(child)  # type: Rect
                    x1, y1, x2, y2 = rect.getBounds()
                    p = ClippingPath()
                    p.moveTo(x1, y1)
                    p.lineTo(x2, y1)
                    p.lineTo(x2, y2)
                    p.lineTo(x1, y2)
                    p.closePath()
                    # copy the styles from the rect to the clipping path
                    self.shape_converter.apply_style(from_node=child, to_shape=p)
                    return p
                else:
                    # recursively process the children
                    return get_path_from_node(child)

        clip_path = node_attr(node, 'clip-path')
        if clip_path:
            m = re.match(r'url\(#([^\)]*)\)', clip_path)
            if m:
                ref = m.groups()[0]
                if ref in self.definitions:
                    path = get_path_from_node(self.definitions[ref])
                    if path:
                        path = ClippingPath(copy_from=path)
                        return path
                    else:
                        _logger.debug("couldn't find path reference %s" % ref)

    def get_viewbox(self, node):
        width, height, view_box = node_attrs(node, "width", "height", "viewBox")
        width, height = map(attributes.convert_length, (width, height))
        if view_box:
            view_box = attributes.convert_length_list(view_box)
            return Box(*view_box)
        else:
            return Box(0, 0, width, height)

    def render_title(self, node):
        # Main SVG title attr. could be used in the PDF document info field.
        pass

    def render_desc(self, node):
        # Main SVG desc. attr. could be used in the PDF document info field.
        pass

    def render_svg(self, node):
        """
        Renders the SVG node and all children, and sets up the renderer's ViewBox
        """
        self.box = self.get_viewbox(node)
        group = Group()
        for child in node.getchildren():
            self.render_node(child, group)
        return group

    def render_g(self, node, clipping=None, display=1):
        node_id, transform = node_attrs(node, "id", "transform")
        gr = Group()

        if clipping:
            gr.add(clipping)

        for child in node.getchildren():
            item = self.render_node(child, parent=gr)
            if item and display:
                gr.add(item)

        if transform:
            self.shape_converter.apply_transform(transform, gr)

        return gr

    def render_symbol(self, node):
        return self.render_g(node, display=0)

    def render_a(self, node):
        # currently nothing but a group...
        # there is no linking info stored in shapes, maybe a group should?
        return self.render_g(node)

    def render_use(self, node, group=None, clipping=None):
        if group is None:
            group = Group()

        xlink_href = node_xlink_href(node)
        if not xlink_href:
            return

        # strip the leading "#"
        if xlink_href[1:] not in self.definitions:
            # The missing definition should appear later in the file
            self.waiting_use_nodes[xlink_href[1:]].append((node, group))
            return group

        if clipping:
            group.add(clipping)

        if len(node.getchildren()) == 0:
            # Append a copy of the referenced node as the <use> child (if not already done)
            node.append(copy.deepcopy(self.definitions[xlink_href[1:]]))

        self.render_node(node.getchildren()[-1], parent=group)

        x, y, transform = node_attrs(node, "x", "y", "transform")
        if x or y:
            transform += " translate(%s, %s)" % (x or '0', y or '0')

        if transform:
            self.shape_converter.apply_transform(transform, group)

        return group
