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
.. module:: timestream.manipulate.pot
    :platform: Unix, Windows
    :synopsis: Pot-level image manipulation

.. moduleauthor:: Joel Granados, Chuong Nguyen
"""

import numpy as np
import matplotlib.pyplot as plt
import timestream.manipulate.plantSegmenter as tm_ps


class ImagePotRectangle(object):

    def __init__(self, rectDesc, imgSize, growM=100):
        """ Handles all logic to do with rectangles in images.

        Attribures:
          rectDesc([x,y,x',y'])*: This is the total description of the rectangle:
            upper left corner and lower right corner.
          rectDesc([x,y]): This is the center of a rectangle. We will grow it by
            growM in every direction.
          imgSize([height, width]): Size of the image containing the rectangle.
            Whatever img.shape returns.
          growM(int): The maximum amount (in pixels) when we receive a coordinate.
          * y is vertical | x is horizontal.

        Raises:
          TypeError: When we don't receive a list for a rectangle descriptor.
        """
        self._rect = np.array([-1, -1, -1, -1])

        if not isinstance(imgSize, tuple) or len(imgSize) < 2:
            raise TypeError("ImgSize must be a tuple of at least len 2")
        if True in (np.array(imgSize[0:2]) < 1):
            raise TypeError("ImgSize elements must be >0")
        self._imgwidth = imgSize[1]
        self._imgheight = imgSize[0]

        if not (isinstance(rectDesc, list) or isinstance(rectDesc, np.ndarray))\
                or (len(rectDesc) != 2 and len(rectDesc) != 4):
            raise TypeError(
                "Rectangle Descriptor must be a list of len 2 or 4")

        elif len(rectDesc) == 4:
            self._rect = np.array(rectDesc)

        elif len(rectDesc) == 2:
            pt1 = np.array(rectDesc) - growM
            pt2 = np.array(rectDesc) + growM
            self._rect = np.concatenate((pt1, pt2))

        # Check to see if rect is within size.
        if sum(self._rect < 0) > 0 \
                or sum(self._rect[[1, 3]] > self._imgheight) > 0 \
                or sum(self._rect[[0, 2]] > self._imgwidth) > 0:
            raise TypeError("Rectangle is outside containing image dims.")

    def __getitem__(self, item):
        if item > 4 or item < 0:
            raise IndexError("Rectangle index should be [0,3]")
        return self._rect[int(item)]

    def asList(self):
        return self._rect

    @property
    def imgSize(self):
        """Be consistent with shape"""
        return (self._imgheight, self._imgwidth)

    @property
    def width(self):
        return abs(self._rect[2] - self._rect[0])

    @property
    def height(self):
        return abs(self._rect[3] - self._rect[1])


class ImagePotHandler(object):

    def __init__(self, potID, rect, ipm,
                 metaids=None, ps=None):
        """ImagePotHandler: a class for individual pot images.

        Args:
          potID (object): Should be unique between pots. Is given by the
            potMatrix. Is not changeable.
          rect (ImagePotRectangle): [x,y,x`,y`]: (x,y) and (x`,y`)* are
            reciprocal corners
          ipm (ImagePotMatrix): Its the ImagePotMatrix instance that this pot
            belongs to
          metaids (dict): info that might be used by the pot image in
            other contexts (e.g {chamberID:#, universalID:#...}). We can only
            bind to a numeric or character value.
          ps (PotSegmenter): It can be any child class from PotSegmenter. Its
            instance that has a segment method.
          * y is vertical | x is horizontal.

        Attributes:
          _id: Set on instantiation. Unique in ImagePotMatrix.
          _ipm(ImagePotMatrix): The containing ImagePotMatrix.
          _rect,rect(ImagePotRectangle): Rectangle describing this pot.
          _ps(PotSegmenter): The component that does the image segmentation.
          fc(StatParamCalculator): The component that calculates features from
            segmented images. We create a new instance for every fc call.
          iphPrev(ImagePotHandler): Is the ImagePotHandler of the previous
            ImagePotMatrix with the same id as self.
          _image(ndarray): Return the cropped image (defined by rect) of
            self._ipm.image.
          getImage: Return images that is either masked, cropped and/or with
            feature strings
          mask,_mask(ndarray): binary image represenging the mask.
          features: Return the calculated features

        Raises:
          TypeError: When the Args is of an unexpected type.
        """
        self._id = potID

        if not isinstance(ipm, ImagePotMatrix):
            raise TypeError("ipm must be instance of ImagePotMatrix")
        self._ipm = ipm

        if not isinstance(rect, ImagePotRectangle):
            raise TypeError("rect must be an instance of ImagePotRectangle")
        if rect.imgSize[0] != self._ipm.image.pixels.shape[0] \
                or rect.imgSize[1] != self._ipm.image.pixels.shape[1]:
            raise RuntimeError("rect size must be equal to superImage shape")
        self._rect = rect

        if ps is None:
            self._ps = None
        elif isinstance(ps, tm_ps.PotSegmenter):
            self._ps = ps
        else:
            raise TypeError("ps must be an instance of PotSegmenter")

        self._features = {}
        self._mask = None

        if metaids is None:
            self._mids = {}
        elif not isinstance(metaids, dict):
            raise TypeError("Metaids must be dictionary")
        elif len(metaids) < 1:
            self._mids = {}
        else:
            self._mids = metaids
        # Check all metaids are (int, long, float, complex, str)
        for key, val in self._mids.iteritems():
            if not isinstance(val, (int, long, float, complex, str)):
                raise TypeError("Metaids must be of type"
                                + "int, long, float, complex or string")

    @property
    def mask(self):
        if self._mask is not None:
            return self._mask

        if self._ps is None:
            return np.zeros([self._rect.height, self._rect.width],
                            np.dtype("float64"))

        self._mask = self.getSegmented()
        return (self._mask)

    @mask.setter
    def mask(self, m):
        if m is not None:
            raise ValueError("Can only reset mask to None")

        # Resetting mask invalidates calculated features.
        self._features = {}
        self._mask = m

    @property
    def ps(self):
        return self._ps

    @ps.setter
    def ps(self, ps):
        if not isinstance(ps, tm_ps.PotSegmenter):
            raise TypeError("ps must be instance of PotSegmenter")

        # When we modify ps we modify mask
        self.mask = None
        self._ps = ps

    @property
    def id(self):
        return self._id

    @property
    def ipm(self):
        return self._ipm

    @ipm.setter
    def ipm(self, val):
        if not isinstance(val, ImagePotMatrix):
            raise TypeError("ipm should be instance of ImagePotMatrix")

        # Raise error if there is an id conflict in the new ImagePotMatrix
        if self.id in val.potIds() and self.id is not val.getPot(self.id):
            raise RuntimeError("Pot with Id %s different from %s exists"
                               % (self.id, self))

        # Setting ipm effectively changes the image, mask features....
        self.mask = None
        self._ipm = val

    @property
    def iphPrev(self):
        """We search for the previous hander in the previous matrix"""
        if self._ipm.ipmPrev is None:
            return None

        return self._ipm.ipmPrev.getPot(self._id)

    def getSegmented(self):
        """Does not change internals of instance

            This method is used to parallelize the pot segmentation
            calculation so we should avoid changing the inner struct
            of the instance.
        """
        # FIXME: here we loose track of the hints
        msk, hint = self._ps.segment(self._image, {})

        # if bad segmentation
        if 1 not in msk and self.iphPrev is not None:
            # Use previous mask. Fit the previous mask size into msk
            pm = self.iphPrev.mask
            msk[:] = 0
            minHeight = np.min([pm.shape[0], msk.shape[0]])
            minWidth = np.min([pm.shape[1], msk.shape[1]])
            msk[0:minHeight ,0:minWidth ] = pm[0:minHeight ,0:minWidth ]

        return msk

    @property  # not deletable
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, r):
        if isinstance(r, np.ndarray):
            if len(r) != 4:
                raise TypeError("Pass an ndarray of len 4 to set a rectangle")
            else:
                self._rect = ImagePotRectangle(r, self._ipm.image.pixels.shape)

        elif isinstance(r, ImagePotRectangle):
            # The right thing to do here is to create a new Imagepotrectangle so
            # we are sure we relate it to the correct image shape.
            self._rect = ImagePotRectangle(r.asList(),
                                           self._ipm.image.pixels.shape)

        else:
            raise TypeError("To set rectangle must pass list or"
                            + "ImagePotRectangle")

        # Changing rect modifies mask, features, image....
        self.mask = None

    @property
    def superImage(self):
        """We return the ndarray"""
        # FIXME: check for _ipm
        return self._ipm.image.pixels

    @property  # not settable nor delettable
    def _image(self):
        # No need to return copy. For internal use only
        return (self._ipm.image.pixels[self._rect[1]:self._rect[3],
                                       self._rect[0]:self._rect[2], :])

    @property
    def fc(self):
        return tm_ps.StatParamCalculator()

    def getImage(self, masked=False, features=[], inSuper=False):
        """Returns pot pixels

        masked(boolean): If True, we replace background pixels with black
        features(list): List of feature classes that should be added to the
          perimeter of the pot image
        inSuper: When True we return the segmentation in the totality of
                 self._ipm.image. When False we return it in the rect.
        """
        img = self._image.copy()

        if masked:
            # trigger creation if needed
            msk = self.mask

            height, width, dims = img.shape
            msk = np.reshape(msk, (height * width, 1), order="F")

            tmpImg = np.zeros((height, width, dims), dtype=img.dtype)
            tmpImg = np.reshape(tmpImg, (height * width, dims), order="F")

            Ind = np.where(msk)[0]
            imgR = np.reshape(img, (height * width, dims), order="F")
            tmpImg[Ind, :] = imgR[Ind,:]
            tmpImg = np.reshape(tmpImg, (height, width, dims), order="F")
            img[::] = tmpImg[::]

        if len(features) > 0:
            # For every calculated feature we try to fit values in image.
            # FIXME: We silently ingore elements in features that are not in
            #        self._features
            # FIXME: We should have a limit to the amount of features we put in
            #        an image
            x = img.shape[1] - 200
            y = 50
            for f in features:
                if f in self._features.keys():
                    feat = self._features[f]
                    feat.drawParamInImg(img, x=x, y=y, tScale=1.2)
                    y += 30

        if inSuper:
            superI = self._ipm.image.pixels.copy()
            superI[self._rect[1]:self._rect[3],
                   self._rect[0]:self._rect[2], :] = img
            del img
            img = superI

        return img

    def increaseRect(self, leftby=5, topby=5, rightby=5, bottomby=5):
        # Using property to trigger assignment, checks and cleanup
        r = self._rect.asList() + np.array([-leftby, -topby, rightby,
                                            bottomby])
        self.rect = r

    def reduceRect(self, leftby=5, topby=5, rightby=5, bottomby=5):
        # Using property to trigger assignment, checks and cleanup
        r = self._rect.asList() + np.array([leftby, topby, -rightby,
                                            -bottomby])
        self.rect = r

    def calcFeatures(self, feats):
        # Calc all the possible features when feats not specfied
        if not isinstance(feats, list):
            raise TypeError("feats should be a list")

        if "all" in feats:
            feats = tm_ps.StatParamCalculator.statParamMethods()

        # Use property to trigger creation
        msk = self.mask
        if msk is None:
            raise RuntimeError("Cannot calculate feature of None")
        fc = self.fc
        for featName in feats:
            # calc the ones we don't have
            if featName not in self._features.keys():
                featFunc = getattr(fc, featName)
                try:
                    self._features[featName] = featFunc(msk, img=self._image)
                except:
                    self._features[featName] = tm_ps.StatParamValue(
                        featName,
                        tm_ps.StatParamCalculator.errStr)

    def getCalcedFeatures(self):
        return self._features

    def getFeature(self, fKey):
        if fKey not in self._features.keys():
            raise KeyError("%s is not a valid feature key" % fKey)

        return self._features[fKey]

    def getMetaIdKeys(self):
        return self._mids.keys()

    def getMetaId(self, mKey):
        if mKey not in self._mids.keys():
            raise IndexError("%s is not a meta key." % mKey)
        else:
            return self._mids[mKey]

    def setMetaId(self, mKey, mValue):
        if not isinstance(mValue, (int, long, float, complex, str)):
            raise TypeError("Metaids values must be of type"
                            + "int, long, float, complex or string")
        else:
            self._mids[mKey] = mValue

    def strip(self):
        self._mask = None


class ImagePotMatrix(object):

    def __init__(self, image, pots=[], growM=100, ipmPrev=None):
        """ImagePotMatrix: To house all the ImagePotHandlers

        We make sure that their IDs are unique inside the ImagePotMatrix
        instance. If there are two equal ids, one will overwrite the other
        without warning.

        Args:
          image (TimeStreamImage): Image in which everything is located
          pots (list): It can be a list of ImagePotHandler instances, of 4
            elment lists or of 2 elment list
          growM (int): The amount of pixels that containing plots should grow if
            they are initialized by a center.
          rects (list): list of tray lists. Each tray list is a list of two
            element sets. The reciprocal corners of the pot rectangle
          ipmPrev (ImagePotMatrix): The previous ImagePotMatrix object.

        Attributes:
          _pots(dict): Pots indexed by pot IDs.
          _image(TimeStreamImage): Image where all the pots fit. Set only once.
          _ipmPrev(ImagePotMatrix): Previous ImagePotMatrix. Set only once.
        """
        # import here to avoid circular imports
        from timestream import TimeStreamImage
        if not isinstance(image, TimeStreamImage):
            raise TypeError("ImagePotMatrix.image must be a TimeStreamImage")
        else:
            self._image = image

        if ipmPrev is None:
            self._ipmPrev = None
        elif isinstance(ipmPrev, ImagePotMatrix):
            self._ipmPrev = ipmPrev
            # avoid a run on memory
            self._ipmPrev.ipmPrev = None
        else:
            raise TypeError("ipmPrev must be an instance of ImagePotMatrix")

        # We make ImagePotHandler instances with whatever we find.
        if not isinstance(pots, list):
            raise TypeError("pots must be a list")
        potIndex = -1  # Used when creating from rect
        self._pots = {}
        for p in pots:
            if isinstance(p, ImagePotMatrix):
                self._pots[p.id] = p

            elif isinstance(p, list) and (len(p) == 2 or len(p) == 4):
                r = ImagePotRectangle(p, self._image.pixels.shape, growM=growM)
                self._pots[potIndex] = ImagePotHandler(potIndex, r, self)
                potIndex -= 1

            else:
                TypeError("Elements in pots must be ImagePotHandler or list"
                          + " of 2 or 4 elments")

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, val):
        raise RuntimeError(
            "ImagePotMatrix.image should only be set by __init__")

    @property
    def ipmPrev(self):
        return self._ipmPrev

    @ipmPrev.setter
    def ipmPrev(self, val):
        if not isinstance(val, ImagePotMatrix) and val is not None:
            raise TypeError("ipmPrev must be ImagePotMatrix or None")
        self._ipmPrev = val

    @property
    def potIds(self):
        """Returns a list of pot ids"""
        return self._pots.keys()

    @property
    def potFeatures(self):
        """ Return a feature name list with all possible features in pots """
        featureNames = []
        for key, pot in self._pots.iteritems():
            for featName in pot.getCalcedFeatures():
                if featName not in featureNames:
                    featureNames.append(featName)

        return (featureNames)

    @property
    def numPots(self):
        return len(self._pots)

    def getPot(self, potId):
        if potId not in self._pots.keys():
            raise IndexError("No pot id %s found" % str(potId))

        return self._pots[potId]

    def addPot(self, pot):
        if not isinstance(pot, ImagePotHandler):
            raise TypeError("Pot must be of type ImagePotHandler")

        # We need to make sure that pot._ipm == self
        if pot.ipm != self:
            # no need to triger the ipm property unnecessarily
            pot.ipm = self
        self._pots[pot.id] = pot

    def iter_through_pots(self):
        for key, pot in self._pots.iteritems():
            yield(key, pot)

    def show(self):
        """ Show segmented image with the plot squares on top. """
        sImage = self.image.pixels
        for key, pot in self._pots.iteritems():
            sImage = sImage & pot.getImage(masked=True, inSuper=True)

        plt.figure()
        plt.imshow(sImage.astype(np.uint8))
        plt.hold(True)

        for key, pot in self._pots.iteritems():
            r = pot.rect
            plt.plot([r[0], r[2], r[2], r[0], r[0]],
                     [r[1], r[1], r[3], r[3], r[1]],
                     linestyle="-", color="r")

        a = plt.gca()
        a.axis('tight')
        plt.title('Pot Rectangles')
        plt.show()

    def strip(self):
        self._ipmPrev = None
        for key, pot in self._pots.iteritems():
            pot.strip()
