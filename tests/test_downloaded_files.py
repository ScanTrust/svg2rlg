#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import traceback
import xml
from unittest.case import skipIf, skip

from tests.utils import fetch_file

import os
import sys
import glob
import re
import gzip
import urllib
import tarfile
from os.path import splitext, exists, join, basename, getsize
import unittest

from reportlab.graphics import renderPDF, renderPM

from svg2rlg import file_to_rlg

try:
    DL_EXTRA = os.environ.get('DL', False)
    import requests
except:
    DL_EXTRA = False

files = {
    "http://upload.wikimedia.org": [
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


@skipIf(not DL_EXTRA, reason="You must set the DL env var to True to test this")
class TestExternalFiles(unittest.TestCase):
    def test_wikipedia_commons(self):
        server = "http://upload.wikimedia.org"
        for path in files[server]:
            local_file = fetch_file(server, path, "wiki-commons")
            file_to_rlg(local_file)


@skipIf(not DL_EXTRA, reason="You must set the DL env var to True to test this")
class WikipediaFlagsTestCase(unittest.TestCase):
    """
    Tests using SVG flags from Wikipedia.org.
    """
    server = "http://en.wikipedia.org"

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
                        "Failed processing file '%s'\n" +
                        "-------------------------------------------\n" +
                        "%s" +
                        "-------------------------------------------\n" +
                        "%s"
                        "-------------------------------------------\n" +
                        "%s"
                    ) % (
                        filename, traceback.format_exc(), locals_dump, open(filename, 'rt').read()
                    )
                )

                # renderPDF.drawToFile(drawing, base, showBoundary=0)


@skip("supid test")
class W3CTestCase(unittest.TestCase):
    def setUp(self):
        """Check if testsuite archive exists, else download and unpack it."""

        server = "http://www.w3.org"
        path = "/Graphics/SVG/Test/20070907/W3C_SVG_12_TinyTestSuite.tar.gz"
        url = server + path

        archive_path = basename(url)
        tarPath = splitext(archive_path)[0]
        self.folderPath = join("samples", splitext(tarPath)[0])

        if not exists(self.folderPath):
            if not exists(join("samples", tarPath)):
                if not exists(join("samples", archive_path)):
                    print("downloading %s" % url)
                    try:
                        data = urllib.urlopen(url).read()
                    except IOError as details:
                        print(details)
                        print("Check your internet connection and try again!")
                        return
                    archive_path = basename(url)
                    open(join("samples", archive_path), "wb").write(data)
                print("unpacking %s" % archive_path)
                tar_data = gzip.open(join("samples", archive_path), "rb").read()
                open(join("samples", tarPath), "wb").write(tar_data)
            print("extracting into %s" % self.folderPath)
            os.mkdir(self.folderPath)
            tar_file = tarfile.TarFile(join("samples", tarPath))
            tar_file.extractall(self.folderPath)
            if exists(join("samples", tarPath)):
                os.remove(join("samples", tarPath))

    def test0(self):
        """Test converting W3C SVG files to PDF using svglib."""

        exclude_list = [
            "paint-stroke-06-t.svg",
        ]

        paths = glob.glob("%s/svg/*.svg" % self.folderPath)
        msg = "Destination folder '%s/svg' not found." % self.folderPath
        self.failUnless(len(paths) > 0, msg)

        for i, path in enumerate(paths):
            print("working on [%d]" % i, path)

            if basename(path) in exclude_list:
                print("excluded (to be tested later)")
                continue

            # convert
            try:
                drawing = file_to_rlg(path)
            except:
                print("could not convert [%d]" % i, path)
                continue

            # save as PDF
            base = splitext(path)[0] + '-generated.pdf'
            try:
                renderPDF.drawToFile(drawing, base, showBoundary=0)
            except:
                print("could not save as PDF [%d]" % i, path)

                # save as PNG
            # (endless loop for file paint-stroke-06-t.svg)
            base = splitext(path)[0] + '-generated.png'
            try:
                renderPM.drawToFile(drawing, base, 'PNG')
            except:
                print("could not save as PNG [%d]" % i, path)
                # outcommented, because many SVG samples seem to generate errors

    def _test1(self):
        """Test converting W3C SVG files to PDF using uniconverter."""

        # skip test, if uniconv tool not found
        if not os.popen("which uniconv").read().strip():
            print("Uniconv not found, test skipped.")
            return

        paths = glob.glob("%s/svg/*" % self.folderPath)
        paths = [p for p in paths
                 if splitext(p.lower())[1] in [".svg", ".svgz"]]
        for path in paths:
            out = splitext(path)[0] + '-uniconv.pdf'
            cmd = "uniconv '%s' '%s'" % (path, out)
            os.popen(cmd).read()
            if exists(out) and getsize(out) == 0:
                os.remove(out)
