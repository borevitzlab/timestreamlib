# coding=utf-8
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

from timestream import TimeStreamImage
import timestream.manipulate.correct_detect as cd
import timestream.manipulate.plantSegmenter as tm_ps
import timestream.manipulate.pot as tm_pot

LOG = logging.getLogger("CONSOLE")


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
        for attrKey, attrVal in self.__class__.argNames.iteritems():
            try:
                setattr(self, attrKey, kwargs[attrKey])
            except KeyError:
                if (not attrVal[0]):
                    # if optional set the default
                    setattr(self, attrKey, attrVal[2])
                else:
                    raise PCExBadRunExpects(self.__class__, attrKey)

    def __call__(self, context, *args):
        """ Is executed every time a component needs to do something.

        Args:
          context(PCFGSection): a tree containing context arguments. Same names
            for all components
          args(list): What this components receives
        """
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


class PCException(Exception):

    def __init__(self):
        pass

    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)


class PCExBadRunExpects(PCException):

    def __init__(self, cls, attrKey=None):
        self.message = "The call to %s should consider \n%s" % \
            (cls.actName, cls.info())
        if attrKey is not None:
            self.message = self.message + \
                " Error: missing entry for '%s'" % attrKey


class PCExBrakeInPipeline(PCException):

    def __init__(self, name, msg):
        self.message = "Unrecoverable error at %s: %s" % (name, msg)


class ImageUndistorter (PipeComponent):
    actName = "undistort"
    argNames = {
        "mess": [True, "Apply lens distortion correction"],
        "cameraMatrix": [True,
                         "3x3 matrix for mapping physical coordinates with "
                         "screen coords"],
        "distortCoefs": [True, "5x1 matrix for image distortion"],
        "imageSize": [True, "2x1 matrix: [width, height]"],
        "rotationAngle": [True, "rotation angle for the image"],
    }

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

    def __call__(self, context, *args):
        LOG.info(self.mess)
        tsi = args[0]
        self.image = tsi.pixels
        if self.UndistMapX is not None and self.UndistMapY is not None:
            self.imageUndistorted = cv2.remap(self.image.astype(np.uint8),
                                              self.UndistMapX, self.UndistMapY,
                                              cv2.INTER_CUBIC)
        else:
            self.imageUndistorted = self.image

        tsi.pixels = cd.rotateImage(self.imageUndistorted, self.rotationAngle)
        return [tsi]

    def show(self):
        plt.figure()
        plt.subplot(211)
        plt.imshow(cd.rotateImage(self.image))
        plt.title('Original image')

        plt.subplot(212)
        plt.imshow(self.imageUndistorted)
        plt.title('Undistorted image')
        plt.show()


class ColorCardDetector (PipeComponent):
    actName = "colorcarddetect"
    argNames = {
        "mess": [True, "Detect color card"],
        "colorcardTrueColors": [True,
                                "Matrix representing the groundtrue color "
                                "card colors"],
        "minIntensity": [False,
                         "Skip colorcard detection if intensity below this value",
                         0],
        "colorcardFile": [True, "Path to the color card file"],
        "colorcardPosition": [True, "(x,y) of the colorcard"],
        "settingPath": [True, "Path to setting files"],
        "useWhiteBackground": [False,
                               "White background as reference for color corretion?",
                               False],
        "backgroundWindow": [False,
                             "Window background region with top-left & "
                             "botom-right corners",
                             []],
        "maxIntensity": [False,
                         "Max intensity when correcting using white background",
                         255],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage, list]

    def __init__(self, context, **kwargs):
        super(ColorCardDetector, self).__init__(**kwargs)
        self.ccf = os.path.join(context.ints.path,
                                self.settingPath, self.colorcardFile)
        # for glasshouse experiment, color card is outside of timestream path
        if not os.path.exists(self.ccf):
            configFilePath = os.path.dirname(
                context.ints.data["settings"]['configFile'])
            self.ccf = os.path.join(configFilePath, self.colorcardFile)

    def __call__(self, context, *args):
        LOG.info(self.mess)
        tsi = args[0]
        self.image = tsi.pixels
        meanIntensity = np.mean(self.image)
        if meanIntensity < self.minIntensity:
            # FIXME: this should be handled with an error.
            LOG.warn('Image is too dark, skiping colorcard detection!')
            return([self.image, [None, None, None]])
        if not self.useWhiteBackground:
            self.imagePyramid = cd.createImagePyramid(self.image)
            ccdImg = cv2.imread(self.ccf)[:, :, ::-1]
            if ccdImg is None:
                raise ValueError("Failed to read %s" % self.ccf)
            self.colorcardPyramid = cd.createImagePyramid(ccdImg)
            # create image pyramid for multiscale matching
            SearchRange = [self.colorcardPyramid[0].shape[1],
                           self.colorcardPyramid[0].shape[0]]
            score, loc, angle = cd.matchTemplatePyramid(
                self.imagePyramid,
                self.colorcardPyramid,
                0,
                EstimatedLocation=self.colorcardPosition,
                SearchRange=SearchRange
            )
            if score > 0.3:
                # extract color information
                self.foundCard = self.image[
                    loc[1] - ccdImg.shape[0] // 2:loc[1] + ccdImg.shape[0] // 2,
                    loc[0] - ccdImg.shape[1] // 2:loc[0] + ccdImg.shape[1] // 2]
                self.ccdColors, _ = cd.getColorcardColors(self.foundCard,
                                                          GridSize=[6, 4])
                self.colorcardParams = cd.estimateColorParameters(
                    self.colorcardTrueColors,
                    self.colorcardColors
                )
                # Save colourcard image to instance
                self.colorcardImage = ccdImg
                # for displaying
                self.loc = loc
            else:
                # FIXME: this should be handled with an error.
                LOG.warn('Cannot find color card')
                self.colorcardParams = [None, None, None]
        else:
            self.colorcardParams = cd.estimateColorParametersFromWhiteBackground(
                self.image, self.backgroundWindow, self.maxIntensity)
        return([tsi, self.colorcardParams])

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
                [TLC[0],
                 TLC[0],
                    BRC[0],
                    BRC[0],
                    TLC[0]],
                [TLC[1],
                 BRC[1],
                    BRC[1],
                    TLC[1],
                    TLC[1]],
                'w')
            plt.title('Selected white region for color correction')
        plt.show()


class ImageColorCorrector (PipeComponent):
    actName = "colorcorrect"
    argNames = {
        "mess": [False, "Correct image color"],
        "writeImage": [False,
                       "Whether to write processing image to output timestream",
                       False],
        "minIntensity": [False,
                         "Skip colorcard correction if intensity below this value",
                         0],
    }

    runExpects = [TimeStreamImage, list]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ImageColorCorrector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        LOG.info(self.mess)
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
            self.imageCorrected[np.where(self.imageCorrected < 0)] = 0
            self.imageCorrected[np.where(self.imageCorrected > 255)] = 255
            self.imageCorrected = self.imageCorrected.astype(np.uint8)
        else:
            # FIXME: This should be handled with an exception.
            LOG.warn('Skip color correction')
            self.imageCorrected = image
        self.image = image  # display

        tsi.pixels = self.imageCorrected
        return([tsi])

    def show(self):
        plt.figure()
        plt.subplot(211)
        plt.imshow(self.image)
        plt.title('Image without color correction')

        plt.subplot(212)
        plt.imshow(self.imageCorrected)
        plt.title('Color-corrected image')
        plt.show()


class TrayDetector (PipeComponent):
    actName = "traydetect"
    argNames = {
        "mess": [False, "Detect tray positions"],
        "trayFiles": [True,
                      "File name pattern for trays such as Trays_%02d.png"],
        "trayNumber": [True, "Number of trays in given image"],
        "trayPositions": [True, "Estimated tray positions"],
        "settingPath": [True, "Path to setting files"],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage, list, list]

    def __init__(self, context, **kwargs):
        super(TrayDetector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        LOG.info(self.mess)
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
            trayImage = cv2.imread(trayFile)[:, :, ::-1]
            if trayImage is None:
                LOG.error("Fail to read", trayFile)
            trayImage[:, :, 1] = 0  # suppress green channel
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
                # FIXME: For now we don't handle missing trays.
                raise PCExBrakeInPipeline(
                    self.actName,
                    "Low tray matching score. Likely tray %d is missing." % i)

            self.trayLocs.append(loc)

        # add tray location information
        context.outputwithimage["trayLocs"] = self.trayLocs

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
    }

    runExpects = [TimeStreamImage, list, list]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PotDetector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        LOG.info(self.mess)
        tsi, self.imagePyramid, self.trayLocs = args
        self.image = tsi.pixels
        # read pot template image and scale to the pot size
        potFile = os.path.join(
            context.ints.path,
            self.settingPath,
            self.potFile)
        potImage = cv2.imread(potFile)[:, :, ::-1]
        potTemplateFile = os.path.join(
            context.ints.path,
            self.settingPath,
            self.potTemplateFile)
        potTemplateImage = cv2.imread(potTemplateFile)[:, :, ::-1]
        potTemplateImage[:, :, 1] = 0  # suppress green channel
        potTemplateImage = cv2.resize(
            potTemplateImage.astype(np.uint8),
            (potImage.shape[1],
             potImage.shape[0]))
        self.potPyramid = cd.createImagePyramid(potTemplateImage)

        XSteps = self.traySize[0] // self.potSize[0]
        YSteps = self.traySize[1] // self.potSize[1]
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
#            SearchRange = [32, 32]
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

        flattened = list(chain.from_iterable(self.potLocs2))
        growM = round(min(spatial.distance.pdist(flattened)) / 2)
        tsi.ipm = tm_pot.ImagePotMatrix(
            tsi,
            pots=[],
            growM=growM,
            ipmPrev=ipmPrev)
        potID = 1
        for tray in self.potLocs2:
            trayID = 1
            for center in tray:
                r = tm_pot.ImagePotRectangle(
                    center,
                    tsi.pixels.shape,
                    growM=growM)
                p = tm_pot.ImagePotHandler(potID, r, tsi.ipm)
                p.setMetaId("trayID", trayID)
                tsi.ipm.addPot(p)
                potID += 1
                trayID += 1

        context.outputwithimage["potLocs"] = self.potLocs2
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
        plt.title('Detected trays and pots')
        plt.show()


class PlantExtractor (PipeComponent):
    actName = "plantextract"
    argNames = {
        "mess": [False, "Extract plant biometrics", "default message"],
        "minIntensity": [False,
                         "Skip image segmentation if intensity below this value",
                         0],
        "meth": [False, "Segmentation Method", "k-means-square"],
        "methargs": [False, "Method Args: maxIter, epsilon, attempts", {}],
        "parallel": [False, "Whether to run in parallel", False],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PlantExtractor, self).__init__(**kwargs)
        if self.meth not in tm_ps.segmentingMethods.keys():
            raise ValueError("%s is not a valid method" % self.meth)
        # FIXME: Check the arg names. Inform an error in yaml file if error.
        self.segmenter = tm_ps.segmentingMethods[self.meth](**self.methargs)

    def __call__(self, context, *args):
        LOG.info(self.mess)
        tsi = args[0]
        img = tsi.pixels
        self.ipm = tsi.ipm

        # Set the segmenter in all the pots
        for key, iph in self.ipm.iter_through_pots():
            iph.ps = self.segmenter

        # Segment all pots and put
        tsi.pixels = self.segAllPots(img.copy())

        # Put current image pot matrix in context for the next run
        context.setVal("ipmPrev", self.ipm)

        return [tsi]

    def segAllPots(self, img):
        if not self.parallel:
            for key, iph in self.ipm.iter_through_pots():
                img = img & iph.maskedImage(inSuper=True)
            return (img)

        # Parallel from here: We create a child process for each pot and pipe
        # the pickled result back to the parent.
        # FIXME: Joel: This should be done using the multiprocessing module if
        # possible.
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
            except Exception as exc:
                raise RuntimeError("Unknown error segmenting %s %s" %
                                   (iph.id, str(exc)))
            finally:
                os._exit(0)
            # Child Section

        for iph, pid, In in childPids:
            pIn = os.fdopen(In, "rb")
            msk = cPickle.loads(pIn.read())
            os.waitpid(pid, 0)
            pIn.close()
            iph.mask = msk
            img = img & iph.maskedImage(inSuper=True)

        return (img)

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

    def __call__(self, context, *args):
        LOG.info(self.mess)
        ipm = args[0].ipm
        for key, iph in ipm.iter_through_pots():
            iph.calcFeatures(self.features)

        return [args[0]]


class ResultingFeatureWriter_ndarray (PipeComponent):
    actName = "writefeatures_ndarray"
    argNames = {
        "mess": [False, "Default message", "Writing the features"],
        "outputfile": [True, "File where the output goes"],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ResultingFeatureWriter_ndarray, self).__init__(**kwargs)

        # np.savez_compressed expects an npz extension
        p, e = os.path.splitext(self.outputfile)
        if e == "":
            self.outputfile = self.outputfile + ".npz"

        # We dont overwrite any data
        if os.path.exists(self.outputfile):
            raise Exception("File %s already exists" % self.outputfile)

    def __call__(self, context, *args):
        LOG.info(self.mess)
        ipm = args[0].ipm

        # Get timestamp of current image.
        ts = time.mktime(context.origImg.datetime.timetuple()) * 1000

        if not os.path.isfile(self.outputfile):
            fNames = np.array(ipm.potFeatures)
            pIds = np.array(ipm.potIds)
            tStamps = np.array([ts])

        else:
            npload = np.load(self.outputfile)
            fNames = npload["fNames"]
            pIds = npload["pIds"]
            featMat = npload["featMat"]
            tStamps = npload["tStamps"]
            tStamps = np.append(tStamps, ts)  # New timestamp

        tmpMat = np.zeros([fNames.shape[0], pIds.shape[0], 1])
        for pId, pot in ipm.iter_through_pots():
            for fName, fVal in pot.getCalcedFeatures().iteritems():
                fOff = np.where(fNames == fName)
                pOff = np.where(pIds == pId)
                tmpMat[fOff, pOff, 0] = fVal

        if "featMat" not in locals():
            featMat = tmpMat
        else:
            featMat = np.concatenate((featMat, tmpMat), axis=2)

        np.savez_compressed(self.outputfile,
                            **{"fNames": fNames, "pIds": pIds,
                                "featMat": featMat, "tStamps": tStamps})

        return (args[0])


class ResultingFeatureWriter_csv (PipeComponent):
    actName = "writefeatures_csv"
    argNames = {
        "mess": [False, "Default message", "Writing the features"],
        "outputdir": [False, "Dir where the output files go", None],
        "overwrite": [False, "Whether to overwrite out files", True],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(ResultingFeatureWriter_csv, self).__init__(**kwargs)

        if self.outputdir is None:
            if not context.hasSubSecName("outputroot"):
                raise Exception("Must define output directory")

            if not os.path.isdir(context.outputroot):
                raise Exception("%s is not a directory" %
                                context.outputroot)

            self.outputdir = os.path.join(context.outputroot, "csv")

        if not os.path.exists(self.outputdir):
            os.makedirs(self.outputdir)

        # Are there any feature csv files? We check all possible features.
        for fName in tm_ps.StatParamCalculator.statParamMethods():
            outputfile = os.path.join(self.outputdir, fName + ".csv")
            if os.path.exists(outputfile):
                if self.overwrite:
                    os.remove(outputfile)
                else:
                    raise Exception("%s might have important info"
                                    % outputfile)

    def __call__(self, context, *args):
        LOG.info(self.mess)
        ipm = args[0].ipm
        ts = time.mktime(context.origImg.datetime.timetuple()) * 1000

        for fName in ipm.potFeatures:
            outputfile = os.path.join(self.outputdir, fName + ".csv")

            # Sorted so we can easily append after.
            potIds = sorted(ipm.potIds)

            if not os.path.exists(outputfile):  # we initialize it.
                fd = open(outputfile, "w+")
                fd.write("timestamp")
                for potId in potIds:
                    fd.write(",%s" % potId)
                fd.write("\n")
                fd.close()

            fd = open(outputfile, 'a')
            fd.write("%f" % ts)
            for potId in potIds:
                pot = ipm.getPot(potId)
                fd.write(",%f" % pot.getCalcedFeatures()[fName])
            fd.write("\n")
            fd.close()

        return (args[0])


class ResultingImageWriter (PipeComponent):
    actName = "imagewrite"
    argNames = {
        "mess": [False, "Output Message", "Writing Image"],
        "outstream": [True, "Name of stream to use"],
    }

    runExpects = [TimeStreamImage]
    runReturns = [None]

    def __init__(self, context, **kwargs):
        super(ResultingImageWriter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print (self.mess)
        # FIXME: Can we just use args[0] here?
        img = args[0]
        ts_out = context.getVal("outts." + self.outstream)
        img.parent_timestream = ts_out
        img.data["processed"] = "yes"
        for key, value in context.outputwithimage.iteritems():
            img.data[key] = value

        ts_out.write_image(img)
        ts_out.write_metadata()
        img.parent_timestream = None  # reset to move forward

        return [img]


class PopulatePotMetaIds (PipeComponent):
    actName = "populatepotmetaids"
    argNames = {
        "mess": [False, "Output Message", "Populating Metaids"],
        "metas": [False, "Dictionary binidng potID with global IDS", {}],
    }

    runExpects = [TimeStreamImage]
    runReturns = [TimeStreamImage]

    def __init__(self, context, **kwargs):
        super(PopulatePotMetaIds, self).__init__(**kwargs)

    def __call__(self, context, *args):
        ipm = args[0].ipm
        # assign all the metaids that we find in self.metas
        for midName in self.metas.keys():
            for potid, mval in self.metas[midName].iteritems():
                ipm.getPot(potid).setMetaId(midName, mval)

        return [args[0]]
