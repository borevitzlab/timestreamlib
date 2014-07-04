#!/usr/bin/python
from __future__ import print_function
import docopt
import csv
import cv2
import logging
import multiprocessing as mp
import numpy as np
import sys
from timestream import (
        TimeStream,
        setup_module_logging,
        )
from timestream.parse import (
        ts_get_manifest,
        iter_date_range,
        ts_parse_date_path,
        )
from datetime import (
        date,
        datetime,
        time,
        timedelta,
        )

CLI = """
USAGE:
gapDetect -i IN_TIMESTREAM -o OUT_CSV

OPTIONS:
    -i IN_TIMESTREAM    Input timestream
    -o OUT_CSV          Output CSV. This will be a table with days as rows,
                        and day-wise timepoints as columns.
"""

def sum_image(img):
    pixels = img.pixels
    if pixels is not None:
        img.data['sum'] = pixels.sum()
    else:
        img.data['sum'] = "NA"
    return img.clone()

def setup_header(ts_info):
    start_today = datetime.combine(date.today(), time.min)
    end_today = datetime.combine(date.today(), time.max)
    times = iter_date_range(start_today, end_today, ts_info['interval'] * 60)
    times = [x.strftime("%H:%M:%S") for x in times]
    return times

def main(opts):
    setup_module_logging(logging.ERROR)
    ts_name = opts["-i"]
    out_fh = open(opts['-o'], 'w')
    ts_info = ts_get_manifest(ts_name)
    times = setup_header(ts_info)
    out_csv = csv.writer(out_fh)
    header = ["", ]
    header.extend(times)
    out_csv.writerow(header)
    ts = TimeStream()
    ts.load(ts_name)
    res_dict = {}
    print("Collecting image sums...")
    count = 0
    pool = mp.Pool()
    for img in pool.imap(sum_image, ts.iter_by_timepoints()):
    #for img in map(sum_image, ts.iter_by_timepoints()):
        print("Processed {: 6d} images!".format(count), end='\r')
        sys.stdout.flush()
        count += 1
        pix_sum = str(img.data['sum'])
        img_dt = img.datetime
        try:
            res_dict[img_dt.date()][img_dt.time().isoformat()] = pix_sum
        except KeyError:
            res_dict[img_dt.date()] = {img_dt.time().isoformat(): pix_sum}
    pool.close()
    pool.join()
    print("Processed {: 6d} images!".format(count))
    print("Done collecting image sums, now making the table")
    for date, times in sorted(res_dict.items()):
        row = []
        row.append(date.isoformat())
        start_today = datetime.combine(date.today(), time.min)
        end_today = datetime.combine(date.today(), time.max)
        all_times = iter_date_range(start_today, end_today,
                ts_info['interval'] * 60)
        for timepoint in all_times:
            try:
                row.append(times[timepoint.time().isoformat()])
            except KeyError:
                row.append("NA")
        out_csv.writerow(row)
    print("All done!")

if __name__ == "__main__":
    main(docopt.docopt(CLI))
