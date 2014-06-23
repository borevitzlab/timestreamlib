import sys
import timestream
import logging

timestream.setup_debug_logging(level=logging.INFO)
ts = timestream.TimeStream(sys.argv[1])
print "Timestream instance created:"
print "   ts.path:", ts.path
for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
    print "   ts.%s:" % attr, getattr(ts, attr)
print
print "Iterating by date"
for img in ts.iter_by_timepoints(remove_gaps=False):
    if img is None:
        print 'Missing Image'
    else:
        print img
        print "img.path", img.path
        print "img.datetime", img.datetime
        print "img.pixels.shape", img.pixels.shape
        print "img.pixels.dtype", img.pixels.dtype
        print
print
print
print "Iterating by files"
for img in ts.iter_by_files():
    print img
    print "img.path", img.path
    print "img.datetime", img.datetime
    print "img.pixels.shape", img.pixels.shape
    print "img.pixels.dtype", img.pixels.dtype
    print

