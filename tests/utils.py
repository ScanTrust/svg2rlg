# -*- coding: utf-8 -*
from __future__ import print_function, absolute_import, unicode_literals

import os
import sys

import requests

LOCAL_STORAGE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "samples", "download")

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


def fetch_file(server, server_path, dest_folder="misc", dest_file=None):
    """
    Fetch file using http lib module.
    """
    dest_folder = os.path.join(LOCAL_STORAGE, dest_folder)
    if not os.path.exists(dest_folder):
        print("Creating dir: %s" % dest_folder)
        os.makedirs(dest_folder)

    url = "%s%s" % (server, server_path)
    local_file = os.path.join(dest_folder, os.path.split(server_path)[-1] if not dest_file else dest_file)

    if not os.path.exists(local_file):
        with one_liner("~ downloading %s" % (url,)) as l:
            resp = requests.get(url)
            if resp.status_code == 200:
                with open(local_file, "wb") as f:
                    f.write(resp.content)
                l.append(" : success, %sb" % (len(resp.content)))
            else:
                l.append(" : error => status=%s, text=%s" % (resp.status_code, resp.text.splitlines()[0]))

    return local_file
