# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import unittest

from reportlab.lib import colors, units

from svg2rlg import attributes


class TestAttributes(unittest.TestCase):
    longMessage = True

    def test_convert_length_list_with_units(self):
        expected = [5 * units.cm, 5 * units.inch]
        self.assertEqual(expected, attributes.convert_length_list("5cm 5in"))

    def test_convert_length_list_when_no_length_specifier(self):
        """
        When there is no cm/inches/etc specifier, conversion should result in the number only
        """
        self.assertEqual([5, 5], attributes.convert_length_list("5, 5"))

    def test_transform_conversion_on_empty_list(self):
        self.assertEqual([], attributes.convert_transform(""))

    def test_transform_on_single_value_function(self):
        self.assertEqual(
            [("some-name", 3)],
            attributes.convert_transform("some-name(3)")
        )

    def test_transform_on_multi_value_function(self):
        self.assertEqual(
            [("hi-there", (3, 5, 3.2))],
            attributes.convert_transform("hi-there(3,5,3.2)")
        )

    def test_transform_on_multi_value_list(self):
        self.assertEqual(
            [("scale", 2), ("translate", (10, 20))],
            attributes.convert_transform("scale(2) translate(10,20)")
        )

    def test_transform_colors(self):
        reds = [
            "red",
            "#ff0000",
            "#f00",
            "rgb(255,0,0)",
            "rgb(100%,0%,0%)",
            "red",
        ]
        for input_val in reds:
            result = attributes.convert_color(input_val)
            self.assertEqual(colors.red, result, "Error converting %s" % input_val)

    def test_transform_length(self):
        mapping = [
            ("0", 0),
            ("316", 316),
            ("-316", -316),
            ("-3.16", -3.16),
            ("-1e-2", -0.01),
            ("1e-5", 1e-5),
            ("1e1cm", 10 * units.cm),
            ("1e1in", 10 * units.inch),
            ("1e1%", 10),
            ("-8e-2cm", (-8e-2) * units.cm),
        ]
        for input_value, expected in mapping:
            self.assertEqual(expected, attributes.convert_length(input_value))
