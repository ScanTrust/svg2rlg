# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import bz2
import gzip
import logging
import os

import sys
import re
import zipfile
from xml.dom.minidom import Element

PY3 = sys.version_info[0] == 3

if PY3:
    import io

    StringIO = io.StringIO
    BytesIO = io.BytesIO

    TEXT_TYPE = str
    STRING_TYPE = str
    BINARY_TYPE = bytes


    def b(s):
        return s.encode("latin-1")

else:
    import StringIO as _IO

    StringIO = _IO.StringIO
    BytesIO = _IO.StringIO

    TEXT_TYPE = unicode
    BINARY_TYPE = str
    STRING_TYPE = basestring


    def b(s):
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
        TEXT_TYPE.__name__, BINARY_TYPE.__name__, type(value).__name__
    )
    return value.decode() if isinstance(value, BINARY_TYPE) else value


def except_(func, default=None):
    try:
        return func()
    except:
        return default


def node_attrs(node, *args):
    """
    Gets a list of attributes from a node
    """
    return list(map(node.getAttribute, args))


def parse_multi_attribute_string(line):
    """
    Parse an attribute string in the format "name:value;name2:value2;name3:value3..." into a dict
    """
    line = enc(line)
    pairs = [a.strip() for a in line.split(';') if a]
    pairs = [[e.strip() for e in a.split(':')] for a in pairs]
    return {k: v for k, v in pairs}


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


def normalize_svg_path(attr):
    """
    Normalise SVG path.

    This basically introduces operator codes for multi-argument
    parameters. Also, it fixes sequences of consecutive M or m
    operators to MLLL... and mlll... operators. It adds an empty
    list as argument for Z and z only in order to make the resul-
    ting list easier to iterate over.

    E.g. "M 10 20, M 20 20, L 30 40, 40 40, Z"
      -> ['M', [10, 20], 'L', [20, 20], 'L', [30, 40], 'L', [40, 40], 'Z', []]
    """

    # operator codes mapped to the minimum number of expected arguments
    ops = {
        'A': 7, 'a': 7,
        'Q': 4, 'q': 4, 'T': 2, 't': 2, 'S': 4, 's': 4,
        'M': 2, 'L': 2, 'm': 2, 'l': 2, 'H': 1, 'V': 1,
        'h': 1, 'v': 1, 'C': 6, 'c': 6, 'Z': 0, 'z': 0
    }

    # do some pre-processing
    op_keys = ops.keys()
    a = attr
    a = a.replace(',', ' ')
    a = a.replace('e-', 'ee')
    a = a.replace('-', ' -')
    a = a.replace('ee', 'e-')
    for op in op_keys:
        a = a.replace(op, " %s " % op)
    a = a.strip()
    a = a.split()
    a = to_floats(a)
    a = fix_svg_path(a)

    # insert op codes for each argument of an op with multiple arguments
    res = []
    i = 0
    while i < len(a):
        el = a[i]
        if el in op_keys:
            if el in ('z', 'Z'):
                res.append(el)
                res.append([])
            else:
                while i < len(a) - 1:
                    if a[i + 1] not in op_keys:
                        res.append(el)
                        res.append(a[i + 1:i + 1 + ops[el]])
                        i = i + ops[el]
                    else:
                        break
        i += 1

    # fix sequences of M to one M plus a sequence of L operators,
    # same for m and l.
    for i in list(range(0, len(res), 2)):
        op, nums = res[i:i + 2]
        if i >= 2:
            if op == 'M' == res[i - 2]:
                res[i] = 'L'
            elif op == 'm' == res[i - 2]:
                res[i] = 'l'

    return res


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

        with open(path_or_file, 'rb') as f:
            return decompress_fp(f).read()
    else:
        # if we try to combine them we risk double-uncompressing, or early closing of the FP if it was passed to us
        return path_or_file.read()


def pad_list(v, desired_length, fill_value=None):
    if len(v) < desired_length:
        return v + [fill_value] * (desired_length - len(v))
    else:
        return v