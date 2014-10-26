import logging
from sys import stderr


NOEOL = logging.INFO + 1
logging.addLevelName(NOEOL, 'NOEOL')


class NoEOLStreamHandler(logging.StreamHandler):
    """A StreamHandler subclass that optionally doesn't print an EOL."""

    def __init__(self, stream=None):
        super(NoEOLStreamHandler, self).__init__(stream)

    def emit(self, record):
        """
        Emit a record. If level == NOEOL, don't add an EOL.
        """
        try:
            # KDM: I've added this block, to get StreamHandler handle standard
            # log levels.
            if record.levelno != NOEOL:
                return super(NoEOLStreamHandler, self).emit(record)
            msg = self.format(record)
            stream = self.stream
            # KDM: this is the only other change from StreamHandler
            # in StreamHandler, this is fs = "%s\n". We remove the EOL if
            # log level is NOEOL. Everything else is the same.
            fs = "%s"
            if not logging._unicode:  # if no unicode support...
                stream.write(fs % msg)
            else:
                try:
                    if (isinstance(msg, unicode) and
                            getattr(stream, 'encoding', None)):
                        ufs = fs.decode(stream.encoding)
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            # Printing to terminals sometimes fails. For example,
                            # with an encoding of 'cp1251', the above write will
                            # work if written to a stream opened or wrapped by
                            # the codecs module, but fail when writing to a
                            # terminal even when the codepage is set to cp1251.
                            # An extra encoding step seems to be needed.
                            stream.write((ufs % msg).encode(stream.encoding))
                    else:
                        stream.write(fs % msg)
                except UnicodeError:
                    stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def setup_console_logger(level=logging.DEBUG, handler=logging.StreamHandler,
                         stream=stderr):
    """Set up CLI logging"""
    log = logging.getLogger("CONSOLE")
    fmt = logging.Formatter('%(asctime)s: %(message)s', '%H:%M:%S')
    if stream is None:
        stream = open("/dev/null", "w")
    cons = NoEOLStreamHandler(stream=stream)
    cons.setLevel(level)
    cons.setFormatter(fmt)
    log.addHandler(cons)
    log.setLevel(level)

class PCException(Exception):
    id = 0
    def __str__(self):
        return ("PipeComp_Error: %s" % self.message)

class PCExBadRunExpects(PCException):
    id = 1
    def __init__(self, cls, attrKey=None):
        self.message = "The call to %s should consider \n%s" % \
            (cls.actName, cls.info())
        if attrKey is not None:
            self.message = self.message + \
                " Error: missing entry for '%s'" % attrKey

class PCExBadConfig(PCException):
    id = 2
    def __init__(self, compName, confName, msg):
        """Exception used when the error is caused by a faulty config file"""
        self.message = "Config parameter %s is invalid in component %s: %s" \
                        % (compName, confName, msg)

class PCExBadContext(PCException):
    id = 3
    def __init__(self, compName, contName, msg):
        """Exception used when the error is caused by a faulty input context"""
        self.message = "Context parameter error %s in component %s: %s" \
                        % (compName, contName, msg)

class PCExBreakInPipeline(PCException):
    id = 4
    def __init__(self, name, msg):
        """General Exception used when we can't give a good explanation."""
        self.message = "Unrecoverable error at %s: %s" % (name, msg)

class PCExMissingImage(PCException):
    id = 5
    def __init__(self, imgTimestamp, path):
        """Raised when we can't find an image in a timestream"""
        self.message = "Image %s not found for timestamp %s" \
                % (path, imgTimestamp)

class PCExSkippedImage(PCException):
    id = 6
    def __init__(self, imgTimestamp):
        """Raised when user skips an image"""
        self.message = "Image timestamp %s skipped by user" % imgTimestamp

class PCExExistingImage(PCException):
    id = 7
    def __init__(self, imgTimestamp):
        """Raised when img is said to already be calculated"""
        self.message = "Image timestamp %s has already been calculated" \
                % imgTimestamp

