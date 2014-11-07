#!/usr/bin/env python
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

from timestream.manipulate import PCException

import docopt
import sys
import os
import timestream
import logging
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline
import yaml
import datetime

# We log to console by default
timestream.add_log_handler(verbosity=timestream.LOGV.V)
LOG = logging.getLogger("timestreamlib")

CLI_OPTS = """
USAGE:
    run-pipeline -i IN [-o OUT] [-p YML] [-t YML] [--set=CONFIG] [--recalculate]
    run-pipeline (-h | --help)

OPTIONS:
    -h --help   Show this screen.
    -i IN       Input timestream directory
    -o OUT      Output root. Where results will be created.
    -p YML      Path to pipeline yaml configuration. Defaults to
                IN/_data/pipeline.yml
    -t YML      Path to timestream yaml configuration. Defaults to
                IN/_data/timestream.yml
    --set=CONFIG    Overwrite any configuration value. CONFIG is a coma (,)
                    separated string of name=value pairs.
                    E.g: --set=a.b=value,c.d.e=val2
    --recalculate   By default we don't re-calculate images. Passing this option
                    forces recalculation
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

# Initialize the context
ctx = pipeconf.PCFGSection("--")

#create new timestream for output data
existing_ts = []
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
    else:
        ts_out.load(tsoutpath)
        print("Timestream instance loaded:")
        print("   ts_out.path:", ts_out.path)
        existing_ts.append(ts_out.image_data.keys())
    ctx.setVal("outts."+outstream["name"], ts_out)

if not opts["--recalculate"]:
    # Remove repeated timestamps and flatten list
    existing_ts = list(set([item for sl in existing_ts for item in sl]))
else:
    existing_ts = []
print('existing_timestamps = ', existing_ts)

ctx.setVal("outputPathPrefix", plConf.general.outputPathPrefix)
ctx.setVal("outputPrefix", plConf.general.outputPrefix)

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

# initialise input timestream for processing
ts = timestream.TimeStreamTraverser(ts_path=inputRootPath,
        interval=timeInterval, start=startDate, end=endDate,
        start_hour = startHourRange, end_hour=endHourRange,
        existing_ts=existing_ts, err_on_access=True)
#ts.load(inputRootPath)
# FIXME: ts.data cannot have plConf because it cannot be handled by json.
ts.data["settings"] = plConf.asDict()
ctx.setVal("ints",ts)
print(ts)

# initialise processing pipeline
pl = pipeline.ImagePipeline(plConf.pipeline, ctx)

for timestamp in ts.timestamps:

    try:
        img = ts.getImgByTimeStamp(timestamp, update_index=True)
        # Detach img from timestream. We don't need it!
        img.parent_timestream = None
        LOG.info("Process {} ...".format(img.path))
    except PCException as pcex:
        # Propagate PCException to components.
        img = pcex

    try:
        result = pl.process(ctx, [img], visualise)
    except PCException as bip:
        LOG.info(bip.message)
        continue

    LOG.info("Done")

