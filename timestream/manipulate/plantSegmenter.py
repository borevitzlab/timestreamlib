#!/usr/bin/python
# coding=utf-8
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
from scipy import signal
from skimage.measure import regionprops
from skimage.measure import label
import cv2
import inspect


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
        return ((4 * np.pi * area) / np.power(perim, 2))

    def compactness(self, mask):
        # In skimage its called solidity
        compactness = regionprops(mask.astype("int8"), ["Solidity"])
        if len(compactness) == 0:
            return (0.0)  # FIXME: is this the best default?
        return (compactness[0]["Solidity"])

    def eccentricity(self, mask):
        ecce = regionprops(mask.astype("int8"), ["Eccentricity"])
        if len(ecce) == 0:
            return (0.0)  # FIXME: is this the best default?
        return (ecce[0]["Eccentricity"])

    @classmethod
    def statParamMethods(cls):
        ignore = ["statParamMethods"]
        meths = inspect.getmembers(cls, predicate=inspect.ismethod)
        retVal = []
        for meth in meths:
            if (not meth[0] in ignore):
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

        ignore = ["__init__", "imgLAB", "normRange",
                  "_oneLAB", "_oneRGB", "getFeatures"]
        fMeths = inspect.getmembers(self, predicate=inspect.ismethod)
        self.feats = {}
        for feat in fMeths:
            if (not feat[0] in ignore):
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
            retVal = self.normRange(self._imgRGB[:, :dim])
        elif norm == FeatureCalculator.FULL_NORM:
            retVal = self.normRange(self._imgRGB[:, :, dim], rangeVal=(0, 255))
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
            retVal = self.normRange(self.imgLAB[:, :, dim])
        elif norm == FeatureCalculator.FULL_NORM:
            retVal = self.normRange(self.imgLAB[:, :, dim], rangeVal=(0, 255))
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
        falloff = 1.0 / 50.0
        pillsize = 7
        gaussize = 17
        sdH = 4
        sdL = 1

        # pillbox feature (F1)
        pillse = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                           (pillsize, pillsize))
        pillse = pillse.astype(float)
        pillse = pillse / sum(sum(pillse))
        F1 = cv2.filter2D(self.imgLAB[:, :, 1], -1, pillse)

        # Difference of Gaussian (DoG) featrue (F2)
        G1 = cv2.getGaussianKernel(gaussize, sdH)
        G2 = cv2.getGaussianKernel(gaussize, sdL)
        G1 = G1 * cv2.transpose(G1)
        G2 = G2 * cv2.transpose(G2)
        F2 = cv2.filter2D(self.imgLAB[:, :, 0], -1, G1 - G2)

        F = np.exp(-falloff * np.abs(F1 + F2))
        # FIXME: We are ignoring norm for now.
        F = self.normRange(F)
        F = np.reshape(F, (F.shape[0], F.shape[1], 1))

        return F

    def G4mB3mR1(self, norm):
        # We ignore the norm here becase we always FULL_NORM
        F = 4 * self.normRange(self._imgRGB[:, :, 1], rangeVal=(0, 255)) \
            - 3 * self.normRange(self._imgRGB[:, :, 2], rangeVal=(0, 255)) \
            - 1 * self.normRange(self._imgRGB[:, :, 0], rangeVal=(0, 255))
        F = np.reshape(F, (F.shape[0], F.shape[0], 1))
        return(F)

    def getFeatures(self, feats, norm=RELATIVE_NORM):
        """ Calc features in feats (by name). Order matters"""
        retVal = None
        for f in feats:
            if f not in self.feats.keys():
                raise ValueError("%s is not a valid feature" % f)
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
        se = np.ones([size, size])
        convMask = signal.convolve2d(mask, se)

        freq = [float(convMask[np.where(convMask == i)].shape[0])
                for i in range((size * size) + 1)]
        freq = np.array(freq)
        freq = freq / sum(freq)

        # be carefull with ln(0)
        freq = freq + 0.00001

        # spatial complexity
        sc = -sum(freq * np.log(freq)) / np.log(freq.shape[0])

        return (sc)


class PotSegmenter_Method1(PotSegmenter):

    def __init__(self, threshold=0.6, kSize=5, blobMinSize=50):
        self.threshold = threshold
        if kSize % 2 == 0:
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
        fts = fc.getFeatures(["G4mB3mR1"])
        mask = cv2.medianBlur(fts, self.kSize)
        v, mask = cv2.threshold(mask, self.threshold, 1, cv2.THRESH_BINARY)

        # Remove all blobs that are greater than self.blobMinSize
        mask = label(mask, background=0)
        if -1 in mask:  # skimage is going to change in 0.12
            mask += 1

        for i in range(1, np.max(mask) + 1):
            indx = np.where(mask == i)
            if indx[0].shape[0] < self.blobMinSize:
                mask[indx] = 0

        indx = np.where(mask != 0)
        mask[indx] = 1

        return ([mask, hints])


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
        fts = fc.getFeatures(["LAB_A", "LAB_B", "minervini"])

        mask = self.calcKmeans(fts)

        se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
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
        img = np.reshape(img, (oShape[0] * oShape[1], oShape[2]), order="F")

        # k-means. max 10 iters. Stop if diff < 1. Init centers at random
        compactness, labels, centers = cv2.kmeans(
            img,
            2,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, self.maxIter,
                self.epsilon),
            self.attempts,
            cv2.KMEANS_RANDOM_CENTERS)

        labels = np.reshape(labels, (oShape[0], oShape[1]), order="F")

        labels = labels.astype(np.float64)
        # FIXME: do this check if we don't have mean centers.
        FG = sum(sum(labels == 1))
        BG = sum(sum(labels == 0))
        if BG < FG:
            labels = -(labels - 1)

        return (labels.astype(np.float64))

# FIXME: Find a better place to put this.
segmentingMethods = {"k-means-square": PotSegmenter_KmeansSquare,
                     "method1": PotSegmenter_Method1}
