#!/usr/bin/python
#coding=utf-8
# Copyright (C) 2014
# Author(s): Joel Granados <joel.granados@gmail.com>
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

import os
import docopt
import yaml
from timestream import TimeStreamTraverser, TimeStream
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline

def loadConfig(cFile):
    f = file(cFile, "r")
    conf = yaml.load(f)
    f.close()
    return conf

# derandui.py outputs a derandStruct that is different from what the pipeline
# components expects. Here we reconstruct the derandStruct so we can pass it to
# the pipecomponent.
def regenDerandStruct(derandStruct, tsts):
    for mid, midlist in derandStruct.iteritems():
        midlistkeys = midlist.keys()
        for p in midlistkeys:
            newKey = tsts[p]
            derandStruct[mid][newKey] = derandStruct[mid].pop(p)
    return derandStruct

def getTimestamps(tsts):
    timestamps = [] # needed for pipeline execution.
    for i, tspath in tsts.iteritems():
        tst = TimeStreamTraverser(str(tspath))
        if "metas" not in tst.data["settings"]["general"].keys():
            msg = "metas needs to be defined in TS {} settings.".\
                    format(tst.name)
            raise RuntimeError(msg)
        timestamps = timestamps + tst.timestamps
    return timestamps

def derandomize(tsoutpath, derandStruct, timestamps):
    plc = pipeconf.PCFGSection("--")
    plc.setVal("pipeline._0.name", "derandomize")
    plc.setVal("pipeline._0.derandStruct", derandStruct)
    plc.setVal("pipeline._1.name", "imagewrite")
    plc.setVal("pipeline._1.outstream", "outts")

    outts = TimeStream()
    outts.name = "derandomized"
    outts.create(tsoutpath)

    ctx = pipeconf.PCFGSection("--")
    ctx.setVal("outts.outts", outts)

    pl = pipeline.ImagePipeline(plc.pipeline, ctx)

    # 4. Execute pipeline
    for i in range(len(timestamps)):
        ts = timestamps[i]
        try:
            result = pl.process(ctx, [ts], True)
        except Exception as e:
            print("Skipped {}".format(ts))
            continue

CLI_OPTS = """
USAGE:
    derandcl.py -o OUT -c YML

OPTIONS:
    -o OUT      Output directory
    -c YML      Path to derandomization configuration.
"""
def main():
    opts = docopt.docopt(CLI_OPTS)

    outputPath = opts['-o']
    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
    if os.path.isfile(outputPath):
        raise IOError("%s is a file"%outputPath)

    # Configuration.
    confPath = opts["-c"]
    if not os.path.isfile(confPath):
        raise IOError("%s is not a file"%confPath)
    plConf = loadConfig(confPath)

    tsts = plConf[0]
    derandStruct = plConf[1]
    derandStruct = regenDerandStruct(derandStruct, tsts)
    timestamps = getTimestamps(tsts)

    derandomize(outputPath, derandStruct, timestamps)

if __name__ == "__main__":
    main()
