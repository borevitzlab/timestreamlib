import json
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
from timestream.util import (
    imgmeta,  # module
    dict_unicode_to_str,
)


class TestGetExifDate(TestCase):
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_get_exif_date_jpg(self):
        r = imgmeta.get_exif_date(helpers.FILES["zeros_jpg"])
        self.assertEqual(r, helpers.ZEROS_DATETIME)

    def test_get_exif_date_tiff(self):
        r = imgmeta.get_exif_date(helpers.FILES["basic_tiff"])
        self.assertEqual(r, helpers.ZEROS_DATETIME)


class TestGetExifTag(TestCase):
    _multiprocess_can_split_ = True
    maxDiff = None

    def test_get_exif_tag_jpg(self):
        r = imgmeta.get_exif_tag(helpers.FILES["basic_jpg"], "DateTime")
        self.assertEqual(r, "2013:11:12 20:53:09")

    def test_get_exif_tag_jpg_raise(self):
        r = imgmeta.get_exif_tag(
            helpers.FILES["basic_jpg"],
            "DateTime",
            mode="raise"
        )
        self.assertEqual(r, "2013:11:12 20:53:09")

    def test_get_exif_tag_bad_tag(self):
        r = imgmeta.get_exif_tag(helpers.FILES["basic_jpg"], "NOTATAG")
        self.assertIsNone(r)

    def test_get_exif_tag_bad_tag_raise(self):
        with self.assertRaises(KeyError):
            r = imgmeta.get_exif_tag(helpers.FILES["basic_jpg"], "NOTATAG",
                                     mode="raise")
            self.assertIsNone(r)

    def test_get_exif_tag_tiff(self):
        r = imgmeta.get_exif_tag(helpers.FILES["basic_tiff"], "DateTime")
        self.assertEqual(r, "2013:11:12 20:53:09")

    def test_get_exif_tag_tiff_raise(self):
        r = imgmeta.get_exif_tag(
            helpers.FILES["basic_tiff"],
            "DateTime",
            mode="raise"
        )
        self.assertEqual(r, "2013:11:12 20:53:09")


class TestGetExifTags(TestCase):
    _multiprocess_can_split_ = True
    maxDiff = None

    def setUp(self):
        with open(helpers.FILES["basic_jpg_exif"]) as fh:
            self.exif_data_jpg = dict_unicode_to_str(json.load(fh))
        with open(helpers.FILES["basic_tiff_exif"]) as fh:
            self.exif_data_tiff = dict_unicode_to_str(json.load(fh))

    def test_get_exif_tags_jpg(self):
        r = imgmeta.get_exif_tags(helpers.FILES["basic_jpg"])
        self.assertDictEqual(r, self.exif_data_jpg)
        self.assertIn("DateTime", r)
        self.assertIn("Make", r)
        self.assertNotIn("NOTATAG", r)
        self.assertEqual(r["DateTime"], "2013:11:12 20:53:09")

    def test_get_exif_tags_jpg_raise(self):
        r = imgmeta.get_exif_tags(
            helpers.FILES["basic_jpg"],
            mode="raise"
        )
        self.assertDictEqual(r, self.exif_data_jpg)
        self.assertIn("DateTime", r)
        self.assertIn("Make", r)
        self.assertNotIn("NOTATAG", r)
        self.assertEqual(r["DateTime"], "2013:11:12 20:53:09")

    def test_get_exif_tags_tiff(self):
        r = imgmeta.get_exif_tags(helpers.FILES["basic_tiff"])
        self.assertDictEqual(r, self.exif_data_tiff)
        self.assertIn("DateTime", r)
        self.assertIn("Make", r)
        self.assertNotIn("NOTATAG", r)
        self.assertEqual(r["DateTime"], "2013:11:12 20:53:09")

    def test_get_exif_tags_tiff_raise(self):
        r = imgmeta.get_exif_tags(
            helpers.FILES["basic_tiff"],
            mode="raise"
        )
        self.assertDictEqual(r, self.exif_data_tiff)
        self.assertIn("DateTime", r)
        self.assertIn("Make", r)
        self.assertNotIn("NOTATAG", r)
        self.assertEqual(r["DateTime"], "2013:11:12 20:53:09")
