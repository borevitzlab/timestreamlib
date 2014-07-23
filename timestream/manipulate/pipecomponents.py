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
import timestream.manipulate.correct_detect as cd
import timestream.manipulate.plantSegmenter as ps
from timestream import TimeStreamImage, parse
import timestream
import os
import os.path
import time
import sys
import cPickle

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

    # context: dict containing context arguments.
    #           Name and values are predefined for all pipe components.
    # *args: this component receives
    def __call__(self, context, *args):
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

    def show(self):
        pass

class PCException(Exception):
    def __init__(self):
        pass
    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)
class PCExBadRunExpects(PCException):
    def __init__(self, cls):
        self.message = "The call to %s should consider \n%s" % \
                (cls.actName, cls.info())
class PCExBrakeInPipeline(PCException):
    def __init__(self, name, msg):
        self.message = "Urecoverable error at %s: %s" % (name, msg)


class Tester ( PipeComponent ):
    actName = "tester"
    argNames = { "arg1": [True, "Argument 1 example"],
                 "arg2": [False, "Argument 2 example", 4] }

    runExpects = [ np.ndarray, np.ndarray ]
    runReturns = [ np.ndarray, np.ndarray ]

    def __init__(self, context, **kwargs):
        super(Tester, self).__init__(**kwargs)

    def __call__(self, context, *args):
        ndarray = args[0] # np.ndarray
        print(ndarray)

        return ([ndarray, ndarray])

class ImageUndistorter ( PipeComponent ):
    actName = "undistort"
    argNames = {"mess": [True, "Apply lens distortion correction"],
                "cameraMatrix": [True, "3x3 matrix for mapping physical" \
                    + "coordinates with screen coordinates"],\
                "distortCoefs": [True, "5x1 matrix for image distortion"],
                "imageSize":    [True, "2x1 matrix: [width, height]"],
                "rotationAngle": [True, "rotation angle for the image"] }

    runExpects = [np.ndarray]
    runReturns = [np.ndarray]

    def __init__(self, context, **kwargs):
        super(ImageUndistorter, self).__init__(**kwargs)
        self.UndistMapX, self.UndistMapY = cv2.initUndistortRectifyMap( \
            np.asarray(self.cameraMatrix), np.asarray(self.distortCoefs), \
            None, np.asarray(self.cameraMatrix), tuple(self.imageSize), cv2.CV_32FC1)

    def __call__(self, context, *args):
        print(self.mess)
        self.image = cd.rotateImage(args[0], self.rotationAngle)
        if self.UndistMapX != None and self.UndistMapY != None:
            self.imageUndistorted = cv2.remap(self.image.astype(np.uint8), \
                self.UndistMapX, self.UndistMapY, cv2.INTER_CUBIC)
        else:
            self.imageUndistorted = self.image

        return([self.imageUndistorted])

    def show(self):
        plt.figure()
        plt.subplot(211)
        plt.imshow(self.image)
        plt.title('Original image')

        plt.subplot(212)
        plt.imshow(self.imageUndistorted)
        plt.title('Undistorted image')
        plt.show()

class ColorCardDetector ( PipeComponent ):
    actName = "colorcarddetect"
    argNames = {"mess": [True, "Detect color card"], \
                "colorcardTrueColors": [True, "Matrix representing the " \
                    + "groundtrue color card colors"],
                "minIntensity": [False, "Skip colorcard detection if intensity below this value", 0],
                "colorcardFile": [True, "Path to the color card file"],
                "colorcardPosition": [True, "(x,y) of the colorcard"],
                "settingPath": [True, "Path to setting files"]
                }

    runExpects = [np.ndarray]
    runReturns = [np.ndarray, list]

    def __init__(self, context, **kwargs):
        super(ColorCardDetector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        self.image = args[0]
        meanIntensity = np.mean(self.image)
        if meanIntensity < self.minIntensity:
            print('Image is too dark, mean(I) = %f < %f. Skip colorcard detection!' %(meanIntensity, self.minIntensity) )
            return([self.image, [None, None, None]])

        self.imagePyramid = cd.createImagePyramid(self.image)

        # TODO: move this into __init__ if context is provided
        #       when initialising the pipeline
        ccf = os.path.join(context["rts"].path, self.settingPath, self.colorcardFile)
        self.colorcardImage = cv2.imread(ccf)[:,:,::-1]
        if self.colorcardImage == None:
            raise ValueError ( "Failed to read %s" % ccf )
        self.colorcardPyramid = cd.createImagePyramid(self.colorcardImage)

        # create image pyramid for multiscale matching
        SearchRange = [self.colorcardPyramid[0].shape[1], self.colorcardPyramid[0].shape[0]]
        score, loc, angle = cd.matchTemplatePyramid(self.imagePyramid, self.colorcardPyramid, \
            0, EstimatedLocation = self.colorcardPosition, SearchRange = SearchRange)
        if score > 0.3:
            # extract color information
            self.foundCard = self.image[loc[1]-self.colorcardImage.shape[0]//2:loc[1]+self.colorcardImage.shape[0]//2, \
                                        loc[0]-self.colorcardImage.shape[1]//2:loc[0]+self.colorcardImage.shape[1]//2]
            self.colorcardColors, _ = cd.getColorcardColors(self.foundCard, GridSize = [6, 4])
            self.colorcardParams = cd.estimateColorParameters(self.colorcardTrueColors, self.colorcardColors)
            # for displaying
            self.loc = loc
        else:
            print('Cannot find color card')
            self.colorcardParams = [None, None, None]

        return([self.image, self.colorcardParams])

    def show(self):
        plt.figure()
        plt.subplot(211)
        plt.imshow(self.image)
        plt.hold(True)
        plt.plot([self.loc[0]], [self.loc[1]], 'ys')
        plt.text(self.loc[0]-30, self.loc[1]-15, 'ColorCard', color='yellow')
        plt.title('Detected color card')

        plt.subplot(212)
        plt.imshow(self.foundCard)
        plt.title('Detected color card')
        plt.show()

class ImageColorCorrector ( PipeComponent ):
    actName = "colorcorrect"
    argNames = {"mess": [False, "Correct image color"],
                "writeImage": [False, "Whether to write processing image to output timestream", False],
                "minIntensity": [False, "Skip colorcard correction if intensity below this value", 0]
                }

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray]

    def __init__(self, context, **kwargs):
        super(ImageColorCorrector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        image, colorcardParam = args

        meanIntensity = np.mean(image)
        colorMatrix, colorConstant, colorGamma = colorcardParam
        if colorMatrix != None and meanIntensity > self.minIntensity:
            self.imageCorrected = cd.correctColorVectorised(image.astype(np.float), colorMatrix, colorConstant, colorGamma)
            self.imageCorrected[np.where(self.imageCorrected < 0)] = 0
            self.imageCorrected[np.where(self.imageCorrected > 255)] = 255
            self.imageCorrected = self.imageCorrected.astype(np.uint8)
        else:
            print('Skip color correction')
            self.imageCorrected = image
        self.image = image # display

        return([self.imageCorrected])

    def show(self):
        plt.figure()
        plt.subplot(211)
        plt.imshow(self.image)
        plt.title('Image without color correction')

        plt.subplot(212)
        plt.imshow(self.imageCorrected)
        plt.title('Color-corrected image')
        plt.show()

class TrayDetector ( PipeComponent ):
    actName = "traydetect"
    argNames = {"mess": [False,"Detect tray positions"],
                "trayFiles": [True, "File name pattern for trays "\
                     + "such as Trays_%02d.png"],
                "trayNumber": [True, "Number of trays in given image"],
                "trayPositions": [True, "Estimated tray positions"],
                "settingPath": [True, "Path to setting files"]
                }

    runExpects = [np.ndarray]
    runReturns = [np.ndarray, list]

    def __init__(self, context, **kwargs):
        super(TrayDetector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        self.image = args[0]
        temp = np.zeros_like(self.image)
        temp[:,:,:] = self.image[:,:,:]
        temp[:,:,1] = 0 # suppress green channel
        self.imagePyramid = cd.createImagePyramid(temp)
        self.trayPyramids = []
        for i in range(self.trayNumber):
            trayFile = os.path.join(context["rts"].path, self.settingPath, self.trayFiles % i)
##             fixed tray image so that perspective postions of the trays are fixed
#            trayFile = os.path.join(context["rts"].path, self.settingPath, self.trayFiles % 2)
            trayImage = cv2.imread(trayFile)[:,:,::-1]
            if trayImage == None:
                print("Fail to read", trayFile)
            trayImage[:,:,1] = 0 # suppress green channel
            trayPyramid = cd.createImagePyramid(trayImage)
            self.trayPyramids.append(trayPyramid)

        self.trayLocs = []
        for i,trayPyramid in enumerate(self.trayPyramids):
            SearchRange = [trayPyramid[0].shape[1]//6, trayPyramid[0].shape[0]//6]
            score, loc, angle = cd.matchTemplatePyramid(self.imagePyramid, trayPyramid, \
                RotationAngle = 0, EstimatedLocation = self.trayPositions[i], SearchRange = SearchRange)
            if score < 0.3:
                # FIXME: For now the pipeline does not know how to handle
                #        missing trays.
                raise PCExBrakeInPipeline(self.actName, \
                    "Low tray matching score. Likely tray %d is missing." %i)

            self.trayLocs.append(loc)

        # add tray location information
        date = context["img"].datetime
        context["outputwithimage"]["trayLocs"] = self.trayLocs

        return([self.image, self.imagePyramid, self.trayLocs])

    def show(self):
        plt.figure()
        plt.imshow(self.image.astype(np.uint8))
        plt.hold(True)
        PotIndex = 0
        for i,Loc in enumerate(self.trayLocs):
            if Loc == None:
                continue
            plt.plot([Loc[0]], [Loc[1]], 'bo')
            PotIndex = PotIndex + 1
        plt.title('Detected trays')
        plt.show()

class PotDetector ( PipeComponent ):
    actName = "potdetect"
    argNames = {"mess": [False, "Detect pot position"],
                "potFile": [True, "File name of a pot image"],
                "potTemplateFile": [True, "File name of a pot template image"],
                "potPositions": [True, "Estimated pot positions"],
                "potSize": [True, "Estimated pot size"],
                "traySize": [True, "Estimated tray size"],
                "settingPath": [True, "Path to setting files"]
                }

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray, list]

    def __init__(self, context, **kwargs):
        super(PotDetector, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        self.image, self.imagePyramid, self.trayLocs = args
        # read pot template image and scale to the pot size
        potFile = os.path.join(context["rts"].path, self.settingPath, self.potFile)
        potImage = cv2.imread(potFile)[:,:,::-1]
        potTemplateFile = os.path.join(context["rts"].path, self.settingPath, self.potTemplateFile)
        potTemplateImage = cv2.imread(potTemplateFile)[:,:,::-1]
        potTemplateImage[:,:,1] = 0 # suppress green channel
        potTemplateImage = cv2.resize(potTemplateImage.astype(np.uint8), (potImage.shape[1], potImage.shape[0]))
        self.potPyramid = cd.createImagePyramid(potTemplateImage)

        XSteps = self.traySize[0]//self.potSize[0]
        YSteps = self.traySize[1]//self.potSize[1]
        StepX  = self.traySize[0]//XSteps
        StepY  = self.traySize[1]//YSteps

        self.potLocs2 = []
        self.potLocs2_ = []
        potGridSize = [4,5]
        for trayLoc in self.trayLocs:
            if trayLoc == None:
                self.potLocs2.append(None)
                continue
            StartX = trayLoc[0] - self.traySize[0]//2 + StepX//2
            StartY = trayLoc[1] + self.traySize[1]//2 - StepY//2
            SearchRange = [self.potPyramid[0].shape[1]//4, self.potPyramid[0].shape[0]//4]
#            SearchRange = [32, 32]
            locX = np.zeros(potGridSize)
            locY = np.zeros(potGridSize)
            for k in range(potGridSize[0]):
                for l in range(potGridSize[1]):
                    estimateLoc = [StartX + StepX*k, StartY - StepY*l]
                    score, loc,angle = cd.matchTemplatePyramid(self.imagePyramid, \
                        self.potPyramid, RotationAngle = 0, \
                        EstimatedLocation = estimateLoc, NoLevels = 3, SearchRange = SearchRange)
                    locX[k,l], locY[k,l] = loc

            # correct for detection error
            potLocs = []
            potLocs_ = []
            diffXX = locX[1:,:] - locX[:-1,:]
            diffXY = locX[:,1:] - locX[:,:-1]
            diffYX = locY[1:,:] - locY[:-1,:]
            diffYY = locY[:,1:] - locY[:,:-1]
            diffXXMedian = np.median(diffXX)
            diffXYMedian = np.median(diffXY)
            diffYXMedian = np.median(diffYX)
            diffYYMedian = np.median(diffYY)
            for k in range(potGridSize[0]):
                for l in range(potGridSize[1]):
                    locX[k,l] = trayLoc[0] + diffXXMedian*(k-(potGridSize[0]-1.0)/2.0) + \
                        diffXYMedian*(l-(potGridSize[1]-1.0)/2.0)
                    locY[k,l] = trayLoc[1] + diffYXMedian*(k-(potGridSize[0]-1.0)/2.0) + \
                        diffYYMedian*(l-(potGridSize[1]-1.0)/2.0)
                    # this fixes perpective shift
                    # TODO: need a more elegant solution
                    locY[k,l] = locY[k,l] + 10

                    potLocs.append([locX[k,l], locY[k,l]])
                    potLocs_.append(estimateLoc)
            self.potLocs2.append(potLocs)
            self.potLocs2_.append(potLocs_)

        # add pot location information
        date = context["img"].datetime
        context["outputwithimage"]["potLocs"] = self.potLocs2

        return([self.image, self.potLocs2])

    def show(self):
        plt.figure()
        plt.imshow(self.image.astype(np.uint8))
        plt.hold(True)
        PotIndex = 0
        for i,Loc in enumerate(self.trayLocs):
            if Loc == None:
                continue
            plt.plot([Loc[0]], [Loc[1]], 'bo')
            plt.text(Loc[0], Loc[1]-15, 'T'+str(i+1), color='blue', fontsize=20)
            for PotLoc,PotLoc_ in zip(self.potLocs2[i], self.potLocs2_[i]):
                plt.plot([PotLoc[0]], [PotLoc[1]], 'ro')
                plt.text(PotLoc[0], PotLoc[1]-15, str(PotIndex+1), color='red')
                plt.plot([PotLoc_[0]], [PotLoc_[1]], 'rx')
                PotIndex = PotIndex + 1
        plt.title('Detected trays and pots')
        plt.show()

class PlantExtractor ( PipeComponent ):
    actName = "plantextract"
    argNames = {"mess": [False, "Extract plant biometrics", "default message"], \
                "minIntensity": [False, "Skip image segmentation if intensity below this value", 0],\
                "meth": [False, "Segmentation Method", "k-means-square"], \
                "methargs": [False, "Method Args: maxIter, epsilon, attempts", {}],
                "parallel": [False, "Whether to run in parallel", False]}

    runExpects = [np.ndarray, list]
    runReturns = [np.ndarray, ps.ImagePotMatrix]

    def __init__(self, context, **kwargs):
        super(PlantExtractor, self).__init__(**kwargs)
        if self.meth not in ps.segmentingMethods.keys():
            raise ValueError ("%s is not a valid method" % self.meth)
        #FIXME: Check the arg names. Inform an error in yaml file if error.
        self.segmenter = ps.segmentingMethods[self.meth](**self.methargs)

    def __call__(self, context, *args):
        print(self.mess)
        img = args[0]
        centers = args[1]
        ipmPrev = None
        if "ipm" in context.keys():
            ipmPrev = context["ipm"]
        self.ipm = ps.ImagePotMatrix(img, centers=centers, ipmPrev=ipmPrev)

        # Set the segmenter in all the pots
        for key, iph in self.ipm.iter_through_pots():
            iph.ps = self.segmenter

        # Segment all pots and put
        retImg = self.segAllPots(img.copy())

        # Put current image pot matrix in context for the next run
        context["ipm"] = self.ipm
        return [retImg, self.ipm]

    def segAllPots(self, img):
        if not self.parallel:
            for key, iph in self.ipm.iter_through_pots():
                img = img & iph.maskedImage(inSuper=True)
            return (img)

        # Parallel from here: We create a child process for each pot and pipe
        # the pickled result back to the parent.
        childPids = []
        for key, iph in self.ipm.iter_through_pots():
            In, Out = os.pipe()
            pid = os.fork()
            if pid != 0: # In parent
                os.close(Out)
                childPids.append([iph, pid, In])
                continue

            ## ---- Child Section ---- ##
            try:
                os.close(In)
                msk = cPickle.dumps(iph.getSegmented())
                cOut = os.fdopen(Out, "wb", sys.getsizeof(msk))
                cOut.write(msk)
                cOut.close()
            except e:
                raise RuntimeError("Unknown error segmenting %s %e"%iph.id)
            finally:
                os._exit(0)
            ## ---- Child Section ---- ##

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

class FeatureExtractor ( PipeComponent ):
    actName = "featureextract"
    argNames = {"mess": [False, "Default message","Extracting Features"],
                "features": [False, "Features to extract", ["all"]]}

    runExpects = [np.ndarray, ps.ImagePotMatrix]
    runReturns = [np.ndarray, ps.ImagePotMatrix]

    def __init__(self, context, **kwargs):
        super(FeatureExtractor, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print(self.mess)
        ipm = args[1]
        for key, iph in ipm.iter_through_pots():
            iph.calcFeatures(self.features)

        return [args[0], ipm]

class ResultingFeatureWriter_ndarray ( PipeComponent ):
    actName = "writefeatures_ndarray"
    argNames = {"mess": [False, "Default message", "Writing the features"],
                "outputfile": [True, "File where the output goes"]}

    runExpects = [np.ndarray, ps.ImagePotMatrix]
    runReturns = [np.ndarray]

    def __init__(self, context, **kwargs):
        super(ResultingFeatureWriter_ndarray, self).__init__(**kwargs)

        #np.savez_compressed expects an npz extension
        p, e = os.path.splitext(self.outputfile)
        if e == "":
            self.outputfile = self.outputfile + ".npz"

        # We dont overwrite any data
        if os.path.exists(self.outputfile):
            raise StandardError("File %s already exists" % self.outputfile)

    def __call__(self, context, *args):
        print(self.mess)
        ipm = args[1]

        # Get timestamp of current image.
        ts = time.mktime(context["img"].datetime.timetuple()) * 1000

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
            tStamps = np.append(tStamps, ts) # New timestamp

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

        np.savez_compressed(self.outputfile, \
                    **{ "fNames":fNames, "pIds":pIds, \
                        "featMat":featMat, "tStamps":tStamps })

        return (args[0])

class ResultingFeatureWriter_csv ( PipeComponent ):
    actName = "writefeatures_csv"
    argNames = {"mess": [False, "Default message", "Writing the features"],
                "outputdir": [False, "Dir where the output files go", None],
                "overwrite": [False, "Whether to overwrite out files", True]}

    runExpects = [np.ndarray, ps.ImagePotMatrix]
    runReturns = [np.ndarray]

    def __init__(self, context, **kwargs):
        super(ResultingFeatureWriter_csv, self).__init__(**kwargs)

        if self.outputdir is None:
            if "outputroot" not in context.keys():
                raise StandardError("Must define output directory")

            if not os.path.isdir(context["outputroot"]):
                raise StandardError("%s is not a directory" % \
                        context["outputroot"])

            self.outputdir = os.path.join(context["outputroot"], "csv")

        if not os.path.exists(self.outputdir):
            os.makedirs(self.outputdir)

        # Are there any feature csv files? We check all possible features.
        for fName in ps.StatParamCalculator.statParamMethods():
            outputfile = os.path.join(self.outputdir, fName+".csv")
            if os.path.exists(outputfile):
                if self.overwrite:
                    os.remove(outputfile)
                else:
                    raise StandardError("%s might have important info" \
                            % outputfile)

    def __call__(self, context, *args):
        print(self.mess)
        ipm = args[1]
        ts = time.mktime(context["img"].datetime.timetuple()) * 1000

        for fName in ipm.potFeatures:
            outputfile = os.path.join(self.outputdir, fName+".csv")

            # Sorted so we can easily append after.
            potIds = ipm.potIds
            potIds.sort()

            if not os.path.exists(outputfile): # we initialize it.
                fd = open(outputfile, "w+")
                fd.write("timestamp")
                for potId in potIds:
                    fd.write(",%s"%potId)
                fd.write("\n")
                fd.close()

            fd = open(outputfile, 'a')
            fd.write("%f"%ts)
            for potId in potIds:
                pot = ipm.getPot(potId)
                fd.write(",%f"%pot.getCalcedFeatures()[fName])
            fd.write("\n")
            fd.close()

        return (args[0])

class ResultingImageWriter ( PipeComponent ):
    actName = "imagewrite"
    argNames = {"mess": [False, "Output Message", "Writing Image"],
                "outstream": [True, "Name of stream to use"]}

    runExpects = [np.ndarray]
    runReturns = [None]

    def __init__(self, context, **kwargs):
        super(ResultingImageWriter, self).__init__(**kwargs)

    def __call__(self, context, *args):
        print (self.mess)
        img = timestream.TimeStreamImage()
        img.datetime = context["img"].datetime
        img.pixels = args[0]
        img.data["processed"] = "yes"
        for key, value in context["outputwithimage"].iteritems():
            img.data[key] = value

        ts_out = context[self.outstream]
        ts_out.write_image(img)
        ts_out.write_metadata()

        return (args)
