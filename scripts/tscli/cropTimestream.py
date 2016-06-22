#!/usr/bin/python
import docopt
from itertools import (
        cycle,
        izip,
        )
import multiprocessing as mp
import os
from os import path
import cv2
import sys
from timestream.parse import iter_timestream_images

CLI = """
USAGE:
cropTS [-t THREADS] -i IN_TIMESTREAM -o OUT_TIMESTREAM (-b XYZY | -r XYWH)

OPTIONS:
    -i IN_TIMESTREAM    Input timestream
    -o OUT_TIMESTREAM   Output timestream
    -b XYXY             Ouput bounding box, as "XxY,XxY", being the X & Y
                        coordinates for the top-left and bottom right of the
                        bounding box.
    -r XYWH             Ouput bounding box, as "XxY,WxH", being the X & Y
                        coordinates for the top-left pixel and the width and
                        height of the bounding box.
    -t THREADS          Number of concurrent worker processes.
"""

def crop_image(src, dest, coords=(0, 0, 1, 1), ext="JPEG"):
    img = cv2.imread(src)
    x1, y1, x2, y2 = coords
    cv2.imwrite(dest, img[y1:y2, x1:x2])

def process_image((img, out_ts, xy)):
    sys.stderr.write(".")
    sys.stderr.flush()
    split = path.basename(img).split('_')[1:]
    dest = path.join(
            out_ts,
            split[0],
            "_".join(split[0:2]),
            "_".join(split[0:3]),
            "_".join(split[0:4]),
            path.basename(out_ts) + "_" + "_".join(split),
            )
    if not path.exists(path.dirname(dest)):
        try:
            os.makedirs(path.dirname(dest))
        except IOError as e:
            if not path.exists(path.dirname(dest)):
                raise e
    resize_image(img, dest, xy)

def main(opts):
    pool = mp.Pool()
    if opts['-t']:
        pool = mp.Pool(opts['-t'])
    coords = tuple()
    if opts['-b']:
        coords = 
    xy = [tuple(map(int, opts['-s'].split(','))), ]
    out = [opts['-o'],]
    args = izip(iter_timestream_images(opts['-i']), cycle(out), cycle(xy))
    args = izip(iter_timestream_images(opts['-i']), cycle(out), cycle(xy))
    num = len(pool.map(process_image, args))
    sys.stderr.write("\nProcessed {} Images!".format(num))
    sys.stderr.flush()
    pool.close()
    pool.join()

if __name__ == "__main__":
    main(docopt.docopt(CLI))
