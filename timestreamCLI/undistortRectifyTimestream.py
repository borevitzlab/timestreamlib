# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:31:54 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import division, print_function

import sys, os
import logging
import timestream
from timestream import manipulate
import timestream.manipulate.pipeline as pipeline
import yaml

import docopt

CLI_OPT = """
USAGE:
tc.py -i IN -o OUT

OPTIONS:
    -i IN   Input timestream
    -o OUT  Output timestream
"""

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
manipulate.setup_console_logger()

class PipelineManager(object):
    def __init__(self):
        opts = docopt.docopt(CLI_OPT)
        self.input_path = opts['-i']
        self.output_path = opts['-o']
        self.log = logging.getLogger("CONSOLE")
        # read global settings for processing
        setting_file = os.path.join(self.input_path, '_data', 'pipeline.yml')
        with open(setting_file) as ymlfh:
            self.settings = yaml.load(ymlfh)
        #create new timestream for output data
        self.ts = timestream.TimeStream()
        self.ts.load(self.input_path)
        self.log.info('timestream path = ', self.ts.path)
        self.ts.data["settings"] = settings
        self.ts.data["settingPath"] = os.path.dirname(setting_file)
        #create new timestream for output data
        self.ts_out = timestream.TimeStream()
        self.ts_out.create(outputRootPath)
        self.ts_out.data["settings"] = settings
        self.ts_out.data["settingPath"] = os.path.dirname(setting_file)
        self.ts_out.data["sourcePath"] = self.input_path
        self.log.info("Timestream instance created:")
        for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
            self.log.debug("ts.%s:" % attr, getattr(self.ts, attr))
        self.pl = pipeline.ImagePipeline(self.ts.data["settings"])

    def __run__(self, start=None, end=None, interval=None):
        if start is None:
            start = self.ts.start_datetime
        if end is None:
            end = self.ts.end_datetime
        if interval is None:
            interval = self.ts.interval
        img_iter = self.ts.iter_by_timepoints(remove_gaps=False, start=start,
                                              end=end, interval=interval)
        for img in img_iter:
            if img is None:
                self.log.info('Missing Image at', img.path)
            else:
                self.log.info("Processing", img.path)
                # set visualise to False to run in batch mode
                context = {"rts":ts, "wts":ts_out, "img":img}
                result = pl.process(context, [img], True)

if __name__ == "__main__":
    pmgr = PipelineManager()
    pmgr()
