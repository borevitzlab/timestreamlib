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
.. module:: timestream
    :platform: Unix, Windows
    :synopsis: A python library to manipulate TimeStreams

.. moduleauthor:: Kevin Murray <spam@kdmurray.id.au>
"""

from copy import deepcopy
import cv2
import datetime as dt
import json
import logging
import numpy as np
import os
from os import path
from sys import stderr

from timestream.parse.validate import (
    validate_timestream_manifest,
)
from timestream.parse import (
    _is_ts_v1,
    _is_ts_v2,
    _ts_date_to_path,
    ts_guess_manifest_v1,
    all_files_with_ext,
    ts_parse_date_path,
    ts_parse_date,
    ts_format_date,
    iter_date_range,
    ts_get_image,
    ts_make_dirs,
)
from timestream.parse.validate import (
    IMAGE_EXT_TO_TYPE,
    TS_MANIFEST_KEYS,
)
from timestream.util.imgmeta import (
    get_exif_date,
)


# versioneer
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

LOG = logging.getLogger("timestreamlib")
NOW = dt.datetime.now()


def setup_module_logging(level=logging.DEBUG, handler=logging.StreamHandler,
                         stream=stderr):
    """Setup debug console logging. Designed for interactive use."""
    log = logging.getLogger("timestreamlib")
    fmt = logging.Formatter('%(asctime)s: %(message)s', '%H:%M:%S')
    if stream is None:
        stream = open("/dev/null", "w")
    cons = handler(stream=stream)
    cons.setLevel(level)
    cons.setFormatter(fmt)
    log.addHandler(cons)
    log.setLevel(level)


class TimeStream(object):
    """A TimeStream, including metadata and parsers"""
    _path = None
    _version = None
    _name = None
    version = None
    start_datetime = None
    end_datetime = None
    image_type = None
    extension = None
    interval = None
    image_data = {}
    data = {}
    image_db_path = None
    db_path = None
    data_dir = None

    def __init__(self, version=None):
        # Store version
        if version is None:
            return
        else:
            self.version = version

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        if not isinstance(version, int) or version < 1 or version > 2:
            msg = "Invalid TimeStream version {}.".format(repr(version))
            msg += " Must be an int, 1 or 2"
            LOG.error(msg)
            raise ValueError(msg)
        self._version = version

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if not isinstance(name, str):
            msg = "Timestream name must be a str"
            LOG.error(msg)
            raise TypeError(msg)
        if '_' in name:
            msg = "Timestream name can't contain _. '{}' does".format(name)
            LOG.error(msg)
            raise ValueError(msg)
        self._name = name

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, ts_path):
        """Store the root path of this timestream"""
        # Store root path
        if not isinstance(ts_path, str):
            msg = "Timestream path must be a str"
            LOG.error(msg)
            raise TypeError(msg)
        ts_path = ts_path.rstrip(os.sep)
        # This is required to ensure that path.dirname() of timestreams with
        # relative paths rooted at the current directory returns ".", not "",
        # or the timestream itself.
        dotslash = ".{}".format(os.sep)
        if not ts_path.startswith(os.sep):
            if not ts_path.startswith(dotslash):
                ts_path = "{}{}".format(dotslash, ts_path)
        self._path = ts_path
        self.data_dir = path.join(self._path, "_data")
        if (not path.isdir(self.data_dir)) and path.isdir(ts_path):
            os.mkdir(self.data_dir)

        self.image_db_path = path.join(self.data_dir, "image_data.json")
        self.db_path = path.join(self.data_dir, "timestream_data.json")

    @path.deleter
    def path(self):
        del self._path

    def load(self, ts_path):
        """Load a timestream from ``ts_path``, reading metadata"""
        self.path = ts_path
        if not path.exists(self.path):
            msg = "Timestream at {} does not exsit".format(self.path)
            LOG.error(msg)
            raise ValueError(msg)
        try:
            with open(self.image_db_path) as db_fh:
                self.image_data = json.load(db_fh)
        except IOError:
            self.image_data = {}
        try:
            with open(self.db_path) as db_fh:
                self.data = json.load(db_fh)
        except IOError:
            self.data = {}
        self.read_metadata()

    def create(self, ts_path, version=1, ext="png", type=None, start=NOW,
               end=NOW, name=None):
        self.version = version
        if not isinstance(ts_path, str):
            msg = "Timestream path must be a str"
            LOG.error(msg)
            raise TypeError(msg)
        # Basename will trip over the trailing slash, if given.
        ts_path = ts_path.rstrip(os.sep)
        # This is required to ensure that path.dirname() of timestreams with
        # relative paths rooted at the current directory returns ".", not "",
        # or the timestream itself.
        dotslash = ".{}".format(os.sep)
        if not ts_path.startswith(os.sep):
            if not ts_path.startswith(dotslash):
                ts_path = "{}{}".format(dotslash, ts_path)
        if not path.exists(path.dirname(ts_path)):
            msg = "Cannot create {}. Parent dir doesn't exist".format(ts_path)
            LOG.error(msg)
            raise ValueError(msg)
        if not path.exists(ts_path):
            if self.version == 1:
                os.mkdir(ts_path)
        self.path = ts_path
        self.extension = ext
        self.start_datetime = start
        self.end_datetime = end
        if name is None:
            self.name = path.basename(ts_path)
        if type:
            self.image_type = type
        else:
            try:
                self.image_type = IMAGE_EXT_TO_TYPE[ext]
            except KeyError:
                msg = "Invalid image ext {}".format(ext)
                LOG.error(msg)
                raise ValueError(msg)

    def write_image(self, image, overwrite_mode="skip"):
        if not self.name:
            msg = "write_image() must be called on instance with valid name"
            LOG.error(msg)
            raise RuntimeError(msg)
        if not self.path:
            msg = "write_image() must be called on instance with valid path"
            LOG.error(msg)
            raise RuntimeError(msg)
        if not isinstance(image, TimeStreamImage):
            msg = "write_image() must be given an instance of TimeStreamImage"
            LOG.error(msg)
            raise TypeError(msg)
        if not isinstance(overwrite_mode, str):
            msg = "overwrite_mode must be a str"
            LOG.error(msg)
            raise TypeError(msg)
        if overwrite_mode not in {"skip", "increment", "overwrite", "raise"}:
            msg = "Invalid overwrite_mode {}.".format(overwrite_mode)
            LOG.error(msg)
            raise ValueError(msg)
        if image.pixels is None:
            msg = "Image must have pixels to be able to be written"
            LOG.error(msg)
            raise ValueError(msg)

        if self.version == 1:
            fpath = _ts_date_to_path(self.name, self.extension,
                                     image.datetime, image.subsec)
            fpath = path.join(self.path, fpath)
            if path.exists(fpath):
                if overwrite_mode == "skip":
                    return
                elif overwrite_mode == "increment":
                    while path.exists(fpath) and image.subsec < 100:
                        image.subsec += 1
                        fpath = _ts_date_to_path(self.name, image.datetime,
                                                 image.subsec)
                    if path.exists(fpath):
                        msg = "Too many images at timepoint {}".format(
                            ts_format_date(image.datetime))
                        LOG.error(msg)
                        raise ValueError(msg)
                elif overwrite_mode == "overwrite":
                    # We don't do anything here if we want to overwrite
                    pass
                elif overwrite_mode == "raise":
                    msg = "Image already exists at {}".format(fpath)
                    LOG.error(msg)
                    raise ValueError(msg)
            # Update timestream if required
            if image.datetime > self.end_datetime:
                self.end_datetime = image.datetime
            if image.datetime < self.start_datetime:
                self.start_datetime = image.datetime
            self.image_data[ts_format_date(image.datetime)] = image.data
            self.write_metadata()
            # Actually write image
            ts_make_dirs(fpath)
            cv2.imwrite(fpath, image.pixels[:, :, ::-1])
        else:
            raise NotImplementedError("v2 timestreams not implemented yet")

    def write_metadata(self):
        if not self.path:
            msg = "write_metadata() must be called on instance with valid path"
            LOG.error(msg)
            raise RuntimeError(msg)
        if self.version == 1:
            with open(self.image_db_path, "w") as db_fh:
                json.dump(self.image_data, db_fh)
            with open(self.db_path, "w") as db_fh:
                json.dump(self.data, db_fh)
        else:
            raise NotImplementedError("v2 metadata not implemented")

    def read_metadata(self):
        """Guesses the metadata fields of a timestream, v1 or v2."""
        if not self.path:
            msg = "read_metadata() must be called on instance with valid path"
            LOG.error(msg)
            raise RuntimeError(msg)
        # Detect version
        if self.version is None:
            if _is_ts_v1(self.path):
                self.version = 1
            elif _is_ts_v2(self.path):
                self.version = 2
            else:
                msg = "{} is neither a v1 nor v2 timestream.".format(self.path)
                LOG.error(msg)
                raise ValueError(msg)
        if self.version == 1:
            manifest = ts_guess_manifest_v1(self.path)
            self._set_metadata(**manifest)
            for key in TS_MANIFEST_KEYS:
                self.data[key] = manifest[key]
        elif self.version == 2:
            raise NotImplementedError(
                "No OOP interface to timestream v2 format")
        else:
            msg = "{} is neither a v1 nor v2 timestream.".format(self.path)
            LOG.error(msg)
            raise ValueError(msg)

    def _set_metadata(self, **metadata):
        """Sets class members from ``metadata`` dict, first validating it."""
        metadata = validate_timestream_manifest(metadata)
        for datum, value in metadata.items():
            setattr(self, datum, value)

    def iter_by_files(self):
        for fpath in all_files_with_ext(
                self.path, self.extension, cs=False):
            img = TimeStreamImage()
            img.parent_timestream = self
            img.from_file(fpath)
            img_date = ts_format_date(img.datetime)
            try:
                img.data = self.image_data[img_date]
            except KeyError:
                img.data = {}
            yield img

    def iter_by_timepoints(self, remove_gaps=True, start=None, end=None,
                           interval=None):
        """
        Iterate over a TimeStream in chronological order, yielding a
        TimeStreamImage instance for each timepoint. If ``remove_gaps`` is
        False, yield None for missing images.
        """
        if not start or start < self.start_datetime:
            start = self.start_datetime
        if not end or end < self.end_datetime:
            end = self.end_datetime
        if not interval:
            interval = self.interval * 60
        # iterate thru times
        for time in iter_date_range(start, end, interval):
            # Format the path below the ts root
            relpath = _ts_date_to_path(self.name, self.extension, time, 0)
            # Join to make "absolute" path, i.e. path including ts_path
            img_path = path.join(self.path, relpath)
            # not-so-silently fail if we can't find the image
            if path.exists(img_path):
                LOG.debug("Image at {} in {} is {}.".format(time, self.path,
                                                            img_path))
            else:
                LOG.debug("Expected image {} at {} did not exist.".format(
                    img_path, time, self.path))
                img_path = None
            if remove_gaps and img_path is None:
                continue
            elif img_path is None:
                yield None
            else:
                img = TimeStreamImage(datetime=time)
                img.parent_timestream = self
                img.from_file(img_path)
                img_date = ts_format_date(img.datetime)
                try:
                    img.data = self.image_data[img_date]
                except KeyError:
                    img.data = {}
                yield img


class TimeStreamImage(object):
    _timestream = None
    _path = None
    _datetime = None
    _pixels = None
    subsec = 0
    data = {}

    def __init__(self, datetime=None):
        if datetime:
            self.datetime = datetime

    def from_file(self, img_path):
        self.path = img_path
        try:
            self.datetime = ts_parse_date_path(img_path)
        except ValueError:
            self.datetime = get_exif_date(img_path)

    def clone(self, copy_pixels=False, copy_path=False, copy_timestream=False):
        """
        Make an exact copy of ``self`` in a new instance. By default, the
        members pixels, path and timestream are not copied. All members are
        copied by value, not by reference, so can be changed.
        """
        new = TimeStreamImage()
        new.datetime = deepcopy(self.datetime)
        new.data = deepcopy(self.data)
        new.subsec = self.subsec
        if copy_pixels and self.pixels is not None:
            new.pixels = self.pixels.copy()
        if copy_timestream:
            new.parent_timestream = self.parent_timestream
        if copy_path:
            new.path = self.path
        return new

    @property
    def path(self):
        if self._path:
            return self._path
        if self._timestream:
            ts_path = None
            try:
                if self._timestream.version == 1:
                    ts_path = self._timestream.path
            except AttributeError:
                pass
            if not ts_path or not self._datetime:
                return None
            subpath = _ts_date_to_path(self._timestream.name,
                                       self._timestream.extension,
                                       self._datetime)
            self._path = path.join(ts_path, subpath)
            return self._path
        return None

    @path.setter
    def path(self, img_path):
        # Set image path
        if not isinstance(img_path, str):
            msg = "Image path must be an instance of str."
            LOG.error(msg)
            raise TypeError(msg)
        if not path.isfile(img_path):
            msg = "No file exists at {}. ".format(img_path) + \
                  "``img_path`` must point to an image file"
            LOG.error(msg)
            raise ValueError(msg)
        self._path = img_path

    @property
    def parent_timestream(self):
        return self._timestream

    @parent_timestream.setter
    def parent_timestream(self, ts):
        if not isinstance(ts, TimeStream):
            msg = "Parent timestream must be an instance of TimeStream."
            LOG.error(msg)
            raise TypeError(msg)
        self._timestream = ts

    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, dte):
        self._datetime = ts_parse_date(dte)

    @datetime.deleter
    def datetime(self):
        del self._datetime

    @property
    def pixels(self):
        """
        Lazy-loading pixel property.

        The path of the image must be set before the pixels property is
        accessed, or things will error out with RuntimeError.

        The colour dimension maps to:
            [:,:,RGB]
        not what OpenCV gives us, which is:
            [:,:,BGR]
        So we convert OpenCV back to reality and sanity.
        """
        if self._pixels is None:
            if not self.path:
                msg = "``path`` member of TimeStreamImage must be set " + \
                      "before ``pixels`` member is accessed."
                LOG.error(msg)
                raise RuntimeError(msg)
            try:
                import skimage.io
                try:
                    self._pixels = skimage.io.imread(self.path,
                                                     plugin="freeimage")
                except (RuntimeError, ValueError) as exc:
                    LOG.error(str(exc))
                    self._pixels = None
            except ImportError:
                LOG.warn("Couln't load scikit image io module. " +
                         "Raw images will not be loaded correctly")
                self._pixels = cv2.imread(self.path)[:, :, ::-1]
        return self._pixels

    @pixels.setter
    def pixels(self, value):
        if not isinstance(value, np.ndarray):
            msg = "Cant set TimeStreamImage.pixels to something not an ndarray"
            LOG.error(msg)
            raise TypeError(msg)
        self._pixels = value

    @pixels.deleter
    def pixels(self):
        del self._pixels
