import json
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
from timestream.util import (
    dict_unicode_to_str,
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
