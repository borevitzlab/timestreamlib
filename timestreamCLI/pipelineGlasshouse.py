# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 16:36:05 2014

@author: chuong nguyen
"""
from __future__ import absolute_import, division, print_function

import csv
import glob
import docopt
import sys, os
import timestream
import logging
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline
from timestream.manipulate.pipecomponents import PCExBrakeInPipeline
import yaml
import datetime

#def getColumnCVS(FileCVS, columnID):
#    if len(FileCVS) == 0:
#        print('File name is empty')
#        return []
#    column = []
#    with open(FileCVS, 'rb') as csvfile:
#        fp = csv.reader(csvfile, delimiter=',')
#        for i,row in enumerate(fp):
#            if i == 0: # header
#                print(', '.join(row))
#            else:
#                column.append(row[columnID])
#    return column

#PlantListCSV = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0038/_data/BVZ0038-WheatDroughtTrial-Labels.csv'
#ExpFolder = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0038/_data/BVZ0038-PlantTS'
##ExpFolder = '/home/chuong/Data/BVZ0038-PlantTS'
#plantList = getColumnCVS(PlantListCSV, 2)
#print(plantList)
#
#TSFolderList = glob.glob(os.path.join(ExpFolder, '*'))
#for TSFolder in TSFolderList:
#    print(TSFolder)
#    ts =
#    break

CLI_OPTS = """
USAGE:
    pipelineGlasshouse.py -i IN [-o OUT] [-v VIEW] [-p YML] [-t YML] [--set=CONFIG]

OPTIONS:
    -i IN       Input timestream directory
    -o OUT      Output directory
    -v VIEW     View either SIDE or TOP
    -p YML      Path to pipeline yaml configuration. Defaults to
                IN/_data/pipeline.yml
    -t YML      Path to timestream yaml configuration. Defaults to
                IN/_data/timestream.yml

    --set=CONFIG        Overwrite any configuration value. CONFIG is
                        a coma (,) separated string of name=value
                        pairs. E.g: --set=a.b=value,c.d.e=val2,...
"""
opts = docopt.docopt(CLI_OPTS)

view = 'SIDE' # 'TOP'
if opts['-v']:
    view = opts['-v'].upper()
    if view not in ['SIDE', 'TOP']:
        raise IOError("-v option has to be SIDE or TOP")

inputRootPath = opts['-i']
print('inputRootPath=', inputRootPath)
if os.path.isfile(inputRootPath):
    raise IOError("%s is a file. Expected a directory"%inputRootPath)
if not os.path.exists(inputRootPath):
    raise IOError("%s does not exists"%inputRootPath)
InTSFolderList = glob.glob(os.path.join(inputRootPath, '*' + view + '*'))
print("Input timestreams: ", InTSFolderList)

if opts['-o']:
    outputRootPath = opts['-o']

    if not os.path.exists(outputRootPath):
        os.makedirs(outputRootPath)
    if os.path.isfile(outputRootPath):
        raise IOError("%s is a file"%outputRootPath)
else:
    outputRootPath = inputRootPath
print('outputRootPath=', outputRootPath)

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
    tmpPath = os.path.join(inputRootPath, '_data', 'timestream_{}.yml'.format(view))
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

# Add whatever came in the command line
if opts['--set']:
    for setelem in opts["--set"].split(','):
        #FIXME: print help if any exceptions.
        cName, cVal = setelem.split("=")
        plConf.setVal(cName, cVal)

# Show the user the resulting configuration:
print(plConf)

if plConf.general.hasSubSecName("visualise"):
    visualise = plConf.general.visualise
else:
    visualise = False

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
TSList = []
for InTSFolder in InTSFolderList:
    ts = timestream.TimeStream()
    ts.load(InTSFolder)
    # FIXME: ts.data cannot have plConf because it cannot be handled by json.
    ts.data["settings"] = plConf.asDict()
    #FIXME: TimeStream should have a __str__ method.
    print("Timestream instance loaded:")
    print("   ts.path:", ts.path)
    for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
        print("   ts.%s:" % attr, getattr(ts, attr))
#    TSList.append(ts)

    # Initialize the context
    ctx = pipeconf.PCFGSection("--")
    ctx.setVal("ints",ts)

    #create new timestream for output data
    existing_timestamps = []
    for k, outstream in plConf.outstreams.asDict().iteritems():
        ts_out = timestream.TimeStream()
        ts_out.data["settings"] = plConf.asDict()
        #ts_out.data["settingPath"] = os.path.dirname(settingFile)
        ts_out.data["sourcePath"] = InTSFolder
        ts_out.name = outstream["name"]

        # timeseries output input path plus a suffix
        tsoutpath = os.path.join(os.path.abspath(outputRootPath), os.path.basename(InTSFolder) + '-' + outstream["name"])
        print(tsoutpath)
        if "outpath" in outstream.keys():
            tsoutpath = outstream["outpath"]

        if not os.path.exists(tsoutpath) or len(os.listdir(os.path.join(tsoutpath, '_data'))) == 0:
            if not os.path.exists(tsoutpath) :
                os.makedirs(tsoutpath)
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
        #context[outstream["name"]] = ts_out

    # get ignored list as intersection of all time stamp lists
    for i,timestamps in enumerate(existing_timestamps):
        if i == 0:
            ts_set = set(timestamps)
        else:
            ts_set = ts_set & set(timestamps)
    # set this to [] if want to process everything again
    ignored_timestamps = list(ts_set)
    print('ignored_timestamps = ', ignored_timestamps)

    # We put everything else that is not an time series into outputroot.
    ctx.setVal("outputroot", os.path.abspath(outputRootPath) + '-results')

    if not os.path.exists(ctx.outputroot):
        os.mkdir(ctx.outputroot)

    # Dictionary where we put all values that should be added with an image as soon
    # as it is output with the TimeStream
    ctx.setVal("outputwithimage", {})

    # initialise processing pipeline
    pl = pipeline.ImagePipeline(plConf.pipeline, ctx)

#    for img in ts.iter_by_files():
    for img in ts.iter_by_files(ignored_timestamps):

        if len(img.pixels) == 0:
            print('Missing image at {}'.format(img.datetime))
            continue

        # Detach img from timestream. We don't need it!
        img.parent_timestream = None
        print("Process", img.path, '...'),
        print("Time stamp", img.datetime)
        ctx.setVal("origImg", img)
        try:
            result = pl.process(ctx, [img], visualise)
        except PCExBrakeInPipeline as bip:
            print(bip.message)
            continue
        print("Done")
