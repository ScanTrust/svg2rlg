# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import bz2
import gzip
import logging
import os
import re
import sys
from math import ceil, radians, cos, sin, sqrt, hypot, degrees, copysign, acos, fabs

from reportlab.graphics.shapes import mmult, rotate, translate, transformPoint
from reportlab.pdfgen.canvas import FILL_NON_ZERO

PY3 = sys.version_info > (3, 0)
XML_NS = 'http://www.w3.org/XML/1998/namespace'

if PY3:
    import io

    StringIO = io.StringIO
    BytesIO = io.BytesIO

    TEXT_TYPE = str
    STRING_TYPE = str
    BINARY_TYPE = bytes


    def b(s):
        if isinstance(s, str):
            return s
        elif isinstance(s, bytes):
            return s.decode()

else:
    import StringIO as _IO

    StringIO = _IO.StringIO
    BytesIO = _IO.StringIO

    TEXT_TYPE = unicode
    BINARY_TYPE = str
    STRING_TYPE = basestring


    def b(s):
        if isinstance(s, unicode):
            return s.encode("latin-1")
        else:
            return s

_logger = logging.getLogger(__name__)


def is_string(val):
    return isinstance(val, STRING_TYPE)


def enc(value):
    """
    Trys to encode a string as ascii and then decode it.  This should result
    in a unicode string on py2&3.  I think that was the idea, not sure if this
    needs to stay forever
    :rtype str|unicode
    """
    assert isinstance(value, (TEXT_TYPE, BINARY_TYPE)), 'enc() must be called with %s or %s, got %s' % (
        TEXT_TYPE.__name__, BINARY_TYPE.__name__, value
    )
    return value.decode() if isinstance(value, BINARY_TYPE) else value


def except_(func, default=None):
    try:
        return func()
    except Exception as e:
        return default


# -----------------------------------------------
# NODE HELPERS
#

def node_name(node):
    """
    Return lxml node name without the namespace prefix.
    """
    try:
        return node.tag.split('}')[-1]
    except AttributeError:
        pass


def node_xlink_href(node):
    """
    Reads the xlink:href attribute from a node (e.g.  <use xlink:href="#my-clipping-rect"...>)
    """
    return node.attrib.get('{http://www.w3.org/1999/xlink}href')


def node_preserve_space(node, default=False):
    xml_space = node_attr(node, "{%s}space" % XML_NS)
    if xml_space:
        return xml_space == 'preserve'
    else:
        return default


def node_attr(node, name):
    """
    Gets an attribute from an lxml.etree node, or blank.
    """
    return node.attrib.get(name, '')


def node_attrs(node, *args):
    """
    Gets a list of attributes from a node.  If attribute is not present,
    the default from `node_attr` of "" will be used.
    """
    return [node_attr(node, attr_name) for attr_name in args]


# -----------------------------------------------
# HELPERS
#

def pairwise(iterable):
    """
    Iterate over a list and return 2 values at a time.
    :param iterable
    :rtype (object,object)
    """
    iterable = iter(iterable)
    while True:
        try:
            yield next(iterable), next(iterable)
        except StopIteration:
            return


def split_dots(item_list):
    """
    Yield elements in the existing list, but yield >1 for certain broken numeric elements

    - Fix strings like "-.3939.3939.2910.939" where here are multiple values (all <1) in a string and the
    - svg spec alows you to squish them together.  e.g. -1.3.39.01.5 should be "-1.3 .39 .01 .5", really
    """
    assert isinstance(item_list, list)
    for x in item_list:
        if x.count('.') > 1:
            for item in [v for v in re.split('([-+]?\d*\.\d+)', x) if v]:
                yield item
        else:
            yield x


def to_floats(float_list):
    """
    Convert number strings in list to floats (leave rest untouched).
    Returns None in the position if the value is not a float or ascii encodable
    """

    def conv(item):
        try:
            return float(item)
        except:
            return except_(lambda: enc(item), None)

    return [conv(x) for x in split_dots(float_list)]


def vector_angle(u, v):
    """
    https://github.com/deeplook/svglib/blob/master/svglib/utils.py
    """
    d = hypot(*u) * hypot(*v)
    c = (u[0] * v[0] + u[1] * v[1]) / d
    if c < -1:
        c = -1
    elif c > 1:
        c = 1
    s = u[0] * v[1] - u[1] * v[0]
    return degrees(copysign(acos(c), s))


def convert_quadratic_path_to_cubic(qp0, qp1, qp2):
    """
    Convert a quadratic Bezier curve through Q0, Q1, Q2 to a cubic one.
    """
    factor = (2. / 3.)
    cp1 = (
        qp0[0] + factor * (qp1[0] - qp0[0]),
        qp0[1] + factor * (qp1[1] - qp0[1])
    )
    cp2 = (
        qp2[0] + factor * (qp1[0] - qp2[0]),
        qp2[1] + factor * (qp1[1] - qp2[1])
    )
    return qp0, cp1, cp2, qp2


# noinspection PyPep8Naming
def bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2):
    if phi:
        # Our box bezier arcs can't handle rotations directly
        # move to a well known point, eliminate phi and transform the other point
        mx = mmult(rotate(-phi), translate(-x1, -y1))
        tx2, ty2 = transformPoint(mx, (x2, y2))

        # Convert to box form in unrotated coords
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(
            0, 0, tx2, ty2, fA, fS, rx, ry
        )
        bp = bezier_arc_from_centre(cx, cy, rx, ry, start_ang, extent)

        # Re-rotate by the desired angle and add back the translation
        mx = mmult(translate(x1, y1), rotate(phi))
        res = []
        for x1, y1, x2, y2, x3, y3, x4, y4 in bp:
            res.append(
                transformPoint(mx, (x1, y1)) + transformPoint(mx, (x2, y2)) +
                transformPoint(mx, (x3, y3)) + transformPoint(mx, (x4, y4))
            )
        return res
    else:
        cx, cy, rx, ry, start_ang, extent = end_point_to_center_parameters(
            x1, y1, x2, y2, fA, fS, rx, ry
        )
        return bezier_arc_from_centre(cx, cy, rx, ry, start_ang, extent)


def bezier_arc_from_centre(cx, cy, rx, ry, start_ang=0.0, extent=90.0):
    """
    https://github.com/deeplook/svglib/blob/master/svglib/utils.py
    """
    if abs(extent) <= 90:
        n_frag = 1
        frag_angle = float(extent)
    else:
        n_frag = int(ceil(abs(extent) / 90.))
        frag_angle = float(extent) / n_frag

    frag_rad = radians(frag_angle)
    half_rad = frag_rad * 0.5
    kappa = abs(4. / 3. * (1. - cos(half_rad)) / sin(half_rad))

    if frag_angle < 0:
        kappa = -kappa

    point_list = []
    theta1 = radians(start_ang)
    start_rad = theta1 + frag_rad

    c1 = cos(theta1)
    s1 = sin(theta1)
    for i in range(n_frag):
        c0 = c1
        s0 = s1
        theta1 = start_rad + i * frag_rad
        c1 = cos(theta1)
        s1 = sin(theta1)
        point_list.append((cx + rx * c0,
                           cy - ry * s0,
                           cx + rx * (c0 - kappa * s0),
                           cy - ry * (s0 + kappa * c0),
                           cx + rx * (c1 + kappa * s1),
                           cy - ry * (s1 - kappa * c1),
                           cx + rx * c1,
                           cy - ry * s1))
    return point_list


def end_point_to_center_parameters(x1, y1, x2, y2, fA, fS, rx, ry, phi=0):
    """
    See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
    note that we reduce phi to zero outside this routine
    """
    rx = fabs(rx)
    ry = fabs(ry)

    # step 1
    if phi:
        phi_rad = radians(phi)
        sin_phi = sin(phi_rad)
        cos_phi = cos(phi_rad)
        tx = 0.5 * (x1 - x2)
        ty = 0.5 * (y1 - y2)
        x1d = cos_phi * tx - sin_phi * ty
        y1d = sin_phi * tx + cos_phi * ty
    else:
        x1d = 0.5 * (x1 - x2)
        y1d = 0.5 * (y1 - y2)

    # step 2
    # we need to calculate
    # (rx*rx*ry*ry-rx*rx*y1d*y1d-ry*ry*x1d*x1d)
    # -----------------------------------------
    #     (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    # that is equivalent to
    #
    #          rx*rx*ry*ry
    # = -----------------------------  -    1
    #   (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
    #
    #              1
    # = -------------------------------- - 1
    #   x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
    #
    # = 1/r - 1
    #
    # it turns out r is what they recommend checking
    # for the negative radicand case
    r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
    if r > 1:
        rr = sqrt(r)
        rx *= rr
        ry *= rr
        r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
    r = 1 / r - 1
    if -1e-10 < r < 0:
        r = 0
    r = sqrt(r)
    if fA == fS:
        r = -r
    cxd = (r * rx * y1d) / ry
    cyd = -(r * ry * x1d) / rx

    # step 3
    if phi:
        cx = cos_phi * cxd - sin_phi * cyd + 0.5 * (x1 + x2)
        cy = sin_phi * cxd + cos_phi * cyd + 0.5 * (y1 + y2)
    else:
        cx = cxd + 0.5 * (x1 + x2)
        cy = cyd + 0.5 * (y1 + y2)

    # step 4
    theta1 = vector_angle((1, 0), ((x1d - cxd) / rx, (y1d - cyd) / ry))
    dtheta = vector_angle(
        ((x1d - cxd) / rx, (y1d - cyd) / ry),
        ((-x1d - cxd) / rx, (-y1d - cyd) / ry)
    ) % 360
    if fS == 0 and dtheta > 0:
        dtheta -= 360
    elif fS == 1 and dtheta < 0:
        dtheta += 360
    return cx, cy, rx, ry, -theta1, -dtheta


def fix_svg_path(path_list):
    """
    Normalise certain "abnormalities" in SVG paths.

    Basically, this reduces adjacent number values for h and v
    operators to the sum of these numbers and those for H and V
    operators to the last number only.

    Returns a slightly more compact list if such reductions
    were applied or a copy of the same list, otherwise.
    """

    # this could also modify the path to contain an op code
    # for each coord. tuple of a tuple sequence...
    hPos = [x == 'h' for x in path_list]
    vPos = [x == 'v' for x in path_list]
    HPos = [x == 'H' for x in path_list]
    VPos = [x == 'V' for x in path_list]
    numPos = [isinstance(x, float) for x in path_list]

    fixed_list = []

    i = 0
    while i < len(path_list):
        if hPos[i] + vPos[i] + HPos[i] + VPos[i] == 0:
            fixed_list.append(path_list[i])
        elif hPos[i] == 1 or vPos[i] == 1:
            fixed_list.append(path_list[i])
            sum = 0
            j = i + 1
            while j < len(path_list) and numPos[j] == 1:
                sum = sum + path_list[j]
                j += 1
            fixed_list.append(sum)
            i = j - 1
        elif HPos[i] == 1 or VPos[i] == 1:
            fixed_list.append(path_list[i])
            last = 0
            j = i + 1
            while j < len(path_list) and numPos[j] == 1:
                last = path_list[j]
                j += 1
            fixed_list.append(last)
            i = j - 1
        i += 1

    return fixed_list


def split_floats(op, min_num, value):
    """
    Split `value`, a list of numbers as a string, to a list of float numbers.
    Also optionally insert a `l` or `L` operation depending on the operation
    and the length of values.
    Example: with op='m' and value='10,20 30,40,' the returned value will be
             ['m', [10.0, 20.0], 'l', [30.0, 40.0]]
    """
    floats = [float(seq) for seq in re.findall('(-?\d*\.?\d*(?:e[+-]\d+)?)', value) if seq]
    res = []
    for i in range(0, len(floats), min_num):
        if i > 0 and op in {'m', 'M'}:
            op = 'l' if op == 'm' else 'L'
        res.extend([op, floats[i:i + min_num]])
    return res


def normalize_svg_path(attr):
    """
    Normalise SVG path.

    This basically introduces operator codes for multi-argument parameters.
    Also, it fixes sequences of consecutive M or m operators to MLLL...
    and mlll... operators. It adds an empty list as argument for Z and z only
    in order to make the resulting list easier to iterate over.

    E.g. "M 10 20, M 20 20, L 30 40, 40 40, Z"
      -> ['M', [10, 20], 'L', [20, 20], 'L', [30, 40], 'L', [40, 40], 'Z', []]
    """

    # operator codes mapped to the minimum number of expected arguments
    ops = {
        'A': 7, 'a': 7,
        'Q': 4, 'q': 4, 'T': 2, 't': 2, 'S': 4, 's': 4,
        'M': 2, 'L': 2, 'm': 2, 'l': 2, 'H': 1, 'V': 1,
        'h': 1, 'v': 1, 'C': 6, 'c': 6, 'Z': 0, 'z': 0,
    }
    op_keys = ops.keys()

    # do some preprocessing
    result = []
    groups = re.split('([achlmqstvz])', attr.strip(), flags=re.I)
    op = None
    for item in groups:
        if item.strip() == '':
            continue
        if item in op_keys:
            # fix sequences of M to one M plus a sequence of L operators,
            # same for m and l.
            if item == 'M' and item == op:
                op = 'L'
            elif item == 'm' and item == op:
                op = 'l'
            else:
                op = item
            if ops[op] == 0:  # Z, z
                result.extend([op, []])
        else:
            result.extend(split_floats(op, ops[op], item))
            op = result[-2]  # Remember last op

    return result


def _decomp_bz2(f):
    """
    Decompresses a BZ2 stream and returns an in-memory file-like object that can be read.
    Working with BZ2 in python in 2&3 mode is a pain.
    """
    return BytesIO(bz2.decompress(f.read()))


def decompress_fp(file_pointer):
    """
    Wraps a filepointer in a decompressing reader for BZ/GZ.  ZIP can be added, but its odder since it contains >1 file
    so we must either restrict to 1 file in archive, or give a way to provide the internal filename.
    """

    assert hasattr(file_pointer, 'seek'), "decompress_fp: object passed does not look like a file (no seek method)"
    assert hasattr(file_pointer, 'read'), "decompress_fp: object passed does not look like a file (no read method)"

    # list of (magic bytes, class name, callable to pass the existing FP to)
    magic = [
        (b"\x1f\x8b\x08", gzip.GzipFile, lambda f: gzip.GzipFile(fileobj=f)),
        (b"\x42\x5a\x68", bz2.BZ2File, lambda f: BytesIO(bz2.decompress(f.read())))
    ]

    _, compressed_types, _ = zip(*magic)

    # short circuit out if the user passed us an actual g/bzip object
    if isinstance(file_pointer, compressed_types):
        return file_pointer

    file_pointer.seek(0)
    header = file_pointer.read(16)
    file_pointer.seek(0)

    for magic_val, klass, opener in magic:
        if header.startswith(magic_val):
            return opener(file_pointer)

    return file_pointer


def read_any(path_or_file):
    """
    Reads from either a file-like object or a string path pointing to a file (attempting to decompress).
    """
    if is_string(path_or_file):
        if not os.path.exists(path_or_file):
            raise Exception("File '%s' does not exist.  Unable to read SVG file" % path_or_file)

        with open(path_or_file, b('rb')) as f:
            return decompress_fp(f).read()
    else:
        # if we try to combine them we risk double-uncompressing, or early closing of the FP if it was passed to us
        return path_or_file.read()


def pad_list(v, desired_length, fill_value=None):
    if len(v) < desired_length:
        return v + [fill_value] * (desired_length - len(v))
    else:
        return v


def monkeypatch_reportlab():
    """
    https://bitbucket.org/rptlab/reportlab/issues/95/
    ReportLab always use 'Even-Odd' filling mode for paths, this patch forces
    RL to honor the path fill rule mode (possibly 'Non-Zero Winding') instead.
    """
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.graphics import shapes
    original_render_path = shapes._renderPath

    # noinspection PyPep8Naming
    def patched_render_path(path, drawFuncs):
        # Patched method to transfer fillRule from Path to PDFPathObject
        # Get back from bound method to instance
        try:
            drawFuncs[0].__self__.fillMode = path._fillRule
        except AttributeError:
            pass
        return original_render_path(path, drawFuncs)

    shapes._renderPath = patched_render_path

    original_draw_path = Canvas.drawPath

    # noinspection PyPep8Naming
    def patched_draw_path(self, path, **kwargs):
        current = self._fillMode
        if hasattr(path, 'fillMode'):
            self._fillMode = path.fillMode
        else:
            self._fillMode = FILL_NON_ZERO
        original_draw_path(self, path, **kwargs)
        self._fillMode = current

    Canvas.drawPath = patched_draw_path
