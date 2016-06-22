#!/usr/bin/python
from __future__ import print_function
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
import traceback
from timestream.parse import ts_iter_images

CLI = """
USAGE:
resizeTS [-t THREADS] -i IN_TIMESTREAM -o OUT_TIMESTREAM -s XY

OPTIONS:
    -i IN_TIMESTREAM    Input timestream
    -o OUT_TIMESTREAM   Output timestream
    -s XY               Ouput size, as "x,y" comma or 'x' seperated pixel
                        dimensions.
    -t THREADS          Number of concurrent worker processes.
"""


def process_image((img, out_ts, size)):
    # get output path
    split = path.basename(img).split('_')[1:]
    dest = path.join(
            out_ts,
            split[0],
            "_".join(split[0:2]),
            "_".join(split[0:3]),
            "_".join(split[0:4]),
            path.basename(out_ts) + "_" + "_".join(split),
            )
    # Force JPEG output, even w/ PNG input
    dest = path.splitext(dest)[0] + ".JPG"
    # make output dir if not exists
    if not path.exists(path.dirname(dest)):
        try:
            os.makedirs(path.dirname(dest))
        except (OSError, IOError) as e:
            if not path.exists(path.dirname(dest)):
                raise e
    # Skip if exists
    if not path.exists(dest):
        try:
            w_final, h_final = size
            imgmat = cv2.imread(img)
            if imgmat is None:
                return
            if h_final < 1:
                h, w, d = imgmat.shape
                scale = w_final / float(w)
                h_final = int(h * scale)
            res = cv2.resize(imgmat, (w_final, h_final),
                             interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(dest, res, (cv2.IMWRITE_JPEG_QUALITY, 85))
        except cv2.error:
            print("\n[resize_image] ERROR: weird image", img, file=sys.stderr)
            print("Traceback is:\n", traceback.format_exc(), file=sys.stderr)


def main(opts):
    pool = mp.Pool()
    if opts['-t']:
        pool = mp.Pool(opts['-t'])
    xy = tuple(map(int, opts['-s'].replace('x', ',').split(',')))
    if len(xy) == 1:
        xy = (xy[0], 0)
    xy = [xy, ]
    out = [opts['-o'],]
    args = izip(ts_iter_images(opts['-i']), cycle(out), cycle(xy))
    count = 0
    print("Resizing {} to {}".format(opts['-i'], opts['-s']))
    for _ in pool.imap(process_image, args):
        print("Resized {: 5d} images!".format(count), end="\r")
        count += 1
    print("Resized {: 5d} images! Done!".format(count))
    pool.close()
    pool.join()

if __name__ == "__main__":
    main(docopt.docopt(CLI))
