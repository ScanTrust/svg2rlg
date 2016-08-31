# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import unittest
from distutils import dirname

from svg2rlg import svg2rlg

BASE = dirname(__file__) + "/samples/misc/"


class TestSampleSvgs(unittest.TestCase):
    """
    Test each sample file in a separate test case.

    We could do this in one large test case by using glob.glob() to get all the files, but that
    just ends up with one long running test, and we'd rather know specifically which test failed
    or which one is taking a long time.
    """

    def test_airbus(self):
        svg2rlg(BASE + "airbus.svg")

    def test_arcs_2(self):
        svg2rlg(BASE + "arcs02-abs.svg")

    def test_arcs_2_relative(self):
        svg2rlg(BASE + "arcs02-rel.svg")

    def test_car(self):
        svg2rlg(BASE + "car.svg")

    def test_circle_arc(self):
        svg2rlg(BASE + "circle_arc.svg")

    def test_logo_a3(self):
        svg2rlg(BASE + "logo_a3.svg")

    def test_newlion(self):
        svg2rlg(BASE + "newlion.svg")

    def est_py221(self):
        svg2rlg(BASE + "python221imap.svg")

    def test_rl_logo(self):
        svg2rlg(BASE + "rllogo.svg")

    def test_tiger(self):
        svg2rlg(BASE + "tiger.svg")

    def test_timezones(self):
        svg2rlg(BASE + "timezones.svg")
