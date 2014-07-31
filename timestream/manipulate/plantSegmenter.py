#!/usr/bin/python
#coding=utf-8
# Copyright (C) 2014
# Author(s): Joel Granados <joel.granados@gmail.com>
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

import numpy as np
from scipy import spatial
from scipy import signal
from itertools import chain
from skimage.measure import regionprops
from skimage.measure import label
import cv2
import inspect
import matplotlib.pyplot as plt
import skimage

class StatParamCalculator(object):

    def area(self, mask):
        area = regionprops(mask.astype("int8"), ["Area"])
        if len(area) == 0:
            return (0.0)
        return (area[0]["Area"])

    def perimeter(self, mask):
        perim = regionprops(mask.astype("int8"), ["Perimeter"])
        if len(perim) == 0:
            return (0.0)
        return (perim[0]["Perimeter"])

    def roundness(self, mask):
        # (4 (pi) * AREA) / PERIM^2
        retVal = regionprops(mask.astype("int8"), ["Area", "Perimeter"])
        if len(retVal) == 0:
            return (0.0)
        area = retVal[0]["Area"]
        perim = retVal[0]["Perimeter"]
        return ( (4*np.pi * area) / np.power(perim,2) )

    def compactness(self, mask):
        # In skimage its called solidity
        compactness = regionprops(mask.astype("int8"), ["Solidity"])
        if len(compactness) == 0:
            return (0.0) #FIXME: is this the best default?
        return (compactness[0]["Solidity"])

    def eccentricity(self, mask):
        ecce = regionprops(mask.astype("int8"), ["Eccentricity"])
        if len(ecce) == 0:
            return (0.0) #FIXME: is this the best default?
        return (ecce[0]["Eccentricity"])

    @classmethod
    def statParamMethods(cls):
        ignore = ["statParamMethods"]
        meths = inspect.getmembers(cls, predicate=inspect.ismethod)
        retVal = []
        for meth in meths:
            if ( not meth[0] in ignore ):
                retVal.append(meth[0])
        return (retVal)

class FeatureCalculator(object):
    RELATIVE_NORM = 1
    FULL_NORM = 2

    def __init__(self, img):
        """Calculating the image pixel features (transformations)

        getFeatures should be the only method called from outside

        Attributes:
          _imgRGB (np.ndarray): Input image
          (_)imgLAB (np.ndarray): Image in CIELAB color space
          feats (dictionary): Holds all the possible feature methods.

        """
        self._imgRGB = img.astype(np.uint8)
        self._imgLAB = None

        ignore = ["__init__", "imgLAB", "normRange", \
                    "_oneLAB", "_oneRGB", "getFeatures"]
        fMeths = inspect.getmembers(self, predicate=inspect.ismethod)
        self.feats = {}
        for feat in fMeths:
            if ( not feat[0] in ignore ):
                self.feats[feat[0]] = feat[1]

    @property
    def imgLAB(self):
        if self._imgLAB is None:
            # Transformation is from uint8. Ranges are [0,255] for all dims.
            # http://docs.opencv.org/modules/imgproc/doc/miscellaneous_transformations.html
            self._imgLAB = cv2.cvtColor(self._imgRGB, cv2.COLOR_BGR2LAB)
        return self._imgLAB

    def normRange(self, F, rangeVal=None):
        """ Normalize values to [0,1]

        Arguments:
          minVal (numeric): minimum value of F range
          maxVal (numeric): maximum value of F range
        """
        F = F.astype(np.float32)
        m = np.min(F)
        M = np.max(F)
        if rangeVal is not None:
            if rangeVal[0] > np.min(F) or rangeVal[1] < np.max(F):
                raise ValueError("Values out of normalization range")
            m = rangeVal[0]
            M = rangeVal[1]

        F -= m
        M -= m
        F /= (float(M) + 0.00000001)
        return (F)

    def _oneRGB(self, norm, dim):
        retVal = None
        if norm == FeatureCalculator.RELATIVE_NORM:
            retVal = self.normRange(self._imgRGB[:,:dim])
        elif norm == FeatureCalculator.FULL_NORM:
            retVal = self.normRange(self._imgRGB[:,:,dim], rangeVal=(0,255))
        else:
            raise ValueError("Must select relative or full normalization")
        retVal = np.reshape(retVal, (retVal.shape[0], retVal.shape[1], 1))
        return retVal
    def RGB_R(self, norm):
        return self._oneRGB(norm, 0)
    def RGB_G(self, norm):
        return self._oneRGB(norm, 1)
    def RGB_B(self, norm):
        return self._oneRGB(norm, 2)

    def _oneLAB(self, norm, dim):
        retVal = None
        if norm == FeatureCalculator.RELATIVE_NORM:
            retVal = self.normRange(self.imgLAB[:,:,dim])
        elif norm == FeatureCalculator.FULL_NORM:
            retVal = self.normRange(self.imgLAB[:,:,dim], rangeVal=(0,255))
        else:
            raise ValueError("Must select relative or full normalization")
        retVal = np.reshape(retVal, (retVal.shape[0], retVal.shape[1], 1))
        return retVal
    def LAB_L(self, norm):
        return self._oneLAB(norm, 0)
    def LAB_A(self, norm):
        return self._oneLAB(norm, 1)
    def LAB_B(self, norm):
        return self._oneLAB(norm, 2)

    def minervini(self, norm):
        # Calculate texture response filter from Minervini 2013
        # FIXME: radius, gaussian size and sigmas should be user defined.
        falloff = 1.0/50.0
        pillsize = 7
        gaussize = 17
        sdH = 4
        sdL = 1

        # pillbox feature (F1)
        pillse = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, \
                (pillsize,pillsize))
        pillse = pillse.astype(float)
        pillse = pillse/sum(sum(pillse))
        F1 = cv2.filter2D(self.imgLAB[:,:,1], -1, pillse)

        # Difference of Gaussian (DoG) featrue (F2)
        G1 = cv2.getGaussianKernel(gaussize, sdH)
        G2 = cv2.getGaussianKernel(gaussize, sdL)
        G1 = G1 * cv2.transpose(G1)
        G2 = G2 * cv2.transpose(G2)
        F2 = cv2.filter2D(self.imgLAB[:,:,0], -1, G1-G2)

        F = np.exp( -falloff * np.abs(F1+F2) )
        #FIXME: We are ignoring norm for now.
        F = self.normRange(F)
        F = np.reshape(F, (F.shape[0], F.shape[1], 1))

        return F

    def G4mB3mR1(self, norm):
        # We ignore the norm here becase we always FULL_NORM
        F = 4 * self.normRange(self._imgRGB[:,:,1], rangeVal=(0,255) ) \
            - 3 * self.normRange(self._imgRGB[:,:,2], rangeVal=(0,255)) \
            - 1 * self.normRange(self._imgRGB[:,:,0], rangeVal=(0,255))
        F = np.reshape(F, (F.shape[0], F.shape[0], 1))
        return(F)

    def getFeatures(self, feats, norm = RELATIVE_NORM):
        """ Calc features in feats (by name). Order matters"""
        retVal = None
        for f in feats:
            if f not in self.feats.keys():
                raise ValueError("%s is not a valid feature"%f)
            if retVal is None:
                retVal = self.feats[f](norm)
                continue

            retVal = np.concatenate((retVal, self.feats[f](norm)), axis=2)

        return retVal

class PotSegmenter(object):
    def __init__(self, *args, **kwargs):
        pass

    def segment(self, img, hints):
        """Method that returns segmented images.

        Args:
          img (np.ndarray): Image to segment
          hints (dict): dictionary with hints useful for segmentation
        """
        raise NotImplementedError()

    def calcComplexity(self, mask, size=5):
        """Apply Parrott et. al. 2008"""
        se = np.ones([size,size])
        convMask = signal.convolve2d(mask, se)

        freq = [ float(convMask[np.where(convMask==i)].shape[0]) \
                for i in range((size*size)+1) ]
        freq = np.array(freq)
        freq = freq/sum(freq)

        # be carefull with ln(0)
        freq = freq + 0.00001

        # spatial complexity
        sc = -sum(freq*np.log(freq)) / np.log(freq.shape[0])

        return (sc)

class PotSegmenter_Method1(PotSegmenter):
    def __init__(self, threshold=0.6, kSize=5, blobMinSize=50):
        self.threshold = threshold
        if kSize%2 == 0:
            raise ValueError("kSize must be inpair")
        self.kSize = kSize
        if blobMinSize < 10:
            raise ValueError("blobMinSize should be greater than 10")
        self.blobMinSize = blobMinSize

    def segment(self, img, hints):
        """Segment using a simple method

        Steps:
        1. Get feature G4mB3mR1
        2. Apply a median filter
        3. Apply a hard threshold.
        4. Remove all blobs greater than self.blobMinSize
        """
        fc = FeatureCalculator(img)
        fts = fc.getFeatures( ["G4mB3mR1"] )
        mask = cv2.medianBlur(fts, self.kSize)
        v, mask = cv2.threshold(mask, self.threshold, 1, cv2.THRESH_BINARY)

        # Remove all blobs that are greater than self.blobMinSize
        mask = label(mask, background=0)
        if -1 in mask: # skimage is going to change in 0.12
            mask += 1

        for i in range(1,np.max(mask)+1):
            indx = np.where(mask == i)
            if indx[0].shape[0] < self.blobMinSize:
                mask[indx] = 0

        indx = np.where(mask!=0)
        mask[indx] = 1

        return ([mask,hints])

class PotSegmenter_KmeansSquare(PotSegmenter):
    def __init__(self, maxIter=10, epsilon=1, attempts=20):
        """PotSegmenter_Kmeans: Segmenter by k-means

        Args:
          maxIter: maximum num of iterations per attempt
          epsilon: stopping difference
          attempts: times we try with different centers
        """
        self.maxIter = maxIter
        self.epsilon = epsilon
        self.attempts = attempts
        self.maxComplexity = 0.3

    def segment(self, img, hints):
        """Segment subimage centered at iph

        Steps:
        1. Calculate relative features.
        2. Calculate a k-means (k=2)
        3. Remove noise and bring close connected components together.
        4. Ignore if complexity is too high

        """

        fc = FeatureCalculator(img)
        fts = fc.getFeatures( ["LAB_A", "LAB_B", "minervini"])

        mask = self.calcKmeans(fts)

        se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, se)

        # When complexity is large, image is too noisy.
        if self.calcComplexity(mask) > self.maxComplexity:
            mask[:] = 0

        return ([mask, hints])

    def calcKmeans(self, img):
        """Calculate mask based on k-means

        Don't do any checks.

        Args:
          img: 3D structure where x,y are image axis and z represents
               different features.
        """
        oShape = img.shape
        img = np.float32(img)
        img = np.reshape(img, (oShape[0]*oShape[1], oShape[2]), order="F")

        # k-means. max 10 iters. Stop if diff < 1. Init centers at random
        compactness,labels,centers = cv2.kmeans(img, 2, \
                ( cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, \
                  self.maxIter, self.epsilon ), \
                self.attempts, cv2.KMEANS_RANDOM_CENTERS)

        labels = np.reshape(labels, (oShape[0], oShape[1]), order="F")

        labels = labels.astype(np.float64)
        #FIXME: do this check if we don't have mean centers.
        FG = sum(sum(labels==1))
        BG = sum(sum(labels==0))
        if BG < FG:
            labels = -(labels-1)


        return (labels.astype(np.float64))

#FIXME: Find a better place to put this.
segmentingMethods = {"k-means-square": PotSegmenter_KmeansSquare,
        "method1": PotSegmenter_Method1}

class ImagePotHandler(object):
    def __init__(self, id, rect, superImage, ps=None, iphPrev=None):
        """ImagePotHandler: a class for individual pot images.

        Args:
          id (object): Should be unique between pots. Is given by the
                       potMatrix. Is not changeable.
          rect (list): [x,y,x`,y`]: (x,y) and (x`,y`)* are reciprocal corners
          superImage (ndarray): Image in which the image pot is located
          ps (PotSegmenter): It can be any child class from PotSegmenter. Its
                             instance that has a segment method.
          iphPrev (ImagePotHandler): The previous ImagePotHandler for this pot
                                     position.

        Attributes:
          image: Return the cropped image (with rect) of superImage
          maskedImage: Return the segmented cropped image.
          features: Return the calculated features

        * y is vertical | x is horizontal.
        """
        self._id = id

        # FIXME: This check for ndarray should be fore TimestreamImage
        if isinstance(superImage, np.ndarray):
            self.si = superImage
        else:
            raise TypeError("superImate must be an ndarray")

        rect = np.array(rect)
        if sum(rect < 0) > 0 \
                or sum(rect[[1,3]] > self.si.shape[0]) > 0 \
                or sum(rect[[0,2]] > self.si.shape[1]) > 0:
            raise TypeError("rect must fit in superImage")
        else:
            self._rect = rect

        if ps == None:
            self._ps = None
        elif isinstance(ps, PotSegmenter):
            self._ps = ps
        else:
            raise TypeError("ps must be an instance of PotSegmenter")

        if iphPrev == None:
            self.iphPrev = None
        elif isinstance(iphPrev, ImagePotHandler):
            self.iphPrev = iphPrev
            # avoid a run on memory
            self.iphPrev.iphPrev = None

            # Don't let previous pot run segmentation code
            self.iphPrev.ps = None
        else:
            raise TypeError("iphPrev must be an instance of ImagePotHandler")

        self._fc = StatParamCalculator()
        self._features = {}
        self._mask = np.zeros( [np.abs(self._rect[2]-self._rect[0]), \
                                np.abs(self._rect[3]-self._rect[1])], \
                                dtype=np.dtype("float64")) - 1

    @property
    def ps(self):
        return self._ps

    @ps.setter
    def ps(self, ps):
        self._ps = ps

    @ps.deleter
    def ps(self):
        self._ps = None

    @property
    def id(self):
        return self._id

    @property # not settable nor delettable
    def image(self):
        return ( self.si[self._rect[1]:self._rect[3],
                            self._rect[0]:self._rect[2], :] )

    def getSegmented(self):
        """Does not change internals of instance

            This method is used to parallelize the pot segmentation
            calculation so we should avoid changing the inner struct
            of the instance.
        """
        # FIXME: here we loose track of the hints
        msk, hint = self._ps.segment(self.image, {})

        # if bad segmentation
        if 1 not in msk and self.iphPrev is not None:
            # We try previous mask. This is tricky because we need to fit the
            # previous mask size into msk
            pm = self.iphPrev.mask

            vDiff = msk.shape[0] - pm.shape[0]
            if vDiff < 0: # reduce pm vertically
                side = True
                for i in range(abs(vDiff)):
                    if side:
                        pm = pm[1:,:]
                    else:
                        pm = pm[:-1,:]
                    side = not side

            if vDiff > 0: # grow pm vertically
                padS = np.array([1,0])
                for i in range(abs(vDiff)):
                    pm = np.lib.pad(pm, (padS.tolist(), (0,0)), 'constant', \
                            constant_values = 0)
                    padS = -(padS-1) # other side

            hDiff = msk.shape[1] - pm.shape[1]
            if hDiff < 0: # reduce pm horizontally
                side = True
                for i in range(abs(hDiff)):
                    if side:
                        pm = pm[:,1:]
                    else:
                        pm = pm[:,:-1]
                    side = not side

            if hDiff > 0: # grow pm horizontally
                padS = np.array([1,0])
                for i in range(abs(hDiff)):
                    pm = np.lib.pad(pm, ((0,0), padS.tolist()), 'constant', \
                            constant_values = 0)
                    padS = -(padS-1) # other side

            msk = pm

        return msk

    @property
    def mask(self):
        if -1 not in self._mask:
            return self._mask

        if self._ps == None:
            return np.zeros(self._mask.shape, np.dtype("float64"))

        self._mask = self.getSegmented()
        return (self._mask)

    @mask.setter
    def mask(self, m):
        if ( not isinstance(m, np.ndarray) \
                or m.dtype != np.dtype("float64") \
                or m.shape != self._mask.shape ):
            raise ValueError("Invalid mask assigment")
        self._mask = m

    @property # not deletable
    def rect(self):
        return (self._rect)

    @rect.setter
    def rect(self, r):
        if sum(r[0:2] < 0) > 0 or sum(r[[3,2]] > self.si.shape[0:2]) > 0:
            raise ValueError("Rect overflows original image")

        self._rect = r
        self._mask = np.zeros( [np.abs(self._rect[2]-self._rect[0]), \
                                np.abs(self._rect[3]-self._rect[1])], \
                                dtype=np.dtype("float64")) - 1
        #FIXME: Reset everything that depends on self._mask

    def maskedImage(self, inSuper=False):
        """Returns segmented pixels on a black background

        inSuper: When True we return the segmentation in the totality of
                 self.si. When False we return it in the rect.
        """
        # We use the property to trigger creation if needed.
        msk = self.mask
        img = self.image

        height, width, dims = img.shape
        msk = np.reshape(msk, (height*width, 1), order="F")
        img = np.reshape(img, (height*width, dims), order="F")

        retVal = np.zeros((height, width, dims), dtype=img.dtype)
        retVal = np.reshape(retVal, (height*width, dims), order="F")

        Ind = np.where(msk)[0]
        retVal[Ind,:] = img[Ind,:]
        retVal = np.reshape(retVal, (height, width, dims), order="F")

        if inSuper:
            superI = self.si.copy()
            superI[self._rect[1]:self._rect[3], \
                       self._rect[0]:self._rect[2], :] = retVal
            retVal = superI

        return (retVal)

    def increaseRect(self, by=5):
        """Only increase rectangle if it fits in self.image"""
        if sum(self._rect[0:2] < by) > 0 \
                or sum(self._rect[[3,2]]+by > self.si.shape[0:2]) > 0:
            raise ValueError("Increasing rect overflows original image")

        # Using property to trigger assignment cleanup
        self.rect = self._rect + np.array([-by, -by, by, by])

    def reduceRect(self, by=5):
        if ( abs(self._rect[0]-self._rect[2]) < 2*by \
                or abs(self._rect[1]-self._rect[3]) < 2*by ):
            raise ValueError("Rect is too small to decrease")

        # Using property to trigger assignment cleanup
        self.rect = self.rect + np.array([by, by, -by, -by])

    def calcFeatures(self, feats):
        # Calc all the possible features when feats not specfied
        if not isinstance(feats, list):
            raise TypeError("feats should be a list")

        if "all" in feats:
            feats = StatParamCalculator.statParamMethods()

        for featName in feats:
            # calc not-indexed feats
            if not featName in self._features.keys():
                featFunc = getattr(self._fc, featName)
                self._features[featName] = featFunc(self._mask)

    def getCalcedFeatures(self):
        return self._features

class ImagePotMatrix(object):
    class ImageTray(object):
        def __init__(self, pots, name):
            self.pots = pots
            self.name = name
            self.numPots = len(self.pots)

        @property
        def asTuple(self):
            retVal = []
            for pot in self.pots:
                retVal.append(tuple(pot.rect))
            return(retVal)

    def __init__(self, image, centers = None, rects = None, ipmPrev = None):
        """ImagePotMatrix: To house all the ImagePotHandlers

        Args:
          image (ndarray): Image in which everything is located
          centers (list): list of tray lists. Each tray list is a list of two
                          element sets. The centers of the pots
          rects (list): list of tray lists. Each tray list is a list of two
                        element sets. The reciprocal corners of the pot
                        rectangle

        Attributes:
          its: Dictionary of image tray instances.
        """
        if ipmPrev == None:
            self.ipmPrev = None
        elif isinstance(ipmPrev, ImagePotMatrix):
            self.ipmPrev = ipmPrev
            # avoid a run on memory
            self.ipmPrev.ipmPrev = None
        else:
            raise TypeError("ipmPrev must be an instance of ImagePotHandler")

        potIndex = 1
        self.its = []
        if (centers is None and rects is None):
            raise TypeError("Must specify either center or rects")

        elif (rects is not None):
            for i, tray in enumerate(rects):
                tmpTray = []
                for rect in tray:

                    # Get previous pot if present
                    iphPrev = None
                    if self.ipmPrev is not None:
                        iphPrev = self.ipmPrev.getPot(potIndex)

                    tmpTray.append(ImagePotHandler(potIndex, \
                            rects[i][j], image, iphPrev=iphPrev))
                    potIndex += 1

                self.its.append(ImagePotMatrix.ImageTray(trayTmp, i))

        elif (centers is not None):
            # Calc rects for every center. Growth will be half the min
            # distance between centers
            flattened = list(chain.from_iterable(centers))
            growM = round(min(spatial.distance.pdist(flattened))/2)
            for i, tray in enumerate(centers):
                trayTmp = []
                for center in tray:

                    # Calc rect
                    pt1 = np.array(center) - growM
                    pt2 = np.array(center) + growM
                    rect = pt1.tolist() + pt2.tolist()

                    # Get previous pot if present
                    iphPrev = None
                    if self.ipmPrev is not None:
                        iphPrev = self.ipmPrev.getPot(potIndex)

                    trayTmp.append(ImagePotHandler(potIndex, rect, image, \
                            iphPrev=iphPrev))
                    potIndex += 1

                self.its.append(ImagePotMatrix.ImageTray(trayTmp, i))

        self.image = image

    def getPot(self, potId):
        for tray in self.its:
            for pot in tray.pots:
                if (pot.id == potId):
                    return (pot)

        raise IndexError("No pot number %d found"%potNum)

    @property
    def potIds(self):
        """Returns a list of pot ids"""
        retVal = []
        for tray in self.its:
            for pot in tray.pots:
                retVal.append(pot.id)
        return (retVal)

    def iter_through_pots(self):
        pots = []
        for tray in self.its:
            pots = pots + tray.pots

        for i in range(len(pots)):
            yield(i, pots[i])

    @property
    def asTuple(self):
        mat = []
        for tray in self.its:
            mat.append(tray.asTuple)
        return(mat)

    @property
    def potFeatures(self):
        """ Return a feature name list with all possible features in pots """
        featureNames = []
        for tray in self.its:
            for pot in tray.pots:
                for featName in pot.getCalcedFeatures():
                    if featName not in featureNames:
                        featureNames.append(featName)

        return (featureNames)

    def show(self):
        """ Show segmented image with the plot squares on top. """
        sImage = self.image
        for tray in self.its:
            for pot in tray.pots:
                sImage = sImage & pot.maskedImage(inSuper=True)

        plt.figure()
        plt.imshow(sImage.astype(np.uint8))
        plt.hold(True)

        for tray in self.its:
            for pot in tray.pots:
                r = pot.rect
                plt.plot([r[0], r[2], r[2], r[0], r[0]],
                         [r[1], r[1], r[3], r[3], r[1]],
                         linestyle="-", color="r")
        plt.title('Pot Rectangles')
        plt.show()
