#!/usr/bin/env python
# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import logging
import os
import sys
from os.path import dirname, basename
from svg2rlg import file_to_rlg

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

if len(sys.argv) < 2:
    print("Pass in the file name to convert, e.g. convert_local.py ./myfile.svg")
    exit(1)

in_file = os.path.join(dirname(__file__), sys.argv[1])
out_file = basename(in_file) + ".pdf"

drawing = file_to_rlg(in_file)
drawing.save(fnRoot=out_file)
