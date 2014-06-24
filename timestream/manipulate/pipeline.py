#coding=utf-8
# Copyright (C) 2014
# Author(s): Joel Granados <joel.granados@gmail.com>
#            Chuong Nguyen <chuong.v.nguyen@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

import yaml
import numpy as np

from pipecomponents import *

class ImagePipeline ( object ):
    complist = {
                 Tester.actName:                Tester, \
                 ImageUndistorter.actName:      ImageUndistorter,
                 ColorCardDetector.actName:     ColorCardDetector, \
                 ImageColorCorrector.actName:   ImageColorCorrector, \
                 TrayDetector.actName:          TrayDetector, \
                 PotDetector.actName:           PotDetector, \
                 PlantExtractor.actName:        PlantExtractor, \
               }

    def __init__(self, defFilePath):
        f = file(defFilePath)
        ymlelems = yaml.load(f)
        f.close()

        self.pipeline = []

        # First elements expects [ndarray]
        yelem = ymlelems.pop(0)
        firstExpects = ImagePipeline.complist[yelem[0]].runExpects
        if ( isinstance(firstExpects, list) \
                and firstExpects[0] is not np.ndarray ):
            raise ValueError("First pipe element should be [ndarray]")
        self.pipeline.append( ImagePipeline.complist[yelem[0]](**yelem[1]) )

        # Add elements while checking for dependencies
        for yelem in ymlelems:
            compExpects = ImagePipeline.complist[yelem[0]].runExpects
            prevReturns = self.pipeline[-1].__class__.runReturns
            if ( not isinstance(compExpects, list) \
                    or not isinstance(prevReturns, list) \
                    or len(compExpects) is not len(prevReturns) \
                    or not compExpects == prevReturns ):
                raise ValueError("Dependancy error in pipeline")

            self.pipeline.append( ImagePipeline.complist[yelem[0]](**yelem[1]) )

    # contArgs: dict containing context arguments.
    #           Name are predefined for all pipe components.
    # initArgs: argument list to get the pipeline going.
    def process(self, contArgs, initArgs):
        if ( not isinstance(contArgs, dict) \
                or not isinstance(initArgs, list) ):
            raise ValueError("Process expects (dict, list)")

        # First element expects [ndarray]
        if ( len(initArgs) > 0 and not isinstance(initArgs[0], np.ndarray) ):
            raise ValueError("First pipe element should be [ndarray]")

        # First elem with input image
        elem = self.pipeline.pop(0)
        res = elem(contArgs, *initArgs)

        for elem in self.pipeline:
            res = elem(contArgs, *res)

        return (res)

    @classmethod
    def printCompList(cls):
        for clKey, clVal in ImagePipeline.complist.iteritems():
            print (clVal.info())
