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
tc.py [-s START -e END -I INTERVAL] -i IN -o OUT

OPTIONS:
    -i IN       Input timestream
    -o OUT      Output timestream
    -s START    Start date, in %Y_%m_%d_%H_%M_%S format.
    -e END      End date, in %Y_%m_%d_%H_%M_%S format.
    -I INTERVAL Interval, in seconds
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
        self.log.info('timestream path = %s', self.ts.path)
        self.ts.data["settings"] = self.settings
        self.ts.data["settingPath"] = os.path.dirname(setting_file)
        #create new timestream for output data
        self.ts_out = timestream.TimeStream()
        self.ts_out.create(self.output_path)
        self.ts_out.data["settings"] = self.settings
        self.ts_out.data["settingPath"] = os.path.dirname(setting_file)
        self.ts_out.data["sourcePath"] = self.input_path
        self.log.info("Timestream instance created:")
        try:
            self.start_at = timestream.parse.ts_parse_date(opts['-s'])
        except (ValueError, TypeError):
            self.start_at = self.ts.start_datetime
        try:
            self.end_at = timestream.parse.ts_parse_date(opts['-e'])
        except (ValueError, TypeError):
            self.end_at = self.ts.end_datetime
        try:
            self.interval = int(opts['-I'])
        except (ValueError, TypeError):
            self.interval = self.ts.interval
        for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
            self.log.debug("ts.%s: %r", attr, getattr(self.ts, attr))

    def __call__(self, start=None, end=None, interval=None):
        if start is None:
            start = self.start_at
        if end is None:
            end = self.end_at
        if interval is None:
            interval = self.interval
        img_iter = self.ts.iter_by_timepoints(remove_gaps=False, start=start,
                                              end=end, interval=interval)
        pl = pipeline.ImagePipeline(self.ts.data["settings"])
        for img in img_iter:
            if img is None:
                self.log.info('Missing Image')
            else:
                try:
                    self.log.info("Processing %s", img.path)
                    # set visualise to False to run in batch mode
                    context = {"rts":self.ts, "wts":self.ts_out, "img":img}
                    result = pl.process(context, [img], visualise=False)
                except:
                    self.log.error("DOES NOT COMPUTE %s", img.path)

if __name__ == "__main__":
    pmgr = PipelineManager()
    pmgr()
