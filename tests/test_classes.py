import datetime as dt
from inspect import (
    isgenerator,
)
import json
import os
from os import path
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

class TestTimeStreamInit(TestCase):
    """Test setup of TimeStream classes. Tests read_metadata as well."""

    def _check_ts_instance_ts_manifold_v1(self, ts_path):
        """Check members of a TimeStream class instance"""
        inst = TimeStream(ts_path)
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

    def test_timestream_init_bad(self):
        """Test TimeStream initialisation with bad/non timestream"""
        with self.assertRaises(ValueError):
            inst = TimeStream(helpers.FILES["not_a_timestream"])
        with self.assertRaises(ValueError):
            inst = TimeStream(helpers.FILES["timestream_bad"])

    def test_timestream_init_bad_params(self):
        """Test TimeStream initialisation with invalid parameters"""
        with self.assertRaises(ValueError):
            inst = TimeStream(None)
        with self.assertRaises(ValueError):
            inst = TimeStream("")
        with self.assertRaises(ValueError):
            inst = TimeStream(helpers.FILES["timestream_bad"], ts_version=None)
        with self.assertRaises(ValueError):
            inst = TimeStream(helpers.FILES["timestream_bad"], ts_version=3)


