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

import imghdr
import sys
import os
import os.path
import warnings
import pickle
import numpy

from unittest import TestCase
from tests import helpers
sys.path.insert(0, "./scripts")
from run_pipeline import maincli
from timestream import TimeStreamImage
from timestream.manipulate.pot import ImagePotMatrix


class TestSimplePipelineRun(TestCase):

    """ Test a simple run of pipeline.

    We produce:
            1. Output Color corrected images
            2. Segemented images
            3. Feature files (csv files)
    Not really testing the results. Just makings sure that everything is
    produced as expected.

    """

    def setUp(self):
        self.simple_opts = {'--comp': False, '--conf': False, '--doc': False,
                            '--gui': False, '--help': False, '--logfile': None,
                            '--recalculate': False, '--set': None,
                            '-i': helpers.FILES["timestream_good_images"],
                            '-o': None, '-p': None, '-s': True, '-t': None,
                            '-v': 0}
        self.outdirs = []
        for suf in ["cor", "seg"]:
            self.outdirs.append(os.path.join(
                helpers.TESTS_DIR, "data", "timestreams",
                "timestream-good-" + suf))

        self.outimgs = []
        self.segpickles = []
        self.corpickles = []
        for suf in ["cor", "seg"]:
            for _day, _min in [("28", "30"), ("29", "00")]:
                d1 = os.path.join(helpers.TESTS_DIR, "data", "timestreams",
                                  "timestream-good-" + suf)
                d2 = os.path.join("2014", "2014_06", "2014_06_" + _day,
                                  "2014_06_" + _day + "_12")
                i = "timestream-good-" + suf + "_2014_06_" + _day + "_12_" \
                    + _min + "_00_00"
                iName = i + ".jpg"
                pName = i + ".p"

                self.outimgs.append(os.path.join(d1, d2, iName))

                if suf == "cor":
                    self.corpickles.append(os.path.join(d1, "_data",
                                                        d2, pName))
                elif suf == "seg":
                    self.segpickles.append(os.path.join(d1, "_data",
                                                        d2, pName))

        self.csv = os.path.join(helpers.TESTS_DIR, "data", "timestreams",
                                "timestream-good-csv")

        self.features = ["area", "exg", "hsv", "rms", "audit", "gcc",
                         "leafcount1", "roundness", "compactness",
                         "height2", "mincircle", "wilting2", "eccentricity",
                         "height", "perimeter", "wilting"]

    def test_default_run(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            maincli(self.simple_opts)

        # We produce the image output dirs
        for d in self.outdirs:
            self.assertTrue(os.path.isdir(d))
            self.assertTrue(os.path.isdir(os.path.join(d, "_data")))

        # We produce images in the output dirs
        for i in self.outimgs:
            self.assertTrue(os.path.isfile(i))
            self.assertEqual(imghdr.what(i), "jpeg")

        # We produce the feature CSV files.
        for f in self.features:
            self.assertTrue(os.path.isfile(
                os.path.join(self.csv, "timestream-good-" + f + ".csv")))

        # We produce the pickle files for each image. and they are usable
        for p in self.corpickles + self.segpickles:
            self.assertTrue(os.path.isfile(p))
            f = file(p, "r")
            obj = pickle.load(f)
            f.close()
            self.assertTrue(isinstance(obj, TimeStreamImage))
            self.assertTrue(isinstance(obj.ipm, ImagePotMatrix))
            for pid in range(1, 161):
                self.assertTrue(pid, obj.ipm.potIds[pid - 1])

        # We actually segment the images.
        for seg in self.segpickles:
            f = file(p, "r")
            obj = pickle.load(f)
            f.close()
            for pid in range(1, 161):
                P = obj.ipm.getPot(1)
                self.assertTrue(isinstance(P.mask, numpy.ndarray))

    def tearDown(self):
        for top in self.outdirs + [self.csv]:
            for root, dirs, files in os.walk(top, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(top)
