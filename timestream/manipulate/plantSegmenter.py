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
.. module:: timestream.manipulate.plantSegmenter
    :platform: Unix, Windows
    :synopsis: Submodule which parses timestream formats.

.. moduleauthor:: Joel Granados
"""

import numpy as np
from scipy import signal
from scipy import ndimage
from skimage.measure import regionprops
from skimage.measure import label
import cv2
import inspect


class StatParamValue(object):
    """Besides the actual value, instance will have range of validity"""

    def __init__(self, name, value, rMin=0.0, rMax=1.0):
        self._name = name
        self._value = value
        self._min = rMin
        self._max = rMax

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def range(self):
        return [self._min, self._max]

    def drawParamInImg(self, img, x=0, y=0, nMax=3, tMax=11,
                       font=cv2.FONT_HERSHEY_SIMPLEX, color=(255,255,255),
                       tScale=1):
        """Draw param name and value on image

        Arguments:
          img(np.array): The image to draw to.
          x,y(int): Coordinates to draw to.
          nMax(int): Maximum size of name
          tMax(int): Maximum of total text
          font(cv2FONT): The font to be used
          color(tuple): Font color
          tScale(float): Scaling of the font
        """
        txt = self._name[0:nMax]+":"+str(self._value)
        txt = txt[0:tMax]
        cv2.putText(img, txt, (x,y), font, tScale, color, 3)


class StatParamMinCircle(StatParamValue):
    """The value is the radius and we add center"""

    def __init__(self, name, radius, center=(0,0), rMin=0.0, rMax=float("Inf")):
        super(StatParamMinCircle, self).__init__(name, radius,
                                                 rMin=rMin, rMax=rMax)
        self._center = center
        self._radius = self._value

    @property
    def radius(self):
        return self._value

    @property
    def center(self):
        return self._center

    def drawParamInImg(self, img, color=(255,255,255), *args, **kwargs):
        if self._radius > 0 and self._center[0] >= 0 and self._center[1] >= 0:
            # FIXME: Why is the center returned by cv2.minEnclosingCircle need
            #        to be swapped for cv2.circle??????
            c = (self._center[1], self._center[0])
            cv2.circle(img, c, self._radius, color)


class StatParamPerimeter(StatParamValue):
    """The value is the sum of the perimeter. Also perimeter coords"""

    def __init__(self, name, plen, xycoords, rMin=0.0, rMax=float("Inf")):
        super(StatParamPerimeter, self).__init__(name, plen,
                                                 rMin=rMin, rMax=rMax)
        self._length = self._value
        self._coords = xycoords

    @property
    def length(self):
        return self._length

    @property
    def coords(self):
        return self._coords

    def drawParamInImg(self, img, color=(255,255,255), *args, **kwargs):
        if self._length > 0:
            img[self._coords[0], self._coords[1], :] = 255


class StatParamLeafCount(StatParamValue):
    """The number of leaves on a rosette. Also leaf coordinates"""

    def __init__(self, name, centerCoords, radius=5, rMin=0.0, rMax=float("Inf")):
        super(StatParamLeafCount, self).__init__(name, len(centerCoords),
                                                 rMin=rMin, rMax=rMax)
        self._centers = centerCoords
        self._radius = radius

    @property
    def centers(self):
        return self._centers

    def drawParamInImg(self, img, color=(255,255,255), *args, **kwargs):
        if self._centers > 0:
            for c in self._centers:
                cv2.circle(img, (int(c[0]), int(c[1])), self._radius, color)


class StatParamCalculator(object):

    # FIXME: this should be the same as in pipecompoment.ResultingFeatureWriter.
    #       Find a place to put this string so its in the general scope.
    errStr = "NaN"

    def area(self, mask, img=None):
        retVal = 0.0
        area = regionprops(mask.astype("int8"), ["Area"])
        if len(area) > 0:
            retVal = area[0]["Area"]

        return StatParamValue("area", retVal, rMax=float("Inf"))

    def perimeter(self, mask, img=None):
        retVal = 0.0
        perim = regionprops(mask.astype("int8"), ["Perimeter"])

        bmsk = ndimage.binary_erosion(mask, np.ones((3,3)), border_value=0)
        bmsk = mask - bmsk
        xycoords = np.where(bmsk == 1)
        if len(perim) > 0:
            retVal = perim[0]["Perimeter"]

        return StatParamPerimeter("perimeter", retVal, xycoords)

    def roundness(self, mask, img=None):
        # (4 (pi) * AREA) / PERIM^2
        retVal = 0.0
        roundness = regionprops(mask.astype("int8"), ["Area", "Perimeter"])
        if len(roundness) > 0:
            area = roundness[0]["Area"]
            perim = roundness[0]["Perimeter"]
            retVal = (4 * np.pi * area) / np.power(perim, 2)

        return StatParamValue("roundness", retVal, rMax=float("Inf"))

    def compactness(self, mask, img=None):
        # In skimage its called solidity
        retVal = StatParamCalculator.errStr
        compactness = regionprops(mask.astype("int8"), ["Solidity"])
        if len(compactness) > 0:
            retVal = compactness[0]["Solidity"]

        return StatParamValue("compactness", retVal, rMax=float("Inf"))

    def eccentricity(self, mask, img=None):
        # In skimage eccentricity ratio between minor and  major axis length of
        # the ellipse with the same second moment as the region.
        retVal = StatParamCalculator.errStr
        ecce = regionprops(mask.astype("int8"), ["Eccentricity"])
        if len(ecce) > 0:
            retVal = ecce[0]["Eccentricity"]

        return StatParamValue("eccentricity", retVal)

    def rms(self, mask, img=None):
        # RMS: Rotational Mass Symmetry. For PSI (Photon Systems Instruments) is
        #      the ratio between foci and major axis of the ellipse with the
        #      same second moment as the region. We calc with eccentricity
        retVal = StatParamCalculator.errStr
        ecce = regionprops(mask.astype("int8"), ["Eccentricity"])
        if len(ecce) > 0:
            retVal = 1 - (ecce[0]["Eccentricity"])**2

        return StatParamValue("rms", retVal)

    def mincircle(self, mask, img=None):
        r = 0.0
        c = (0,0)
        a, b = np.where(mask == 1)
        if len(a) > 0 and len(b) > 0:
            ab = np.transpose(np.vstack((a,b)))
            c, r = cv2.minEnclosingCircle(ab)
            c = (int(c[0]), int(c[1]))
            r = int(r)

        return StatParamMinCircle("mincircle", r, c, rMax=float('Inf'))

    def leafcount1(self, mask, img=None):
        # each leaf is located at a maxima of the distance transform. This
        # function implements the paper "3-D Histogram-Based Segmentation and
        # Leaf Detection for Rosette Plants" Jean-Michel Pape et. al. 2014
        # FIXME: We are missing some leafs when because there are isthmus in the
        #        distance transform that are leaves but are not a max.

        # 1. Calc the distance transform
        dt = cv2.distanceTransform(mask.astype("uint8"), cv2.cv.CV_DIST_C, 5)

        # 2. Mark non-max coordinates
        #    Potential maxima where 8-neighbor max <= pixel.
        sel = np.ones([3, 3]).astype("uint8")
        sel[1, 1] = 0
        maximas = dt - cv2.dilate(dt.astype("uint8"), sel)

        # Potential maximas >= 0
        maximas[np.where(maximas >= 0)] = 1

        # No max where dtDiff is negative nor mask == 0.
        maximas[np.where(maximas < 0)] = 0
        maximas[np.where(mask == 0)] = 0

        # 3. Prune connected components.
        cc, ccNum = label(maximas, return_num=True)
        sel = np.ones([3, 3]).astype("uint8")
        for i in range(1, ccNum):
            ccmsk = (cc == i).astype("float32")
            ccCoords = np.where(ccmsk == 1)
            perim = cv2.dilate(ccmsk, sel) - ccmsk
            perimCoords = np.where(perim == 1)
            if np.min(dt[ccCoords]) <= np.max(dt[perimCoords]):
                # No max if connected component has an adjacent max or equal.
                cc[ccCoords] = 0

        # 4. Find leaf centers.
        centers = []
        for rp in regionprops(cc):
            c = rp["centroid"]
            centers.append((c[1], c[0]))

        return StatParamLeafCount("leafcount1", centers)

    def height(self, mask, img=None):
        '''
        Plant height
        Only used for images taken from the side of a plant.
        '''
        bbox = regionprops(mask.astype("int8"), ["bbox"])
        if len(bbox) == 0:
            return StatParamValue("height", 0.0)  # FIXME: is this the best default?
        min_row, min_col, max_row, max_col = bbox[0]["bbox"]
        return StatParamValue("height", max_row - min_row,
                              rMax=float("Inf"))

    def height2(self, mask, img=None):
        '''
        Plant top and bottom are at 5% and 95% respectively of green pixel
        integration. This is supposed to provide a more less noisy height
        Only used for images taken from the side of a plant.
        '''
        GreenPixels = np.zeros(mask.shape[0])
        for i in range(mask.shape[0]):
            GreenPixels[i] = np.sum(mask[i, :])
        GreenPixelsCumSum = np.cumsum(GreenPixels)
        if GreenPixelsCumSum[-1] != 0:
            GreenPixelsCumSum = GreenPixelsCumSum/GreenPixelsCumSum[-1]
        else:
            return StatParamValue("height2", 0.0, rMax=float("Inf"))

        # Plant top when reaching 5% of total green pixels
        PlantTop = 0
        for i in range(mask.shape[0]):
            if GreenPixelsCumSum[i] >= 0.05:
                PlantTop = i
                break
        # Plant bottom when reaching 5% of total green pixels
        PlantBottom = mask.shape[0]
        for i in range(mask.shape[0]):
            if GreenPixelsCumSum[i] >= 0.95:
                PlantBottom = i
                break

        return StatParamValue("height2", PlantBottom-PlantTop,
                              rMax=float("Inf"))

    def wilting(self, mask, img=None):
        '''
        Plant wilting is at 50% of green pixel integration.
        Only used for images taken from the side of a plant.
        '''
        GreenPixels = np.zeros(mask.shape[0])
        for i in range(mask.shape[0]):
            GreenPixels[i] = np.sum(mask[i, :])

        # get range of plant height
        PlantTop = 0
        for i in range(mask.shape[0]):
            if GreenPixels[i] != 0:
                PlantTop = i
                break
        PlantBottom = mask.shape[0]
        for i in range(mask.shape[0]-1, -1, -1):
            if GreenPixels[i] != 0:
                PlantBottom = i
                break

        # get wilting height
        GreenPixelsCumSum = np.cumsum(GreenPixels)
        if GreenPixelsCumSum[-1] != 0:
            GreenPixelsCumSum = GreenPixelsCumSum/GreenPixelsCumSum[-1]
        else:
            return StatParamValue("wilting", 0.0, rMax=float("Inf"))

        WiltedHeight = PlantTop
        for i in range(PlantTop, PlantBottom):
            if GreenPixelsCumSum[i] >= 0.5:
                WiltedHeight = i
                break
        Wilting = float(PlantBottom-WiltedHeight)
        return StatParamValue("wilting", Wilting)

    def wilting2(self, mask, img=None):
        '''
        This is a normalised wilting with the height calculated from
        Plant top and bottom are at 5% and 95% respectively of
        green pixels. Plant wilting is at 50% of green pixel integration.
        Only used for images taken from the side of a plant.
         '''
        GreenPixels = np.zeros(mask.shape[0])
        for i in range(mask.shape[0]):
            GreenPixels[i] = np.sum(mask[i, :])
        GreenPixelsCumSum = np.cumsum(GreenPixels)
        if GreenPixelsCumSum[-1] != 0:
            GreenPixelsCumSum = GreenPixelsCumSum/GreenPixelsCumSum[-1]
        else:
            return StatParamValue("wilting", 0.0, rMax=float("Inf"))

        # Plant top when reaching 5% of total green pixels
        PlantTop = 0
        for i in range(mask.shape[0]):
            if GreenPixelsCumSum[i] >= 0.05:
                PlantTop = i
                break
        # Plant bottom when reaching 5% of total green pixels
        PlantBottom = mask.shape[0]
        for i in range(mask.shape[0]):
            if GreenPixelsCumSum[i] >= 0.95:
                PlantBottom = i
                break
        # Plantt wilting height at 50% of total green pixels
        WiltedHeight = PlantTop
        for i in range(PlantTop, PlantBottom):
            if GreenPixelsCumSum[i] >= 0.5:
                WiltedHeight = i
                break
        if PlantBottom-PlantBottom != 0:
            Wilting = float(PlantBottom - WiltedHeight)/float(PlantBottom-PlantTop)
        else:
            Wilting = 0.0
        return StatParamValue("wilting2", Wilting)

    def gcc(self, mask, img=None):
        retVal = StatParamCalculator.errStr
        gcc = img[mask == 1]
        if gcc.shape[0] != 0:
            gcc = np.float32(gcc)
            # What is the best way to calculate total GCC? 1. The relation of
            # the means or 2. the mean of the relation.??? We go with 2.
            #gcc = np.mean(gcc[:,1]) / np.mean(gcc[:,0])
            #                          + np.mean(gcc[:,1])
            #                          + np.mean(gcc[:,2])))
            gcc = np.mean(gcc[:,1] / (gcc[:,0]+gcc[:,1]+gcc[:,2]+1))
            retVal = gcc
        return StatParamValue("ColorGCC", retVal)

    def exg(self, mask, img=None):
        retVal = StatParamCalculator.errStr
        exg = img[mask == 1]
        if exg.shape[0] != 0:
            exg = np.float32(exg)
            exg = np.mean((2*exg[:,1]) - exg[:,0] - exg[:,2])
            retVal = exg
        return StatParamValue("ColorExG", retVal)

    def hsv(self, mask, img=None):
        retVal = StatParamCalculator.errStr
        hsv = img[mask == 1]
        if hsv.shape[0] != 0:
            hsv = hsv.reshape((1,hsv.shape[0],hsv.shape[1]))
            # FIXME: is it BGR2HSV or RGB2HSV
            hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)
            hsv = np.mean(hsv[0,:,1])
            retVal = hsv
        return StatParamValue("ColorHSV_H", retVal, rMax=360)

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
        F = np.reshape(F, (F.shape[0], F.shape[1], 1))
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
