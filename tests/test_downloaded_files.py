#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import os
import re
import sys
import traceback
import unittest
from os.path import basename
from unittest.case import skipIf

from requests.utils import unquote

from svg2rlg import file_to_rlg
from tests.utils import fetch_file

try:
    DL_EXTRA = os.environ.get('DL', False)
    import requests
except:
    DL_EXTRA = False


@skipIf(not DL_EXTRA, reason="You must set the DL env var to True to test this")
class TestExternalFiles(unittest.TestCase):
    files = {
        "https://upload.wikimedia.org": [
            "/wikipedia/commons/f/f7/Biohazard.svg",
            "/wikipedia/commons/1/11/No_smoking_symbol.svg",
            "/wikipedia/commons/b/b0/Dharma_wheel.svg",
            "/wikipedia/commons/a/a7/Eye_of_Horus_bw.svg",
            "/wikipedia/commons/1/17/Yin_yang.svg",
            "/wikipedia/commons/a/a7/Olympic_flag.svg",
            "/wikipedia/commons/4/46/Ankh.svg",
            "/wikipedia/commons/5/5b/Star_of_life2.svg",
            "/wikipedia/commons/9/97/Tudor_rose.svg"
        ]
    }

    def test_wikipedia_commons(self):
        server = "https://upload.wikimedia.org"
        for path in self.files[server]:
            local_file = fetch_file(server, path, "wiki-commons")
            file_to_rlg(local_file)


@skipIf(not DL_EXTRA, reason="You must set the DL env var to True to test this")
class WikipediaFlagsTestCase(unittest.TestCase):
    """
    Tests using SVG flags from Wikipedia.org.
    """
    server = "https://en.wikipedia.org"

    found_flags = []

    def setUp(self):
        """
        Check if files exists, else download.
        Get a list of all flags to use, based on the ones in the html.
            don't use the fs file list (no reason for this, though, we could)
        """
        flags_file = fetch_file(self.server, "/wiki/Gallery_of_sovereign_state_flags", "wiki-flags", "flags.html")
        with open(flags_file) as f:
            flags_data = f.read()

        # Find the "a href = "/wiki/File:(flag name)" here
        pattern = r"upload.wikimedia.org(/wikipedia/commons/thumb/[^/]*/[^/]*/Flag_of_[^/]*\.svg)/"
        for (url, fn) in set([(u, unquote(basename(u))) for u in re.findall(pattern, flags_data)]):
            fn = re.sub("[^\w.]", '__', fn).lower().replace("flag_of_", "")
            url = url.replace("/thumb", "")
            self.found_flags.append(
                fetch_file("http://upload.wikimedia.org", url, "wiki-flags", fn)
            )

    def test_all_flags(self):
        """
        Requires that setup has been run
        :return:
        """

        for filename in self.found_flags:
            try:
                file_to_rlg(filename)
            except:
                tb = sys.exc_info()[2]  # get the traceback (stack trace)
                while tb.tb_next:  # find the last frame
                    tb = tb.tb_next

                locals_dump = ""
                for k, v in tb.tb_frame.f_locals.items():
                    try:
                        locals_dump += "\n\t%s\t=\t%s (%s)" % (k, str(v), type(v).__name__)
                    except:
                        locals_dump += "\n\t%s\t=<error printing>" % (k,)

                self.fail(
                    (
                        "Failed processing file '{fn}'\n" +
                        "-------------------------------------------\n" +
                        "{tb}" +
                        "-------------------------------------------\n" +
                        "{locals}"
                    ).format(
                        fn=filename, tb=traceback.format_exc(), locals=locals_dump,
                    )
                )

# -
# todo: Add a test which downloads the W3C test suite
#       https://www.w3.org/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz
