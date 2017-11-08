# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import os
import sys

import requests
from os.path import dirname, realpath

from svg2rlg.utils import b

LOCAL_DOWNLOAD_DIR = os.path.join(dirname(realpath(__file__)), "samples", "download")
SAMPLES_MISC = os.path.join(dirname(realpath(__file__)), "samples", "misc")

# should all be under the download dir, where fetch_file downloads to.  Use
# the same folder here as your call to fetch_file, and use this enum in the
# call to create_test_class_for_dir
DL_W3C_TINY = os.path.join(LOCAL_DOWNLOAD_DIR, "w3c-tiny")
DL_WIKI_COMMONS = os.path.join(LOCAL_DOWNLOAD_DIR, "wiki-commons")
DL_WIKI_FLAGS = os.path.join(LOCAL_DOWNLOAD_DIR, "wiki-flags")


def write_line(line):
    sys.stdout.write("%s \r" % line)
    sys.stdout.flush()


def one_liner(text):
    class OneLiner(object):
        def __init__(self, text):
            self.text = text

        def __enter__(self):
            self.write(self.text)
            return self

        def write(self, text):
            self.text = text
            sys.stdout.write("%s\r" % (self.text.strip(),))
            sys.stdout.flush()

        def append(self, ending):
            sys.stdout.write("%s%s" % (self.text, ending))
            sys.stdout.flush()

        def __exit__(self, exc_type, exc_val, exc_tb):
            sys.stdout.write("\n")
            sys.stdout.flush()

    return OneLiner(text)


def list_downloaded_files(dest_folder):
    """
    Returns a list of full paths to files and all files in a subdirectory that match a pattern
    """
    base = os.path.join(LOCAL_DOWNLOAD_DIR, dest_folder)
    patterns = [".svg", ".svgz", ".svg.gz", ".svg.bz2"]
    matches = []
    for root, dirnames, filenames in os.walk(base):
        matches += [
            os.path.join(root, f) for f in filenames if any(f.endswith(x) for x in patterns)
        ]
    return matches


def fetch_file(server, server_path, dest_folder="misc", dest_file=None, large=False):
    """
    Fetch file using http lib module.  This will auto-un-gzip anything that is sent as gzipped!
    E.g. if you have /fetch/f.tar.gz which sets content-encoding:gzip, it will ge auto extracted
    to the file name inside
    """
    dest_folder = os.path.join(LOCAL_DOWNLOAD_DIR, dest_folder)
    if not os.path.exists(dest_folder):
        print("Creating dir: %s" % dest_folder)
        os.makedirs(dest_folder)

    url = "%s%s" % (server, server_path)
    local_file = os.path.join(dest_folder, os.path.split(server_path)[-1] if not dest_file else dest_file)

    if not os.path.exists(local_file):
        with one_liner("~ downloading %s" % (url,)) as l:
            if large:
                l.append(" (large file, please wait)")
                resp = requests.get(url, stream=True)
                with open(local_file, b('wb')) as fd:
                    for chunk in resp.iter_content(chunk_size=512):
                        fd.write(chunk)
            else:
                resp = requests.get(url)
                if resp.status_code == 200:
                    with open(local_file, b("wb")) as f:
                        f.write(resp.content)
                    l.append(" : success, %sb" % (len(resp.content)))
                else:
                    l.append(" : error => status=%s, text=%s" % (resp.status_code, resp.text.splitlines()[0]))

        return local_file

    return local_file
