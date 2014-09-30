import json
import numpy as np
from unittest import TestCase

from timestream.util import (
    dict_unicode_to_str,
    jsonify_data,
    dejsonify_data,
    str2numpy,
    numpy2str,
)


class TestDictUnicodeToString(TestCase):

    """Tests for timestream.util.dict_unicode_to_str"""
    _multiprocess_can_split_ = True
    maxDiff = None

    unicode_dict = {
        u"A": u"b",
        u"B": u"c",
    }
    str_dict = {
        "A": "b",
        "B": "c",
    }
    mixed_dict = {
        u"A": "b",
        "B": u"c",
    }
    nested_dict = {
        u"A": u"b",
        u"B": u"c",
        u"list": [u"a", u"b"],
        u"dict": {u"a": u"b"},
        u"tuple": (u"a", u"b"),
    }
    str_nested_dict = {
        "A": "b",
        "B": "c",
        "list": ["a", "b"],
        "dict": {"a": "b"},
        "tuple": ("a", "b"),
    }

    def test_ucode2str_all_unicode(self):
        """Test timestream.util.dict_unicode_to_str with all unicode dict."""
        res = dict_unicode_to_str(self.unicode_dict)
        self.assertDictEqual(res, self.str_dict)
        res_item = res.popitem()
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))

    def test_ucode2str_mixed_unicode(self):
        """Test timestream.util.dict_unicode_to_str with mixed unicode dict."""
        res = dict_unicode_to_str(self.mixed_dict)
        self.assertDictEqual(res, self.str_dict)
        res_item = res.popitem()
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))

    def test_ucode2str_already_strs(self):
        """Test timestream.util.dict_unicode_to_str with non-unicode dict."""
        res = dict_unicode_to_str(self.str_dict)
        self.assertDictEqual(res, self.str_dict)
        res_item = res.popitem()
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))

    def test_ucode2str_nested(self):
        """Test timestream.util.dict_unicode_to_str with nested dict."""
        res = dict_unicode_to_str(self.nested_dict)
        self.assertDictEqual(res, self.str_nested_dict)
        # check the list is still a list, and it's values have been converted
        res_item = res["list"]
        self.assertTrue(isinstance(res_item, list))
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))
        # Ditto, but with a tuple
        res_item = res["tuple"]
        self.assertTrue(isinstance(res_item, tuple))
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))
        # check the dict has been recusively processed
        res_item = res["dict"]
        self.assertTrue(isinstance(res_item, dict))
        res_item = res_item.popitem()
        self.assertTrue(isinstance(res_item[0], str))
        self.assertTrue(isinstance(res_item[1], str))


class TestJsonifyDataDict(TestCase):

    """Test ts.util.jsonify_data"""

    def test_jsonify_primitive_types(self):
        """Test jsonify_data with primitive data types only"""
        dct = {"a": 1, "b": "2", "1": True, "31": None, }
        res = jsonify_data(dct)
        self.assertEqual(res, json.dumps(dct))
        back = dejsonify_data(res)
        self.assertDictEqual(dct, dict_unicode_to_str(back))

    def test_jsonify_nested(self):
        """Test jsonify_data with primitive data types only"""
        dct = {"a": 1, "b": "2", "1": True, "31": None,
               "dct": {"nesting": "isfun", },
               }
        res = jsonify_data(dct)
        self.assertEqual(res, json.dumps(dct))
        back = dejsonify_data(res)
        self.assertDictEqual(dct, dict_unicode_to_str(back))

    def test_jsonify_numpy(self):
        """Test jsonify_data with dict w/ numpy array"""
        dct = {"array": np.arange(10), }
        res = jsonify_data(dct)
        back = dejsonify_data(res)
        self.assertIsInstance(res, str)
        self.assertIsInstance(back, dict)
        self.assertIn("array", back)
        np.testing.assert_array_equal(dct["array"], back["array"])
        self.assertEqual(dct["array"].dtype, back["array"].dtype)
        self.assertEqual(dct["array"].shape, back["array"].shape)

    def test_jsonify_numpy_shaped(self):
        """Test jsonify_data with dict w/ 3d numpy array"""
        dct = {"array": np.arange(27).reshape((3, 3, 3)), }
        res = jsonify_data(dct)
        back = dejsonify_data(res)
        self.assertIsInstance(res, str)
        self.assertIsInstance(back, dict)
        self.assertIn("array", back)
        np.testing.assert_array_equal(dct["array"], back["array"])
        self.assertEqual(dct["array"].dtype, back["array"].dtype)
        self.assertEqual(dct["array"].shape, back["array"].shape)


class TestStrNumpy(TestCase):

    """Test ts.util.str2numpy and numpy2str"""

    def _arrays_eq(self, arr1, arr2):
        np.testing.assert_array_equal(arr1, arr2)
        self.assertEqual(arr1.dtype, arr2.dtype)
        self.assertEqual(arr1.shape, arr2.shape)

    def test_int64_flat(self):
        arr = np.arange(27)
        arr_str = numpy2str(arr)
        arr_loaded = str2numpy(arr_str)
        self._arrays_eq(arr, arr_loaded)

    def test_uint64_flat(self):
        arr = np.arange(27, dtype="uint64")
        arr_str = numpy2str(arr)
        arr_loaded = str2numpy(arr_str)
        self._arrays_eq(arr, arr_loaded)

    def test_int8_flat(self):
        arr = np.arange(27, dtype="int8")
        arr_str = numpy2str(arr)
        arr_loaded = str2numpy(arr_str)
        self._arrays_eq(arr, arr_loaded)

    def test_int64_3d(self):
        arr = np.arange(27)
        arr = arr.reshape((3, 3, 3))
        arr_str = numpy2str(arr)
        arr_loaded = str2numpy(arr_str)
        self._arrays_eq(arr, arr_loaded)

    def test_float_flat(self):
        arr = np.arange(27, dtype="float")
        arr_str = numpy2str(arr)
        arr_loaded = str2numpy(arr_str)
        self._arrays_eq(arr, arr_loaded)
