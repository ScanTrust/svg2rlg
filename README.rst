.. -*- mode: rst -*-

========
Svglib
========

---------------------------------------------------------------------------
A pure-Python library for reading and converting SVG
---------------------------------------------------------------------------

|ci|

.. |ci| image:: http://img.shields.io/travis/scantrust/svg2rlg.svg
  :target: https://travis-ci.org/scantrust/svg2rlg

-------------------------------------------------------------------------
ScanTrust Fork of: https://github.com/deeplook/svglib
Originally From:   https://github.com/sweh/svglib

This version has been reorganized and updated a little in the api department,
but is largely derived from `deeplook/svglib` which is from `sweh` original.

It is packaged as `svg2rlg` and can be found in the ScanTrust pypi.

- Requires lxml
- Handles `<use>` and other types of references properly
- Proper clipping support for Path and Rect data
- Many other spec-matching improvements (thanks deeplook!)

-------------------------------------------------------------------------


About
-----

``Svglib`` is a pure-Python library for reading SVG_ files and converting
them (to a reasonable degree) to other formats using the ReportLab_ Open
Source toolkit.

Used as a package you can read existing SVG files and convert them into
ReportLab ``Drawing`` objects that can be used in a variety of contexts,
e.g. as ReportLab Platypus ``Flowable`` objects or in RML_.
As a command-line tool it converts SVG files into PDF ones (but adding
other output formats like bitmap or EPS is really easy and will be better
supported, soon).

Tests include a huge `W3C SVG test suite`_ plus ca. 200 `flags from
Wikipedia`_ and some selected `symbols from Wikipedia`_ (with increasingly
less pointing to missing features).

This release introduces *many* contributions by Claude Paroz, who
stepped forward to give this project a long needed overhaul after ca.
six years of taking a nap, for which I'm really very grateful! Thanks,
Claude!

Previous versions were hosted at https://bitbucket.org/deeplook/svglib.


Features
--------

- convert SVG_ files into ReportLab_ Graphics ``Drawing`` objects
- handle plain or compressed SVG files (.svg and .svgz)
- allow patterns for output files on command-line
- install a Python package named ``svglib``
- install a Python command-line script named ``svg2pdf``
- provide a PyTest_ test suite with over 90% code coverage
- test entire `W3C SVG test suite`_ after pulling from the internet
- test all SVG `flags from Wikipedia`_ after pulling from the internet
- test selected SVG `symbols from Wikipedia`_ after pulling from the net
- run on Python 2.7 and Python 3.5


Known limitations
-----------------

- stylesheets are not supported (only the style attribute)
- clipping is limited to single paths and rects, no mask support
- color gradients are not supported


Examples
--------

You can use ``svglib`` as a Python package e.g. like in the following
interactive Python session::

    >>> from svglib.svglib import svg2rlg
    >>> from reportlab.graphics import renderPDF, renderPM
    >>>
    >>> drawing = svg2rlg("file.svg")
    >>> renderPDF.drawToFile(drawing, "file.pdf")
    >>> renderPM.drawToFile(drawing, "file.png")

In addition a script named ``svg2pdf`` can be used more easily from
the system command-line. Here is the output from ``svg2pdf -h``::

    usage: svg2pdf [-h] [-v] [-o PATH_PAT] [PATH [PATH ...]]

    svg2pdf v. 0.8.1
    A converter from SVG to PDF (via ReportLab Graphics)

    positional arguments:
      PATH                  Input SVG file path with extension .svg or .svgz.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         Print version number and exit.
      -o PATH_PAT, --output PATH_PAT
                            Set output path (incl. the placeholders: dirname,
                            basename,base, ext, now) in both, %(name)s and {name}
                            notations.

    examples:
      # convert path/file.svg to path/file.pdf
      svg2pdf path/file.svg

      # convert file1.svg to file1.pdf and file2.svgz to file2.pdf
      svg2pdf file1.svg file2.svgz

      # convert file.svg to out.pdf
      svg2pdf -o out.pdf file.svg

      # convert all SVG files in path/ to PDF files with names like:
      # path/file1.svg -> file1.pdf
      svg2pdf -o "%(base)s.pdf" path/file*.svg

      # like before but with timestamp in the PDF files:
      # path/file1.svg -> path/out-12-58-36-file1.pdf
      svg2pdf -o {{dirname}}/out-{{now.hour}}-{{now.minute}}-{{now.second}}-%(base)s.pdf path/file*.svg

    issues/pull requests:
        https://github.com/deeplook/svglib

    Copyleft by Dinu Gherman, 2008-2017 (LGPL 3):
        http://www.gnu.org/copyleft/gpl.html


Dependencies
------------

``Svglib`` depends mainly on the ``reportlab`` package, which provides
the abstractions for building complex ``Drawings`` which it can render
into different fileformats, including PDF, EPS, SVG and various bitmaps
ones. Other dependancies are ``lxml`` which is used in the context of SVG
CSS stylesheets.


Installation
------------

There are three ways to install ``svglib``.

1. Using ``pip``
++++++++++++++++

Install of the library version requires access to the ScanTrust PYPI
instance.  You can also use the deeplook version, with instructions
at https://github.com/deeplook/svglib/blob/master/README.rst#installation

    $ pip install svg2rlg

If you do not have the ScanTrust pypi set up, you can add it on the
command line:

    $ pip install svglib --extra-index-url https://pypi.scantrust.io/pypi/

Testing
-------

Testing has been migrated to `unittest` and should do everything automatically
when you use the `discover` runner.

    $ python -m unittest discover

    # To download the assets for testing from wikipedia, set the env variable
    # `DL=True` as in:

    $ DL=True python -m unittest discover

Bug reports
-----------

Please report bugs on the `svglib issue tracker`_ on GitHub (pull
requests are also appreciated)!
If necessary, please include information about the operating system, as
well as the versions of ``svglib``, ReportLab and Python being used!
Warning: there is no `support for Windows`_, sorry for that!


.. _SVG: http://www.w3.org/Graphics/SVG/
.. _W3C SVG test suite:
      http://www.w3.org/Graphics/SVG/WG/wiki/Test_Suite_Overview
.. _flags from Wikipedia:
      https://en.wikipedia.org/wiki/Gallery_of_sovereign_state_flags
.. _symbols from Wikipedia:
      http://en.wikipedia.org/wiki/List_of_symbols
.. _ReportLab: http://www.reportlab.org
.. _RML: http://www.reportlab.com/software/rml-reference/
.. _svglib issue tracker: https://github.com/deeplook/svglib/issues
.. _PyTest: http://pytest.org
.. _svglib page on PyPI: https://pypi.python.org/pypi/svglib
.. _svglib releases page on GitHub: https://github.com/deeplook/svglib/releases
.. _support for Windows: https://github.com/deeplook/svglib/issues/70
.. _Anaconda: https://www.anaconda.com/download/
.. _Miniconda: https://conda.io/miniconda.html
.. _Conda: https://conda.io
.. _svglib with conda: https://github.com/conda-forge/svglib-feedstock
.. _nicoddemus: https://github.com/nicoddemus
