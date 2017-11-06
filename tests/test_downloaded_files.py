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
from tests import utils
from tests.utils import fetch_file

######################################
#
# Funny looking test classes which test svg conversion on a wide variety of files,
# some of which are downloaded from wikipedia and/or others in the future.
#
# ** All files in samples/download and subdirectories are tested
# ** All files in samples/misc are tested as well, 1 level deep only
#
# Custom test classes are dynamically created so that we get one test_case_method
# PER FILE, rather than one large hanging test cases (well, it looks like its hanging)
#
# Note:
#
# If you don't have the files locally, add them by passing in the environment var `DL`
#    $ DL=True python -m unittest discover
#

try:
    DL_EXTRA = os.environ.get('DL', False)
    import requests
except:
    DL_EXTRA = False

# --------------------------------------------------------------------------
# download all the files if DL is turned on (skipping if they already exist)
# -----------
if DL_EXTRA:
    def download_wiki_flags():
        server = "https://en.wikipedia.org"
        flags_file = fetch_file(
            server=server,
            server_path="/wiki/Gallery_of_sovereign_state_flags",
            dest_folder="wiki-flags",
            dest_file="flags.html"
        )
        with open(flags_file, b"rt") as f:
            flags_data = f.read()

        # Find the "a href = "/wiki/File:(flag name)" here
        pattern = r"upload.wikimedia.org(/wikipedia/commons/thumb/[^/]*/[^/]*/Flag_of_[^/]*\.svg)/"
        for (url, fn) in set([(u, unquote(basename(u))) for u in re.findall(pattern, flags_data)]):
            fn = re.sub("[^\w.]", '__', fn).lower().replace("flag_of_", "")
            url = url.replace("/thumb", "")
            fetch_file("http://upload.wikimedia.org", url, "wiki-flags", fn)


    def download_specific_files():
        specified_files = {
            "https://upload.wikimedia.org => wiki-commons": [
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

        for key, file_list in specified_files.items():
            server, dest_dir = key.replace("=>", " ").split()
            for path in file_list:
                fetch_file(server, path, "wiki-commons")


    download_specific_files()
    download_wiki_flags()


def create_test_class_for_dir(class_name, base_directory):
    """
    Creates the test class that
    :param class_name: The name to use for the class.  Useful for error reports.
    :param base_directory: The base directory to start searching for other sub-directories
    """

    class TestTheStuff(unittest.TestCase):
        pass

    TestTheStuff.__name__ = class_name

    def add_test(file_full_path):
        dir, method_name = os.path.split(file_full_path)
        method_name = "test__%s__%s" % (
            re.sub("\W", "_", os.path.split(dir)[1]),  # take the last directory name
            re.sub("\W", "_", method_name)
        )

        # noinspection PyUnusedLocal
        def test_method(self):
            try:
                file_to_rlg(file_full_path)
            except Exception as e:
                tb = sys.exc_info()[2]  # get the traceback (stack trace)
                while tb.tb_next:  # find the last frame
                    tb = tb.tb_next

                locals_dump = ""
                for k, v in tb.tb_frame.f_locals.items():
                    try:
                        locals_dump += "\n\t%s\t=\t%s (%s)" % (k, str(v), type(v).__name__)
                    except Exception as e:
                        locals_dump += "\n\t%s\t=<error printing>" % (k,)

                self.fail("\n".join([
                    "Failed processing file '{fn}'".format(fn=file_full_path),
                    "-" * 40,
                    traceback.format_exc(),
                    "-" * 40,
                    locals_dump
                ]))

        test_method.name = method_name
        setattr(TestTheStuff, test_method.name, test_method)

    # walk all files in the directory itself (for the manual test cases)
    [add_test(f) for f in utils.list_downloaded_files(base_directory)]

    # walk all subdirectories as well (only 1 level though)
    for s in [x[0] for x in os.walk(base_directory)]:
        [add_test(f) for f in utils.list_downloaded_files(os.path.join(s))]

    return TestTheStuff


TestDownloadedFiles = create_test_class_for_dir(b"TestDownloadedFiles", utils.LOCAL_DOWNLOAD_DIR)
TestMiscFiles = create_test_class_for_dir(b"TestMiscFiles", utils.MISC_SAMPLES_DIR)

# -
# todo: Add a test which downloads the W3C test suite
#       https://www.w3.org/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz
