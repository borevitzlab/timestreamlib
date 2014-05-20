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
    # make output dir if not exists
    if not path.exists(path.dirname(dest)):
        try:
            os.makedirs(path.dirname(dest))
        except (OSError, IOError) as e:
            if not path.exists(path.dirname(dest)):
                raise e
    # Skip or not skip
    if not path.exists(dest):
        sys.stderr.write(".")
        sys.stderr.flush()
        try:
            w_final, h_final = size
            imgmat = cv2.imread(img)
            if imgmat is None:
                raise cv2.error;
            if h_final < 1:
                h, w, d = imgmat.shape
                scale = w_final / float(w)
                h_final = int(h * scale)
            res = cv2.resize(imgmat, (w_final, h_final))
            cv2.imwrite(dest, res)
        except cv2.error:
            sys.stderr.write(
                "\n[resize_image] ERROR: something weird in {}\n".format(img))
            sys.stderr.flush()
    else:
        sys.stderr.write("S")
        sys.stderr.flush()

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
    args = izip(ts_iter_images(opts['-i']), cycle(out), cycle(xy))
    num = len(pool.map(process_image, args))
    sys.stderr.write("\nProcessed {} Images!\n\n".format(num))
    sys.stderr.flush()
    pool.close()
    pool.join()

if __name__ == "__main__":
    main(docopt.docopt(CLI))
