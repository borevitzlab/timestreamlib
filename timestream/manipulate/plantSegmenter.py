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
import cv2

class ImagePot(object):
    def __init__(self, rect, superImage):
        """ImagePot: a class for individual pot images.

        Args:
          rect (list): [x,y,x`,y`]: (x,y) and (x`,y`)* are reciprocal corners
          superImage (ndarray): Image in which the image pot is located

        Attributes:
          image: Return the cropped image (with rect) of superImage
          maskedImage: Return the segmented cropped image.
          mask: The segmented image.
          rect: Return [x,y,x`,y`]* rectangle.

        * y is vertical | x is horizontal.
        """

        self._rect = np.array(rect)
        if sum(self._rect < 0) > 0 \
                or sum(self._rect[[1,3]] > superImage.shape[0]) > 0 \
                or sum(self._rect[[0,2]] > superImage.shape[1]) > 0:
            raise TypeError("rect must fit in superImage")

        self.si = superImage
        self._mask = None

    # Image is not settable nor deletable
    @property
    def image(self):
        return ( self.si[self._rect[1]:self._rect[3],
                            self._rect[0]:self._rect[2], :] )

    @property
    def mask(self):
        return (self._mask)

    @mask.setter
    def mask(self, m):
        if not isinstance(m, np.ndarray) or m.dtype is not np.dtype("uint8"):
            raise TypeError("Mask must be numpy.ndarray of uint8")

        # New dims have to fit exactly
        if abs(self._rect[2]-self._rect[0]) != m.shape[1] \
                or abs(self._rect[1]-self._rect[3]) != m.shape[0]:
            raise TypeError("Mask dim must agree with rect")

        self._mask = m

    @mask.deleter
    def mask(self):
        self._mask = None

    # rect is not deletable
    @property
    def rect(self):
        return (self._rect)

    @rect.setter
    def rect(self, r):
        if sum(r[0:2] < 0) > 0 or sum(r[[3,2]] > self.si.shape[0:2]) > 0:
            raise ValueError("Rect overflows original image")

        self._mask = None
        self._rect = r

    # FIXME: This should be a property
    def maskedImage(self, inSuper=False):
        """Returns segmented pixels on a black background

        inSuper: When True we return the segmentation in the totality of
                 self.si. When False we return it in the rect.
        """
        if self._mask is None:
            raise ValueError("Set mask in order to calculate masked image")

        img = self.image
        height = img.shape[0]
        width = img.shape[1]
        dims = img.shape[2]

        img = np.reshape(img, (height*width, dims), order="F")

        retVal = np.zeros((height, width, dims), dtype=img.dtype)
        retVal = np.reshape(retVal, (height*width, dims), order="F")

        msk = self._mask
        msk = np.reshape(msk, (height*width, 1), order="F")

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

        self._rect[0:2] = self._rect[0:2] - by
        self._rect[2:4] = self._rect[2:4] + by

    def reduceRect(self, by=5):
        if ( abs(self._rect[0]-self._rect[2]) < 2*by \
                or abs(self._rect[1]-self._rect[3]) < 2*by ):
            raise ValueError("Rect is too small to decrease")

        self._rect[0:2] = self._rect[0:2] + by
        self._rect[2:4] = self._rect[2:4] - by

class ImagePotMatrix(object):
    class ImageTray(object):
        def __init__(self, pots, name):
            self.pots = pots
            self.name = name

        @property
        def asTuple(self):
            retVal = []
            for pot in self.pots:
                retVal.append(tuple(pot.rect))
            return(retVal)

    def __init__(self, image, centers = None, rects = None):
        """ImagePotMatrix: To house all the ImagePots

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
        self.its = []
        if (centers is None and rects is None):
            raise TypeError("Must specify either center or rects")

        elif (rects is not None):
            for i in range(len(rects)):
                tmpTray = []
                for j in range(len(rects[i])):
                    tmpTray.append(ImagePot(rects[i][j], image))

                self.its.append(ImagePotMatrix.ImageTray(trayTmp, i))

        elif (centers is not None):
            # Calc rects for every center. Growth will be half the min
            # distance between centers
            flattened = list(chain.from_iterable(centers))
            growM = round(min(spatial.distance.pdist(flattened))/3)
            for i in range(len(centers)):
                trayTmp = []
                for j in range(len(centers[i])):

                    pt1 = np.array(centers[i][j]) - growM
                    pt2 = np.array(centers[i][j]) + growM
                    rect = pt1.tolist() + pt2.tolist()
                    trayTmp.append(ImagePot(rect, image))

                self.its.append(ImagePotMatrix.ImageTray(trayTmp, i))

        self.image = image

    def getPot(potNum):
        pots = []
        for tray in self.its:
            pots = pots + tray.pots

        if potNum > len(pots)-1:
            raise IndexError("Pot number %d out of range"%potNum)

        return (pots[potNum])

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


class PotSegmenter(object):
    def __init__(self, *args, **kwargs):
        pass

    def getInitialSegmentation(ip):
        """Method run when we dont have any hints

        Args:
          ip (ImagePot): Image pot to segment
        """
        if ( not isinstance(ip, ImagePot) ):
            raise TypeError("ip needs to be an ImagePot")

        img = ip.image()
        if img.ndim is not 3 or img.shape[2] is not 3:
            raise ValueError("img should have only 3 dims:MxNx3")

        oShape = img.shape
        img = np.float32(img)
        img = np.reshape(img, (oShape[0]*oShape[1], 3), order="F")

        # k-means. max 10 iters. Stop if diff < 1. Init centers at random
        compactness,labels,centers = cv2.kmeans(img, 2, \
                (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0), \
                10, cv2.KMEANS_RANDOM_CENTERS)

        labels = np.reshape(labels, (oShape[0], oShape[1]), order="F")

        # return mask
        return (mask)

    def segment(self, ip, hints):
        """Method that returns segmented images.

        Args:
          ip (ImagePot): Image pot to segment
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

    def segment(self, ip, hints):
        """Segment a growing subimage centered at ip

        Args:
          ip (ImagePot): Image pot
          hints (dict): dictionalry hints
        """
        oRect = ip.rect #keep original rect in case we need to revert
        foundSeg = False # Ture when a segmentation is found
        for i in range(int(round(self.mGrowth/self.growBy))):
            try:
                ip.increaseRect(by=self.growBy)
            except ValueError:
                break

            mask = self.calcKmeans(ip.image)
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
            ip.rect = oRect
            mask = np.array( np.zeros( (abs(ip.rect[2]-ip.rect[0]),
                                        abs(ip.rect[3]-ip.rect[1])) ),
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

class ChamberHandler(object):
    methods = {"k-means-square": PotSegmenter_KmeansSquare}

    def __init__(self, meth="k-means-square", methargs={}):
        self._segmenter = ChamberHandler.methods[meth](**methargs)

        # Previous analyzed images. [0] is most recent.
        self.tail = []

    def segment(self, image, centers = None, rects = None):
        ipm = ImagePotMatrix(image, centers=centers, rects=rects)
        retImg = np.zeros(image.shape, dtype=image.dtype)
        hint = {}
        for key, ip in ipm.iter_through_pots():
            print ("Segmenting pot %s"% key)
            ip.mask, hint =  self._segmenter.segment(ip, hint)
            retImg = retImg | ip.maskedImage(inSuper=True)

        return(retImg, ipm)

