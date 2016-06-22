# Copyright 2006-2014 Tim Brown/TimeScience LLC
# Copyright 2013-2014 Kevin Murray/Bioinfinio
# Copyright 2014- The Australian National Univesity
# Copyright 2014- Joel Granados
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

"""
.. module:: timestream.manipulate.pipeline
    :platform: Unix, Windows
    :synopsis: Pipeline management

.. moduleauthor:: Joel Granados, Chuong Nguyen
"""

from __future__ import absolute_import, division, print_function

from timestream.manipulate import PCException
from timestream.manipulate.pipecomponents import (
    ImageMarginAdder,
    ImageUndistorter,
    ColorCardDetector,
    ImageColorCorrector,
    TrayDetector,
    PotDetector,
    PotDetectorGlassHouse,
    PlantExtractor,
    FeatureExtractor,
    ResultingFeatureWriter,
    ResultingImageWriter,
    DerandomizeTimeStreams,
    ResizeImage,
    ResizeAndWriteImage,
)


class ImagePipeline (object):
    complist = {
        ImageMarginAdder.actName: ImageMarginAdder,
        ImageUndistorter.actName: ImageUndistorter,
        ColorCardDetector.actName: ColorCardDetector,
        ImageColorCorrector.actName: ImageColorCorrector,
        TrayDetector.actName: TrayDetector,
        PotDetector.actName: PotDetector,
        PotDetectorGlassHouse.actName: PotDetectorGlassHouse,
        PlantExtractor.actName: PlantExtractor,
        ResultingImageWriter.actName: ResultingImageWriter,
        FeatureExtractor.actName: FeatureExtractor,
        ResultingFeatureWriter.actName: ResultingFeatureWriter,
        DerandomizeTimeStreams.actName: DerandomizeTimeStreams,
        ResizeImage.actName: ResizeImage,
        ResizeAndWriteImage.actName: ResizeAndWriteImage
    }

    def __init__(self, plConf, context):
        # FIXME: Check the first element is ok.
        self.pipeline = []
        # Add elements while checking for dependencies
        for i, setElem in plConf.itersections():
            component = ImagePipeline.complist[setElem["name"]]
            if i > 0:  # 0 element skipped; expects ndarray.
                compExpects = component.runExpects
                prevReturns = self.pipeline[-1].__class__.runReturns

                # Error if compExpects and prevReturns are not lists
                if (not isinstance(compExpects, list)
                        or not isinstance(prevReturns, list)):
                    raise ValueError("Both %s and %s must handle in lists" %
                                     (component, self.pipeline[-1].__class__))

                # Special case for components with prevReturns = [None]
                if len(prevReturns) > 0 and prevReturns[0] is None:
                    # Previous [-2, -3....] prevReturns until not [None]
                    for j in [x * -1 for x in range(2, len(self.pipeline) + 1)]:
                        prevReturns = self.pipeline[j].__class__.runReturns
                        if prevReturns[0] is not None:
                            break

                # Error if first compExpects not contained prevReturns (in
                # order)
                if (len(compExpects) > len(prevReturns)
                    or False in [compExpects[k] == prevReturns[k]
                                 for k in range(len(compExpects))]):
                    raise ValueError("Dependency error between %s and %s" %
                                     (component, self.pipeline[-1].__class__))

            self.pipeline.append(component(context, **setElem))

    # contArgs: struct/class containing context arguments.
    #           Name are predefined for all pipe components.
    # initArgs: argument list to get the pipeline going.
    def process(self, contArgs, initArgs, visualise=False):
        res = initArgs
        for elem in self.pipeline:
            try:
                res = elem(contArgs, *res)
                if visualise:
                    elem.show()
            except PCException as e:
                res = [e]  # propagate exception

        for e in res:
            if isinstance(e, PCException):
                raise e

        return (res)

    @classmethod
    def printCompList(cls):
        for clKey, clVal in ImagePipeline.complist.iteritems():
            print (clVal.info())
