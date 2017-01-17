# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import logging

from xml.dom.minidom import Element

from reportlab.graphics.shapes import Group, Drawing

from . import utils, attributes
from svg2rlg.shapes import ShapeConverter

_logger = logging.getLogger(__name__)


class SvgRenderer:
    """
    Renderer that renders an SVG file on a ReportLab Drawing instance.

    This is the base class for walking over an SVG DOM document and
    transforming it into a ReportLab Drawing instance.
    """

    def __init__(self, path=None):
        self.shapeConverter = ShapeConverter()
        self.shapeConverter.svgSourceFile = path  # path is required to convert SVG relative images (should be rare, not normally needed)
        self.handledShapes = self.shapeConverter.get_handled_shapes()
        self.drawing = None  # type: Drawing
        self.mainGroup = Group()
        self.definitions = {}
        self.does_process_definitions = False
        self.logFile = None

    def render(self, node, parent=None):
        assert isinstance(node, Element)

        parent = parent or self.mainGroup
        name = node.nodeName

        if name == "svg":
            self.renderSvg(node)
            children = node.childNodes
            for child in [c for c in children if c.nodeType == 1]:
                self.render(child, self.mainGroup)

        elif name == "defs":
            self.does_process_definitions = True
            parent.add(self.renderG(node))
            self.does_process_definitions = False

        elif name == 'a':
            parent.add(self.renderA(node))

        elif name == 'g':
            display = node.getAttribute("display")
            item = self.renderG(node)

            if display != "none":
                parent.add(item)

            if self.does_process_definitions:
                self.definitions[node.getAttribute("id")] = item

        elif name == "symbol":
            item = self.renderSymbol(node)
            node_id = node.getAttribute("id")
            if node_id:
                self.definitions[node_id] = item

        elif name in self.handledShapes:
            shape = getattr(self.shapeConverter, "convert_" + name)(node)
            if shape:
                self.shapeConverter.apply_style(shape, node)
                transform = node.getAttribute("transform")
                display = node.getAttribute("display")
                if transform and display != "none":
                    gr = Group()
                    self.shapeConverter.apply_transform(transform, gr)
                    gr.add(shape)
                    parent.add(gr)
                elif display != "none":
                    parent.add(shape)
        else:
            _logger.debug("Ignoring node: %s" % name)

    def renderTitle_(self, node):
        # Main SVG title attr. could be used in the PDF document info field.
        pass

    def renderDesc_(self, node):
        # Main SVG desc. attr. could be used in the PDF document info field.
        pass

    def renderSvg(self, node):
        """
        Renders the "SVG" element
        :type node: Element
        :rtype: reportlab.graphics.shapes.Drawing
        """
        width, height = utils.node_attrs(node, "width", "height")  # list(map(node.getAttribute, ("width", "height")))
        width, height = list(map(attributes.convert_length, (width, height)))
        view_box = node.getAttribute("viewBox")
        if view_box:
            view_box = attributes.convert_length_list(view_box)
            width, height = view_box[2:4]
        self.drawing = Drawing(width, height)
        return self.drawing

    def renderG(self, node):
        """
        Renders a <g> element (group)
        :type node: Element
        :rtype: reportlab.graphics.shapes.Group
        """
        # removed the display param and some lines, since render doesn't return anything so there
        # was never an "item" to add to the group.  removed self.attrs assignment since it was never used
        style, transform = list(map(node.getAttribute, ("style", "transform")))
        gr = Group()
        for child in [c for c in node.childNodes if c.nodeType == 1]:
            self.render(child, parent=gr)

        if transform:
            self.shapeConverter.apply_transform(transform, gr)

        return gr

    def renderSymbol(self, node):
        return self.renderG(node)

    def renderA(self, node):
        # currently nothing but a group...
        # there is no linking info stored in shapes, maybe a group should?
        return self.renderG(node)

    def renderUse(self, node):
        xlink_href = node.getAttributeNS("http://www.w3.org/1999/xlink", "href")
        grp = Group()
        try:
            item = self.definitions[xlink_href[1:]]
            grp.add(item)
            transform = node.getAttribute("transform")
            if transform:
                self.shapeConverter.apply_transform(transform, grp)
        except KeyError:
            _logger.debug("Ignoring unavailable object width ID '%s'." % xlink_href)

        return grp

    def finish(self):
        """
        Returns the finished "drawing" shape, which can then be saved to a pdf.

        :rtype: reportlab.graphics.shapes.Drawing
        """
        height = self.drawing.height
        self.mainGroup.scale(1, -1)
        self.mainGroup.translate(0, -height)
        self.drawing.add(self.mainGroup)
        return self.drawing
