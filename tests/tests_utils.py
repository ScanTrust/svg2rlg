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
            (
                "m246.026 120.178c-.558-.295-1.186-.768-1.395-1.054-.314-.438-.132-.456 1.163-.104 "
                + "2.318.629 3.814.383 5.298-.873l1.308-1.103 1.54.784c.848.428 1.748.725 "
                + "2.008.656.667-.176 2.05-1.95 2.005-2.564-.054-.759.587-.568.896.264.615 1.631-.281 "
                + "3.502-1.865 3.918-.773.201-1.488.127-2.659-.281-1.438-.502-1.684-.494-2.405.058-1.618 "
                + "1.239-3.869 1.355-5.894.299z"
            ): [
                'm', [246.026, 120.178], 'c', [-0.558, -0.295, -1.186, -0.768, -1.395, -1.054],
                'c', [-0.314, -0.438, -0.132, -0.456, 1.163, -0.104],
                'c', [2.318, 0.629, 3.814, 0.383, 5.298, -0.873],
                'l', [1.308, -1.103], 'l', [1.54, 0.784],
                'c', [0.848, 0.428, 1.748, 0.725, 2.008, 0.656],
                'c', [0.667, -0.176, 2.05, -1.95, 2.005, -2.564],
                'c', [-0.054, -0.759, 0.587, -0.568, 0.896, 0.264],
                'c', [0.615, 1.631, -0.281, 3.502, -1.865, 3.918],
                'c', [-0.773, 0.201, -1.488, 0.127, -2.659, -0.281],
                'c', [-1.438, -0.502, -1.684, -0.494, -2.405, 0.058],
                'c', [-1.618, 1.239, -3.869, 1.355, -5.894, 0.299],
                'z', []
            ],

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
