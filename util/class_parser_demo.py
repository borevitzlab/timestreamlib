import sys
import timestream
import logging

timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()
ts.load(sys.argv[1])
ts_out = timestream.TimeStream()
ts_out.create("./new-ts")
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
        print "Copying image to ts_out",
        sys.stdout.flush()
        newimg = timestream.TimeStreamImage()
        newimg.datetime = img.datetime
        newimg.pixels = img.pixels
        newimg.data["copy"] = "yes"
        ts_out.write_image(newimg)
        print "Done\n"

