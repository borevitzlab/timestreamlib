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
from timestream.manipulate.pipecomponents import PCExBrakeInPipeline
import yaml
import datetime

if len(sys.argv) != 3:
    R = "/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/"
    inputRootPath = os.path.join(R,"BVZ0036-GC02L-C01~fullres-orig")
    outputRootPath = os.path.join(R,"BVZ0036-GC02L-C01~fullres-processed")
else:
    inputRootPath = sys.argv[1]
    outputRootPath = sys.argv[2]

# read global settings for processing
settingFile = os.path.join(inputRootPath, '_data', 'pipeline.yml')
f = file(os.path.join(inputRootPath, '_data', 'pipeline.yml'))
yfile = yaml.load(f)
f.close()
settings = yfile["pipeline"]
outstreams = yfile["outstreams"]
general = yfile["general"]

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
    tsoutpath = os.path.join(outputRootPath, outstream["name"])
    if "outpath" in outstream.keys():
        tsoutpath = outstream["outpath"]
    if not os.path.exists(os.path.dirname(tsoutpath)):
        os.mkdir(os.path.dirname(tsoutpath))
    ts_out.create(tsoutpath)
    context[outstream["name"]] = ts_out

context["outputroot"] = outputRootPath

# Dictionary where we put all values that should be added with an image as soon
# as it is output with the TimeStream
context["outputwithimage"] = {}

# initialise processing pipeline
pl = pipeline.ImagePipeline(ts.data["settings"], context)

print("Iterating by date")

if "startdate" in general.keys():
    sd = general["startdate"]
    startDate = datetime.datetime(sd["year"], sd["month"], sd["day"], \
                                    sd["hour"], sd["minute"], sd["second"])
else:
    startDate = timestream.parse.ts_parse_date("2014_06_18_12_00_00")

if "enddate" in general.keys():
    ed = general["enddate"]
    if len(ed) == 0:
        endDate = None
    else:
        endDate = datetime.datetiem(ed["year"], ed["month"], ed["day"], \
                                ed["hour"], ed["minute"], ed["second"])
else:
    endDate = None

if "timeinterval" in general.keys():
    timeInterval = general["timeinterval"]
else:
    timeInterval = 24*60*60

if "visualise" in general.keys():
    visualise = general["visualise"]
else:
    visualise = False

if "starthourrange" in general.keys():
    sr = general["starthourrange"]
    startHourRange = datetime.time(sr["hour"], sr["minute"], sr["second"])
else:
    startHourRange = datetime.time(0,0,0)

if "endhourrange" in general.keys():
    er = general["endhourrange"]
    endHourRange = datetime.time(er["hour"], er["minute"], er["second"])
else:
    endHourRange = datetime.time(23,59,59)

for img in ts.iter_by_timepoints(remove_gaps=False, start=startDate, \
                                    end=endDate, interval=timeInterval ):

    if img is None or img.pixels is None:
        print('Missing Image')
        continue

    rStart = datetime.datetime.combine(img.datetime.date(), startHourRange)
    rEnd = datetime.datetime.combine(img.datetime.date(), endHourRange)
    if img.datetime >= rStart and img.datetime <= rEnd:
        print("Process", img.path, '...'),
        print("Time stamp", img.datetime)
        context["img"] = img
        try:
            result = pl.process(context, [img.pixels], visualise)
        except PCExBrakeInPipeline as bip:
            print(bip.message)
            continue
        print("Done")

# Just an example of how the yaml should look
#pipeline:
#  - - component1
#    - arg1: ---Writing Image---
#      arg2: colorcorrected
#  - - component2
#    - arg1: ---perform tray detection---
#      arg2: Tray_%02d.png
#      arg3: 8
#  - - component3
#    - arg1: ---perform pot detection---
#      arg2: Pot.png
#
#outstreams:
#  - name: colorcorrected
#  - name: segmented
#
#general:
#  startdate: { year: 2014, month: 06, day: 18, hour: 12, minute: 0, second: 0}
#  enddate: {}
#  starthourrange: { hour: 10, minute: 0, second: 0}
#  endhourrange: { hour: 15, minute: 0, second: 0}
#  timeinterval: 86400

