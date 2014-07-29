# -*- coding: utf-8 -*-
"""
Created on Mon Jul 28 17:49:08 2014

@author: chuong nguyen, chuong.v.nguyen@gmail.com
"""
from __future__ import absolute_import, division, print_function

import cv2
import logging
import timestream
import sys
import numpy as np

interval = 24*60*60 #None
start = None
end = None
delay = 500
if len(sys.argv) < 2:
    inputRootPath = '/home/chuong/Data/phenocam/a_data/TimeStreams/Borevitz/BVZ0018/BVZ0018-GC05B-C01~fullres-unr'
else:
    try:
        inputRootPath = sys.argv[1]
        delay = int(sys.argv[2])
        interval = sys.argv[3]
        start = sys.argv[4]
        end = sys.argv[5]
    except:
        pass
    
timestream.setup_module_logging(level=logging.INFO)
ts = timestream.TimeStream()
ts.load(inputRootPath)

windowName = 'image'
cv2.imshow(windowName, np.zeros([100,100], dtype = np.uint8))
cv2.moveWindow(windowName, 10,10)
for img in ts.iter_by_timepoints(start=start, end=end, interval = interval):
    if img is None or img.pixels is None:
        continue
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