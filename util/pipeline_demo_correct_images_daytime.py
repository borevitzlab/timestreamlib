#!/usr/bin/env python

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
import datetime

# default values
startDate = None
endDate = None
timeInterval = 60 * 60 # every hour
timeStart = datetime.time(8,0,0) # 8AM
timeEnd   = datetime.time(15, 0,0) # 3PM
visualise = False

if len(sys.argv) != 4:
    inputRootPath  = '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-orig'
    outputRootPath = '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-corr'
    startDate = timestream.parse.ts_parse_date("2014_06_18_00_00_00")
else:
    try:
        inputRootPath = sys.argv[1]
        outputRootPath = sys.argv[2]
        startDate = timestream.parse.ts_parse_date(sys.argv[3])
        timeInterval = eval(sys.argv[4]) # allow some expression such as 24*60*60
        timeStartList = sys.argv[5].split('_')
        timeStart = datetime.time(int(timeStartList[0]), int(timeStartList[1]), int(timeStartList[2]))
        timeEndList  = sys.argv[6].split('_')
        timeEnd = datetime.time(int(timeEndList[0]), int(timeEndList[1]), int(timeEndList[2]))
        visualise = eval(sys.argv[7]) # need to enter "True" or "False"
    except:
        print('Try running with provided info')

# read global settings for processing
settingFile = os.path.join(inputRootPath, '_data', 'pipeline.yml')
f = file(os.path.join(inputRootPath, '_data', 'pipeline.yml'))
settings = yaml.load(f)
f.close()

# run only 3 stages, from distortion correction to color correction
settings = settings[:3]
# set writeImage flag to write corrected image into output timestream
settings[2][1]['writeImage'] = True

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()

ts.load(inputRootPath)
print('timestream path = ', ts.path)
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
# TODO: context could be part of initialising input here
pl = pipeline.ImagePipeline(ts.data["settings"])

print("Iterating by date and time range")
#endDate = timestream.parse.ts_parse_date("2014_06_19_12_00_00")
#timeInterval = 15 * 60
for img in ts.iter_by_timepoints(remove_gaps=False, start=startDate, end=endDate, interval=timeInterval ):
    if img is None or img.pixels is None:
        print('Missing Image')
    else:
        print("Process", img.path, '...'),
        print("Time stamp", img.datetime)
        startOfDay = datetime.datetime.combine(img.datetime.date(), timeStart)
        endOfDay = datetime.datetime.combine(img.datetime.date(), timeEnd)
        if img.datetime >= startOfDay and img.datetime <= endOfDay:
            context = {"rts":ts, "wts":ts_out, "img":img}
            result = pl.process(context, [img], visualise)
        else:
            print('Skip this time slot', img.datetime)

print("Done")
