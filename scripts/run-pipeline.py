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

import sys
import os
import timestream
import logging
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline
import yaml
import datetime
from docopt import (docopt,DocoptExit)

def genConfig(opts):
    # input timestream directory
    inputRootPath = opts['-i']
    if os.path.isfile(inputRootPath):
        raise DocoptExit("%s is a file. Expected a directory"%inputRootPath)
    if not os.path.exists(inputRootPath):
        raise DocoptExit("%s does not exists"%inputRootPath)

    # Pipeline configuration.
    if opts['-p']:
        plConfPath = opts['-p']
    else:
        plConfPath = os.path.join(inputRootPath, '_data', 'pipeline.yml')
    if not os.path.isfile(plConfPath):
        raise DocoptExit("%s is not a file"%plConfPath)
    plConf = pipeconf.PCFGConfig(plConfPath, 2)
    plConf.addSubSec("plConfPath", plConfPath)
    plConf.addSubSec("inputRootPath", inputRootPath)

    # Timestream configuration
    if opts['-t']:
        tsConfPath = opts['-t']
    else:
        tsConfPath = os.path.join(plConf.inputRootPath, '_data',
                'timestream.yml')
    if not os.path.isfile(tsConfPath):
        raise DocoptExit("%s is not a file"%tsConfPath)
    tsConf = pipeconf.PCFGConfig(tsConfPath, 1)
    tsConf.addSubSec("tsConfPath", tsConfPath)

    # Merge timestream configuration into pipeline.
    if not plConf.hasSubSecName("general"):
        plConf.addSubSec("general", pipeconf.PCFGSection("general"))
    for tsComp in tsConf.listSubSecNames():
        merged = False
        tsss = tsConf.getVal(tsComp)
        for pComp in plConf.pipeline.listSubSecNames():
            plss = plConf.getVal("pipeline."+pComp)
            if plss.name == tsComp:
                # Merge when component has same name
                pipeconf.PCFGConfig.merge(tsss, plss)
                merged = True
                break
        if merged:
            continue
        plConf.general.setVal(tsComp, tsss)

    # Add whatever came in the command line
    if opts['--set']:
        for setelem in opts["--set"].split(','):
            try:
                cName, cVal = setelem.split("=")
                plConf.setVal(cName, cVal)
            except:
                raise DocoptExit("Error in the --set string")

    # There are two output variables:
    # outputPath : Directory where resulting directories will be put
    # outputPrefix : Prefix identifying all outputs from this "run"
    # outputPrefixPath : Convenience var. outputPath/outputPrefix.
    if not plConf.general.hasSubSecName("outputPrefix"):
        plConf.general.setVal("outputPrefix",
                os.path.basename(os.path.abspath(plConf.inputRootPath)))

    if opts['-o']:
        plConf.general.setVal("outputPath", opts['-o'])

        if os.path.isfile(plConf.general.outputPath):
            raise DocoptExit("%s is a file"%plConf.general.outputPath)
        outputPrefixPath = os.path.join (plConf.general.outputPath,
                plConf.general.outputPrefix)
        plConf.general.setVal("outputPrefixPath", outputPrefixPath)
    else:
        plConf.general.setVal("outputPath",
                os.path.dirname(plConf.inputRootPath))
        plConf.general.setVal("outputPrefixPath",
                os.path.join(plConf.general.outputPath,
                    plConf.general.outputPrefix))

    # Modify to usable objects (e.g. dict->datetime)
    sd = None
    if plConf.general.hasSubSecName("startDate"):
        if plConf.general.startDate.size == 6:
            sd = plConf.general.startDate
            sd = datetime.datetime(sd.year, sd.month, sd.day, \
                                   sd.hour, sd.minute, sd.second)
        plConf.general.startDate = sd
    else:
        plConf.general.addSubSec("startDate", None)

    ed = None
    if plConf.general.hasSubSecName("endDate"):
        if plConf.general.endDate.size == 6:
            ed = plConf.general.endDate
            ed = datetime.datetime(ed.year, ed.month, ed.day, \
                                   ed.hour, ed.minute, ed.second)
        plConf.general.endDate = ed
    else:
        plConf.general.addSubSec("endDate", None)

    if not plConf.general.hasSubSecName("timeInterval"):
        plConf.general.addSubSec("timeInterval", None)

    if not plConf.general.hasSubSecName("visualise"):
        plConf.general.addSubSec("visualis", False)

    if plConf.general.hasSubSecName("startHourRange"):
        sr = plConf.general.startHourRange
        plConf.general.startHourRange = \
                datetime.time(sr.hour, sr.minute, sr.second)
    else:
        plConf.general.addSubSec("startHourRange", None)

    if plConf.general.hasSubSecName("endHourRange"):
        er = plConf.general.endHourRange
        plConf.general.endHourRange = \
                datetime.time(er.hour, er.minute, er.second)
    else:
        plConf.general.addSubSec("endHourRange", None)

    return plConf

def createOutputs(plConf):
    if not plConf.hasSubSecName("general") \
            or not plConf.general.hasSubSecName("outputPath"):
        raise DocoptExit("Configuration missing outputPath")
    if not os.path.exists(plConf.general.outputPath):
        os.makedirs(plConf.general.outputPath)

def initlogging(opts):
    # 1. We init verbosity. log to console by default.
    if opts["-v"] == 0 or opts["-v"] == 1:
        vbsty = timestream.LOGV.V
    elif opts["-v"] == 2:
        vbsty = timestream.LOGV.VV
    elif opts["-v"] == 3:
        vbsty = timestream.LOGV.VVV
    if opts["-s"]: # Silent will trump all
        vbsty = timestream.LOGV.S
        return

    outlog = timestream.add_log_handler(verbosity=vbsty)
    if outlog is os.devnull:
        raise DocoptExit("Error setting up output to console")

    if "--logfile" in opts.keys():
        f = opts["--logfile"]
        outlog = timestream.add_log_handler(stream=f, verbosity=vbsty)
        if outlog is os.devnull:
            raise DocoptExit("Error setting log to file {}".format(f))

def genContext(plConf):
    if not plConf.hasSubSecName("outstreams") \
            or not plConf.hasSubSecName("general"):
        raise DocoptExit("Error while generating context")

    # Initialize the context
    ctx = pipeconf.PCFGSection("--")

    #create new timestream for output data
    for k, outstream in plConf.outstreams.asDict().iteritems():
        ts_out = timestream.TimeStream()
        ts_out.data["settings"] = plConf.asDict()
        #ts_out.data["settingPath"] = os.path.dirname(settingFile)
        ts_out.data["sourcePath"] = plConf.inputRootPath
        ts_out.name = outstream["name"]

        # timeseries output input path plus a suffix
        tsoutpath = os.path.abspath(plConf.general.outputPrefixPath) \
                + '-' + outstream["name"]
        if "outpath" in outstream.keys():
            tsoutpath = outstream["outpath"]
        if not os.path.exists(tsoutpath) \
                or len(os.listdir(os.path.join(tsoutpath, '_data'))) == 0:
            ts_out.create(tsoutpath)
        else:
            ts_out.load(tsoutpath)
        ctx.setVal("outts."+outstream["name"], ts_out)

    ctx.setVal("outputPrefixPath", plConf.general.outputPrefixPath)
    ctx.setVal("outputPrefix", plConf.general.outputPrefix)

    return ctx


def genExistingTS(ctx):
    existing_ts = []
    for tsname in ctx.outts.listSubSecNames():
        ts_out = ctx.outts.getVal(tsname)
        existing_ts.append(ts_out.image_data.keys())

    existing_ts = list(set([item for sl in existing_ts for item in sl]))
    return existing_ts

CLI_OPTS = """
USAGE:
    run-pipeline -i IN
                 [-o OUT] [-p YML] [-t YML]
                 [-v | -vv | -vvv | -s] [--logfile=FILE]
                 [--recalculate] [--set=CONFIG]
    run-pipeline (-h | --help)

OPTIONS:
    -h --help   Show this screen.
    -i IN       Input timestream directory
    -o OUT      Output root. Where results will be created.
    -p YML      Path to pipeline yaml configuration. Defaults to
                IN/_data/pipeline.yml
    -t YML      Path to timestream yaml configuration. Defaults to
                IN/_data/timestream.yml
    -v          Level 1 verbosity: Simple process information
    -vv         Level 2 verbosity: same as -v but with timestamps
    -vvv        Level 3 verbosity: for  debugging. Will output file, function
                name, timestamps and additional debuggin information.
    -s          Silent verbosity: Remove all output logging.
    --logfile=FILE   If given, log to FILE with given verbosity.
    --set=CONFIG     Overwrite any configuration value. CONFIG is a coma (,)
                     separated string of name=value pairs.
                     E.g: --set=a.b=value,c.d.e=val2
    --recalculate    By default we don't re-calculate images. Passing this
                     option forces recalculation

"""

#LOG = logging.getLogger("timestreamlib")
def main():
    opts = docopt(CLI_OPTS)

    # logging, re-initialize with user options.
    initlogging(opts)
    LOG = logging.getLogger("timestreamlib")

    # configuration
    plConf = genConfig(opts)
    createOutputs(plConf)
    LOG.info(str(plConf))

    # context
    ctx = genContext(plConf)
    if not ctx.hasSubSecName("outts"):
        raise DocoptExit("Could not identify output timestreams")
    for tsname in ctx.outts.listSubSecNames():
        ts_out = ctx.outts.getVal(tsname)
        LOG.info("Output timestream instance:")
        LOG.info("   ts_out.path: {}".format(ts_out.path))

    # Skiping
    existing_ts = []
    if not opts["--recalculate"]:
        existing_ts = genExistingTS(ctx)
    LOG.info("Skipping time stamps {}".format(existing_ts))

    # initialise input timestream for processing
    ts = timestream.TimeStreamTraverser(
            ts_path=plConf.inputRootPath,
            interval=plConf.general.timeInterval,
            start=plConf.general.startDate,
            end=plConf.general.endDate,
            start_hour=plConf.general.startHourRange,
            end_hour=plConf.general.endHourRange,
            existing_ts=existing_ts,
            err_on_access=True)
    # FIXME: asDict because it cannot be handled by json.
    ts.data["settings"] = plConf.asDict()
    ctx.setVal("ints",ts)
    LOG.info(str(ts))

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
            result = pl.process(ctx, [img], plConf.general.visualise)
        except PCException as bip:
            LOG.info(bip.message)
            continue

        LOG.info("Done")

if __name__ == "__main__":
    main()

