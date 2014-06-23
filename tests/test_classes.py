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

import datetime as dt
from inspect import (
    isgenerator,
)
import json
import os
from os import path
import shutil
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
from timestream import (
    TimeStream,
    TimeStreamImage,
)
from timestream.parse import (
    _ts_has_manifest,
    ts_guess_manifest,
    all_files_with_ext,
    all_files_with_exts,
    ts_iter_images,
    ts_get_image,
    ts_parse_date,
    ts_parse_date_path,
    ts_format_date,
)
from timestream.parse.validate import (
    TS_MANIFEST_KEYS,
)

class TestTimeStreamLoad(TestCase):
    """Test loading of TimeStream classes. Tests read_metadata as well."""

    def _check_ts_instance_ts_manifold_v1(self, ts_path):
        """Check members of a TimeStream class instance"""
        inst = TimeStream()
        inst.load(ts_path)
        self.assertEqual(inst.path, ts_path)
        self.assertEqual(inst.version, 1)
        self.assertEqual(inst.name, path.basename(ts_path))
        for key in TS_MANIFEST_KEYS:
            if key == "name":
                continue
            self.assertEqual(getattr(inst, key),
                             helpers.TS_MANIFOLD_DICT_PARSED[key])

    def test_timestream_init(self):
        """Test TimeStream initialisation with good timestream"""
        self._check_ts_instance_ts_manifold_v1(
                helpers.FILES["timestream_manifold"])
        self._check_ts_instance_ts_manifold_v1(
                helpers.FILES["timestream_nomanifold"])

    def test_timestream_load_bad(self):
        """Test TimeStream initialisation with bad/non timestream"""
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.load(helpers.FILES["not_a_timestream"])
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.load(helpers.FILES["timestream_bad"])
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.load(None)
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.version = 42
            inst.load(helpers.FILES["timestream_manifold"])

    def test_read_metatdata_weird(self):
        """Do weird things to TimeStream instance and check methods raise"""
        inst = TimeStream()
        with self.assertRaises(RuntimeError):
            inst.read_metadata()
        inst.load(helpers.FILES["timestream_manifold"])
        del inst.path
        with self.assertRaises(RuntimeError):
            inst.read_metadata()


class TestTimeStreamInit(TestCase):
    """Test init of TimeStream classes"""

    def test_timestream_init_bad_params(self):
        """Test TimeStream initialisation with invalid parameters"""
        with self.assertRaises(ValueError):
            inst = TimeStream("")
        with self.assertRaises(ValueError):
            inst = TimeStream(ts_version=3)



class TestTimeStreamImageInit(TestCase):
    """Test setup of TimeStreamImage classes."""

    def test_image_init(self):
        """Test TimeStreamImage initialisation with no parameters"""
        img = TimeStreamImage()
        self.assertIs(img._timestream, None)
        self.assertIs(img._path, None)
        self.assertIs(img._datetime, None)
        self.assertIs(img._pixels, None)

    def test_image_init_with_date(self):
        """Test TimeStreamImage initialisation with valid datetime parameter"""
        date = dt.datetime.now()
        img = TimeStreamImage(date)
        self.assertIs(img._timestream, None)
        self.assertIs(img._path, None)
        self.assertEqual(img._datetime, date)
        self.assertIs(img._pixels, None)

    def test_image_init_bad_params(self):
        """Test TimeStreamImage initialisation with invalid parameters"""
        with self.assertRaises(TypeError):
            # Can't coerce int to datetime
            TimeStreamImage(1234)
        with self.assertRaises(ValueError):
            # Bad date format
            TimeStreamImage("2013_20")

class TestTimeStreamImageFromFile(TestCase):
    """Test TimeStreamImage().from_file()"""

    def test_ts_image_from_file(self):
        """Test TimeStreamImage.from_file() with valid parameters"""
        img = TimeStreamImage()
        img.from_file(helpers.TS_MANIFOLD_FILES_JPG[0])
        self.assertEqual(img.path, helpers.TS_MANIFOLD_FILES_JPG[0])
        self.assertEqual(img.datetime, helpers.TS_MANIFOLD_DATES_PARSED[0])

    def test_ts_image_from_file_parent(self):
        """Test TimeStreamImage.from_file() with valid parameters & parent"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_manifold"])
        img = TimeStreamImage()
        img.parent_timestream = ts
        img.from_file(helpers.TS_MANIFOLD_FILES_JPG[0])
        self.assertEqual(img.path, helpers.TS_MANIFOLD_FILES_JPG[0])
        self.assertEqual(img.datetime, helpers.TS_MANIFOLD_DATES_PARSED[0])

    def test_image_from_file_bad_params(self):
        """Test TimeStreamImage.from_file() with invalid parameters"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_manifold"])
        img = TimeStreamImage()
        with self.assertRaises(TypeError):
            img.from_file(123)
        with self.assertRaises(ValueError):
            img.from_file("")

class TestTimeStreamIterByFiles(TestCase):
    """Test TimeStream().iter_by_files()"""

    def test_iter_by_files(self):
        """Test TimeStream().iter_by_files with a good timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_manifold"])
        res = ts.iter_by_files()
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            self.assertEqual(image.path, helpers.TS_MANIFOLD_FILES_JPG[iii])
            self.assertEqual(image.datetime,
                             helpers.TS_MANIFOLD_DATES_PARSED[iii])
            self.assertEqual(image.pixels.dtype, helpers.TS_MANIFOLD_JPG_DTYPE)
            self.assertEqual(image.pixels.shape, helpers.TS_MANIFOLD_JPG_SHAPE)

class TestTimeStreamIterByTimepoints(TestCase):
    """Test TimeStream().iter_by_timepoints"""

    def test_iter_by_timepoints_full(self):
        """Test TimeStream().iter_by_timepoints with a complete timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_manifold"])
        res = ts.iter_by_timepoints()
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            # Check lazy-loading
            self.assertIsNone(image._pixels)
            self.assertEqual(image.path, helpers.TS_MANIFOLD_FILES_JPG[iii])
            self.assertEqual(image.datetime,
                             helpers.TS_MANIFOLD_DATES_PARSED[iii])
            self.assertEqual(image.pixels.dtype, helpers.TS_MANIFOLD_JPG_DTYPE)
            self.assertEqual(image.pixels.shape, helpers.TS_MANIFOLD_JPG_SHAPE)

    def test_iter_by_timepoints_withgaps(self):
        """Test TimeStream().iter_by_timepoints with a complete timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_gaps"])
        res = ts.iter_by_timepoints()
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            # Check lazy-loading
            self.assertIsNone(image._pixels)
            # We don't check path, as it's got a different timestream name
            self.assertEqual(image.datetime,
                             helpers.TS_GAPS_DATES_PARSED[iii])
            # We don't check pixels to save time. We know if this fails, it
            # will fail above, or be a problem in our data files which should
            # change the date and make the previous statement fail.

    def test_iter_by_timepoints_withgaps_no_rm_gaps(self):
        """Test TimeStream().iter_by_timepoints with a complete timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream_gaps"])
        res = ts.iter_by_timepoints(remove_gaps=False)
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            if iii in {3, 5}:
                # Missing images
                self.assertIsNone(image)
                continue
            # Check lazy-loading
            self.assertIsNone(image._pixels)
            # We don't check path, as it's got a different timestream name
            self.assertEqual(image.datetime,
                             helpers.TS_MANIFOLD_DATES_PARSED[iii])
            # We don't check pixels to save time. We know if this fails, it
            # will fail above, or be a problem in our data files which should
            # change the date and make the previous statement fail.

class TestTimeStreamCreate(TestCase):
    """Test TimeStream().create()"""
    def setUp(self):
        self.tmp_path = helpers.make_tmp_file()

    def test_timestream_create(self):
        ts = TimeStream()
        ts.version = 1
        ts.create(self.tmp_path)
        self.assertEqual(ts.path, self.tmp_path)

    def test_timestream_create_bad(self):
        ts = TimeStream()
        with self.assertRaises(ValueError):
            ts.create(self.tmp_path, ts_version=3)
        with self.assertRaises(ValueError):
            ts.create("not_a/valid/path")
        with self.assertRaises(TypeError):
            ts.create(123)

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_path)
        except (OSError,):
            pass
