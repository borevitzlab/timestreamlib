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

import logging
from sys import stderr
from unittest import TestCase

from timestream import (
    NoEOLStreamHandler,
    add_log_handler,
    LOGV
)


class TestLoggingVerbosity(TestCase):

    def setUp(self):
        """remove all existing handlers before each test"""
        log = logging.getLogger("timestreamlib")
        for handler in log.handlers:
            log.removeHandler(handler)

    def _do_test(self, verbosity, expectedLevel):
        add_log_handler(verbosity=verbosity)
        log = logging.getLogger("timestreamlib")
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(type(log.handlers[0]), NoEOLStreamHandler)
        self.assertEqual(log.handlers[0].level, expectedLevel)
        self.assertEqual(log.getEffectiveLevel(), logging.DEBUG)

    def test_add_log_handler_V(self):
        self._do_test(LOGV.V, logging.INFO)

    def test_add_log_handler_VV(self):
        self._do_test(LOGV.VV, logging.DEBUG)

    def test_add_log_handler_VVV(self):
        self._do_test(LOGV.VV, logging.DEBUG)

    def tearDown(self):
        log = logging.getLogger("timestreamlib")
        for handler in log.handlers:
            log.removeHandler(handler)
        handler = logging.NullHandler()
        handler.setLevel(logging.INFO)
        log.addHandler(handler)
        log.setLevel(logging.INFO)
