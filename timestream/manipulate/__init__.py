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

    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)


class PCExBadRunExpects(PCException):
    id = 1

    def __init__(self, cls, attrKey=None):
        self.message = "The call to %s should consider \n%s" % (
            cls.actName, cls.info())
        if attrKey is not None:
            self.message += " Error: entry '%s'" % attrKey


class PCExBadConfig(PCException):
    id = 2

    def __init__(self, compName, confName, msg):
        """Exception used when the error is caused by a faulty config file"""
        self.message = "Config parameter %s is invalid in component %s: %s" % (
            compName, confName, msg)


class PCExBadContext(PCException):
    id = 3

    def __init__(self, compName, contName, msg):
        """Exception used when the error is caused by a faulty input context"""
        self.message = "Context parameter error %s in component %s: %s" % (
            compName, contName, msg)


class PCExBreakInPipeline(PCException):
    id = 4

    def __init__(self, name, msg):
        """General Exception used when we can't give a good explanation."""
        self.message = "Unrecoverable error at %s: %s" % (name, msg)


class PCExMissingImage(PCException):
    id = 5

    def __init__(self, imgTimestamp, path):
        """Raised when we can't find an image in a timestream"""
        self.message = "Image %s not found for timestamp %s" % (path,
                                                                imgTimestamp)


class PCExSkippedImage(PCException):
    id = 6

    def __init__(self, imgTimestamp):
        """Raised when user skips an image"""
        self.message = "Image timestamp %s skipped by user" % imgTimestamp


class PCExExistingImage(PCException):
    id = 7

    def __init__(self, imgTimestamp):
        """Raised when img is said to already be calculated"""
        self.message = "Image timestamp %s has already been calculated" % \
            imgTimestamp


class PCExCorruptImage(PCException):
    id = 8

    def __init__(self, path):
        """Raised when receiving an error on image read"""
        self.message = "Image at path %s is corrupted" % path
