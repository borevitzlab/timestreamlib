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

import collections
import datetime as dt
import logging
import os
from os import path
from sys import stderr

from timestream.parse.validate import (
    validate_timestream_manifest,
)
from timestream.parse import (
    _is_ts_v1,
    _is_ts_v2,
    ts_guess_manifest_v1,
    all_files_with_ext,
    ts_parse_date_path,
    ts_parse_date,
    iter_date_range,
    ts_get_image,
    #ts_guess_manifest_v2,
)

LOG = logging.getLogger("timestreamlib")

def setup_debug_logging(level=logging.DEBUG, handler=logging.StreamHandler,
                        stream=stderr):
    log = logging.getLogger("timestreamlib")
    fmt = logging.Formatter('%(asctime)s: %(message)s', '%H:%M:%S')
    if stream is None:
        stream = open("/dev/null", "w")
    ch = handler(stream=stream)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    log.addHandler(ch)
    log.setLevel(level)

class TimeStream(object):
    path = None
    version = None
    name = None
    version = None
    start_datetime = None
    end_datetime = None
    image_type = None
    extension = None
    interval = None

    def __init__(self, ts_path, ts_version=1):
        # Store root path
        if not isinstance(ts_path, str) or not path.exists(ts_path):
            msg = "Timestream at {} does not exsit".format(ts_path)
            LOG.error(msg)
            raise ValueError(msg)
        else:
            self.path = ts_path
        # Store version
        if not isinstance(ts_version, int) or ts_version < 1 or ts_version > 2:
            msg = "Invalid TimeStream version {}.".format(repr(ts_version)) + \
                  " Must be an int, 1 or 2"
            LOG.error(msg)
            raise ValueError(msg)
        else:
            self.version = ts_version
        self.read_metadata()

    def read_metadata(self):
        """Guesses the metadata fields of a timestream, v1 or v2."""
        if not self.path:
            msg = "read_metadata() must be called on initialised instance"
            LOG.error(msg)
            raise RuntimeError(msg)
        ## Detect version
        if _is_ts_v1(self.path):
            self.version = 1
            self._set_metadata(ts_guess_manifest_v1(self.path))
        elif _is_ts_v2(self.path):
            self.version = 2
            self._set_metadata(ts_guess_manifest_v2(self.path))
        else:
            msg = "{} is neither a v1 nor v2 timestream.".format(self.path)
            LOG.error(msg)
            raise ValueError(msg)

    def _set_metadata(self, metadata):
        """Sets class members from ``metadata`` dict, first validating it."""
        metadata = validate_timestream_manifest(metadata)
        for datum, value in metadata.items():
            setattr(self, datum, value)

    def iter_by_files(self):
        for fpath in all_files_with_ext(self.path, self.extension, cs=False):
            yield TimeStreamImage(self, fpath)

    def iter_by_timepoints(self, remove_gaps=True):
        """
        Iterate over a TimeStream in chronological order, yielding a
        TimeStreamImage instance for each timepoint. If ``remove_gaps`` is
        False, yield None for missing images.
        """
        start = self.start_datetime
        end = self.end_datetime
        interval = self.interval * 60
        for time in iter_date_range(start, end, interval):
            img = ts_get_image(self.path, time)
            if remove_gaps and img is None:
                continue
            elif img is None:
                yield None
            else:
                yield TimeStreamImage(self, img, datetime=time)


class TimeStreamImage(object):
    timestream = None
    path = None
    _datetime = None
    _pixels = None
    _datetime = None

    def __init__(self, ts, img_path, datetime=None):
        if not isinstance(ts, TimeStream):
            msg = "Parent timestream must be an instance of TimeStream."
            LOG.error(msg)
            raise TypeError(msg)
        self.timestream = ts
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
        self.path = img_path
        if datetime:
            self.datetime = datetime
        else:
            self.datetime = ts_parse_date_path(img_path)

    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, dte):
        self._datetime = ts_parse_date(dte)

    @datetime.deleter
    def datetime(self):
        del(self._datetime)

    @property
    def pixels(self):
        """
        Lazy-loading pixel property.

        The path of the image must be set before the pixels property is
        accessed, or things will error out with RuntimeError.
        """
        if not self.path:
            msg = "``path`` member of TimeStreamImage must be set " + \
                  "before ``pixels`` member is accessed."
            LOG.error(msg)
            raise RuntimeError(msg)
        if self._pixels is None:
            try:
                import skimage.io
                self._pixels = skimage.io.imread(self.path,
                                                 plugin="freeimage")
            except ImportError:
                LOG.warn("Couln't load scikit image io module. " +
                         "Raw images not supported")
                self._pixels = cv2.imread(self.path)
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
        del(self._pixels)
