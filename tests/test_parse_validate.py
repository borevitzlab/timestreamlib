import datetime as dt
from unittest import TestCase
from voluptuous import MultipleInvalid

from timestream.parse.validate import (
    validate_timestream_manifest,
    v_date,
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


class TestDateValidators(TestCase):

    """Tests for misc date format validators"""

    def test_v_date_invalid(self):
        """Test v_date validator with invalid dates"""
        # standard date format
        date_str = "2013_44_01"
        with self.assertRaises(ValueError):
            v_date(date_str)
        # with different date format
        date_str = "2013-44-01"
        with self.assertRaises(ValueError):
            v_date(date_str)

    def test_v_date_valid(self):
        """Test v_date validator with valid dates"""
        # standard date format
        date_str = "2013_03_01"
        self.assertEqual(v_date(date_str), dt.datetime(2013, 3, 1))
        date_obj = dt.datetime(2013, 3, 1)
        self.assertEqual(v_date(date_obj), date_obj)
        # with different date format
        date_str = "2013-03-01"
        self.assertEqual(v_date(date_str, format="%Y-%m-%d"),
                         dt.datetime(2013, 3, 1))
