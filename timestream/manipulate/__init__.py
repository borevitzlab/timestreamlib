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
            self.message = self.message + \
                " Error: missing entry for '%s'" % attrKey


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
