# -*- coding: utf-8 -*-
"""
Created on Mon Jul 28 17:49:08 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import absolute_import, division, print_function

import cv2
import logging
import timestream
import numpy as np
from timestream.parse import ts_parse_date
import docopt
import datetime
import os

CLI_OPTS = """
USAGE:
    playtTimestream.py -i IN [-d DELAY] [--int INTERVAL] [-s START] [-e END] [--sh STARTHOUR] [--eh ENDHOUR] [-o OUT]

OPTIONS:
    -i IN          Input timestream directory
    -d DELAY       Playing time delay [500 msecs]
    --int INTERVAL Looping time interval [24*60*60 mins]
    -s START       Start date and time of looping
    -e END         End  date and time of looping
    --sh STARTHOUR Start time range of looping
    --eh ENDHOUR   End time range of looping
    -o OUT         Outputfolder
"""
opts = docopt.docopt(CLI_OPTS)

interval = 24*60*60 #None
start = None
end = None
start_hour = None
end_hour = None
delay = 500
inputRootPath = opts['-i']
if opts['-d']:
    delay = int(opts['-d'])
if opts['--int']:
    interval = int(opts['-int'])
if opts['-s']:
    start = ts_parse_date(opts['-s'])
if opts['-e']:
    end = ts_parse_date(opts['-e'])
if opts['--sh']:
    start_hour = datetime.time(int(opts['--sh']), 0, 0)
if opts['--eh']:
    end_end = datetime.time(int(opts['--eh']), 0, 0)
if opts['-o']:
    outputRootPath = opts['-o']
else:
    outputRootPath = None

timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()
ts.load(inputRootPath)

windowName = 'image'
cv2.imshow(windowName, np.zeros([100,100], dtype = np.uint8))
cv2.moveWindow(windowName, 10,10)
for img in ts.iter_by_timepoints(start=start, end=end, interval = interval,
                                 start_hour = start_hour, end_hour = end_hour):
    if img is None or img.pixels is None:
        continue

    if outputRootPath:
        if not os.path.exists(outputRootPath):
            os.makedirs(outputRootPath)
        cv2.imwrite(os.path.join(outputRootPath, os.path.basename(img.path)), img.pixels)

    # estimate a downscale factor to make image fit into a normal HD screen
    scale = img.pixels.shape[0]//1000 + 1
    imgResized = cv2.resize(img.pixels, (img.pixels.shape[1]//scale, img.pixels.shape[0]//scale))
    timestamp = timestream.parse.ts_format_date(img.datetime)
    cv2.putText(imgResized, timestamp, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), thickness = 1)
    cv2.imshow(windowName, imgResized[:,:,::-1])
    k = cv2.waitKey(delay)
    if k == 1048603:
        # escape key is pressed
        break
cv2.destroyAllWindows()