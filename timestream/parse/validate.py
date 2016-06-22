# Copyright 2014 Kevin Murray/Bioinfinio
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: timestream.parse.validate
    :platform: Unix, Windows
    :synopsis: Validate timestream metadata

.. moduleauthor:: Kevin Murray
"""

from os import path
from voluptuous import Schema, Required, Range, All, Length, Any

from timestream.util.validation import (
    v_datetime,
    v_num_str,
)

#: Acceptable constants for image filetypes
IMAGE_TYPE_CONSTANTS = ["raw", "jpg", "png"]
#: Acceptable constants indicating that a timestream is full resolution
FULLRES_CONSTANTS = ["fullres"]
#: Acceptable constants 'raw' image format file extensions
RAW_FORMATS = ["cr2", "nef", "tif", "tiff"]
IMAGE_EXT_CONSTANTS = ["jpg", "png"]
IMAGE_EXT_CONSTANTS.extend(RAW_FORMATS)
IMAGE_EXT_CONSTANTS.extend([x.upper() for x in IMAGE_EXT_CONSTANTS])
IMAGE_EXT_TO_TYPE = {
    "jpg": "jpg",
    "png": "png",
    "cr2": "raw",
    "nef": "raw",
    "tif": "raw",
    "tiff": "raw",
    "JPG": "jpg",
    "PNG": "png",
    "CR2": "raw",
    "NEF": "raw",
    "TIF": "raw",
    "TIFF": "raw",
}
TS_DATE_FORMAT = "%Y_%m_%d_%H_%M_%S"
__TS_V1_LEVELS = [
    '%Y',
    '%Y_%m',
    '%Y_%m_%d',
    '%Y_%m_%d_%H',
    '{tsname:s}_%Y_%m_%d_%H_%M_%S_{n:02d}.{ext:s}',
]
TS_V1_FMT = path.join(*__TS_V1_LEVELS)

TS_MANIFEST_KEYS = [
    "name",
    "version",
    "start_datetime",
    "end_datetime",
    "image_type",
    "extension",
    "interval",
]


def validate_timestream_manifest(manifest):
    """Validtes a json manifest, and returns the validated ``dict``

    :param dict manifest: The raw json manifest from ``json.load`` or similar.
    :returns: The validated and type-converted manifest as a ``dict``
    :rtype: dict
    :raises: TypeError, MultipleInvalid
    """
    if not isinstance(manifest, dict):
        raise TypeError("Manfiest should be in ``dict`` form.")
    sch = Schema({
        Required("name"): All(str, Length(min=1)),
        Required("version"): All(v_num_str, Range(min=1, max=2)),
        Required("start_datetime"): v_datetime,
        Required("end_datetime"): v_datetime,
        Required("image_type"): Any(*IMAGE_TYPE_CONSTANTS),
        Required("extension"): Any(*IMAGE_EXT_CONSTANTS),
        Required("interval", default=1): All(v_num_str, Range(min=1)),
        "missing": list,
    })
    return sch(manifest)
