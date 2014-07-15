# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:31:54 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import division, print_function

import os
from itertools import cycle, izip, imap
import logging
import timestream
from timestream import manipulate
import timestream.manipulate.pipeline as pipeline
import yaml
import multiprocessing as mp
import docopt

CLI_OPT = """
USAGE:
tc.py [-s START -e END -I INTERVAL -t THREADS] -i IN -o OUT

OPTIONS:
    -i IN       Input timestream
    -o OUT      Output timestream
    -s START    Start date, in %Y_%m_%d_%H_%M_%S format.
    -e END      End date, in %Y_%m_%d_%H_%M_%S format.
    -I INTERVAL Interval, in seconds
    -t THREADS  Threads.
"""

# initialise input timestream for processing
timestream.setup_module_logging(level=logging.INFO)
manipulate.setup_console_logger()

class PipelineManager(object):
    def __init__(self):
        log = logging.getLogger("CONSOLE")
        opts = docopt.docopt(CLI_OPT)
        self.input_path = opts['-i']
        self.output_path = opts['-o']
        # read global settings for processing
        setting_file = os.path.join(self.input_path, '_data', 'corr.yml')
        ymlfh = open(setting_file)
        self.settings = yaml.load(ymlfh)
        ymlfh.close()
        # create new timestream for output data
        self.ts = timestream.TimeStream()
        self.ts.load(self.input_path)
        log.info('timestream path = %s', self.ts.path)
        self.ts.data["settings"] = self.settings
        self.ts.data["settingPath"] = os.path.dirname(setting_file)
        # create new timestream for output data
        self.ts_out = timestream.TimeStream()
        self.ts_out.create(self.output_path)
        self.ts_out.data["settings"] = self.settings
        self.ts_out.data["settingPath"] = os.path.dirname(setting_file)
        self.ts_out.data["sourcePath"] = self.input_path
        log.debug("Timestream instance created:")
        for attr in timestream.parse.validate.TS_MANIFEST_KEYS:
            log.debug("ts.%s: %r", attr, getattr(self.ts, attr))

def call_pipeline((self, img)):
    pl = pipeline.ImagePipeline(self.ts.data["settings"])
    log = logging.getLogger("CONSOLE")
    if img is None:
        log.info('Missing Image')
    else:
        try:
            log.info("Processing %s", img.path)
            # set visualise to False to run in batch mode
            context = {"rts":self.ts, "wts":self.ts_out, "img":img}
            # result = process() removed as we don't use result yet
            pl.process(context, [img], visualise=False)
        except:
            log.error("DOES NOT COMPUTE %s", img.path)

if __name__ == "__main__":
    pmgr = PipelineManager()
    opts = docopt.docopt(CLI_OPT)
    try:
        start_at = timestream.parse.ts_parse_date(opts['-s'])
    except (ValueError, TypeError):
        start_at = pmgr.ts.start_datetime
    try:
        end_at = timestream.parse.ts_parse_date(opts['-e'])
    except (ValueError, TypeError):
        end_at = pmgr.ts.end_datetime
    try:
        interval = int(opts['-I'])
    except (ValueError, TypeError):
        interval = pmgr.ts.interval * 60
    img_iter = pmgr.ts.iter_by_timepoints(remove_gaps=False, start=start_at,
                                          end=end_at, interval=interval)
    pool = mp.Pool(12)
    count = 0
    call_stack = izip(cycle([pmgr,]), img_iter)
    for _ in pool.imap(call_pipeline, call_stack):
        print("processed", count, end="\r")
    pool.close()
    pool.join()
