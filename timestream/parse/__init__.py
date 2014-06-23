# Copyright 2014 Kevin Murray
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: timestream.parse
    :platform: Unix, Windows
    :synopsis: Submodule which parses timestream formats.

.. moduleauthor:: Kevin Murray <spam@kdmurray.id.au>
"""

import collections
import cv2
from datetime import (
    datetime,
    timedelta,
)
import glob
from itertools import (
    ifilter,
)
import json
import logging
import os
from os import path
from voluptuous import MultipleInvalid
from warnings import warn

from timestream.parse.validate import (
    validate_timestream_manifest,
    IMAGE_EXT_CONSTANTS,
    IMAGE_EXT_TO_TYPE,
    TS_DATE_FORMAT,
    TS_V1_FMT,
)
from timestream.util import (
    PARAM_TYPE_ERR,
    dict_unicode_to_str,
)

#: Default timestream manifest extension
MANIFEST_EXT = "tsm"
LOG = logging.getLogger("timestreamlib")


def _ts_has_manifest(ts_path):
    """Checks if a timestream has a manifest.

    :param str ts_path: Path to the root of a timestream.
    :returns: The path to the manifest, or ``False``.
    """
    pattern = "{}{}*.{}".format(ts_path, os.sep, MANIFEST_EXT)
    manifest = glob.glob(pattern)
    if len(manifest):
        return manifest[0]
    else:
        return False


def ts_parse_date_path(img):
    basename = path.basename(img)
    fields = basename.split("_")[1:7]
    string_time = "_".join(fields)
    return ts_parse_date(string_time)


def ts_parse_date(dt):
    if isinstance(dt, datetime):
        return dt
    else:
        return datetime.strptime(dt, TS_DATE_FORMAT)


def ts_format_date(dt):
    if isinstance(dt, str):
        return dt
    elif isinstance(dt, datetime):
        return dt.strftime(TS_DATE_FORMAT)
    else:
        msg = PARAM_TYPE_ERR.format(param="dt", func="ts_format_date",
                                    type="datetime.datetime")
        LOG.error(msg)
        raise TypeError(msg)


def ts_guess_manifest(ts_path):
    """Conveience function to keep API compatibiliy. DEPRICATED"""
    warn("ts_guess_manifest is deprecated, use TimeStream class.",
         DeprecationWarning)
    return ts_guess_manifest_v1(ts_path)

def ts_guess_manifest_v1(ts_path):
    """Guesses the values of manifest fields in a timestream
    """
    # This whole thing's one massive fucking kludge. But it seems to work
    # pretty good so, well, whoop.
    retval = {}
    # get a sorted list of all files
    all_files = []
    for root, _, files in os.walk(ts_path):
        for fle in files:
            all_files.append(path.join(root, fle))
    all_files = sorted(all_files)
    # find most common extension, and assume this is the ext
    exts = collections.Counter(IMAGE_EXT_CONSTANTS)
    our_exts = map(lambda x: path.splitext(x)[1][1:], all_files)
    for ext in our_exts:
        try:
            exts[ext] += 1
        except KeyError:
            pass
    # most common gives list of tuples. [0] = (ext, count), [0][0] = ext
    retval["extension"] = exts.most_common(1)[0][0]
    # get image type from extension:
    try:
        retval["image_type"] = IMAGE_EXT_TO_TYPE[retval["extension"]]
    except KeyError:
        retval["image_type"] = None
    # Get list of images:
    images = ifilter(
        lambda x: path.splitext(x)[1][1:] == retval["extension"],
        all_files)
    # decode times from images:
    times = map(ts_parse_date_path, sorted(images))
    # get first and last dates:
    retval["start_datetime"] = ts_format_date(times[0])
    retval["end_datetime"] = ts_format_date(times[-1])
    # Get time intervals between images
    intervals = list()
    for iii in range(len(times) - 1):
        interval = times[iii + 1] - times[iii]
        intervals.append(interval.seconds / 60)
    retval["interval"] = max(min(intervals), 1)
    retval["name"] = path.basename(ts_path.rstrip(os.sep))
    # This is dodgy isn't it :S
    retval["missing"] = []
    # If any of this worked, it must be version 1
    retval["version"] = 1
    return retval


def all_files_with_ext_sorted(topdir, ext, cs=False):
    itr = all_files_with_ext(topdir, ext, cs)
    return sorted(list(itr))

def all_files_with_ext(topdir, ext, cs=False):
    """Iterates over files with extension ``ext`` recursively from ``topdir``
    """
    if not isinstance(topdir, str):
        msg = PARAM_TYPE_ERR.format(param="topdir",
                                    func="all_files_with_ext",  type="str")
        LOG.error(msg)
        raise ValueError(msg)
    if not isinstance(ext, str):
        msg = PARAM_TYPE_ERR.format(param="ext",
                                    func="all_files_with_ext",  type="str")
        LOG.error(msg)
        raise ValueError(msg)
    if not isinstance(cs, bool):
        msg = PARAM_TYPE_ERR.format(param="cs",
                                    func="all_files_with_ext",  type="bool")
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


def all_files_with_exts(topdir, exts, cs=False):
    """Creates a dictionary of {"ext": [files]} for each ext in exts
    """
    if not isinstance(exts, list):
        msg = PARAM_TYPE_ERR.format(param="exts",
                                    func="all_files_with_exts",  type="list")
        LOG.error(msg)
        raise ValueError(msg)
    ext_dict = {}
    for ext in exts:
        ext_dict[ext] = sorted(list(all_files_with_ext(topdir, ext, cs)))
    return ext_dict


def ts_get_manifest(ts_path):
    """Reads in or makes up a manifest for the timestream at ``ts_path``, and
    returns it as a ``dict``
    """
    manifest = _ts_has_manifest(ts_path)
    if manifest:
        try:
            LOG.debug("Manifest for {} exists at {}".format(ts_path, manifest))
            with open(manifest) as ifh:
                manifest = json.load(ifh)
            if isinstance(manifest, list):
                # it comes in as a list, we want a dict
                manifest = dict_unicode_to_str(manifest[0])
            else:
                manifest = dict_unicode_to_str(manifest)
            manifest = validate_timestream_manifest(manifest)
        except (IOError, OSError, ValueError, MultipleInvalid):
            # We can't read manifest or it's invalid
            manifest = None
    if not manifest:
        LOG.debug("Manifest for {} doesn't exist (yet)".format(ts_path))
        manifest = ts_guess_manifest(ts_path)
        manifest = validate_timestream_manifest(manifest)
    LOG.debug("Manifest for {} is {!r}".format(ts_path, manifest))
    return manifest


def ts_update_manifest(ts_path, ts_info):
    try:
        mfname = "{}.{}".format(ts_info["name"], MANIFEST_EXT)
        mfname = path.join(ts_path, mfname)
        with open(mfname, "w") as mffh:
            json.dump(ts_info, mffh)
    except:
        LOG.warn("Couldn't write JSON manifest for ts {}".format(ts_path))


def ts_iter_images(ts_path):
    """Iterate over a ``timestream`` in chronological order
    """
    manifest = ts_guess_manifest(ts_path)
    for fpath in all_files_with_ext(ts_path, manifest["extension"], cs=False):
        yield fpath


def ts_iter_images_all_times(ts_path):
    """Iterate over a ``timestream`` in chronological order, returning a tuple
    of (time, image)
    """
    for time in ts_iter_times(ts_path):
        yield (time, ts_get_image(ts_path, time))


def iter_date_range(start, end, interval):
    ts_range = end - start
    range_secs = int(ts_range.total_seconds())
    for offset in range(0, range_secs + 1, interval):
        yield start + timedelta(seconds=offset)


def ts_iter_times(ts_path):
    """Iterate over a ``timestream`` in chronological order
    """
    manifest = ts_get_manifest(ts_path)
    start = manifest["start_datetime"]
    end = manifest["end_datetime"]
    interval = manifest['interval'] * 60
    for time in iter_date_range(start, end, interval):
        yield time


def ts_get_image(ts_path, date, n=0, write_manifest=False):
    """Get the image path of the image in ``ts_path`` at ``date``
    """
    if isinstance(date, datetime):
        date = ts_format_date(date)
    if not isinstance(date, str):
        msg = PARAM_TYPE_ERR.format(param="date",
                                    func="ts_get_image",
                                    type="datetime.datetime or str")
        LOG.error(msg)
        raise ValueError(msg)
    if not isinstance(ts_path, str):
        msg = PARAM_TYPE_ERR.format(param="ts_path",
                                    func="all_files_with_ext",  type="str")
        LOG.error(msg)
        raise ValueError(msg)
    # Get ts_info from manifest
    ts_info = ts_get_manifest(ts_path)
    # Bail early if we know it's missing
    if date in ts_info["missing"]:
        return None
    # Format the path below the ts root (ts_path)
    relpath = _ts_date_to_path(ts_info["name"], ts_info["extension"],
                               ts_parse_date(date), n)
    # Join to make "absolute" path, i.e. path including ts_path
    abspath = path.join(ts_path, relpath)
    # not-so-silently fail if we can't find the image
    if path.exists(abspath):
        LOG.debug("Image at {} in {} is {}.".format(date, ts_path, abspath))
        return abspath
    else:
        LOG.warn("Expected image {} at {} in {} did not exist.".format(
            abspath, date, ts_path))
        if write_manifest:
            ts_info["missing"].append(date)
            ts_update_manifest(ts_path, ts_info)
            ts_info = ts_get_manifest(ts_path)
        return None


def _ts_date_to_path(ts_name, ts_ext, date, n=0):
    """Formats a string that should correspond to the relative (from
    ``ts_path``) path to the image at the given ``time``.
    """
    pth = TS_V1_FMT.format(tsname=ts_name, ext=ts_ext, n=n)
    return date.strftime(pth)


def ts_iter_numpy(fname_iter):
    """Take each image filename from ``fname_iter`` and yield the image as a
    numpy array, via ``cv2.imread``. The image is returned as a tuple of
    ``(img_path, img_matrix)``.
    """
    for img in fname_iter:
        try:
            import skimage.io as imgio
            yield (img, imgio.imread(img, plugin="freeimage"))
        except ImportError:
            LOG.warn("Couln't load scikit image io module. " +
                     "Raw images not supported")
            yield (img, cv2.imread(img))

def _is_ts_v2(ts_path):
    """Check if ``ts_path`` is a v2 timestream stored in netcdf4, i.e HDF5."""
    # This will need to be written properly, but for now we just check the
    # magic number.
    if not path.isfile(ts_path):
        return False
    with open(ts_path, "rb") as tmpfh:
        file_sig = tmpfh.read(8)
        return file_sig == '\x89\x48\x44\x46\x0d\x0a\x1a\x0a'

def _is_ts_v1(ts_path):
    """Check if ``ts_path`` is a v1 timestream stored as date-nested folders"""
    # Again, this should, in time, be rewritten to check the folder structure
    # fully, and check images exist etc.
    if not path.isdir(ts_path):
        LOG.debug("'{}' is not a directory, can't be v1 TS".format(ts_path))
        return False
    # we want to check all folders in the root path match the year
    walker = os.walk(ts_path)
    root, dirs, files = next(walker)
    is_ok = True
    for fldr in dirs:
        worked = False
        try:
            LOG.debug("Found folder with date {}".format(
                datetime.strptime(fldr, '%Y')))
            worked = True
        except ValueError:
            worked = False
        is_ok &= worked
    if is_ok:
        LOG.debug("'{}' contains year-based folders, assume its v1 TS".format(
                ts_path))
    else:
        LOG.debug("'{}' contains non-year-based folders, or has extras".format(
                ts_path))
    return is_ok
