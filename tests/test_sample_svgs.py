# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import unittest
from distutils import dirname

from svg2rlg import file_to_rlg as convert_file

BASE = dirname(__file__) + "/samples/misc/"


class TestSampleSvgs(unittest.TestCase):
    """
    Test each sample file in a separate test case.

    We could do this in one large test case by using glob.glob() to get all the files, but that
    just ends up with one long running test, and we'd rather know specifically which test failed
    or which one is taking a long time.
    """

    def test_arcs_2(self):
        convert_file(BASE + "arcs02-abs.svg")

    def test_arcs_2_relative(self):
        convert_file(BASE + "arcs02-rel.svg")

    def test_car(self):
        convert_file(BASE + "car.svg")

    def test_compressed_gzip(self):
        convert_file(BASE + "car.svg.gz")

    def test_compressed_bzip2(self):
        fn = BASE + "car.svg.bz2"
        convert_file(fn)

    def test_circle_arc(self):
        convert_file(BASE + "circle_arc.svg")

    def test_logo_a3(self):
        convert_file(BASE + "logo_a3.svg")

    def test_newlion(self):
        convert_file(BASE + "newlion.svg")

    def test_rl_logo(self):
        convert_file(BASE + "rllogo.svg")

    def test_tiger(self):
        convert_file(BASE + "tiger.svg")
