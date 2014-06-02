#!/usr/bin/python
from __future__ import print_function
import docopt
import csv
import cv2
import multiprocessing as mp
import numpy as np
from timestream.parse import (
        ts_iter_images,
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
    try:
        imgmat = cv2.imread(img)
        if imgmat is None:
            # make it go to the except block, where we deal with other things
            raise cv2.error;
        ret =  imgmat.sum()
    except cv2.error:
        ret = 0
    return (img, ret)


def setup_header(ts_info):
    start_today = datetime.combine(date.today(), time.min)
    end_today = datetime.combine(date.today(), time.max)
    times = iter_date_range(start_today, end_today, ts_info['interval'] * 60)
    times = [x.strftime("%H:%M:%S") for x in times]
    return times

def main(opts):
    ts_name = opts["-i"]
    out_fh = open(opts['-o'], 'w')
    ts_info = ts_get_manifest(ts_name)
    times = setup_header(ts_info)
    out_csv = csv.writer(out_fh)
    header = ["", ]
    header.extend(times)
    out_csv.writerow(header)
    pl = mp.Pool()
    img_iter = ts_iter_images(ts_name)
    res_dict = {}
    print("Collecting image sums...")
    count = 0
    for img, pix_sum in pl.imap(sum_image, img_iter, 100):
        if count % 10 == 0:
            print("Processed {: 6d} images!".format(count), end='\r')
        count += 1
        img_dt = ts_parse_date_path(img)
        try:
            res_dict[img_dt.date()][img_dt.time().isoformat()] = pix_sum
        except KeyError:
            res_dict[img_dt.date()] = {img_dt.time().isoformat(): pix_sum}
    print("Processed {: 6d} images!".format(count))
    pl.close()
    pl.join()
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
                row.append(0)
        out_csv.writerow(row)
    print("All done!")

if __name__ == "__main__":
    main(docopt.docopt(CLI))
