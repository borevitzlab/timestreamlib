# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:31:54 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import absolute_import, division, print_function

import sys, os
import timestream
import logging
import timestream.manipulate.pipeline as pipeline
import yaml

if len(sys.argv) != 4:
    settingFile    = "/home/joel/.Trash/pipeline.yml"
    inputRootPath  = '/home/joel/.Trash/BVZ0036-GC02L-C01~fullres-orig'
    outputRootPath = '/home/joel/.Trash/processed'
else:
    settingFile = sys.argv[1]
    inputRootPath = sys.argv[2]
    outputRootPath = sys.argv[3]

# read global settings for processing
f = file(settingFile)
settings = yaml.load(f)
f.close()

# initialise input timestream for processing
timestream.setup_debug_logging(level=logging.INFO)
ts = timestream.TimeStream()

ts.load(inputRootPath)
ts.data["settings"] = settings
ts.data["settingPath"] = os.path.dirname(settingFile)

#create new timestream for output data
ts_out = timestream.TimeStream()
ts_out.create(outputRootPath)
ts_out.data["settings"] = settings
ts_out.data["settingPath"] = os.path.dirname(settingFile)
ts_out.data["sourcePath"] = inputRootPath
print("Timestream instance created:")
print("   ts.path:", ts.path)
for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
    print("   ts.%s:" % attr, getattr(ts, attr))

# initialise processing pipeline
pl = pipeline.ImagePipeline(ts.data["settings"])

print("Iterating by date")
startDate = timestream.parse.ts_parse_date("2014_06_18_12_00_00")
#endDate = timestream.parse.ts_parse_date("2014_06_19_12_00_00")
#timeInterval = 15 * 60
endDate = None
timeInterval = 24 * 60 * 60
for img in ts.iter_by_timepoints(remove_gaps=False, start=startDate, end=endDate, interval=timeInterval ):
    if img is None:
        print('Missing Image')
    else:
        print("Process", img.path, '...'),
        # set visualise to False to run in batch mode
        context = {"rts":ts, "wts":ts_out, "img":img}
        result = pl.process(context, [img])

        print("Done")
