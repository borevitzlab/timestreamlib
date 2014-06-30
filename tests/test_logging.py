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


from copy import deepcopy
import logging
from sys import stderr
from unittest import TestCase, skip, skipIf, skipUnless

from tests import helpers
from timestream import (
    setup_module_logging,
)

class TestSetupDebugLogging(TestCase):
    def setUp(self):
        """remove all existing handlers before each test"""
        log = logging.getLogger("timestreamlib")
        for handler in log.handlers:
            log.removeHandler(handler)

    def _do_test(self, level, stream):
        setup_module_logging(level=level, stream=stream)
        log = logging.getLogger("timestreamlib")
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(type(log.handlers[0]), logging.StreamHandler)
        self.assertEqual(log.handlers[0].level, level)
        self.assertEqual(log.getEffectiveLevel(), level)

    def test_setup_module_logging_info(self):
        self._do_test(logging.INFO, stderr)

    def test_setup_module_logging_debug(self):
        self._do_test(logging.DEBUG, stderr)

    def test_setup_module_logging_debug_devnull(self):
        self._do_test(logging.DEBUG, None)

    def tearDown(self):
        log = logging.getLogger("timestreamlib")
        for handler in log.handlers:
            log.removeHandler(handler)
        handler = logging.NullHandler()
        handler.setLevel(logging.INFO)
        log.addHandler(handler)
        log.setLevel(logging.INFO)
