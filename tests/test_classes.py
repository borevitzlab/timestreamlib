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
import numpy as np
from os import path
import shutil
from unittest import TestCase

from tests import helpers
from timestream import (
    TimeStream,
    TimeStreamImage,
)
from timestream.parse import (
    ts_format_date,
)
from timestream.parse.validate import (
    TS_MANIFEST_KEYS,
)


class TestTimeStreamStr(TestCase):

    """Test str(instance) of TimeStream classes."""

    def _check_ts_instance_ts_v1(self, ts_path):
        """Check members of a TimeStream class instance"""

    def test_timestream_str(self):
        """Test TimeStream str(instance) with good timestream"""
        inst = TimeStream()
        inst.load(helpers.FILES["timestream"])
        self.assertEqual(str(inst), helpers.TS_STR)


class TestTimeStreamLoad(TestCase):

    """Test loading of TimeStream classes. Tests read_metadata as well."""

    def _check_ts_instance_ts_v1(self, ts_path):
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
                             helpers.TS_DICT_PARSED[key])
        return inst

    def test_timestream_init(self):
        """Test TimeStream initialisation with good timestream"""
        self._check_ts_instance_ts_v1(
            helpers.FILES["timestream"])
        self._check_ts_instance_ts_v1(
            helpers.FILES["timestream_gaps"])
        self._check_ts_instance_ts_v1(
            helpers.FILES["timestream_datafldr"])
        self._check_ts_instance_ts_v1(
            helpers.FILES["timestream_imgdata"])

    def test_timestream_load_bad(self):
        """Test TimeStream initialisation with bad/non timestream"""
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.load(helpers.FILES["not_a_timestream"])
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.load(helpers.FILES["timestream_bad"])
        with self.assertRaises(TypeError):
            inst = TimeStream()
            inst.load(None)
        with self.assertRaises(ValueError):
            inst = TimeStream()
            inst.version = 42
            inst.load(helpers.FILES["timestream"])

    def test_read_metatdata_weird(self):
        """Do weird things to TimeStream instance and check methods raise"""
        inst = TimeStream()
        with self.assertRaises(RuntimeError):
            inst.read_metadata()
        inst.load(helpers.FILES["timestream"])
        del inst.path
        with self.assertRaises(AttributeError):
            inst.read_metadata()

    def test_load_jsons(self):
        inst = self._check_ts_instance_ts_v1(
            helpers.FILES["timestream_imgdata"])
        self.assertIn("has_data", inst.data)
        self.assertIs(inst.data["has_data"], True)
        for img_date_str in helpers.TS_DATES:
            self.assertIn(img_date_str, inst.image_data)
            self.assertIn("has_data", inst.image_data[img_date_str])
            self.assertIs(inst.image_data[img_date_str]["has_data"], True)


class TestTimeStreamInit(TestCase):

    """Test init of TimeStream classes"""

    def test_timestream_init_bad_params(self):
        """Test TimeStream initialisation with invalid parameters"""
        with self.assertRaises(ValueError):
            TimeStream("asdf")
        with self.assertRaises(ValueError):
            TimeStream(version=3)


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


class TestTimeStreamImagePathAssing(TestCase):

    """Test TimeStreamImage() path assignment"""

    def test_ts_image_path_assign(self):
        """Test TimeStreamImage. path assignment with valid parameters"""
        img = TimeStreamImage()
        img.path = helpers.TS_FILES_JPG[0]
        self.assertEqual(img.path, helpers.TS_FILES_JPG[0])

    def test_ts_image_path_assign_truncated(self):
        """Test TimeStreamImage path assignment with valid parameters"""
        img = TimeStreamImage()
        img.path = helpers.FILES["zeros_jpg"]
        self.assertEqual(img.path, helpers.FILES["zeros_jpg"])
        self.assertEqual(img.datetime, helpers.ZEROS_DATETIME)
        np.testing.assert_array_equal(img.pixels, helpers.ZEROS_PIXELS)

    def test_ts_image_path_assign_parent(self):
        """Test TimeStreamImage path assignment with valid parameters & parent"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream"])
        img = TimeStreamImage()
        img.parent_timestream = ts
        img.path = helpers.TS_FILES_JPG[0]
        self.assertEqual(img.path, helpers.TS_FILES_JPG[0])
        self.assertEqual(img.datetime, helpers.TS_DATES_PARSED[0])


class TestTimeStreamImageClone(TestCase):

    """Test TimeStreamImage().clone()"""

    def test_ts_image_clone(self):
        """Test TimeStreamImage.clone()"""
        img = TimeStreamImage()
        img.path = helpers.FILES["zeros_jpg"]
        cpy = img.clone()
        self.assertIsNot(cpy, img)
        self.assertIsNot(cpy.datetime, img.datetime)
        self.assertIsNot(cpy.data, img.data)
        self.assertEqual(cpy.data, img.data)
        self.assertIs(cpy._pixels, None)
        self.assertIs(cpy._timestream, None)
        self.assertIs(cpy._path, None)

    def test_ts_image_clone_all(self):
        """Test TimeStreamImage.clone(), cloning all members"""
        ts = TimeStream()
        img = TimeStreamImage()
        img.parent_timestream = ts
        img.path = helpers.FILES["zeros_jpg"]
        cpy = img.clone(True, True, True)
        self.assertIsNot(cpy, img)
        self.assertIsNot(cpy.datetime, img.datetime)
        self.assertEqual(cpy.datetime, img.datetime)
        self.assertIsNot(cpy.data, img.data)
        self.assertEqual(cpy.data, img.data)
        self.assertIsNot(cpy.pixels, img.pixels)
        np.testing.assert_array_equal(cpy.pixels, img.pixels)
        # TS should be copied as a refernce, hence *Is*, not Is Not
        self.assertIs(cpy.parent_timestream, img.parent_timestream)
        self.assertEqual(cpy.parent_timestream, img.parent_timestream)
        # Strings are cached, so no assertIsNot for path
        self.assertEqual(cpy.path, img.path)


class TestTimeStreamIterByFiles(TestCase):

    """Test TimeStream().iter_by_files()"""

    def test_iter_by_files(self):
        """Test TimeStream().iter_by_files with a good timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream"])
        res = ts.iter_by_files()
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            self.assertIsNot(image, None)
            self.assertEqual(image.path, helpers.TS_FILES_JPG[iii])
            self.assertEqual(image.datetime,
                             helpers.TS_DATES_PARSED[iii])
            self.assertIsNot(image.pixels, None)
            self.assertEqual(image.pixels.dtype, helpers.TS_JPG_DTYPE)
            self.assertEqual(image.pixels.shape, helpers.TS_JPG_SHAPE)


class TestTimeStreamIterByTimepoints(TestCase):

    """Test TimeStream().iter_by_timepoints"""

    def test_iter_by_timepoints_full(self):
        """Test TimeStream().iter_by_timepoints with a complete timestream"""
        ts = TimeStream()
        ts.load(helpers.FILES["timestream"])
        res = ts.iter_by_timepoints()
        self.assertTrue(isgenerator(res))
        for iii, image in enumerate(res):
            # Check lazy-loading
            self.assertIsNot(image, None)
            self.assertIsNone(image._pixels)
            self.assertEqual(image.path, helpers.TS_FILES_JPG[iii])
            self.assertEqual(image.datetime,
                             helpers.TS_DATES_PARSED[iii])
            self.assertIsNot(image.pixels, None)
            self.assertEqual(image.pixels.dtype, helpers.TS_JPG_DTYPE)
            self.assertEqual(image.pixels.shape, helpers.TS_JPG_SHAPE)

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
                self.assertEqual(0, len(image.pixels))
                continue
            self.assertIsNot(image, None)
            # Check lazy-loading
            self.assertIsNone(image._pixels)
            # We don't check path, as it's got a different timestream name
            self.assertEqual(image.datetime,
                             helpers.TS_DATES_PARSED[iii])
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
        self.assertDictEqual(ts.image_data, {})
        self.assertDictEqual(ts.data, {})

    def test_timestream_create_bad(self):
        ts = TimeStream()
        with self.assertRaises(ValueError):
            ts.create(self.tmp_path, version=3)
        with self.assertRaises(ValueError):
            ts.create("not_a/valid/path")
        with self.assertRaises(TypeError):
            ts.create(123)

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_path)
        except (OSError,):
            pass


class TestTimeStreamWrite(TestCase):

    def setUp(self):
        self.tmp_path = helpers.make_tmp_file()

    def test_timestream_write(self):
        ts = TimeStream()
        ts.version = 1
        ts.create(self.tmp_path, ext="jpg")
        self.assertEqual(ts.path, self.tmp_path)
        self.assertDictEqual(ts.image_data, {})
        self.assertDictEqual(ts.data, {})
        for _ in range(10):
            img = TimeStreamImage()
            arr = np.arange(300, dtype="uint8")
            arr = arr.reshape((10, 10, 3))
            date = dt.datetime.now()
            str_date = ts_format_date(date)
            img.pixels = arr
            img.datetime = date
            img.data["fake"] = True
            ts.write_image(img)
            self.assertIn(str_date, ts.image_data)
            self.assertDictEqual(img.data, ts.image_data[str_date])
            self.assertTrue(path.exists, img.path)

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_path)
        except (OSError,):
            pass
