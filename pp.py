#!/usr/bin/env python
# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import os
from os.path import dirname
from svg2rlg import file_to_rlg

BASE = os.path.join(dirname(__file__), "tests", "samples", "misc")


def out_fn(filename, suffix):
    return "test_%s_py3_%s" % (filename, suffix)


for filename in ['rllogo', 'circle_arc', 'car']:
    fn = os.path.join(BASE, filename + ".svg")
    print("Reading", fn)

    print("  writing", out_fn(filename, "orig"))
    drawing = file_to_rlg(fn)
    drawing.save(fnRoot=out_fn(filename, "orig"))

