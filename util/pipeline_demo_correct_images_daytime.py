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
timeInterval = 24 * 60 * 60 # every hour
timeStart = datetime.time(8,0,0) # 8AM
timeEnd   = datetime.time(15, 0,0) # 3PM
visualise = False

if len(sys.argv) <= 2:
    inputRootPath  = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0018/BVZ0018-GC05L-C01~fullres-orig'
    outputRootPath = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0018/BVZ0018-GC05L-C01~fullres'
    startDate = timestream.parse.ts_parse_date("2013_08_06_12_00_00")
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
settingFile = os.path.join(inputRootPath, '_data', 'pipeline_v2.yml')
f = file(os.path.join(inputRootPath, '_data', 'pipeline_v2.yml'))
yfile = yaml.load(f)
f.close()
settings = yfile["pipeline"]
outstreams = yfile["outstreams"]
general = yfile["general"]

#outstreams = outstreams[:1]
#settings = settings[:6]

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()

ts.load(inputRootPath)
print('timestream path = ', ts.path)
ts.data["settings"] = settings
ts.data["settingPath"] = os.path.dirname(settingFile)
context = {"rts":ts}
print("Timestream instance created:")
print("   ts.path:", ts.path)
for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
    print("   ts.%s:" % attr, getattr(ts, attr))

#create new timestream for output data
for outstream in outstreams:
    ts_out = timestream.TimeStream()
    ts_out.data["settings"] = settings
    ts_out.data["settingPath"] = os.path.dirname(settingFile)
    ts_out.data["sourcePath"] = inputRootPath
    ts_out.name = outstream["name"]
    base_name = os.path.basename(outputRootPath)
    tsoutpath = os.path.join(outputRootPath, base_name + '-' + outstream["name"])
    if "outpath" in outstream.keys():
        tsoutpath = outstream["outpath"]
    if not os.path.exists(os.path.dirname(tsoutpath)):
        os.mkdir(os.path.dirname(tsoutpath))
    ts_out.create(tsoutpath)
    context[outstream["name"]] = ts_out
    print("   ts_out.path:", ts_out.path)

context["outputroot"] = outputRootPath

# Dictionary where we put all values that should be added with an image as soon
# as it is output with the TimeStream
context["outputwithimage"] = {}

# initialise processing pipeline
pl = pipeline.ImagePipeline(ts.data["settings"], context)

print("Iterating by date")

if "startdate" in general.keys():
    sd = general["startdate"]
    if len(sd) == 0:
        startDate = None
    else:
        startDate = datetime.datetime(sd["year"], sd["month"], sd["day"], \
                                      sd["hour"], sd["minute"], sd["second"])
else:
    startDate = None #timestream.parse.ts_parse_date("2014_06_18_12_00_00")

if "enddate" in general.keys():
    ed = general["enddate"]
    if len(ed) == 0:
        endDate = None
    else:
        endDate = datetime.datetiem(ed["year"], ed["month"], ed["day"], \
                                ed["hour"], ed["minute"], ed["second"])
else:
    endDate = None

if "timeInterval" in general.keys():
    timeInterval = general["timeinterval"]
else:
    timeInterval = 24*60*60

if "visualise" in general.keys():
    visualise = general["visualise"]
else:
    visualise = False

print("Iterating by date and time range")
#endDate = timestream.parse.ts_parse_date("2014_06_19_12_00_00")
#timeInterval = 15 * 60
print(startDate)
print(endDate)
print(timeInterval)
#for img in ts.iter_by_timepoints(remove_gaps=False, start=startDate, end=endDate, interval=timeInterval ):
for img in ts.iter_by_timepoints(remove_gaps=False):
    if img is None or img.pixels is None:
        print('Missing Image')
    else:
        print("Process", img.path, '...'),
        print("Time stamp", img.datetime)
        startOfDay = datetime.datetime.combine(img.datetime.date(), timeStart)
        endOfDay = datetime.datetime.combine(img.datetime.date(), timeEnd)
        if img.datetime >= startOfDay and img.datetime <= endOfDay:
            context["img"] = img
            result = pl.process(context, [img.pixels], visualise)
        else:
            print('Skip this time slot', img.datetime)

print("Done")
