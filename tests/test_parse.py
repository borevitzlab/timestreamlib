from inspect import (
        isgenerator,
        )
import json
from os import path
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
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

class TestTSHasManifest(TestCase):
    """Test function timestream.parse._ts_has_manifest"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_good_ts_with_manifold(self):
        """Test _ts_has_manifest with a TS with a manifold"""
        res = _ts_has_manifest(helpers.FILES["timestream_manifold"])
        self.assertEqual(res, path.join(helpers.FILES["timestream_manifold"],
                "BVZ0022-GC05L-CN650D-Cam07~fullres-orig.tsm"))

    def test_good_ts_with_no_manifold(self):
        """Test _ts_has_manifest with a TS without a manifold"""
        res = _ts_has_manifest(helpers.FILES["timestream_nomanifold"])
        self.assertFalse(res)

class TestAllFilesWithExt(TestCase):
    """Test function timestream.parse.all_files_with_ext"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_with_timestream_ext_jpg(self):
        res = all_files_with_ext(helpers.FILES["timestream_manifold"], "jpg")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_jpggccaps(self):
        res = all_files_with_ext(helpers.FILES["timestream_manifold"], "JPG")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_jpg_cs(self):
        res = all_files_with_ext(helpers.FILES["timestream_manifold"], "jpg",
                cs=True)
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, [])
        res = all_files_with_ext(helpers.FILES["timestream_manifold"], "JPG",
                cs=True)
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_xyz(self):
        res = all_files_with_ext(helpers.FILES["timestream_manifold"], "xyz")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, [])

    def test_with_emptydir_ext_xyz(self):
        res = all_files_with_ext(helpers.FILES["empty_dir"], "xyz")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
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

class TestAllFilesWithExts(TestCase):
    """Test function timestream.parse.all_files_with_exts"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_with_timestream_ext_jpg(self):
        res = all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg",])
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": helpers.TS_MANIFOLD_FILES_JPG})

    def test_with_timestream_ext_jpg_tsm(self):
        res = all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg", "tsm"])
        self.assertTrue(isinstance(res, dict))
        expt = {
            "jpg": helpers.TS_MANIFOLD_FILES_JPG,
            "tsm": helpers.TS_MANIFOLD_FILES_TSM,
            }
        self.assertDictEqual(res, expt)

    def test_with_timestream_ext_jpg_cs(self):
        # with incorrect capitialisation
        res = all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg",], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": []})
        # With correct capitilisation
        res = all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["JPG",], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"JPG": helpers.TS_MANIFOLD_FILES_JPG})

class TestIterImages(TestCase):
    """Test function timestream.parse.ts_iter_images"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_good_timestream_manifold(self):
        """Test ts_iter_images with a timestream with a manifold"""
        res = ts_iter_images(helpers.FILES["timestream_manifold"])
        self.assertTrue(isgenerator(res))
        self.assertListEqual(sorted(list(res)), helpers.TS_MANIFOLD_FILES_JPG)

class TestGuessManifest(TestCase):
    """Tests for timestream.parse.ts_guess_manifest"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_good_ts(self):
        expect = {
                "name": "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
                "start_datetime": "2013_10_30_03_00_00",
                "end_datetime": "2013_10_30_06_00_00",
                "version": 1,
                "image_type": "jpg",
                "extension": "JPG",
                "interval": 30,
                "missing": [],
                }
        got = ts_guess_manifest(helpers.FILES["timestream_manifold"])
        self.assertTrue(isinstance(got, dict))
        self.assertDictEqual(got, expect)

class TestGetImage(TestCase):
    """Test function timestream.parse.ts_get_image"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_get_image_good_str(self):
        """Test ts_get_image with a str date on a good timestream"""
        for iii in range(len(helpers.TS_MANIFOLD_DATES)):
            date = helpers.TS_MANIFOLD_DATES[iii]
            ts = helpers.FILES["timestream_manifold"]
            res = ts_get_image(ts, date)
            self.assertEqual(res, helpers.TS_MANIFOLD_FILES_JPG[iii])

    def test_get_image_good_datetime(self):
        """Test ts_get_image with a datetime obj on a good timestream"""
        for iii in range(len(helpers.TS_MANIFOLD_DATES)):
            date = ts_parse_date(helpers.TS_MANIFOLD_DATES[iii])
            ts = helpers.FILES["timestream_manifold"]
            res = ts_get_image(ts, date)
            self.assertEqual(res, helpers.TS_MANIFOLD_FILES_JPG[iii])

    def test_get_image_missing_str(self):
        """Test ts_get_image with a missing str date on a good timestream"""
        date = "2010_10_10_10_10_10"
        ts = helpers.FILES["timestream_manifold"]
        res = ts_get_image(ts, date)
        self.assertEqual(res, None)

    def test_get_image_missing_datetime(self):
        """Test ts_get_image with a missing datetime on a good timestream"""
        date = ts_parse_date("2010_10_10_10_10_10")
        ts = helpers.FILES["timestream_manifold"]
        res = ts_get_image(ts, date)
        self.assertEqual(res, None)

    def test_get_image_bad_params(self):
        """Test giving bad paramters to ts_get_image raises ValueError"""
        with self.assertRaises(ValueError):
            # bad ts_path param
            ts_get_image(None, helpers.TS_MANIFOLD_DATES[0])
        with self.assertRaises(ValueError):
            # bad date param
            ts_get_image(helpers.FILES["timestream_manifold"], None)
        with self.assertRaises(ValueError):
            # unparseable str date param
            ts_get_image(helpers.FILES["timestream_manifold"], "NOTADATE")
        with self.assertRaises(ValueError):
            # bad subsecond param
            ts_get_image(helpers.FILES["timestream_manifold"],
                    helpers.TS_MANIFOLD_DATES[0], n="this should be an int")
