import datetime
import logging
import os
from os import path
import shutil
import tempfile


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
    "basic_jpg": path.join(TESTS_DIR, "data", "IMG_0001.JPG"),
    "basic_jpg_exif": path.join(TESTS_DIR, "data", "IMG_0001-JPG-exif.json"),
    "basic_jpg_noexif": path.join(TESTS_DIR, "data", "IMG_0001_NOEXIF.JPG"),
    "basic_cr2": path.join(TESTS_DIR, "data", "IMG_0001.CR2"),
    "basic_cr2_exif": path.join(TESTS_DIR, "data", "IMG_0001-CR2-exif.json"),
    "empty_dir": path.join(TESTS_DIR, "data", "empty_dir"),
    "tmp_dir": path.join(TESTS_DIR, "data", "tmp"),
    "timestream_manifold": path.join(TESTS_DIR, "data", "timestreams",
                                     "BVZ0022-GC05L-CN650D-Cam07~fullres-orig"),
    "timestream_nomanifold": path.join(TESTS_DIR, "data", "timestreams",
                                       "nomanifold"),
    "timestream_bad": path.join(TESTS_DIR, "data", "timestreams",
                                "badts"),
    "timestream_gaps": path.join(TESTS_DIR, "data", "timestreams",
                                "withgaps"),
    "not_a_timestream": path.join(TESTS_DIR, "data", "timestreams",
                                  "not"),
}

TS_MANIFOLD_FILES_JPG = [
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_03/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_03_00_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_03/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_03_30_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_04/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_04_00_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_04/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_04_30_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_05/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_05_00_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_05/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_05_30_00_00.JPG",
    "timestreams/BVZ0022-GC05L-CN650D-Cam07~fullres-orig/2013/2013_10/2013_10_30/2013_10_30_06/BVZ0022-GC05L-CN650D-Cam07~fullres-orig_2013_10_30_06_00_00_00.JPG",
]
TS_MANIFOLD_JPG_DTYPE = 'uint8'
TS_MANIFOLD_JPG_SHAPE = (3456, 5184, 3)

TS_MANIFOLD_DICT_PARSED = {
    "name": "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
    "start_datetime": datetime.datetime(2013, 10, 30, 3, 0),
    "end_datetime": datetime.datetime(2013, 10, 30, 6, 0),
    "version": 1,
    "image_type": "jpg",
    "extension": "JPG",
    "interval": 30,
    "missing": [],
}

TS_MANIFOLD_DICT = {
    "name": "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
    "start_datetime": "2013_10_30_03_00_00",
    "end_datetime": "2013_10_30_06_00_00",
    "version": 1,
    "image_type": "jpg",
    "extension": "JPG",
    "interval": 30,
    "missing": [],
}

TS_MANIFOLD_FILES_JPG = [
    path.join(TESTS_DIR, "data", x) for x in TS_MANIFOLD_FILES_JPG
]
TS_MANIFOLD_FILES_TSM = [
    path.join(TESTS_DIR, "data", "timestreams",
              "BVZ0022-GC05L-CN650D-Cam07~fullres-orig",
              "BVZ0022-GC05L-CN650D-Cam07~fullres-orig.tsm"),
]

TS_MANIFOLD_FILES = TS_MANIFOLD_FILES_JPG + TS_MANIFOLD_FILES_TSM
TS_MANIFOLD_DATES = [
    "2013_10_30_03_00_00",
    "2013_10_30_03_30_00",
    "2013_10_30_04_00_00",
    "2013_10_30_04_30_00",
    "2013_10_30_05_00_00",
    "2013_10_30_05_30_00",
    "2013_10_30_06_00_00",
]
TS_MANIFOLD_DATES_PARSED = [
    datetime.datetime(2013, 10, 30, 3, 0),
    datetime.datetime(2013, 10, 30, 3, 30),
    datetime.datetime(2013, 10, 30, 4, 0),
    datetime.datetime(2013, 10, 30, 4, 30),
    datetime.datetime(2013, 10, 30, 5, 0),
    datetime.datetime(2013, 10, 30, 5, 30),
    datetime.datetime(2013, 10, 30, 6, 0),
]
TS_GAPS_DATES_PARSED = [
    datetime.datetime(2013, 10, 30, 3, 0),
    datetime.datetime(2013, 10, 30, 3, 30),
    datetime.datetime(2013, 10, 30, 4, 0),
    datetime.datetime(2013, 10, 30, 5, 0),
    datetime.datetime(2013, 10, 30, 6, 0),
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
