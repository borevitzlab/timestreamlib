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
.. module:: timestream.manipulate.pipecomponents
    :platform: Unix, Windows
    :synopsis: Various image processing components

.. moduleauthor:: Joel Granados, Chuong Nguyen, Kevin Murray
"""

from __future__ import absolute_import, division, print_function

import cPickle
import cv2
from itertools import chain
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import spatial
import sys
import time
import datetime
import skimage.transform

from timestream import TimeStreamImage, TimeStreamTraverser
import timestream.manipulate.correct_detect as cd
import timestream.manipulate.plantSegmenter as tm_ps
import timestream.manipulate.pot as tm_pot
from timestream.parse import (
    read_image,
    RIException
)
from timestream.manipulate import (
    PCException,
    PCExBadRunExpects,
    PCExBreakInPipeline,
    PCExBadConfig,
    PCExBadContext,
    PCExCorruptImage,
    PCExUndefinedMeta,
    PCExBadImage,
    PCExImageTooDark,
    PCExCannotFindColorCard,
    PCExCannotFindTray,
    PCExCannotCalcTimestamp,
    PCExCannotFindFeatures,
    PCExPotRectangleDimsOutOfImage,
)


LOG = logging.getLogger("timestreamlib")


class PipeComponent (object):
    # Name has to be unique among pipecomponents
    actName = ""

    # Arguments used when initializing
    # { "name1": [required, description, default],
    #   "name2": [required, description, default],.... }
    # name: is the name of the argument
    # required: True if arg is required, False if optional
    # default: Default value. Relevant only for required args
    argNames = {}

    # These two should be lists of ty
    runExpects = []
    runReturns = []

    def __init__(self, *args, **kwargs):
        self.mess = "---Executing PipeComponent---"
        for attrKey, attrVal in self.__class__.argNames.iteritems():
            try:
                setattr(self, attrKey, kwargs[attrKey])
            except KeyError:
                if (not attrVal[0]):
                    # if optional set the default
                    setattr(self, attrKey, attrVal[2])
                else:
                    # This check runs during instantiation.
                    raise PCExBadRunExpects(self.__class__, attrKey)

    def __call__(self, context, *args):
        """ Is executed every time a component needs to do something.

        Procedure:
          1. Check for propagated exceptions
          2. Check argument consistency against runExpects
          3. Call self.__exec__ (should be overridden by children )
        Args:
          context(PCFGSection): a tree containing context arguments. Same names
            for all components
          args(list): What this components receives
        """
        self.__chkExcept__(context, *args)

        for i in range(len(self.runExpects)):
            if not isinstance(args[i], self.runExpects[i]):
                raise PCExBadRunExpects(
                    self.__class__,
                    "Call Expected %s but got %s"
                    % (self.runExpects[i], type(args[i])))

        # Only PCExceptions get propagated correctly through the pipeline. Here
        # we translate "general" exceptions into a PCException.
        try:
            if len(self.mess) > 0:
                LOG.info(self.mess)
            retVal = self.__exec__(context, *args)
        except RIException as rie:
            raise PCExCorruptImage(rie.path)

        return retVal

    def __chkExcept__(self, context, *args):
        # Separated from __call__ so it might be overridden by children that
        # need special treatment of propagated exceptions.
        for arg in args:
            if isinstance(arg, PCException):
                raise arg

    def __exec__(self, context, *args):
        raise NotImplementedError()

    @classmethod
    def info(cls, _str=True):
        if _str:
            retVal = "  " + cls.actName + "\n"
            retVal = retVal + "  (Initializing Args)\n"
            for aKey, aVal in cls.argNames.iteritems():
                aType = "optional"
                if (aVal[0]):
                    aType = "required"
                retVal = retVal + "    %s(%s): %s\n" % (aKey, aType, aVal[1])

            retVal = retVal + "  (Args Received)\n"
            for arg in cls.runExpects:
                retVal = retVal + "    %s\n" % (arg)

            retVal = retVal + "  (Args Returned)\n"
            for arg in cls.runReturns:
                retVal = retVal + "    %s\n" % (arg)
        elif not _str:
            retVal = {"actName": cls.actName,
                      "argNames": cls.argNames,
                      "runExpects": cls.runExpects,
                      "runReturns": cls.runReturns}

        return (retVal)

    def show(self):
        pass


class ImageMarginAdder(PipeComponent):
    actName = "addMargin"
    argNames = {
        "mess": [True, "Adding a margin to the image"],
        "pixsize": [True, "Margin size in pixels", 0],
        "padval": [False, "Padding value", 0]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ImageMarginAdder, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        tsi = args[0]
        # Stack 3 dimensioned with added margins.
        tsi.pixels = np.dstack(
            (np.lib.pad(tsi.pixels[:, :, 0], self.pixsize, self.padlocal),
            np.lib.pad(tsi.pixels[:, :, 1], self.pixsize, self.padlocal),
            np.lib.pad(tsi.pixels[:, :, 2], self.pixsize, self.padlocal)))
        self.image = tsi.pixels
        return [tsi]

    def padlocal(self, vector, pad_width, iaxis, kwargs):
        vector[:pad_width[0]] = self.padval
        vector[-pad_width[1]:] = self.padval
        return vector

    def show(self):
        plt.figure()
        plt.imshow(self.image)
        plt.title('Image with Additional Margin')
        plt.show()


class ImageUndistorter (PipeComponent):
    actName = "undistort"
    argNames = {
        "mess": [True, "Apply lens distortion correction"],
        "cameraMatrix": [True, "3x3 matrix that maps physical to screen "
                               "coordinates"],
        "distortCoefs": [True, "5x1 matrix for image distortion"],
        "imageSize": [True, "2x1 matrix: [width, height]"],
        "rotationAngle": [True, "rotation angle for the image"]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)
        self.UndistMapX, self.UndistMapY = cv2.initUndistortRectifyMap(
            np.asarray(self.cameraMatrix),
            np.asarray(self.distortCoefs),
            None,
            np.asarray(self.cameraMatrix),
            tuple(self.imageSize),
            cv2.CV_32FC1)

    def __exec__(self, context, *args):
        tsi = args[0]
        self.image = tsi.pixels

        if self.image is None:
            raise PCExBadImage(tsi.path)

        if self.UndistMapX is not None and self.UndistMapY is not None:
            self.imageUndistorted = cv2.remap(self.image.astype(np.uint8),
                                              self.UndistMapX, self.UndistMapY,
                                              cv2.INTER_CUBIC)
        else:
            self.imageUndistorted = self.image

        tsi.pixels = cd.rotateImage(self.imageUndistorted,
                                    self.rotationAngle)
        return [tsi]

    def show(self):
        plt.figure()
        plt.imshow(cd.rotateImage(self.image))
        plt.title('Original image')

        plt.figure()
        plt.imshow(self.imageUndistorted)
        plt.title('Undistorted image')

        plt.show()


class ColorCardDetector (PipeComponent):
    actName = "colorcarddetect"
    argNames = {
        "mess": [True, "Detect color card"],
        "colorcardTrueColors": [True, "Matrix with 'true' color card colors"],
        "minIntensity": [False,
            "Skip colorcard detection if intensity below this value", 0],
        "colorcardFile": [True, "Path to the color card file"],
        "colorcardPosition": [True, "(x,y) of the colorcard"],
        "settingPath": [True, "Path to setting files"],
        "useWhiteBackground": [False,
            "Use white background as reference", False],
        "backgroundWindow": [False,
            "top-left and botom-right points of background region", []],
        "maxIntensity": [False,
            "Max intensity when using white background", 255]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage, tuple]

    def __init__(self, context, **kwargs):
        super(ColorCardDetector, self).__init__(**kwargs)
        self.ccf = os.path.join(context.ints.path,
                                self.settingPath, self.colorcardFile)
        # for glasshouse experiment, color card is outside of timestream path
        if not os.path.exists(self.ccf):
            configFilePath = os.path.dirname(context.ints.data['configFile'])
            self.ccf = os.path.join(configFilePath, self.colorcardFile)

    def __exec__(self, context, *args):
        tsi = args[0]
        self.image = tsi.pixels
        meanIntensity = np.mean(self.image)
        if meanIntensity < self.minIntensity:
            raise PCExImageTooDark(tsi.path)
        if not self.useWhiteBackground:
            self.imagePyramid = cd.createImagePyramid(self.image)
            ccdImg = read_image(self.ccf)[:, :, 0:3]
            if ccdImg is None:
                raise PCExBadImage(self.ccf)
            self.ccdPyramid = cd.createImagePyramid(ccdImg)
            # create image pyramid for multiscale matching
            SearchRange = [self.ccdPyramid[0].shape[1] * 1.5,
                           self.ccdPyramid[0].shape[0] * 1.5]
            score, loc, angle = cd.matchTemplatePyramid(
                self.imagePyramid, self.ccdPyramid,
                0, EstimatedLocation=self.colorcardPosition,
                SearchRange=SearchRange)
            if score > 0.3:
                # extract color information
                self.foundCard = self.image[
                    loc[1] - ccdImg.shape[0] // 2:loc[1] + ccdImg.shape[0] // 2,
                    loc[0] - ccdImg.shape[1] // 2:loc[0] + ccdImg.shape[1] // 2]
                self.ccdColors, _ = cd.getColorcardColors(self.foundCard,
                                                          GridSize=[6, 4])
                self.ccdParams = cd.estimateColorParameters(
                    self.colorcardTrueColors,
                    self.ccdColors)
                # Save colourcard image to instance
                self.colorcardImage = ccdImg
                # for displaying
                self.loc = loc
            else:
                raise PCExCannotFindColorCard(tsi.path)
        else:
            self.ccdParams = cd.estimateColorParametersFromWhiteBackground(
                self.image, self.backgroundWindow, self.maxIntensity)
        return([tsi, self.ccdParams])

    def show(self):
        plt.figure()
        if not self.useWhiteBackground:
            plt.subplot(211)
            plt.imshow(self.image)
            plt.hold(True)
            if hasattr(self, "loc"):
                plt.plot([self.loc[0]], [self.loc[1]], 'ys')
                plt.text(
                    self.loc[0] - 30,
                    self.loc[1] - 15,
                    'ColorCard',
                    color='yellow')
                plt.title('Detected color card')
                plt.subplot(212)
                plt.imshow(self.foundCard)
                plt.title('Detected color card')
        else:
            plt.imshow(self.image)
            TLC = self.backgroundWindow[0:2]
            BRC = self.backgroundWindow[2:]
            plt.plot(
                [TLC[0], TLC[0], BRC[0], BRC[0], TLC[0]],
                [TLC[1], BRC[1], BRC[1], TLC[1], TLC[1]],
                'w')
            plt.title('Selected white region for color correction')
        plt.show()


class ImageColorCorrector (PipeComponent):
    actName = "colorcorrect"
    argNames = {
        "mess": [False, "Correct image color"],
        "minIntensity": [False, "Skip when below this value", 0],
        "fieldOfView": [False, "Field of view in degrees", None]}

    runExpects = [TimeStreamImage, tuple]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ImageColorCorrector, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        tsi, colorcardParam = args
        image = tsi.pixels

        meanIntensity = np.mean(image)
        colorMatrix, colorConstant, colorGamma = colorcardParam
        if colorMatrix is not None and meanIntensity > self.minIntensity:
            self.imageCorrected = cd.correctColorVectorised(
                image.astype(np.float),
                colorMatrix,
                colorConstant,
                colorGamma)
            self.imageCorrected = np.clip(np.round(self.imageCorrected),
                                          0, 255)
            self.imageCorrected = self.imageCorrected.astype(np.uint8)
        else:
            # FIXME: This should be handled with an exception.
            LOG.warn('Skip color correction')
            self.imageCorrected = image
        self.image = image  # display

        # adjust intensity due to angle in field of view
        if self.fieldOfView is not None:
            imageSize = self.image.shape[1::-1]
            xp, yp = np.meshgrid(range(imageSize[0]),
                                 range(imageSize[1]))
            xp -= imageSize[0]/2
            yp -= imageSize[1]/2
            W = 2.0*np.tan(self.fieldOfView[0]/2.0/180.0*np.pi)
            H = 2.0*np.tan(self.fieldOfView[1]/2.0/180.0*np.pi)
            angleX = np.arctan(W/imageSize[0]*xp)
            angleY = np.arctan(H/imageSize[1]*yp)
            self.angles = np.sqrt(angleX**2 + angleY**2)

            # scale intensity with inverse of angle cosine
            temp0 = self.imageCorrected[:, :, 0]/np.cos(self.angles)
            temp1 = self.imageCorrected[:, :, 1]/np.cos(self.angles)
            temp2 = self.imageCorrected[:, :, 2]/np.cos(self.angles)

            # clip to range between 0 and 255 before converting to uint8
            self.imageAdjusted = np.zeros_like(self.imageCorrected)
            self.imageAdjusted[:, :, 0] = np.clip(np.round(temp0), 0, 255)
            self.imageAdjusted[:, :, 1] = np.clip(np.round(temp1), 0, 255)
            self.imageAdjusted[:, :, 2] = np.clip(np.round(temp2), 0, 255)

            tsi.pixels = self.imageAdjusted
        else:
            tsi.pixels = self.imageCorrected

        return([tsi])

    def show(self):
        plt.figure()
        plt.imshow(self.image)
        plt.title('Image without color correction')

        plt.figure()
        plt.imshow(self.imageCorrected.astype(np.uint8))
        plt.title('Color-corrected image')

        if self.fieldOfView is not None:
            plt.figure()
            plt.imshow(self.imageAdjusted)
            plt.title('Color- and intensity-corrected image')
            plt.figure()
            plt.imshow(np.cos(self.angles))

        plt.show()


class TrayDetector (PipeComponent):
    actName = "traydetect"
    argNames = {
        "mess": [False, "Detect tray positions"],
        "trayFiles": [True,
            "File name pattern for trays such as Trays_%02d.png"],
        "trayNumber": [True, "Number of trays in given image"],
        "trayPositions": [True, "Estimated tray positions"],
        "settingPath": [True, "Path to setting files"]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage, list, list]

    def __init__(self, context, **kwargs):
        super(TrayDetector, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        tsi = args[0]
        self.image = tsi.pixels
        temp = np.zeros_like(self.image)
        temp[:, :, :] = self.image[:, :, :]
        temp[:, :, 1] = 0  # suppress green channel
        self.imagePyramid = cd.createImagePyramid(temp)
        self.trayPyramids = []
        for i in range(self.trayNumber):
            # fixed tray image so that perspective postions of the trays are
            # fixed
            trayFile = os.path.join(context.ints.path,
                                    self.settingPath,
                                    self.trayFiles % i)
            trayImage = read_image(trayFile)
            if trayImage is None:
                LOG.error("Fail to read", trayFile)
            trayImage[:, :, 1] = 0  # suppress green channel
            trayImage = trayImage[:, :, 0:3]  # supress Alpha channel
            trayPyramid = cd.createImagePyramid(trayImage)
            self.trayPyramids.append(trayPyramid)

        self.trayLocs = []
        for i, trayPyramid in enumerate(self.trayPyramids):
            SearchRange = [trayPyramid[0].shape[1] // 6,
                           trayPyramid[0].shape[0] // 6]
            score, loc, angle = cd.matchTemplatePyramid(
                self.imagePyramid,
                trayPyramid,
                RotationAngle=0,
                EstimatedLocation=self.trayPositions[i],
                SearchRange=SearchRange)
            if score < 0.3:
                raise PCExCannotFindTray(i, tsi.path)

            self.trayLocs.append(loc)

        tsi.pixels = self.image
        return([tsi, self.imagePyramid, self.trayLocs])

    def show(self):
        plt.figure()
        plt.imshow(self.image.astype(np.uint8))
        plt.hold(True)
        PotIndex = 0
        for i, Loc in enumerate(self.trayLocs):
            if Loc is None:
                continue
            plt.plot([Loc[0]], [Loc[1]], 'bo')
            PotIndex = PotIndex + 1
        plt.title('Detected trays')
        a = plt.gca()
        a.axis('tight')
        plt.show()


class PotDetector (PipeComponent):
    actName = "potdetect"
    argNames = {
        "mess": [False, "Detect pot position"],
        "potFile": [True, "File name of a pot image"],
        "potTemplateFile": [True, "File name of a pot template image"],
        "potPositions": [True, "Estimated pot positions"],
        "potSize": [True, "Estimated pot size"],
        "traySize": [True, "Estimated tray size"],
        "settingPath": [True, "Path to setting files"],
        "startingPotId": [False, "Starting offset for pot IDs", 1]}

    runExpects = [TimeStreamImage, list, list]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PotDetector, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        tsi, self.imagePyramid, self.trayLocs = args
        self.image = tsi.pixels
        # read pot template image and scale to the pot size
        potFile = os.path.join(
            context.ints.path,
            self.settingPath,
            self.potFile)
        potImage = read_image(potFile)
        potTemplateFile = os.path.join(
            context.ints.path,
            self.settingPath,
            self.potTemplateFile)
        potTemplateImage = read_image(potTemplateFile)
        potTemplateImage[:, :, 1] = 0  # suppress green channel
        potTemplateImage = cv2.resize(
            potTemplateImage.astype(np.uint8),
            (potImage.shape[1],
             potImage.shape[0]))
        self.potPyramid = cd.createImagePyramid(potTemplateImage)

        XSteps = int(round(self.traySize[0] / float(self.potSize[0])))
        YSteps = int(round(self.traySize[1] / float(self.potSize[1])))
        StepX = self.traySize[0] // XSteps
        StepY = self.traySize[1] // YSteps

        self.potLocs2 = []
        self.potLocs2_ = []
        potGridSize = [4, 5]
        for trayLoc in self.trayLocs:
            if trayLoc is None:
                self.potLocs2.append(None)
                continue
            StartX = trayLoc[0] - self.traySize[0] // 2 + StepX // 2
            StartY = trayLoc[1] + self.traySize[1] // 2 - StepY // 2
            SearchRange = [self.potPyramid[0].shape[1] // 4,
                           self.potPyramid[0].shape[0] // 4]
            # SearchRange = [32, 32]
            locX = np.zeros(potGridSize)
            locY = np.zeros(potGridSize)
            for k in range(potGridSize[0]):
                for l in range(potGridSize[1]):
                    estimateLoc = [StartX + StepX * k, StartY - StepY * l]
                    score, loc, angle = cd.matchTemplatePyramid(
                        self.imagePyramid,
                        self.potPyramid,
                        RotationAngle=0,
                        EstimatedLocation=estimateLoc,
                        NoLevels=3,
                        SearchRange=SearchRange)
                    locX[k, l], locY[k, l] = loc

            # correct for detection error
            potLocs = []
            potLocs_ = []
            diffXX = locX[1:, :] - locX[:-1, :]
            diffXY = locX[:, 1:] - locX[:, :-1]
            diffYX = locY[1:, :] - locY[:-1, :]
            diffYY = locY[:, 1:] - locY[:, :-1]
            diffXXMedian = np.median(diffXX)
            diffXYMedian = np.median(diffXY)
            diffYXMedian = np.median(diffYX)
            diffYYMedian = np.median(diffYY)
            for k in range(potGridSize[0]):
                for l in range(potGridSize[1]):
                    locX[k, l] = trayLoc[0] + diffXXMedian * (k - (potGridSize[0] - 1.0) / 2.0) + \
                        diffXYMedian * (l - (potGridSize[1] - 1.0) / 2.0)
                    locY[k, l] = trayLoc[1] + diffYXMedian * (k - (potGridSize[0] - 1.0) / 2.0) + \
                        diffYYMedian * (l - (potGridSize[1] - 1.0) / 2.0)
                    # this fixes perpective shift
                    # TODO: need a more elegant solution
                    locY[k, l] = locY[k, l] + 10

                    potLocs.append([locX[k, l], locY[k, l]])
                    potLocs_.append(estimateLoc)
            self.potLocs2.append(potLocs)
            self.potLocs2_.append(potLocs_)

        # Create a new ImagePotMatrix with newly discovered locations
        ipmPrev = None
        if context.hasSubSecName("ipmPrev"):
            ipmPrev = context.ipmPrev

        # Calculate growM with potSize from potdetect component.
        growM = 0
        if isinstance(self.potSize, list) and len(self.potSize) == 2:
            growM = round(max(self.potSize) / 2)
        else:
            # if no user vals, we try to calculate it.
            flattened = list(chain.from_iterable(self.potLocs2))
            sortDist = np.sort(spatial.distance.pdist(flattened))
            sortDist = sortDist[0:len(flattened)]
            growM = round(np.median(sortDist) / 2)

        tsi.ipm = tm_pot.ImagePotMatrix(
            tsi, pots=[], growM=growM, ipmPrev=ipmPrev)
        potID = self.startingPotId
        for tray in self.potLocs2:
            trayID = 1
            for c in tray:  # c => center
                m = dict([[x, context.metas.getVal(x)[potID]]
                        for x in context.metas.listSubSecNames()
                        if potID in context.metas.getVal(x).keys()])
                try:
                    r = tm_pot.ImagePotRectangle(c, tsi.pixels.shape,
                        growM=growM)
                except:
                    raise PCExPotRectangleDimsOutOfImage(potID, c,
                        tsi.pixels.shape)

                p = tm_pot.ImagePotHandler(potID, r, tsi.ipm, metaids=m)
                p.setMetaId("trayID", trayID)
                tsi.ipm.addPot(p)
                potID += 1
            trayID += 1

        return([tsi])

    def show(self):
        plt.figure()
        plt.imshow(self.image.astype(np.uint8))
        plt.hold(True)
        PotIndex = 0
        for i, Loc in enumerate(self.trayLocs):
            if Loc is None:
                continue
            plt.plot([Loc[0]], [Loc[1]], 'bo')
            plt.text(
                Loc[0],
                Loc[1] - 15,
                'T' + str(i + 1),
                color='blue',
                fontsize=20)
            for PotLoc, PotLoc_ in zip(self.potLocs2[i], self.potLocs2_[i]):
                plt.plot([PotLoc[0]], [PotLoc[1]], 'ro')
                plt.text(
                    PotLoc[0],
                    PotLoc[1] - 15,
                    str(PotIndex + 1),
                    color='red')
                plt.plot([PotLoc_[0]], [PotLoc_[1]], 'rx')
                PotIndex = PotIndex + 1
        a = plt.gca()
        a.axis('tight')
        plt.title('Detected trays and pots')
        plt.show()


class PotDetectorGlassHouse (PipeComponent):
    actName = "potdetectglasshouse"
    argNames = {
        "mess": [False, "Just set pot position fron config file"],
        "potRectangle": [True, "Pot bounding box"]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PotDetectorGlassHouse, self).__init__(**kwargs)

    def __call__(self, context, *args):
        tsi = args[0]
        self.image = tsi.pixels

        tsi.ipm = tm_pot.ImagePotMatrix(tsi, pots=[])
        potID = 1
        r = tm_pot.ImagePotRectangle(self.potRectangle, tsi.pixels.shape)
        p = tm_pot.ImagePotHandler(potID, r, tsi.ipm)
        tsi.ipm.addPot(p)

        self.PotLoc = [(self.potRectangle[0]+self.potRectangle[2])//2,
                       (self.potRectangle[1]+self.potRectangle[3])//2]
        context.outputwithimage["potLocs"] = self.PotLoc
        return([tsi])

    def show(self):
        plt.figure()
        plt.imshow(self.image.astype(np.uint8))
        plt.hold(True)
        plt.plot([self.PotLoc[0]], [self.PotLoc[1]], 'ro')
        plt.title('Pot Location')
        plt.show()


class PlantExtractor (PipeComponent):
    actName = "plantextract"
    argNames = {
        "mess": [False, "Extract plant biometrics", "default message"],
        "minIntensity": [False, "Skip if intensity below value", 0],
        "meth": [False, "Segmentation Method", "k-means-square"],
        "methargs": [False, "Args: maxIter, epsilon, attempts", {}],
        "parallel": [False, "Whether to run in parallel", False]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PlantExtractor, self).__init__(**kwargs)
        if self.meth not in tm_ps.segmentingMethods.keys():
            raise PCExBadConfig(self.actName, self.meth,
                                "Invalid method for component")
        # FIXME: Check the arg names. Inform an error in yaml file if error.
        self.segmenter = tm_ps.segmentingMethods[self.meth](**self.methargs)

    def __exec__(self, context, *args):
        tsi = args[0]
        self.ipm = tsi.ipm

        # Set the segmenter in all the pots
        for key, iph in self.ipm.iter_through_pots():
            iph.ps = self.segmenter

        # Segment all pots
        self.segAllPots()

        # Put current image pot matrix in context for the next run
        context.setVal("ipmPrev", self.ipm)

        return [tsi]

    def segAllPots(self):
        if not self.parallel:
            for key, iph in self.ipm.iter_through_pots():
                # Property will trigger the segmentation (from where???)
                _ = iph.mask
            return

        # Parallel from here: We create a child process for each pot and pipe
        # the pickled result back to the parent.
        childPids = []
        for key, iph in self.ipm.iter_through_pots():
            In, Out = os.pipe()
            pid = os.fork()
            if pid != 0:  # In parent
                os.close(Out)
                childPids.append([iph, pid, In])
                continue

            # Child Section
            try:
                os.close(In)
                msk = cPickle.dumps(iph.getSegmented())
                cOut = os.fdopen(Out, "wb", sys.getsizeof(msk))
                cOut.write(msk)
                cOut.close()

            except Exception:
                os._exit(1)

            finally:
                os._exit(0)
            # Child Section

        for iph, pid, In in childPids:
            pIn = os.fdopen(In, "rb")
            msk = cPickle.loads(pIn.read())
            p, status = os.waitpid(pid, 0)
            pIn.close()
            if (status is not 1):
                iph.mask = msk
            # FIXME: We need to handle the case where there is a seg error
            # The challange is to put this in the audit file without a
            # global exception.

        return

    def show(self):
        self.ipm.show()


class FeatureExtractor (PipeComponent):
    actName = "featureextract"
    argNames = {
        "mess": [False, "Default message", "Extracting Features"],
        "features": [False, "Features to extract", ["all"]],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(FeatureExtractor, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        ipm = args[0].ipm
        for key, iph in ipm.iter_through_pots():
            iph.calcFeatures(self.features)

        return [args[0]]


class ResultingFeatureWriter(PipeComponent):
    actName = "writefeatures"
    argNames = {
        "mess": [False, "Default message", "Writing the features"],
        "overwrite": [False, "Whether to overwrite out files", False],
        "ext": [False, "Output Extension", "csv"],
        "outname": [False, "String to append to outputPrefixPath", None],
        "timestamp": [False, "Timestamp format", "%Y_%m_%d_%H_%M_%S_00"],
        "extraheaders": [False, "Extra headers to include.", []]
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    errStr = "NaN"
    # FIXME: hardcoded "timestamp" as header for timestamp.
    tsHName = "timestamp"  # Timestamp column name

    def __init__(self, context, **kwargs):
        super(ResultingFeatureWriter, self).__init__(**kwargs)

        if not context.hasSubSecName("outputPrefixPath"):
            raise PCExBadContext(self.actName, "outputPrefixPath",
                                 "Must define output prefix directory")
        if not context.hasSubSecName("outputPrefix"):
            raise PCExBadContext(self.actName, "outputPrefix",
                                 "Must define an output prefix")
        if self.ext is not "csv":
            raise PCExBadConfig(self.actName, self.ext, "Invalid extension")

        if self.outname is None:
            self.outname = "-" + self.ext
        self.outputdir = context.outputPrefixPath + self.outname
        self.outputPrefix = context.outputPrefix

        if not os.path.exists(self.outputdir):
            os.makedirs(self.outputdir)

        # Output audit file
        self._auditFile = os.path.join(self.outputdir,
                                       self.outputPrefix + "-audit." + self.ext)

        # Filenames for every feature.
        self._featFiles = {}
        for fName in tm_ps.StatParamCalculator.statParamMethods():
            full_fname = self.outputPrefix + "-" + fName + "." + self.ext
            self._featFiles[fName] = os.path.join(self.outputdir, full_fname)

        self._prevCsvIndex = {}
        if self.overwrite:
            # Remove any conflicting csv
            for fName, fPath in self._featFiles.iteritems():
                if os.path.exists(fPath):
                    os.remove(fPath)
        else:
            self._initPrevCsvIndex()

    def __exec__(self, context, *args):
        img = args[0]
        ipm = img.ipm

        # 1. Calculate time stamp (ts)
        ts = self._guessTimeStamp(img)
        if ts is None:
            self._appendToAudit(ResultingFeatureWriter.errStr,
                                PCExCannotCalcTimestamp.id)

            raise PCExCannotCalcTimestamp(img.path)

        # 2. If we have no features
        if ipm is None or len(ipm.potFeatures) < 1:
            self._appendToAudit(ts, PCExCannotFindFeatures.id)

            raise PCExCannotFindFeatures(img.path)

        # 3. Write features
        potIds = sorted(ipm.potIds)  # Sorted to easily append
        for fName, fPath in self._featFiles.iteritems():
            if not os.path.exists(fPath):  # we initialize it.
                self._initHeaders(fPath, ipm, potIds)

            outputline = None
            if not self.overwrite:  # Search in previous csvs
                outputline = self._recoverFromPrev(ts, fName)

            if outputline is None:
                outputline = str(ts)
                for potId in potIds:
                    pot = ipm.getPot(potId)
                    fet = pot.getCalcedFeatures()[fName]
                    outputline = "%s,%s" % (outputline,str(fet.value))
                outputline = outputline+"\n"

            fd = open(fPath, 'a')
            fd.write("%s" % outputline)
            fd.close()

        self._appendToAudit(ts, str(-1))
        return args

    def __chkExcept__(self, context, *args):
        recExcept = None  # received exception
        for arg in args:
            if isinstance(arg, PCException):
                recExcept = arg

        if recExcept is None:
            return  # No exceptions, we should continue normally.

        if not context.hasSubSecName("ints"):
            self._appendToAudit(ResultingFeatureWriter.errStr, recExcept.id)
            raise recExcept  # We can't guess time stamp.

        # 1. Guess time stamp (ts) from ints
        # FIXME: HACK!!! Here we want to ignore the _err_on_access of the
        #       TimeStreamTraverser instance.
        eoa = context.ints._err_on_access
        context.ints._err_on_access = False
        img = context.ints.curr()
        context.ints._err_on_access = eoa

        ts = self._guessTimeStamp(img)
        if ts is None:
            self._appendToAudit(ResultingFeatureWriter.errStr, recExcept.id)
            raise recExcept
        self._appendToAudit(ts, recExcept.id)

        # 2. Write features
        for fName, fPath in self._featFiles.iteritems():
            if not os.path.exists(fPath):  # we initialize it.
                res = self._recoverFromPrev(ResultingFeatureWriter.tsHName,
                                            fName)
                # If no header row, continue without header.
                if res is not None:
                    fd = open(fPath, 'a+')
                    fd.write("%s" % res)
                    fd.close()

            if self.overwrite:
                self._addErrStr(ts, fPath)
            else:
                res = self._recoverFromPrev(ts, fName)
                if res is None:
                    self._addErrStr(ts, fPath)
                else:
                    fd = open(fPath, 'a+')
                    fd.write("%s" % res)
                    fd.close()

        raise recExcept

    def _guessTimeStamp(self, img):
        ts = None
        if not isinstance(img, TimeStreamImage):
            return ts

        if self.timestamp == "LINUX_SEC" or self.timestamp is None:
            ts = time.mktime(img.datetime.timetuple())
        elif self.timestamp == "LINUX_MILISEC":
            ts = time.mktime(img.datetime.timetuple()) * 1000
        else:
            try:
                ts = img.datetime.strftime(self.timestamp)
            except:
                ts = time.mktime(img.datetime.timetuple()) * 1000

        return ts

    def _addErrStr(self, timestamp, filename):
        """appends a row of cls.errStr using first row as a referenc"""
        if not os.path.exists(filename):
            return

        fd = open(filename, 'r')
        l = fd.readline()
        fd.close()

        if len(l) < 1:
            return

        numElem = l.count(",")
        strOut = str(timestamp)+(","+ResultingFeatureWriter.errStr)*numElem
        strOut = strOut[:-1]  # eliminate last comma
        strOut = strOut+"\n"

        fd = open(filename, 'a')
        fd.write("%s" % strOut)
        fd.close()

        return strOut

    def _recoverFromPrev(self, timestamp, featName):
        """Searches timestamp in previous csv files

        self._prevCsvIndex has correspondence between feature names and
        timestamps. It also links tmp files to feature names.
        """
        if featName not in self._prevCsvIndex.keys():
            return
        tss = self._prevCsvIndex[featName][1]
        if timestamp not in tss.keys():
            return

        boffset = tss[timestamp]
        tsf = self._prevCsvIndex[featName][0]
        fd = open(tsf, 'r')
        fd.seek(boffset)
        l = fd.readline()
        fd.close()

        # del line from index
        del(tss[timestamp])
        if (len(tss) < 1) or (len(tss) == 1 and self.tsHName in tss.keys()[0]):
            del(self._prevCsvIndex[featName])
            os.remove(tsf)

        return l

    def _initHeaders(self, fPath, ipm, potIds):
        fd = open(fPath, "w+")
        for eh in self.extraheaders:
            outputline = str(eh)
            for potId in potIds:
                try:
                    outputline += "," + str(ipm.getPot(potId).getMetaId(eh))
                except IndexError:
                    raise PCExUndefinedMeta(potId, eh)
            outputline += "\n"
            fd.write(outputline)

        outputline = str(self.tsHName)
        for potId in potIds:
            outputline += "," + str(potId)
        outputline += "\n"
        fd.write(outputline)
        fd.close()

    def _initPrevCsvIndex(self):
        """ Ths structure of self._prevCsvIndex:
        {featName:[tmpFile,{timestamp:byteoffset,timestamps:byteoffset...}],
         featName:[tmpFile, {...}...]}

        """
        for fName, fpath in self._featFiles.iteritems():
            if not os.path.exists(fpath):
                continue
            if fName in self._prevCsvIndex.keys():
                continue

            # (1) rename to a tempfile
            H, T = os.path.split(fpath)
            tmpFilePath = os.path.join(H, "tmp"+str(int(time.time()) * 1000)+T)
            os.rename(fpath, tmpFilePath)
            self._prevCsvIndex[fName] = [tmpFilePath, {}]

            # (2) read all timestamps
            fd = open(tmpFilePath, "r")
            while True:
                byteoffset = fd.tell()
                l = fd.readline()
                if l == "":
                    break
                ind = l.split(",")[0]
                self._prevCsvIndex[fName][1][ind] = byteoffset

            fd.close()

    def _appendToAudit(self, ts, val):
        if not os.path.exists(self._auditFile):
            fd = open(self._auditFile, 'a')
            fd.write("Code Meanings:\n")
            for pcc in PCException.__subclasses__():
                fd.write("    %d: %s\n" % (pcc.id, pcc.doc))
            fd.close()

        fd = open(self._auditFile, 'a')
        fd.write("%s,%s\n" % (str(ts), val))
        fd.close()


class ResultingImageWriter (PipeComponent):
    actName = "imagewrite"
    argNames = {
        "mess": [False, "Output Message", "Writing Image"],
        "outstream": [True, "Name of stream to use"],
        "addStats": [False, "List of statistics", []],
        "masked": [False, "Whether to output masked images", False]}

    runExpects = [TimeStreamImage]
    runReturns = [None]

    def __init__(self, context, **kwargs):
        super(ResultingImageWriter, self).__init__(**kwargs)

    def __exec__(self, context, *args):
        """
        We change self.img.pixels just for the ts_out.write_image call.
        Once we have written, we revert self.img.pixels to its original value.
        """
        self.img = args[0]
        origimg = self.img.pixels.copy()
        ts_out = context.getVal("outts." + self.outstream)
        self.img.parent_timestream = ts_out
        self.img.data["processed"] = "yes"

        if self.img.ipm is not None:
            for key, iph in self.img.ipm.iter_through_pots():
                self.img.pixels = iph.getImage(
                    masked=self.masked, features=self.addStats,
                    inSuper=True)

        ts_out.write_image(self.img)
        ts_out.write_metadata()

        # reset to move forward
        self.img.parent_timestream = None
        self.img.pixels = origimg

        return [self.img]


class ResizeImage (PipeComponent):
    actName = "resize"
    argNames = {"mess": [False, "Output Message", "Resizing Image"],
                "resolution": [False, "Resolution, scale factor or None", None]}

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ResizeImage, self).__init__(**kwargs)
        if self.resolution is not None:
            try:
                self.resolution = float(self.resolution)
            except TypeError:
                try:
                    self.resolution = tuple(self.resolution)
                except TypeError:
                    raise PCExBadRunExpects(self.__class__, "resolution")

    def __exec__(self, context, *args):
        """
        We try to resize the image to whatever resolution the user specifies
        """
        if self.resolution is None:
            return args

        img = args[0]
        if isinstance(self.resolution, tuple):
            img.pixels = skimage.transform.resize(img.pixels, self.resolution)
        elif isinstance(self.resolution, float):
            img.pixels = skimage.transform.rescale(img.pixels, self.resolution)
        else:
            raise PCExBreakInPipeline(self.actName, "Invalid resolution value")

        return [img]


class DerandomizeTimeStreams (PipeComponent):
    actName = "derandomize"
    argNames = {"mess": [False, "Output Message", "Derandomizing"],
                "derandStruct": [True, "Derandomization Structure"]}
    # derandStruct(dict): {mid0:{TS0:[(PotId,Text), (PotId,Text)...],
    #                            TS1:[(PotId,Text), (PotId,Text)...]...},
    #                      mid1:{TS0:[(PotId,Text), (PotId,Text)...],
    #                            TS1:[(PotId,Text), (PotId,Text)...],...},...}
    # mid*(str): is the metaid string
    # TS*(str): is the path to the TimeStreamTraverser
    # PotId(str): is the Pot number in TS*
    # Text(str): is the string that we put on every pot

    runExpects = [datetime.datetime]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(DerandomizeTimeStreams, self).__init__(**kwargs)

        # 1. Create only one instance of all TSs and use
        #    it when referencing pots.
        self._tsts = {}
        # unique Timestream paths from derandStruct
        tspaths = set([x for _, l in self.derandStruct.iteritems()
                       for x in l.keys()])
        for tspath in tspaths:
            self._tsts[tspath] = TimeStreamTraverser(str(tspath))

        # Create _mids(dict): {mid0:[(PotObj:Text),(PotObj:Text)...],
        #                      mid1:[(PotObj:Text),(PotObj:Text)...]...}
        # PotObj(PyObject): is the Pot Object.
        # Text(str): Text that is output on top of image.
        # Easy direct relation between mids and pot objects
        self._mids = {}
        for mid in [i for i, _ in self.derandStruct.iteritems()]:
            self._mids[mid] = []

        self._numPotPerMid = self.refreshMids(timestamp=None)
        self._numMid = len(self._mids)

        # Variables for putText
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._scale = 1
        self._color = (255, 0, 0)

    def __exec__(self, context, *args):
        img = TimeStreamImage(args[0])
        img.pixels = self.createCompoundImage(args[0])
        return [img]

    def createCompoundImage(self, timestamp):

        # 1. Max size of pot imgs. All pots are checked.
        self.refreshMids(timestamp=timestamp)
        maxPotRect = (0, 0)
        for _, potlist in self._mids.iteritems():
            for pot, _ in potlist:
                if pot.rect.width > maxPotRect[0] \
                        or pot.rect.height > maxPotRect[1]:
                    maxPotRect = (pot.rect.width, pot.rect.height)

        # 2. Find column and row length for both _numPotPerMid and _numMid
        v = np.sqrt(self._numPotPerMid)
        if v % 1 == 0 or v % 1 > 0.5:
            numPotPerMidSize = (np.ceil(v), np.ceil(v))
        else:
            numPotPerMidSize = (np.floor(v), np.floor(v)+1)

        v = np.sqrt(self._numMid)
        if v % 1 == 0 or v % 1 > 0.5:
            numMidSize = (np.ceil(v), np.ceil(v))
        else:
            numMidSize = (np.floor(v), np.floor(v)+1)

        # 3 Init the derandomized image
        retImgHeight = maxPotRect[1] * numPotPerMidSize[0] * numMidSize[0]
        retImgWidth = maxPotRect[0] * numPotPerMidSize[1] * numMidSize[1]
        retImg = np.zeros((retImgHeight, retImgWidth, 3),
                          dtype=np.dtype("uint8"))

        i = 0  # the ith mid being added
        for mid, potlist in self._mids.iteritems():
            midGrpRow = i % numMidSize[0]
            midGrpCol = int(np.floor(float(i)/numMidSize[0]))

            # Width {From,To}
            wF = midGrpRow*maxPotRect[0]*numPotPerMidSize[0]
            wT = wF + (maxPotRect[0]*numPotPerMidSize[0])
            # Height {From,To}
            hF = midGrpCol*maxPotRect[1]*numPotPerMidSize[1]
            hT = hF + (maxPotRect[1]*numPotPerMidSize[1])

            retImg[wF:wT, hF:hT, :] = self.getMidGrpImg(mid,
                                                        potlist,
                                                        maxPotRect,
                                                        numPotPerMidSize)
            i += 1

        return retImg

    def getMidGrpImg(self, mid, potList, maxPotRect, numPotPerMidSize):
        midGrpImgHeight = maxPotRect[1] * numPotPerMidSize[0]
        midGrpImgWidth = maxPotRect[0] * numPotPerMidSize[1]
        midGrpImg = np.zeros((midGrpImgHeight, midGrpImgWidth, 3),
                             dtype=np.dtype("uint8"))

        j = 0  # j'th pot being added
        for pot, pottext in potList:
            potGrpRow = j % numPotPerMidSize[0]
            potGrpCol = int(np.floor(float(j)/numPotPerMidSize[0]))

            # Width {From,To}
            wF = potGrpRow*maxPotRect[0]
            wT = wF + maxPotRect[0]
            # Height {From,To}
            hF = potGrpCol*maxPotRect[1]
            hT = hF + maxPotRect[1]

            # Increase images size to fit maximum
            wdiff = maxPotRect[0] - pot.rect.width
            hdiff = maxPotRect[1] - pot.rect.height
            if wdiff > 0 or hdiff > 0:
                pot.increaseRect(leftby=0, topby=0,
                                 rightby=wdiff, bottomby=hdiff)

            img = pot.getImage()
            if len(pottext) > 11:
                pottext = pottext[:4]+"..."+pottext[-4:]
            cv2.putText(img, pottext, (10,img.shape[1]-5),
                        self._font, self._scale*.7, self._color, 2)
            midGrpImg[wF:wT, hF:hT, :] = img
            j += 1

        # Wite image Perimeter
        midGrpImg[:, [0,(midGrpImgWidth-1)], :] = (255,255,255)
        midGrpImg[[0,(midGrpImgHeight-1)], :, :] = (255,255,255)

        # Write the mid name on the midgrpimg
        txt = str(mid)
        cv2.putText(midGrpImg, txt, (30,30),
                    self._font, self._scale, self._color, 3)

        return midGrpImg

    def refreshMids(self, timestamp=None):
        # Count pots at the same time
        maxPotPerMid = 0

        # Flush current _mids
        for mid in self._mids.keys():
            self._mids[mid] = []

        # Create intermediate tuple list to ease _mids creation
        mid_pth_pts = [(mid,pth,pts)
                       for mid,l in self.derandStruct.iteritems()
                       for pth, pts in l.iteritems() ]
        # Pre-load images to avoid going to disk
        tsimgs = {}
        for pth, ts in self._tsts.iteritems():
            if timestamp is None:
                tsimgs[pth] = ts.curr()
            else:
                # Get the closest image to timestamp
                deltas = [abs(timestamp-t) for t in ts.timestamps]
                tInd = deltas.index(min(deltas))
                tsimgs[pth] = ts.getImgByTimeStamp(ts.timestamps[tInd],
                                                   update_index=True)

        # mid -> meta ids
        # pth -> TimeStream path
        # pts -> list of pot numbers
        for mid, pth, pts in mid_pth_pts:
            if pth not in tsimgs.keys():
                continue
            img = tsimgs[pth]
            if img.ipm is None:
                continue
            for potnum, pottext in pts:
                pot = img.ipm.getPot(int(potnum))
                self._mids[mid].append((pot, pottext))

            # Find the max number of elements for one mid
            if len(self._mids[mid]) > maxPotPerMid:
                maxPotPerMid = len(self._mids[mid])

        return maxPotPerMid


class ResizeAndWriteImage (PipeComponent):
    actName = "resizeAndWriteImage"
    # For now we have resolution and size because the image writer also wants
    # to resize. We should remove size when we fix image write.
    argNames = {
        "mess": [False, "Output Message", "Resizing and Writing Image"],
        "resolution": [False, "Resolution, scale factor or None", None],
        "outstream": [True, "Name of stream to use"],
        "addStats": [False, "List of statistics", []],
        "masked": [False, "Whether to output masked images", False]
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ResizeAndWriteImage, self).__init__(**kwargs)
        kwargs["mess"] = ""
        self.resizeImage = ResizeImage(context, **kwargs)
        self.resultingImageWriter = ResultingImageWriter(context, **kwargs)

    def __exec__(self, context, *args):
        res = self.resizeImage(context, *[args[0].clone(copy_pixels=True)])
        self.resultingImageWriter(context, *res)
        return args

    def show(self):
        self.resizeImage.show()
        self.resultingImageWriter.show()
