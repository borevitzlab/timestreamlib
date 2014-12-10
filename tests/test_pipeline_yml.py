# Copyright 2015 Joel Granados joel.granados@gmail.com
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

import os
from os import path
import numpy
import shutil
import subprocess
import sys
import textwrap
from unittest import TestCase
import warnings

from tests import helpers
from tests.helpers import (
    FILES,
    PIPELINES_DIR,
    SCRIPT_DIR,
    TMPDIR,
)
from timestream import TimeStreamImage
from timestream.manipulate.pot import ImagePotMatrix


class PipelineRunTestcase(TestCase):
    """Tests all example pipeline YAMLs under ./pipelines with run_pipeline"""

    def setUp(self):
        self.tmp_in = FILES["timestream_good_images"]
        self.tmp_out = path.join(TMPDIR, 'out')

    def _run_pipeline_yaml(self, ymlfile):

        cmd = ['python', path.join(SCRIPT_DIR, 'run_pipeline.py'),
               '-i', self.tmp_in,
               '-o', self.tmp_out,
               '-p', path.join(PIPELINES_DIR, ymlfile),
               '-s',
        ]
        subprocess.check_call(cmd, stderr=subprocess.STDOUT)

    def _run_yaml_str(self, ymlstr):
        # NB: you have to start the 'pipeline:' bit on a new line, indented
        # correctly, and start the triple-quote string with '"""\', so the
        # whole string is indented in the same way.
        ymlstr = textwrap.dedent(ymlstr)
        ymlfile = helpers.make_tmp_file()
        with open(ymlfile, 'w') as ymlfh:
            ymlfh.write(ymlstr + '\n')  # Extra newline, just in case

        cmd = ['python', path.join(SCRIPT_DIR, 'run_pipeline.py'),
               '-i', self.tmp_in,
               '-o', self.tmp_out,
               '-p', ymlfile,
               '-s',
        ]
        subprocess.check_call(cmd, stderr=subprocess.STDOUT)

    def tearDown(self):
        if path.isdir(self.tmp_out):
            shutil.rmtree(self.tmp_out)

class TestPipelinesInPLDir(PipelineRunTestcase):

    def test_full(self):
        self._run_pipeline_yaml('full.yml')

class TestResizingPipelines(PipelineRunTestcase):
    fs = """\
    pipeline:
    - name: imagewrite
      mess: '---Write image---'
      outstream: -small
      size: %s

    outstreams:
      - { name: -small }

    general:
      visualise: False
    """

    def _test_resize_pl(self, size):
        self._run_yaml_str(self.fs % size)

    def test_resize_xy(self):
        self._test_resize_pl('[50,30]')
        self._test_resize_pl('50x30')

    def test_resize_float(self):
        self._test_resize_pl('1.5')
        self._test_resize_pl('0.5')
        self._test_resize_pl('0.1')

    def test_resize_fullsize(self):
        self._test_resize_pl('1.0')
        self._test_resize_pl('fullres')

