from inspect import (
        isgenerator,
        )
import json
from os import path
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
from timestream.parse import (
        _ts_has_manifest,
        _guess_manifest_info,
        _all_files_with_ext,
        _all_files_with_exts,
        iter_timestream_images,
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
    """Test function timestream.parse._all_files_with_ext"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_with_timestream_ext_jpg(self):
        res = _all_files_with_ext(helpers.FILES["timestream_manifold"], "jpg")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_jpg_allcaps(self):
        res = _all_files_with_ext(helpers.FILES["timestream_manifold"], "JPG")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_jpg_cs(self):
        res = _all_files_with_ext(helpers.FILES["timestream_manifold"], "jpg",
                cs=True)
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, [])
        res = _all_files_with_ext(helpers.FILES["timestream_manifold"], "JPG",
                cs=True)
        res = sorted(list(res))
        self.assertListEqual(res, helpers.TS_MANIFOLD_FILES_JPG)

    def test_with_timestream_ext_xyz(self):
        res = _all_files_with_ext(helpers.FILES["timestream_manifold"], "xyz")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, [])

    def test_with_emptydir_ext_xyz(self):
        res = _all_files_with_ext(helpers.FILES["empty_dir"], "xyz")
        self.assertTrue(isgenerator(res))
        res = sorted(list(res))
        self.assertListEqual(res, [])

    def test_with_bad_param_types(self):
        # test with bad topdir
        a = _all_files_with_ext(12, "xyz")
        with self.assertRaises(ValueError):
            a = _all_files_with_ext(12, "xyz")
        # test with bad topdir
        with self.assertRaises(ValueError):
            _all_files_with_ext(".", 31)
        # test with bad cs
        with self.assertRaises(ValueError):
            _all_files_with_ext(".", "jpg", cs="No")

class TestAllFilesWithExts(TestCase):
    """Test function timestream.parse._all_files_with_exts"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_with_timestream_ext_jpg(self):
        res = _all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg",])
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": helpers.TS_MANIFOLD_FILES_JPG})

    def test_with_timestream_ext_jpg_tsm(self):
        res = _all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg", "tsm"])
        self.assertTrue(isinstance(res, dict))
        expt = {
            "jpg": helpers.TS_MANIFOLD_FILES_JPG,
            "tsm": helpers.TS_MANIFOLD_FILES_TSM,
            }
        self.assertDictEqual(res, expt)

    def test_with_timestream_ext_jpg_cs(self):
        # with incorrect capitialisation
        res = _all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["jpg",], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"jpg": []})
        # With correct capitilisation
        res = _all_files_with_exts(helpers.FILES["timestream_manifold"],
                ["JPG",], cs=True)
        self.assertTrue(isinstance(res, dict))
        self.assertDictEqual(res, {"JPG": helpers.TS_MANIFOLD_FILES_JPG})

class TestIterTimestreamImages(TestCase):
    """Test function timestream.parse.iter_timestream_images"""
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_good_timestream_manifold(self):
        """Test iter_timestream_images with a timestream with a manifold"""
        res = iter_timestream_images(helpers.FILES["timestream_manifold"])
        self.assertTrue(isgenerator(res))
        self.assertListEqual(sorted(list(res)), helpers.TS_MANIFOLD_FILES_JPG)

