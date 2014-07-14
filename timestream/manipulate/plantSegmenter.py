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
from skimage.morphology import label
import cv2
import inspect
import matplotlib.pyplot as plt

class FeatureCalculator(object):

    def area(self, mask):
        # +1 because to make regionprops see the areas
        lmask = label(mask.astype(np.int), background=0)+1
        areas = regionprops(lmask, ["Area"])
        areaAccum = 0
        for area in areas:
            areaAccum = areaAccum + area["Area"]

        return (areaAccum)

    @classmethod
    def featureMethods(cls):
        ignore = ["featureMethods"]
        meths = inspect.getmembers(cls, predicate=inspect.ismethod)
        retVal = []
        for meth in meths:
            if ( not meth[0] in ignore ):
                retVal.append(meth[0])
        return (retVal)

class PotSegmenter(object):
    def __init__(self, *args, **kwargs):
        pass

    def segment(self, iph, hints):
        """Method that returns segmented images.

        Args:
          iph (ImagePotHandler): Image pot to segment
          hints (dict): dictionary with hints useful for segmentation
        """
        raise NotImplementedError()

class PotSegmenter_KmeansSquare(PotSegmenter):
    def __init__(self, maxIter=10, epsilon=1, attempts=20):
        """PotSegmenter_Kmeans: Segmenter by k-means

        Args:
          maxIter: maximum num of iterations per attempt
          epsilon: stopping difference
          attempts: times we try with different centers

        Steps:
        1. Calculate relative features.
        2. Calculate a k-means (k=2)
        3. Remove noise and bring close connected components together.
        4. Ignore if complexity is too high
        """
        self.maxIter = maxIter
        self.epsilon = epsilon
        self.attempts = attempts
        self.maxComplexity = 0.3

    def segment(self, iph, hints):
        """Segment subimage centered at iph"""
        fts = self.getFeatures(iph.image)

        mask = self.calcKmeans(fts)

        #FIXME: do this check if we don't have mean centers.
        FG = sum(sum(mask==1))
        BG = sum(sum(mask==0))
        if BG < FG:
            mask = -(mask-1)

        se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, se)

        # When complexity is large, image is too noisy.
        if self.calcComplexity(mask) > self.maxComplexity:
            if "iphPrev" in hints.keys() and hints["iphPrev"] is not None:
                # Same as previous iph, if we have it.
                mask = hints["iphPrev"].mask
            else:
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
        labels = labels.astype(np.uint8)

        return (labels)

    def getFeatures(sefl, img):
        def normRange(F):
            """ Streach values to [0,1], change to np.float32."""
            F = F.astype(np.float32)
            m = np.min(F)
            F -= m
            M = np.max(F)
            F /= float(M)
            return (F)

        retVal = None
        imglab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

        # Add a and b from cieL*a*b
        retVal = imglab[:,:,1:3].astype(np.float32)
        retVal[:,:,0] = normRange(retVal[:,:,0])
        retVal[:,:,1] = normRange(retVal[:,:,1])

        # Calculate texture response filter from Minervini 2013
        # FIXME: The pill radius, gaussian size and sigmas should be user
        #        defined.
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
        F1 = cv2.filter2D(imglab[:,:,1], -1, pillse)

        # Difference of Gaussian (DoG) featrue (F2)
        G1 = cv2.getGaussianKernel(gaussize, sdH)
        G2 = cv2.getGaussianKernel(gaussize, sdL)
        G1 = G1 * cv2.transpose(G1)
        G2 = G2 * cv2.transpose(G2)
        F2 = cv2.filter2D(imglab[:,:,0], -1, G1-G2)

        F = np.exp( -falloff * np.abs(F1+F2) )
        F = normRange(F)
        F = np.reshape(F, (F.shape[0], F.shape[1], 1))

        # FIXME: try cv2.merge
        retVal = np.concatenate((retVal, F), axis=2)

        return (retVal)

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

#FIXME: Find a better place to put this.
segmentingMethods = {"k-means-square": PotSegmenter_KmeansSquare}

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

            # We don't actually want the previous pot to run the segmentation
            # code again.
            self.iphPrev.ps = None
        else:
            raise TypeError("iphPrev must be an instance of ImagePotHandler")

        self._fc = FeatureCalculator()
        self._features = {}
        self._mask = np.zeros( [np.abs(self._rect[2]-self._rect[0]), \
                                np.abs(self._rect[3]-self._rect[1])] ) - 1

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

    @property
    def mask(self): # not settable nor delettable
        if -1 in self._mask: #no mask yet
            if self._ps is not None:
                hints = {"iphPrev":self.iphPrev}
                # FIXME: here we loose track of the hints
                self._mask, hint = self._ps.segment(self, hints)
                return self._mask
            else:
                return self._mask + 1

        return self._mask #existing mask

    @property # not deletable
    def rect(self):
        return (self._rect)

    @rect.setter
    def rect(self, r):
        if sum(r[0:2] < 0) > 0 or sum(r[[3,2]] > self.si.shape[0:2]) > 0:
            raise ValueError("Rect overflows original image")

        self._rect = r
        self._mask = np.zeros( [np.abs(self._rect[2]-self._rect[0]), \
                                np.abs(self._rect[3]-self._rect[1])] ) - 1
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
            feats = FeatureCalculator.featureMethods()

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
            growM = round(min(spatial.distance.pdist(flattened))/3)
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
