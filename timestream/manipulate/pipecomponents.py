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

import matplotlib.pyplot as plt
import numpy as np
import cv2

class PipeComponent ( object ):
    # Name has to be unique among pipecomponents
    actName = ""

    # Arguments used when initializing
    # { "name1": [required, description, default],
    #   "name2": [required, description, default],.... }
    # name: is the name of the argument
    # required: True if arg is required, False if optional
    # default: Default value. Relevant only for required args
    argNames = {}

    # These two should be lists of types. order matters
    runExpects = []
    runReturns = []

    def __init__(self, *args, **kwargs):
        for attrKey, attrVal in self.__class__.argNames.iteritems():
            try:
                setattr(self, attrKey, kwargs[attrKey])
            except KeyError:
                if ( not attrVal[0] ):
                    # if optional set the default
                    setattr(self,attrKey, attrVal[2])
                else:
                    raise PCExBadRunExpects(self.__class__)

    # contArgs: dict containing context arguments.
    #           Name and values are predefined for all pipe components.
    # *args: this component receives
    def __call__(self, contArgs, *args):
        raise NotImplementedError()

    @classmethod
    def info(cls, _str=True):
        if _str:
            retVal = "  " + cls.actName + "\n"
            retVal = retVal + "  (Initializing Args)\n"
            for aKey, aVal in cls.argNames.iteritems():
                aType = "optional"
                if ( aVal[0] ):
                    aType = "required"
                retVal = retVal + "    %s(%s): %s\n" % (aKey, aType, aVal[1])

            retVal = retVal + "  (Args Received)\n"
            for arg in cls.runExpects:
                retVal = retVal + "    %s\n" % (arg)

            retVal = retVal + "  (Args Returned)\n"
            for arg in cls.runReturns:
                retVal = retVal + "    %s\n" % (arg)
        elif not _str:
            retVal = { "actName": cls.actName,
                       "argNames": cls.argNames,
                       "runExpects": cls.runExpects,
                       "runReturns": cls.runReturns }

        return (retVal)

class PCException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)
class PCExBadRunExpects(PCException):
    def __init__(self, cls):
        self.message = "The call to %s should consider \n%s" % \
                (cls.actName, cls.info())


class Tester ( PipeComponent ):
    actName = "tester"
    argNames = { "arg1": [True, "Argument 1 example"],
                 "arg2": [False, "Argument 2 example", 4] }

    runExpects = [ np.ndarray, np.ndarray ]
    runReturns = [ np.ndarray, np.ndarray ]

    def __init__(self, **kwargs):
        super(Tester, self).__init__(**kwargs)

    def __call__(self, context, *args):
        ndarray = args[0] # np.ndarray
        print(ndarray)

        return ([ndarray, ndarray])

class ImageUndistorter ( PipeComponent ):
    actName = "undistort"
    argNames = { "cameraMatrix": [True, "3x3 matrix for mapping physical" \
                    + "coordinates with screen coordinates"],\
                 "distortCoefs": [True, "5x1 matrix for image distortion"],
                 "imageSize":    [True, "2x1 matrix: [width, height]"] }

    runExpects = [np.ndarray]
    runReturns = [np.ndarray]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

        self.UndistMapX, self.UndistMapY = cv2.initUndistortRectifyMap( \
            self.cameraMatrix, self.distortCoefs, None, self.cameraMatrix, \
            self.imageSize, cv2.CV_32FC1)

    def __call__(self, context, *args):
        self.image = args[0]
        print("Image size =", self.image.shape)
        if self.UndistMapX != None and self.UndistMapY != None:
            self.image = self.image = cv2.remap(self.image.astype(np.uint8), \
                self.UndistMapX, self.UndistMapY, cv2.INTER_CUBIC)
            plt.imshow(self.image)
            plt.show()
        return(self.image)

class ColorCardDetector ( PipeComponent ):
    actName = "colorcarddetect"
    argNames = { "colorcardColors": [True, "Matrix representing the " \
                    + "color card colors"],
                 "colorcardFile": [True, "Path to the color card file"],
                 "colorcardPosition": [True, "(x,y) of the colorcard"],
                 "colorcardTrueColors": [True, "The true colors of " \
                    + "the colorcard"]}

    runExpects = [np.ndarray]
    runReturns = [np.ndarray, list]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        return (self.colorcardColors)

class ImageColorCorrector ( PipeComponent ):
    actName = "colorcorrect"
    argNames = {"mess": [False, "Correct image color"]}

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

    def __call__(self, inputs):
        print(self.mess)
        image, colorcardInfo = inputs
        print("Image size =", image.shape)
        return(image)

class TrayDetector ( PipeComponent ):
    actName = "traydetect"
    argNames = {"mess": [False,"Detect tray positions"]}

    runExpects = [np.ndarray]
    runReturns = [np.ndarray, list]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        print("Image size =", image.shape)
        trayPositions = []
        return(image, trayPositions)

class PotDetector ( PipeComponent ):
    actName = "potdetect"
    argNames = {"mess": [False, "Detect pot position"]}

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray, list]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        image, trayPositions = args
        print("Image size =", image.shape)
        potPositions = []
        return(image, potPositions)

class PlantExtractor ( PipeComponent ):
    actName = "plantextract"
    argNames = {"mess": [False, "Extract plant biometrics"]}

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray, list]

    def __init__(self, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        image, potPositions = args
        print("Image size =", image.shape)
        plantBiometrics = []
        return(image, plantBiometrics)

