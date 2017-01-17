# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import unittest

from svg2rlg import utils


class TestUtils(unittest.TestCase):
    def test_enc_returns_default_when_not_encodable(self):
        self.assertEqual(u"你好", utils.enc(u"你好"))

    def test_enc_returns_unicode(self):
        self.assertEqual(u"abc", utils.enc(b"abc"))

    def test_parse_multi_attr_string(self):
        expected = {
            "fill": "black",
            "stroke": "yellow"
        }
        self.assertDictEqual(
            expected,
            utils.parse_multi_attribute_string("fill: black; stroke: yellow")
        )

    def test_normalize_svg_path(self):
        tranforms = {
            "": [],
            "Z": ["Z", []],
            "M10 20": ["M", [10, 20]],
            "m10 20": ["m", [10, 20]],
            "m10 20   ": ["m", [10, 20]],
            "   m10 20": ["m", [10, 20]],
            "    m10 20   ": ["m", [10, 20]],
            "L 30 40 40 40": ["L", [30, 40], "L", [40, 40]],
            "M 10 20, M 30 40, L 40 40, Z": ["M", [10, 20], "L", [30, 40], "L", [40, 40], "Z", []],

        }
        for input_value, expected in tranforms.items():
            self.assertEqual(expected, utils.normalize_svg_path(input_value))

    def test_convert_quadratic_path(self):
        quadratic = ((0, 0), (1, 2), (3, 0))
        cubic = (
            (0, 0),
            (2. / 3, 4. / 3),
            (5. / 3, 4. / 3),
            (3, 0)
        )
        self.assertEqual(
            utils.convert_quadratic_path_to_cubic(*quadratic),
            cubic
        )
