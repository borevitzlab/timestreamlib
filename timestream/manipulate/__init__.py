from itertools import (
        cycle,
        izip,
        )
import logging
import multiprocessing


NOEOL = logging.INFO+1
logging.addLevelName(NOEOL, 'NOEOL')


class NoEOLStreamHandler(logging.StreamHandler):
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
            if not logging._unicode: #if no unicode support...
                stream.write(fs % msg)
            else:
                try:
                    if (isinstance(msg, unicode) and
                        getattr(stream, 'encoding', None)):
                        ufs = fs.decode(stream.encoding)
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            #Printing to terminals sometimes fails. For example,
                            #with an encoding of 'cp1251', the above write will
                            #work if written to a stream opened or wrapped by
                            #the codecs module, but fail when writing to a
                            #terminal even when the codepage is set to cp1251.
                            #An extra encoding step seems to be needed.
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


def setup_console_logger():
    """Set up manipulation module CLI logging"""
    log = logging.getLogger("CONSOLE")
    fmt = logging.Formatter('%(asctime)s: %(message)s', '%H:%M:%S')
    ch = NoEOLStreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)
    log.setLevel(logging.INFO)
