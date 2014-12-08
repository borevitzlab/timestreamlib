# Copyright 2006-2014 Tim Brown/TimeScience LLC
# Copyright 2013-2014 Kevin Murray/Bioinfinio
# Copyright 2014- The Australian National Univesity
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
.. module:: timestream.util.imgmeta
    :platform: Unix, Windows
    :synopsis: Access image metadata such as EXIF tags.

.. moduleauthor:: Kevin Murray
"""

import datetime
import exifread as er
from string import (
    digits,
)

from timestream.util import (
    dict_unicode_to_str,
)


def get_exif_tags(image, mode="silent"):
    """Get a dictionary of exif tags from image exif header

    :param str image: Path to image file.
    :param str mode: Behaviour on missing exif tag. If `"silent"`, `None` is
                     returned. If `"raise"`, a `KeyError` is raised.
    :returns: dict -- The EXIF tag dictionary, or None
    :raises: ValueError
    """
    if mode not in {"silent", "raise"}:
        raise ValueError("Bad get_exif_tags mode '{}'".format(mode))
    with open(image, "rb") as fh:
        tags = er.process_file(fh, details=False)
    tags = dict_unicode_to_str(tags)
    # remove the first bit off the tags
    exif = {}
    for k, v in tags.items():
        # Remove the EXIF/Image category from the keys
        k = " ".join(k.split(" ")[1:])
        # weird exif tags in CR2s start with a 2/3, or have hex in them
        if k[0] in digits or "0x" in k:
            continue
        v = str(v)
        exif[k] = v
    return exif


def get_exif_tag(image, tag, mode="silent"):
    """Get a tag from image exif header

    :param str image: Path to image file.
    :param str tag: Tag to extract from exif header.
    :param str mode: Behaviour on missing exif tag. If `"silent"`, `None` is
                     returned. If `"raise"`, a `KeyError` is raised.
    :returns: str -- The EXIF tag value.
    :raises: KeyError, ValueError
    """
    if mode not in {"silent", "raise"}:
        raise ValueError("Bad get_exif_tag mode '{0}'".format(mode))
    exif = get_exif_tags(image, mode)
    try:
        return exif[tag]
    except KeyError as exc:
        if mode == "silent":
            return None
        else:
            raise exc


def get_exif_date(image):
    """Get a tag from image exif header

    :param str image: Path to image file.
    :returns: datetime.datetime -- The DateTime EXIF tag, parsed.
    :raises: KeyError, ValueError
    """
    try:
        str_date = get_exif_tag(image, "DateTime", "raise")
        return datetime.datetime.strptime(str_date, "%Y:%m:%d %H:%M:%S")
    except (KeyError, ValueError):
        return None
