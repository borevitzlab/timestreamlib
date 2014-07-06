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
from itertools import chain
from skimage.measure import regionprops
from skimage.morphology import label
import cv2
import inspect

class FeatureCalculator(object):

    def area(self, mask):
        # +1 because to make regionprops see the areas
        lmask = label(mask, background=0)+1
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
    def __init__(self, mGrowth=30, growBy=5, stopVal=0.1):
        """PotSegmenter_Kmeans: Segmenter by k-means

        Steps:
        1. Analyze increasing subsquares in the image.
        2. Calculate a k-means (k=2) of the current subsquare.
        3. Remove noise and bring close connected components together.
        4. We stop when less than 98% of the side pixels are 1.
        5. Recalculate enclosing square.

        Args:
          mGrowth (int): Max pixels to grow in any direction.
        """
        self.mGrowth = mGrowth
        self.growBy = growBy
        self.stopVal = stopVal

    def segment(self, iph, hints):
        """Segment a growing subimage centered at iph"""
        oRect = iph.rect #keep original rect in case we need to revert
        foundSeg = False # Ture when a segmentation is found
        for i in range(int(round(self.mGrowth/self.growBy))):
            try:
                iph.increaseRect(by=self.growBy)
            except ValueError:
                break

            mask = self.calcKmeans(iph.image)
            mask = np.uint8(mask)

            se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, se)

            # Stop when <2% of the rect perifery is 1
            perifery = np.concatenate((mask[0,:], \
                                        mask[mask.shape[0]-1,:], \
                                        mask[1:mask.shape[0]-2,0], \
                                        mask[1:mask.shape[0]-2,mask.shape[1]-1]))
            if float(sum(perifery))/len(perifery) < self.stopVal:
                foundSeg = True
                break

        # FIXME: What do we do when we don't find a segmentation?
        if not foundSeg:
            iph.rect = oRect
            mask = np.array( np.zeros( (abs(iph.rect[2]-iph.rect[0]),
                                        abs(iph.rect[3]-iph.rect[1])) ),
                             dtype = np.dtype("uint8") )

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
                (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0), \
                10, cv2.KMEANS_RANDOM_CENTERS)

        labels = np.reshape(labels, (oShape[0], oShape[1]), order="F")

        return (labels)

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
        else:
            raise TypeError("iphPrev must be an instance of ImagePotHandler")

        self._fc = FeatureCalculator()
        self._features = {}
        self._mask = None

    @property
    def id(self):
        return self._id

    @property # not settable nor delettable
    def image(self):
        return ( self.si[self._rect[1]:self._rect[3],
                            self._rect[0]:self._rect[2], :] )

    @property
    def mask(self): # not settable nor delettable
        if self._mask == None:
            hints = {} # FIXME: incorporate the hints from  iphPrev
            self._mask, hint = self.ps.segment(self, hints)
        return (self._mask)

    @property # not deletable
    def rect(self):
        return (self._rect)

    @rect.setter
    def rect(self, r):
        if sum(r[0:2] < 0) > 0 or sum(r[[3,2]] > self.si.shape[0:2]) > 0:
            raise ValueError("Rect overflows original image")

        self._mask = None #FIXME: Reset everything that depends on self._mask
        self._rect = r

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
            superBlack = np.zeros(self.si.shape, self.si.dtype)
            superBlack[self._rect[1]:self._rect[3], \
                       self._rect[0]:self._rect[2], :] = retVal
            retVal = superBlack

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

    def __init__(self, image, centers = None, rects = None):
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
        potIndex = 1
        self.its = []
        if (centers is None and rects is None):
            raise TypeError("Must specify either center or rects")

        elif (rects is not None):
            for i, tray in enumerate(rects):
                tmpTray = []
                for rect in tray:
                    tmpTray.append(ImagePotHandler(potIndex, \
                            rects[i][j], image))
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

                    pt1 = np.array(center) - growM
                    pt2 = np.array(center) + growM
                    rect = pt1.tolist() + pt2.tolist()
                    trayTmp.append(ImagePotHandler(potIndex, rect, image))
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

