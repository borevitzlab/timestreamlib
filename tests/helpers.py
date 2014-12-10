import datetime
import logging
import numpy as np
import os
from os import path
import shutil
import skimage.io


LOG = logging.getLogger("timestreamlib")
LGHNDLR = logging.NullHandler()
LGHNDLR.setLevel(logging.INFO)
LOG.addHandler(LGHNDLR)
LOG.setLevel(logging.INFO)

# SKIP messages
SKIP_NEED_INTERNET = "Test requires internet access"
SKIP_NEED_LINUX = "Test must be run on a linux-based system"
SKIP_NEED_MACOSX = "Test must be run on a Mac OSX system"
SKIP_NEED_WINDOWS = "Test must be run on a Windows system"
SKIP_NEED_FILE = "Test requires file {0}"


PKG_DIR = path.dirname(path.dirname(__file__))
TESTS_DIR = path.dirname(__file__)

FILES = {
    "basic_jpg": path.join(TESTS_DIR, "data", "cam_images", "IMG_0001.JPG"),
    "truncated_jpg": path.join(TESTS_DIR, "data", "images", "truncated.jpg"),
    "zeros_jpg": path.join(TESTS_DIR, "data", "images", "zeros.jpg"),
    "basic_jpg_exif": path.join(TESTS_DIR, "data", "cam_images",
                                "IMG_0001-JPG-exif.json"),
    "basic_jpg_noexif": path.join(TESTS_DIR, "data", "cam_images",
                                  "IMG_0001_NOEXIF.JPG"),
    "basic_tiff": path.join(TESTS_DIR, "data", "cam_images", "IMG_0001.tiff"),
    "basic_tiff_exif": path.join(TESTS_DIR, "data", "cam_images",
                                 "IMG_0001-tiff-exif.json"),
    "empty_dir": path.join(TESTS_DIR, "data", "empty_dir"),
    "tmp_dir": path.join(TESTS_DIR, "data", "tmp"),
    "timestream": path.join(TESTS_DIR, "data", "timestreams",
                            "good-timestream"),
    "timestream_bad": path.join(TESTS_DIR, "data", "timestreams",
                                "bad-timestream-good-images"),
    "timestream_gaps": path.join(TESTS_DIR, "data", "timestreams",
                                 "timestream-with-gaps"),
    "timestream_datafldr": path.join(TESTS_DIR, "data", "timestreams",
                                     "timestream-with-data-folder"),
    "timestream_imgdata": path.join(TESTS_DIR, "data", "timestreams",
                                    "timestream-with-imgdata"),
    "not_a_timestream": path.join(TESTS_DIR, "data", "timestreams",
                                  "not-a-timestream"),
    "timestream_good_images": path.join(TESTS_DIR, "data", "timestreams",
                                        "timestream-good-images")
}
ZEROS_PIXELS = np.zeros((100, 100, 3), dtype="uint8")
ZEROS_DATETIME = datetime.datetime(2013, 11, 12, 20, 53, 9)

TS_FILES_JPG_PRE = \
    "timestreams/good-timestream/2013/2013_10/2013_10_30/2013_10_30_"
TS_FILES_JPG = [
    TS_FILES_JPG_PRE + "03/good-timestream_2013_10_30_03_00_00_00.JPG",
    TS_FILES_JPG_PRE + "03/good-timestream_2013_10_30_03_30_00_00.JPG",
    TS_FILES_JPG_PRE + "04/good-timestream_2013_10_30_04_00_00_00.JPG",
    TS_FILES_JPG_PRE + "04/good-timestream_2013_10_30_04_30_00_00.JPG",
    TS_FILES_JPG_PRE + "05/good-timestream_2013_10_30_05_00_00_00.JPG",
    TS_FILES_JPG_PRE + "05/good-timestream_2013_10_30_05_30_00_00.JPG",
    TS_FILES_JPG_PRE + "06/good-timestream_2013_10_30_06_00_00_00.JPG",
    TS_FILES_JPG_PRE + "06/good-timestream_2013_10_30_06_30_00_00.JPG",
]
TS_JPG_DTYPE = 'uint8'
TS_JPG_SHAPE = (35, 52, 3)

TS_DICT_PARSED = {
    "name": "good-timestream",
    "start_datetime": datetime.datetime(2013, 10, 30, 3, 0),
    "end_datetime": datetime.datetime(2013, 10, 30, 6, 30),
    "version": 1,
    "image_type": "jpg",
    "extension": "JPG",
    "interval": 30 * 60,  # In seconds now
    "missing": [],
}

TS_DICT = {
    "name": "good-timestream",
    "start_datetime": "2013_10_30_03_00_00",
    "end_datetime": "2013_10_30_06_30_00",
    "version": 1,
    "image_type": "jpg",
    "extension": "JPG",
    "interval": 30 * 60,  # In seconds now
    "missing": [],
}

TS_STR = "TimeStream called good-timestream\n" \
         + "	path: {}\n".format(FILES["timestream"]) \
         + "	name: good-timestream\n" \
         + "	version: 1\n" \
         + "	start_datetime: 2013-10-30 03:00:00\n" \
         + "	end_datetime: 2013-10-30 06:30:00\n" \
         + "	image_type: jpg\n" \
         + "	extension: JPG\n" \
         + "	interval: 1800\n" \

TS_FILES_JPG = [path.join(TESTS_DIR, "data", x) for x in TS_FILES_JPG]

TS_FILES = TS_FILES_JPG
TS_DATES = [
    "2013_10_30_03_00_00",
    "2013_10_30_03_30_00",
    "2013_10_30_04_00_00",
    "2013_10_30_04_30_00",
    "2013_10_30_05_00_00",
    "2013_10_30_05_30_00",
    "2013_10_30_06_00_00",
]
TS_DATES_PARSED = [
    datetime.datetime(2013, 10, 30, 3, 0),
    datetime.datetime(2013, 10, 30, 3, 30),
    datetime.datetime(2013, 10, 30, 4, 0),
    datetime.datetime(2013, 10, 30, 4, 30),
    datetime.datetime(2013, 10, 30, 5, 0),
    datetime.datetime(2013, 10, 30, 5, 30),
    datetime.datetime(2013, 10, 30, 6, 0),
    datetime.datetime(2013, 10, 30, 6, 30),
]
TS_GAPS_DATES_PARSED = [
    datetime.datetime(2013, 10, 30, 3, 0),
    datetime.datetime(2013, 10, 30, 3, 30),
    datetime.datetime(2013, 10, 30, 4, 0),
    datetime.datetime(2013, 10, 30, 5, 0),
    datetime.datetime(2013, 10, 30, 6, 0),
    datetime.datetime(2013, 10, 30, 6, 30),
]

if path.exists(FILES["empty_dir"]):
    shutil.rmtree(FILES["empty_dir"])
os.mkdir(FILES["empty_dir"])

NUM_TEMPS = 0


def make_tmp_file():
    if not path.isdir(FILES["tmp_dir"]):
        os.mkdir(FILES["tmp_dir"])
    global NUM_TEMPS
    NUM_TEMPS += 1
    return path.join(FILES["tmp_dir"], "{:05d}.tmp".format(NUM_TEMPS))


def imgs_common_tsdir(act, fullpath, skip=None):
    if fullpath.endswith(os.sep):
        fullpath = fullpath[:-1]
    dirname = path.basename(fullpath)
    outimg = np.ones((35, 52, 3))

    if act == "setup":
        for h in ["03", "04", "05", "06"]:
            D = path.join(fullpath, "2013", "2013_10", "2013_10_30",
                          "2013_10_30_" + h)
            if not path.isdir(D):
                os.makedirs(D)
            for m in ["00", "30"]:
                if skip is not None and (h, m) in skip:
                    continue
                F = path.join(D, dirname + "_2013_10_30_"
                              + h + "_" + m + "_00_00.JPG")
                skimage.io.imsave(F, outimg)

    elif act == "teardown":
        top = path.join(fullpath, "2013")
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(top)
