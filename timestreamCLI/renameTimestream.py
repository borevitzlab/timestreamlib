#!/usr/bin/python
from __future__ import print_function
import docopt
from itertools import (
        cycle,
        izip,
        imap,
        )
import multiprocessing as mp
import os
from os import path
import sys
import shutil
from timestream.parse import ts_iter_images

CLI = """
USAGE:
renameTS [-t THREADS] -i IN_TIMESTREAM -o OUT_TIMESTREAM

OPTIONS:
    -i IN_TIMESTREAM    Input timestream
    -o OUT_TIMESTREAM   Output timestream. The name of the new timestream will
                        be the basename of this path.
    -t THREADS          Number of concurrent worker processes.
"""


def process_image((img, out_ts)):
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
        shutil.move(img, dest)

def main(opts):
    out = [opts['-o'],]
    args = izip(ts_iter_images(opts['-i']), cycle(out))
    count = 0
    for _ in imap(process_image, args):
        if count % 10 == 0:
            print("Renamed {} images!".format(count), end="\r")
        count += 1
    print("Renamed {} images!\n\n".format(count))

if __name__ == "__main__":
    main(docopt.docopt(CLI))
