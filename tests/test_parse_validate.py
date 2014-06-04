import datetime as dt
from unittest import TestCase, skip, skipIf, skipUnless
from voluptuous import MultipleInvalid

from tests import helpers
from timestream.parse.validate import (
    validate_timestream_manifest,
)


class TestValidateTimestreamManfiest(TestCase):

    """Tests for ts.parse.validate.validate_timestream_manifest"""
    str_dict = {
        "name": "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
        "start_datetime": "2013_10_30_03_00_00",
        "end_datetime": "2013_10_30_06_00_00",
        "version": "1",
        "image_type": "jpg",
        "extension": "JPG",
        "interval": "30",
        "missing": [],
    }
    val_dict = {
        "name": "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
        "start_datetime": dt.datetime(2013, 10, 30, 3, 0, 0),
        "end_datetime": dt.datetime(2013, 10, 30, 6, 0, 0),
        "version": 1,
        "image_type": "jpg",
        "extension": "JPG",
        "interval": 30,
        "missing": [],
    }

    def test_validate_valid(self):
        """Test validate_timestream_manifest with valid manfests"""
        self.assertDictEqual(validate_timestream_manifest(self.str_dict),
                             self.val_dict)
        self.assertDictEqual(validate_timestream_manifest(self.val_dict),
                             self.val_dict)

    def test_validate_invalid(self):
        """Test validate_timestream_manifest with invalid manfests"""
        with self.assertRaises(TypeError):
            validate_timestream_manifest(None)
        with self.assertRaises(MultipleInvalid):
            validate_timestream_manifest({"A": "b", })
