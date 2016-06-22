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

import glob
from os import path
import shutil
import textwrap
from unittest import TestCase
from run_pipeline import maincli

from tests import helpers
from tests.helpers import (
    FILES,
    PIPELINES_DIR,
    TMPDIR,
)


class PipelineRunTestcase(TestCase):
    """Tests all example pipeline YAMLs under ./pipelines with run_pipeline"""

    def setUp(self):
        self.tmp_in = FILES["timestream_good_images"]
        self.tmp_out = path.join(TMPDIR, 'out')

    def _run_pipeline_yaml(self, ymlfile):
        yml_opts = {'--comp': False, '--conf': False, '--doc': False,
                    '--gui': False, '--help': False, '--logfile': None,
                    '--recalculate': False, '--set': None,
                    '-i': self.tmp_in,
                    '-o': self.tmp_out,
                    '-p': path.join(PIPELINES_DIR, ymlfile),
                    '-s': True, '-t': None, '-v': 0}

        maincli(yml_opts)

    def _run_yaml_str(self, ymlstr):
        # NB: you have to start the 'pipeline:' bit on a new line, indented
        # correctly, and start the triple-quote string with '"""\', so the
        # whole string is indented in the same way.
        ymlstr = textwrap.dedent(ymlstr)
        ymlfile = helpers.make_tmp_file()
        with open(ymlfile, 'w') as ymlfh:
            ymlfh.write(ymlstr + '\n')  # Extra newline, just in case

        yml_opts = {'--comp': False, '--conf': False, '--doc': False,
                    '--gui': False, '--help': False, '--logfile': None,
                    '--recalculate': False, '--set': None,
                    '-i': self.tmp_in,
                    '-o': self.tmp_out,
                    '-p': ymlfile,
                    '-s': True, '-t': None, '-v': 0}

        maincli(yml_opts)

    def tearDown(self):
        if path.isdir(self.tmp_out):
            shutil.rmtree(self.tmp_out)


class TestPipelinesInPLDir(PipelineRunTestcase):
    """Ensure all demo pipelines work with test dataset"""

    def test_all_demo_pipelines(self):
        """Ensure all demo pipelines work with test dataset"""
        for config in glob.glob(path.join(PIPELINES_DIR, '*.yml')):
            self._run_pipeline_yaml(config)


class TestResizingPipelines(PipelineRunTestcase):
    """Test the resizing in ResultingImageWriter"""

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
        """Test the resizing in ResultingImageWriter with cols x rows"""
        self._test_resize_pl('[50,30]')
        self._test_resize_pl('50x30')

    def test_resize_float(self):
        """Test the resizing in ResultingImageWriter with scaling factor"""
        self._test_resize_pl('1.5')
        self._test_resize_pl('0.5')
        self._test_resize_pl('0.1')

    def test_resize_fullsize(self):
        """Test the resizing in ResultingImageWriter with no resizing"""
        self._test_resize_pl('1.0')
        self._test_resize_pl('fullres')
