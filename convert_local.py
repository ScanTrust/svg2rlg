#!/usr/bin/env python
# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import os
import sys
from os.path import dirname, basename
from svg2rlg import file_to_rlg

if len(sys.argv) < 2:
    print("Pass in the file name to convert, e.g. convert_local.py ./myfile.svg")
    exit(1)

full_file_name = os.path.join(dirname(__file__), sys.argv[1])

print("Procesing %s" % full_file_name)

drawing = file_to_rlg(full_file_name)
drawing.save(fnRoot=basename(full_file_name) + ".pdf")
