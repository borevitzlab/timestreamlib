import datetime as dt
from inspect import (
    isgenerator,
)
import numpy as np
import os
from unittest import TestCase

from tests import helpers
from timestream.parse import (
    ts_guess_manifest,
    all_files_with_ext,
    all_files_with_exts,
    ts_iter_images,
    ts_get_image,
    ts_parse_date,
    read_image,
    RIException,
)


class TestAllFilesWithExt(TestCase):
    """Test function timestream.parse.all_files_with_ext"""
    _multiprocess_can_split_ = True
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        helpers.imgs_common_tsdir("setup", helpers.FILES["timestream"])

    def test_with_timestream_ext_jpg(self):
        res = all_files_with_ext(helpers.FILES["timestream"], "jpg")
        self.assertTrue(isgenerator(res))
        res = list(res)
        self.assertListEqual(res, helpers.TS_FILES_JPG)

    def test_with_timestream_ext_jpggccaps(self):
        res = all_files_with_ext(helpers.FILES["timestream"], "JPG")
        self.assertTrue(isgenerator(res))
        res = list(res)
        self.assertListEqual(res, helpers.TS_FILES_JPG)

    def test_with_timestream_ext_jpg_cs(self):
        res = all_files_with_ext(helpers.FILES["timestream"], "jpg",
                                 cs=True)
        self.assertTrue(isgenerator(res))
        res = list(res)
        self.assertListEqual(res, [])
        res = all_files_with_ext(helpers.FILES["timestream"], "JPG",
                                 cs=True)
        res = list(res)
        self.assertListEqual(res, helpers.TS_FILES_JPG)

    def test_with_timestream_ext_xyz(self):
        res = all_files_with_ext(helpers.FILES["timestream"], "xyz")
        self.assertTrue(isgenerator(res))
        res = list(res)
        self.assertListEqual(res, [])

    def test_with_emptydir_ext_xyz(self):
        res = all_files_with_ext(helpers.FILES["empty_dir"], "xyz")
        self.assertTrue(isgenerator(res))
        res = list(res)
        self.assertListEqual(res, [])

    def test_with_bad_param_types(self):
        # test with bad topdir
        with self.assertRaises(ValueError):
            list(all_files_with_ext(12, "xyz"))
        # test with bad topdir
        with self.assertRaises(ValueError):
            list(all_files_with_ext(".", 31))
        # test with bad cs
        with self.assertRaises(ValueError):
            list(all_files_with_ext(".", "jpg", cs="No"))

    @classmethod
    def tearDownClass(cls):
        helpers.imgs_common_tsdir("teardown", helpers.FILES["timestream"])


class TestAllFilesWithExts(TestCase):
    """Test function timestream.parse.all_files_with_exts"""
    _multiprocess_can_split_ = True
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        helpers.imgs_common_tsdir("setup", helpers.FILES["timestream"])

    def test_with_timestream_ext_jpg(self):
        res = all_files_with_exts(helpers.FILES["timestream"],
                                  ["jpg", ])
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": helpers.TS_FILES_JPG})

    def test_with_timestream_ext_jpg_cs(self):
        # with incorrect capitialisation
        res = all_files_with_exts(helpers.FILES["timestream"],
                                  ["jpg", ], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": []})
        # With correct capitilisation
        res = all_files_with_exts(helpers.FILES["timestream"],
                                  ["JPG", ], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"JPG": helpers.TS_FILES_JPG})

    @classmethod
    def tearDownClass(cls):
        helpers.imgs_common_tsdir("teardown", helpers.FILES["timestream"])


class TestIterImages(TestCase):
    """Test function timestream.parse.ts_iter_images"""
    _multiprocess_can_split_ = True
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        helpers.imgs_common_tsdir("setup", helpers.FILES["timestream"])

    def test_good_timestream(self):
        """Test ts_iter_images with a timestream with a manifold"""
        res = ts_iter_images(helpers.FILES["timestream"])
        self.assertTrue(isgenerator(res))
        self.assertListEqual(list(res), helpers.TS_FILES_JPG)

    @classmethod
    def tearDownClass(cls):
        helpers.imgs_common_tsdir("teardown", helpers.FILES["timestream"])


class TestGuessManifest(TestCase):
    """Tests for timestream.parse.ts_guess_manifest"""
    _multiprocess_can_split_ = True
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        helpers.imgs_common_tsdir("setup", helpers.FILES["timestream"])

    def test_good_ts(self):
        got = ts_guess_manifest(helpers.FILES["timestream"])
        self.assertTrue(isinstance(got, dict))
        self.assertDictEqual(got, helpers.TS_DICT)

    def test_trailing_slash(self):
        got = ts_guess_manifest(helpers.FILES["timestream"] + os.sep)
        self.assertTrue(isinstance(got, dict))
        self.assertDictEqual(got, helpers.TS_DICT)

    @classmethod
    def tearDownClass(cls):
        helpers.imgs_common_tsdir("teardown", helpers.FILES["timestream"])


class TestGetImage(TestCase):
    """Test function timestream.parse.ts_get_image"""
    _multiprocess_can_split_ = True
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        helpers.imgs_common_tsdir("setup", helpers.FILES["timestream"])

    def test_get_image_good_str(self):
        """Test ts_get_image with a str date on a good timestream"""
        for iii in range(len(helpers.TS_DATES)):
            date = helpers.TS_DATES[iii]
            ts = helpers.FILES["timestream"]
            res = ts_get_image(ts, date)
            self.assertEqual(res, helpers.TS_FILES_JPG[iii])

    def test_get_image_good_datetime(self):
        """Test ts_get_image with a datetime obj on a good timestream"""
        for iii in range(len(helpers.TS_DATES)):
            date = ts_parse_date(helpers.TS_DATES[iii])
            ts = helpers.FILES["timestream"]
            res = ts_get_image(ts, date)
            self.assertEqual(res, helpers.TS_FILES_JPG[iii])

    def test_get_image_missing_str(self):
        """Test ts_get_image with a missing str date on a good timestream"""
        date = "2010_10_10_10_10_10"
        ts = helpers.FILES["timestream"]
        res = ts_get_image(ts, date)
        self.assertEqual(res, None)

    def test_get_image_missing_datetime(self):
        """Test ts_get_image with a missing datetime on a good timestream"""
        date = ts_parse_date("2010_10_10_10_10_10")
        ts = helpers.FILES["timestream"]
        res = ts_get_image(ts, date)
        self.assertEqual(res, None)

    def test_get_image_bad_params(self):
        """Test giving bad paramters to ts_get_image raises ValueError"""
        with self.assertRaises(ValueError):
            # bad ts_path param
            ts_get_image(None, helpers.TS_DATES[0])
        with self.assertRaises(ValueError):
            # bad date param
            ts_get_image(helpers.FILES["timestream"], None)
        with self.assertRaises(ValueError):
            # unparseable str date param
            ts_get_image(helpers.FILES["timestream"], "NOTADATE")
        with self.assertRaises(ValueError):
            # bad subsecond param
            ts_get_image(helpers.FILES["timestream"],
                         helpers.TS_DATES[0], n="this should be an int")

    @classmethod
    def tearDownClass(cls):
        helpers.imgs_common_tsdir("teardown", helpers.FILES["timestream"])


class TestParseDate(TestCase):
    """Test function timestream.parse.ts_parse_date"""

    def test_parse_date_valid(self):
        """Test timestream.parse.ts_parse_date with a valid date"""
        date_str = "2013_12_11_10_09_08"
        date_obj = dt.datetime(2013, 12, 11, 10, 9, 8)
        self.assertEqual(ts_parse_date(date_str), date_obj)
        # ensure we can pass a datetime and have it silently returned.
        self.assertEqual(ts_parse_date(date_obj), date_obj)

    def test_parse_date_invalid(self):
        """Test timestream.parse.ts_parse_date with a valid date"""
        # Bad format
        date_str = "2013-12-11-10-09-08"
        with self.assertRaises(ValueError):
            ts_parse_date(date_str)
        # Bad date
        date_str = "2013_14_11_10_09_08"
        with self.assertRaises(ValueError):
            ts_parse_date(date_str)
        # Missing time
        date_str = "2013_12_11"
        with self.assertRaises(ValueError):
            ts_parse_date(date_str)


class TestReadImage(TestCase):
    """Test function timestream.parse.read_image"""

    def test_read_image_missing(self):
        """check a warning is raised on non-existant image"""
        with self.assertRaises(RIException):
            read_image("nonexistant_image.jpg")

    def test_read_image_zeros(self):
        """check read_image reads in a png correctly"""
        path = helpers.FILES["zeros_jpg"]
        np.testing.assert_array_equal(read_image(path), helpers.ZEROS_PIXELS)
