# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:31:54 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import absolute_import, division, print_function

import docopt
import sys, os
import timestream
import logging
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline
from timestream.manipulate.pipecomponents import PCExBrakeInPipeline
import yaml
import datetime

CLI_OPTS = """
USAGE:
    pipeline_demo.py -i IN [-o OUT] [-p YML] [-t YML]

OPTIONS:
    -i IN       Input timestream directory
    -o OUT      Output directory
    -p YML      Path to pipeline yaml configuration. Defaults to
                IN/_data/pipeline.yml
    -t YML      Path to timestream yaml configuration. Defaults to
                IN/_data/timestream.yml
"""
opts = docopt.docopt(CLI_OPTS)

inputRootPath = opts['-i']
if os.path.isfile(inputRootPath):
    raise IOError("%s is a file. Expected a directory"%inputRootPath)
if not os.path.exists(inputRootPath):
    raise IOError("%s does not exists"%inputRootPath)

if opts['-o']:
    outputRootPath = opts['-o']

    if not os.path.exists(outputRootPath):
        os.makedirs(outputRootPath)
    if os.path.isfile(outputRootPath):
        raise IOError("%s is a file"%outputRootPath)
    outputRootPath = os.path.join (outputRootPath, \
            os.path.basename(os.path.abspath(inputRootPath)))
else:
    outputRootPath = inputRootPath

# Pipeline configuration.
if opts['-p']:
    tmpPath = opts['-p']
else:
    tmpPath = os.path.join(inputRootPath, '_data', 'pipeline.yml')
if not os.path.isfile(tmpPath):
    raise IOError("%s is not a file"%tmpPath)
plConf = pipeconf.PCFGConfig(tmpPath, 2)

# Timestream configuration
if opts['-t']:
    tmpPath = opts['-t']
else:
    tmpPath = os.path.join(inputRootPath, '_data', 'timestream.yml')
if not os.path.isfile(tmpPath):
    raise IOError("%s is not a file"%tmpPath)
tsConf = pipeconf.PCFGConfig(tmpPath, 1)

# Merge the two configurations
for pComp in plConf.pipeline.listSubSecNames():
    # get a PipLine SubSection
    plss = plConf.getVal("pipeline."+pComp)

    try:
        # get TimeStream SubSection
        tsss = tsConf.getVal(plss.name)
    except pipeconf.PCFGExInvalidSubsection:
        # No additional configuration in tsConf for "pipeline."+pComp
        continue

    # Merge timestream conf onto pipeline conf
    pipeconf.PCFGConfig.merge(tsss, plss)

# Show the user the resulting configuration:
print(plConf)

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()

ts.load(inputRootPath)
# FIXME: ts.data does not have the configuration instance because it cannot be
# handled by json.
ts.data["settings"] = plConf.asDict()
#ts.data["settingPath"] = os.path.dirname(settingFile)
context = {"rts":ts}
#FIXME: TimeStream should have a __str__ method.
print("Timestream instance created:")
print("   ts.path:", ts.path)
for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
    print("   ts.%s:" % attr, getattr(ts, attr))

#create new timestream for output data
for k, outstream in plConf.outstreams.asDict().iteritems():
    ts_out = timestream.TimeStream()
    ts_out.data["settings"] = plConf.asDict()
    #ts_out.data["settingPath"] = os.path.dirname(settingFile)
    ts_out.data["sourcePath"] = inputRootPath
    ts_out.name = outstream["name"]

    # timeseries output input path plus a suffix
    tsoutpath = os.path.abspath(outputRootPath) + '-' + outstream["name"]
    if "outpath" in outstream.keys():
        tsoutpath = outstream["outpath"]
    if not os.path.exists(os.path.dirname(tsoutpath)):
        os.mkdir(os.path.dirname(tsoutpath))
    ts_out.create(tsoutpath)
    context[outstream["name"]] = ts_out

# We put everything else that is not an time series into outputroot.
context["outputroot"] = os.path.abspath(outputRootPath) + '-results'
if not os.path.exists(context["outputroot"]):
    os.mkdir(context["outputroot"])

# Dictionary where we put all values that should be added with an image as soon
# as it is output with the TimeStream
context["outputwithimage"] = {}

# initialise processing pipeline
pl = pipeline.ImagePipeline(plConf.pipeline, context)

if plConf.general.hasSubSecName("startDate"):
    sd = plConf.general.startDate
    if sd.size == 6:
        startDate = datetime.datetime(sd.year, sd.month, sd.day, \
                                    sd.hour, sd.minute, sd.second)
    else:
        startDate = None
else:
    startDate = None

if plConf.general.hasSubSecName("enDdate"):
    ed = plConf.general.enDdate
    if ed.size == 6:
        endDate = datetime.datetime(ed.year, ed.month, ed.day, \
                                ed.hour, ed.minute, ed.second)
    else:
        endDate = None
else:
    endDate = None

if plConf.general.hasSubSecName("timeInterval"):
    timeInterval = plConf.general.timeInterval
else:
    timeInterval = 24*60*60

if plConf.general.hasSubSecName("visualise"):
    visualise = plConf.general.visualise
else:
    visualise = False

if plConf.general.hasSubSecName("startHourRange"):
    sr = plConf.general.startHourRange
    startHourRange = datetime.time(sr.hour, sr.minute, sr.second)
else:
    startHourRange = datetime.time(0,0,0)

if plConf.general.hasSubSecName("endHourRange"):
    er = plConf.general.endHourRange
    endHourRange = datetime.time(er.hour, er.minute, er.second)
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
#  startDate: { year: 2014, month: 06, day: 18, hour: 12, minute: 0, second: 0}
#  endDate: {}
#  startHourRange: { hour: 10, minute: 0, second: 0}
#  endHourRange: { hour: 15, minute: 0, second: 0}
#  timeInterval: 86400

