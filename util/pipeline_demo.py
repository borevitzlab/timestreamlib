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
    inputRootPath  = '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-orig/'
    outputRootPath = '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-processed'
    visualise = True
else:
    inputRootPath = sys.argv[1]
    outputRootPath = sys.argv[2]
    visualise = True
    if sys.argv[3] == "false":
        visualise = False

# read global settings for processing
settingFile = os.path.join(inputRootPath, '_data', 'pipeline.yml')
f = file(os.path.join(inputRootPath, '_data', 'pipeline.yml'))
yfile = yaml.load(f)
f.close()
settings = yfile["pipeline"]
outstreams = yfile["outstreams"]

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
    ts_out.create(outstream["outpath"])
    ts_out.data["settings"] = settings
    ts_out.data["settingPath"] = os.path.dirname(settingFile)
    ts_out.data["sourcePath"] = inputRootPath
    context[outstream["name"]] = ts_out

# initialise processing pipeline
# TODO: context could be part of initialising input here
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
        context["img"] = img
        result = pl.process(context, [img.pixels], visualise)
        print("Done")

# Just an example of how the yaml should look
#pipeline:
#  - - imagewrite
#    - mess: ---Writing Image---
#      outstream: colorcorrected
#  - - traydetect
#    - mess: ---perform tray detection---
#      trayFiles: Tray_%02d.png
#      trayNumber: 8
#  - - potdetect
#    - mess: ---perform pot detection---
#      potFile: Pot.png
#
#outstreams:
#  - name: colorcorrected
#    outpath: /Path/colorcorrected
#  - name: segmented
#    outpath: /Path/segmented
