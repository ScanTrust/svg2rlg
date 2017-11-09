.. -*- mode: rst -*-

=========================
Building and Distributing
=========================

Pre-build Checklist
-------------------

- Distribute from ``master`` only
- Update the ``__version__ = `` line in ``svg2rlg/__init__.py``
  - *Commit message should be "Bumped version to {{newversion}}"*
  - This should be the commit that is built & deployed
- Check https://travis-ci.org/ScanTrust/svg2rlg for status of ``master``
- Create a separate ``venv`` and install there (e.g. ``pip install ../svg2rlg``)
  - *Tests that the installer is not broken in a clean venv*
- Watch the build output, you should see the correct version number, e.g.:
  - ``creating build/bdist.macosx-.../wheel/svg2rlg-{{newversion}}.dist-info/WHEEL``

Building
--------

This projects is built and distributed as universal wheel, since there are no
c libraries (though it does depend on others, like lxml).  It first deletes the
``dist/`` folder to be safe.  Twine is used to upload since the ``upload``
in the standard ```python setup.py upload`` has some issues.  If its fixed and
works for you, then great.

    rm -rf dist/
    python setup.py sdist bdist_wheel
    twine upload --repository <repo-id> dist/*

Setting up your build
---------------------

You need a ``~.pypirc`` file and ``twine``.  Create a ~/.pypirc file that looks
something like this:

    [distutils]
    index-servers =
      pypi
      scantrust

    [pypi]
    username:
    password:

    # private repo.  Replace this name and info as needed
    [scantrust]
    repository: https://pypi.scantrust.io/
    username: your.user.name
    password: yourpassword

Install ``twine``
+++++++++++++++++

    pip install twine

Build!
++++++

Go back to building for mor