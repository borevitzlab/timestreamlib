#Copyright 2014 Kevin Murray

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: timestream.parse
    :platform: Unix, Windows
    :synopsis: Submodule which parses timestream formats.

.. moduleauthor:: Kevin Murray <spam@kdmurray.id.au>
"""

import glob
import json
import logging
import os
from os import path

from timestream.parse.validate import (
        validate_timestream_manifest,
        )
from timestream.util import (
        PARAM_TYPE_ERR,
        dict_unicode_to_str,
        )


#: Default timestream manifest extension
MANIFEST_EXT = ".tsm"

LOG = logging.getLogger(__name__)


def _ts_has_manifest(ts_path):
    """Checks if a timestream has a manifest.

    :param str ts_path: Path to the root of a timestream.
    :returns: The path to the manifest, or ``False``.
    """
    pattern = "{}{}*{}".format(ts_path, os.sep, MANIFEST_EXT)
    manifest = glob.glob(pattern)
    if len(manifest):
        return manifest[0]
    else:
        return False

def _guess_manifest_info(ts_path):
    """Guesses the values of manifest fields in a timestream
    """
    pass

def _all_files_with_ext(topdir, ext, cs=False):
    """Iterates over all files with extension ``ext`` recursively from ``topdir``
    """
    if not isinstance(topdir, str):
        msg = PARAM_TYPE_ERR.format(param="topdir",
                func="_all_files_with_ext",  type="str")
        LOG.error(msg)
        raise ValueError(msg)
    if not isinstance(ext, str):
        msg = PARAM_TYPE_ERR.format(param="ext",
                func="_all_files_with_ext",  type="str")
        LOG.error(msg)
        raise ValueError(msg)
    if not isinstance(cs, bool):
        msg = PARAM_TYPE_ERR.format(param="cs",
                func="_all_files_with_ext",  type="bool")
        LOG.error(msg)
        raise ValueError(msg)
    # Trim any leading spaces from the extension we've been given
    if ext.startswith("."):
        ext = ext[1:]
    # For speed, we pre-convert the ext to lowercase here if we're being case
    # insensitive
    if not cs:
        ext = ext.lower()
    # OK, walk the dir. we only care about files, hence why dirs never gets
    # touched
    for root, dirs, files in os.walk(topdir):
        for fpath in files:
            # split out ext, and do any case-conversion we need
            fname, fext = path.splitext(fpath)
            if not cs:
                fext = fext.lower()
            # remove the dot at the start, as splitext returns ("fn", ".ext")
            fext = fext[1:]
            if fext == ext:
                # we give the whole path to  the file
                yield path.join(root, fpath)

def _all_files_with_exts(topdir, exts, cs=False):
    """Creates a dictionary of {"ext": [files]} for each ext in exts
    """
    if not isinstance(exts, list):
        LOG.error("Exts must be a list of strings")
        raise ValueError("Exts must be a list of strings")
    ext_dict = {}
    for ext in exts:
        ext_dict[ext] = sorted(list(_all_files_with_ext(topdir, ext, cs)))
    return ext_dict

def get_timestream_manifest(ts_path):
    """Reads in or makes up a manifest for the timestream at ``ts_path``, and
    returns it as a ``dict``
    """
    manifest = _ts_has_manifest(ts_path)
    if manifest:
        with open(manifest) as ifh:
            manifest = json.load(ifh)
        if isinstance(manifest, list):
            # it comes in as a list, we want a dict
            manifest = dict_unicode_to_str(manifest[0])
        manifest = validate_timestream_manifest(manifest)
    else:
        manifest = _guess_manifest_info(ts_path)
    return manifest

def iter_timestream_images(ts_path):
    """Iterate over a ``timestream`` in chronological order
    """
    manifest = get_timestream_manifest(ts_path)

    for fpath in _all_files_with_ext(ts_path, manifest["extension"], cs=False):
        yield fpath
    #LOG.debug("Found {} files with ext {} in {}".format(n, ext, topdir))

