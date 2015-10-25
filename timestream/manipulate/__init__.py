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
.. module:: timestream.manipulate
    :platform: Unix, Windows
    :synopsis: Image manipulation and processing for Plant Phenomics

.. moduleauthor:: Joel Granados, Chuong Nguyen, Kevin Murray
"""

import logging
from sys import stderr


class PCException(Exception):
    id = 0
    doc = """Exception: General Pipeline Component Exception"""

    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)


class PCExBadRunExpects(PCException):
    id = 1
    doc = """Exception: Faulty argument in component """

    def __init__(self, cls, attrKey=None):
        """Exception thrown when a component receives a faulty argument"""
        self.message = "The call to %s should consider \n%s" % (
            cls.actName, cls.info())
        if attrKey is not None:
            self.message += " Error: entry '%s'" % attrKey


class PCExBadConfig(PCException):
    id = 2
    doc = """Exception: Faulty configuration file"""

    def __init__(self, compName, confName, msg):
        """Exception used when the error is caused by a faulty config file"""
        self.message = "Config parameter %s is invalid in component %s: %s" % (
            compName, confName, msg)


class PCExBadContext(PCException):
    id = 3
    doc = """Exception: Faulty context"""

    def __init__(self, compName, contName, msg):
        """Exception used when the error is caused by a faulty input context"""
        self.message = "Context parameter error %s in component %s: %s" % (
            compName, contName, msg)


class PCExBreakInPipeline(PCException):
    id = 4
    doc = """Exception: Unknown cause"""

    def __init__(self, name, msg):
        """General Exception used when we can't give a good explanation."""
        self.message = "Unrecoverable error at %s: %s" % (name, msg)


class PCExMissingImage(PCException):
    id = 5
    doc = """Exception: Can't find an image in timestream"""

    def __init__(self, imgTimestamp, path):
        """Raised when we can't find an image in a timestream"""
        self.message = "Image %s not found for timestamp %s" % (path,
                                                                imgTimestamp)


class PCExSkippedImage(PCException):
    id = 6
    doc = """Exception: User skipped an image"""

    def __init__(self, imgTimestamp):
        """Raised when user skips an image"""
        self.message = "Image timestamp %s skipped by user" % imgTimestamp


class PCExExistingImage(PCException):
    id = 7
    doc = """Exception: Image already calculated"""

    def __init__(self, imgTimestamp):
        """Raised when img is said to already be calculated"""
        self.message = "Image timestamp %s has already been calculated" % \
            imgTimestamp


class PCExCorruptImage(PCException):
    id = 8
    doc = """Exception: Error reading image"""

    def __init__(self, path):
        """Raised when receiving an error on image read"""
        self.message = "Image at path %s is corrupted" % path


class PCExUndefinedMeta(PCException):
    id = 9
    doc = """Exception: MetaId is undefined for a pot. Check metas config."""

    def __init__(self, potId, metaId):
        """Raised when a pot is missing from the meta list"""
        self.message = "Pot %s is missing %s" % (potId, metaId)


class PCExBadImage(PCException):
    id = 10
    doc = """Exception: Raised when an expected image variable is corrupted"""

    def __init__(self, path):
        self.message = "Image %s is corrupted" % path


class PCExImageTooDark(PCException):
    id = 11
    doc = """Excetpion: Raised when image is too dart to detect"""

    def __init__(self, path):
        self.message = "Image %s is too dark" % path


class PCExCannotFindColorCard(PCException):
    id = 12
    doc = """Excpetion: Raised when we cannot find the color card"""

    def __init__(self, path):
        self.message = "Cannot find color card in %s" % path


class PCExCannotFindTray(PCException):
    id = 13
    doc = """Exception: Raised when the tray score is to low to accept"""

    def __init__(self, trayNum, path):
        self.message = "Cannot find tray number %s in %s" % (trayNum, path)


class PCExSegmentation(PCException):
    id = 14
    doc = """Exception: Raised when there is an exception error"""

    def __init__(self, potid, path):
        self.message = "Cannot segment pot %s in %s" % (potid, path)


class PCExCannotCalcTimestamp(PCException):
    id = 15
    doc = """Exception: Raised when we cannot calculate a timestamp"""

    def __init__(self, path):
        self.message = "Cannot calculate timestamp in %s" % path


class PCExCannotFindFeatures(PCException):
    id = 16
    doc = """Exception: Raised when no features can be calculated"""

    def __init__(self, path):
        self.message = "Cannot find any features for %s" % path


class PCExPotRectangleDimsOutOfImage(PCException):
    id = 17
    doc = """Exception: Raised when the pot rectangle outside image"""

    def __init__(self, tray, pot, imageSize):
        self.message = "Pot %s of Tray %s is out of image (%s)" % \
            (tray, pot, imageSize)
