from os import path

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
    "basic_jpg_exif": path.join(TESTS_DIR, "data", "IMG_0001-exif.json"),
    "basic_jpg_noexif": path.join(TESTS_DIR, "data", "IMG_0001_NOEXIF.JPG"),
    "basic_cr2": path.join(TESTS_DIR, "data", "IMG_0001.CR2"),
}
