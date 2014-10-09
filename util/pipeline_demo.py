#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2014
# Author(s): Chuong Nguyen <chuong.v.nguyen@gmail.com>
#            Joel Granados <joel.granados@gmail.com>
#            Kevin Murray <kevin@kdmurray.id.au>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

timestream.setup_module_logging(level=logging.INFO)
LOG = logging.getLogger("timestreamlib")

CLI_OPTS = """
USAGE:
    pipeline_demo.py -i IN [-o OUT] [-p YML] [-t YML] [--set=CONFIG]
    pipeline_demo.py (-h | --help)

OPTIONS:
    -h --help   Show this screen.
    -i IN       Input timestream directory
    -o OUT      Output root. Where results will be created.
    -p YML      Path to pipeline yaml configuration. Defaults to
                IN/_data/pipeline.yml
    -t YML      Path to timestream yaml configuration. Defaults to
                IN/_data/timestream.yml

    --set=CONFIG        Overwrite any configuration value. CONFIG is
                        a coma (,) separated string of name=value
                        pairs. E.g: --set=a.b=value,c.d.e=val2,...
"""
opts = docopt.docopt(CLI_OPTS)

inputRootPath = opts['-i']
if os.path.isfile(inputRootPath):
    raise IOError("%s is a file. Expected a directory"%inputRootPath)
if not os.path.exists(inputRootPath):
    raise IOError("%s does not exists"%inputRootPath)

# Pipeline configuration.
if opts['-p']:
    tmpPath = opts['-p']
else:
    tmpPath = os.path.join(inputRootPath, '_data', 'pipeline.yml')
if not os.path.isfile(tmpPath):
    raise IOError("%s is not a file"%tmpPath)
plConf = pipeconf.PCFGConfig(tmpPath, 2)
plConf.configFile = tmpPath

# Timestream configuration
if opts['-t']:
    tmpPath = opts['-t']
else:
    tmpPath = os.path.join(inputRootPath, '_data', 'timestream.yml')
if not os.path.isfile(tmpPath):
    raise IOError("%s is not a file"%tmpPath)
tsConf = pipeconf.PCFGConfig(tmpPath, 1)

# Merge timestream configuration into pipeline.
for tsComp in tsConf.listSubSecNames():
    merged = False
    tsss = tsConf.getVal(tsComp)
    for pComp in plConf.pipeline.listSubSecNames():
        plss = plConf.getVal("pipeline."+pComp)
        if plss.name == tsComp:
            # Merge if we find a pipeline component with the same name.
            pipeconf.PCFGConfig.merge(tsss, plss)
            merged = True
            break
    if merged:
        continue
    plConf.general.setVal(tsComp, tsss)

# Add whatever came in the command line
if opts['--set']:
    for setelem in opts["--set"].split(','):
        #FIXME: print help if any exceptions.
        cName, cVal = setelem.split("=")
        plConf.setVal(cName, cVal)

# There are two output variables:
# outputPath : Directory where resulting directories will be put
# outputPathPrefix : Convenience var. outputPath/outputPrefix.
#                    Where outputPrefix will identify all the outputs from
#                    this run in that directory.
if not plConf.general.hasSubSecName("outputPrefix"):
    plConf.general.setVal("outputPrefix",
            os.path.basename(os.path.abspath(inputRootPath)))

if opts['-o']:
    plConf.general.setVal("outputPath", opts['-o'])

    if os.path.isfile(plConf.general.outputPath):
        raise IOError("%s is a file"%plConf.general.outputPath)
    if not os.path.exists(plConf.general.outputPath):
        os.makedirs(plConf.general.outputPath)
    outputPathPrefix = os.path.join (plConf.general.outputPath,
            plConf.general.outputPrefix)
    plConf.general.setVal("outputPathPrefix", outputPathPrefix)
else:
    plConf.general.setVal("outputPath",os.path.dirname(inputRootPath))
    plConf.general.setVal("outputPathPrefix",
            os.path.join(plConf.general.outputPath,
                plConf.general.outputPrefix))

# Show the user the resulting configuration:
print(plConf)

# initialise input timestream for processing
ts = timestream.TimeStream()
ts.load(inputRootPath)
# FIXME: ts.data cannot have plConf because it cannot be handled by json.
ts.data["settings"] = plConf.asDict()
print(ts)

# Initialize the context
ctx = pipeconf.PCFGSection("--")
ctx.setVal("ints",ts)

#create new timestream for output data
existing_timestamps = []
for k, outstream in plConf.outstreams.asDict().iteritems():
    ts_out = timestream.TimeStream()
    ts_out.data["settings"] = plConf.asDict()
    #ts_out.data["settingPath"] = os.path.dirname(settingFile)
    ts_out.data["sourcePath"] = inputRootPath
    ts_out.name = outstream["name"]

    # timeseries output input path plus a suffix
    tsoutpath = os.path.abspath(plConf.general.outputPathPrefix) \
            + '-' + outstream["name"]
    print(tsoutpath)
    if "outpath" in outstream.keys():
        tsoutpath = outstream["outpath"]
    if not os.path.exists(tsoutpath) \
            or len(os.listdir(os.path.join(tsoutpath, '_data'))) == 0:
        ts_out.create(tsoutpath)
        print("Timestream instance created:")
        print("   ts_out.path:", ts_out.path)
        existing_timestamps.append([])
    else:
        ts_out.load(tsoutpath)
        print("Timestream instance loaded:")
        print("   ts_out.path:", ts_out.path)
        existing_timestamps.append(ts_out.image_data.keys())
    ctx.setVal("outts."+outstream["name"], ts_out)

# get ignored list as intersection of all time stamp lists
for i,timestamps in enumerate(existing_timestamps):
    if i == 0:
        ts_set = set(timestamps)
    else:
        ts_set = ts_set & set(timestamps)
# set this to [] if want to process everything again
ignored_timestamps = list(ts_set)
print('ignored_timestamps = ', ignored_timestamps)

ctx.setVal("outputPathPrefix", plConf.general.outputPathPrefix)
ctx.setVal("outputPrefix", plConf.general.outputPrefix)

# initialise processing pipeline
pl = pipeline.ImagePipeline(plConf.pipeline, ctx)

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
    timeInterval = None #24*60*60

if plConf.general.hasSubSecName("visualise"):
    visualise = plConf.general.visualise
else:
    visualise = False

if plConf.general.hasSubSecName("startHourRange"):
    sr = plConf.general.startHourRange
    startHourRange = datetime.time(sr.hour, sr.minute, sr.second)
else:
    startHourRange = None #datetime.time(0,0,0)

if plConf.general.hasSubSecName("endHourRange"):
    er = plConf.general.endHourRange
    endHourRange = datetime.time(er.hour, er.minute, er.second)
else:
    endHourRange = None #datetime.time(23,59,59)

for img in ts.iter_by_timepoints(remove_gaps=False, start=startDate,
                                 end=endDate, interval=timeInterval,
                                 start_hour = startHourRange, end_hour = endHourRange,
                                 ignored_timestamps = ignored_timestamps):

    if len(img.pixels) == 0:
        LOG.info('Missing image at {}'.format(img.datetime))
        continue

    # Detach img from timestream. We don't need it!
    img.parent_timestream = None
    LOG.info("Process {} ...".format(img.path))
    LOG.info("Time stamp {}".format(img.datetime))
    ctx.setVal("origImg", img)
    try:
        result = pl.process(ctx, [img], visualise)
    except PCExBrakeInPipeline as bip:
        LOG.info(bip.message)
        continue
    LOG.info("Done")

# Example of the 2 yaml configuration files:
#
####### Timestream Configuration File: #######
#undistort:
#  cameraMatrix:
#  - [4234.949389, 0.0, 2591.5]
#  - [0.0, 4234.949389, 1727.5]
#  - [0.0, 0.0, 1.0]
#  distortCoefs: [-0.166191, 0.142034, 0.0, 0.0, 0.0]
#  imageSize: [5184, 3456]
#  rotationAngle: 180
#colorcarddetect:
#  colorcardFile: CapturedColorcard.png
#  colorcardPosition: [2692.3015027273236, 1573.2581105092597]
#  colorcardTrueColors:
#  - [115.0, 196.0, 91.0, 94.0, 129.0, 98.0, 223.0, 58.0, 194.0, 93.0, 162.0, 229.0,
#    49.0, 77.0, 173.0, 241.0, 190.0, 0.0, 242.0, 203.0, 162.0, 120.0, 84.0, 50.0]
#  - [83.0, 147.0, 122.0, 108.0, 128.0, 190.0, 124.0, 92.0, 82.0, 60.0, 190.0, 158.0,
#    66.0, 153.0, 57.0, 201.0, 85.0, 135.0, 243.0, 203.0, 163.0, 120.0, 84.0, 50.0]
#  - [68.0, 127.0, 155.0, 66.0, 176.0, 168.0, 47.0, 174.0, 96.0, 103.0, 62.0, 41.0,
#    147.0, 71.0, 60.0, 25.0, 150.0, 166.0, 245.0, 204.0, 162.0, 120.0, 84.0, 52.0]
#  settingPath: _data
#traydetect:
#  settingPath: _data
#  trayFiles: Tray_%02d.png
#  trayNumber: 8
#  trayPositions:
#  - [818.0761402657033, 2462.1591636537523]
#  - [1970.4242733553706, 2467.2637865082843]
#  - [3117.65419882686, 2462.3500598446635]
#  - [4269.311435725616, 2418.3133608083576]
#  - [799.9851021748162, 1045.3911201462004]
#  - [1967.556065737193, 1024.2273934825796]
#  - [3133.567925490481, 1028.7864972916682]
#  - [4311.802615716479, 1009.5636668189586]
####### Timestream Configuration File: #######
#
####### Pipeline Configuration File: #######
#pipeline:
#- name: undistort
#  mess: '---Perform optical undistortion---'
#- name: colorcarddetect
#  mess: '---Perform color card detection---'
#- name: colorcorrect
#  mess: '---Perform color correction---'
#
#outstreams:
#  - { name: segg }
#  - { name: corr }
#
#general:
#  startDate: { year: 2014, month: 06, day: 03, hour: 9, minute: 0, second: 0}
#  enddate: { year : 2014, month : 06, day : 20, hour : 12, minute : 00, second : 00}
#  startHourRange: { hour: 9, minute: 0, second: 0}
#  endHourRange: { hour: 15, minute: 0, second: 0}
#  timeInterval: 900
#  visualise: False
####### Pipeline Configuration File: #######

