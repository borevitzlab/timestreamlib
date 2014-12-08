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
.. module:: timestream.util.layouts
    :platform: Unix, Windows
    :synopsis: Convert between different grid layout notations

.. moduleauthor:: Kevin Murray
"""

import logging
import re

from timestream.util import (
    PARAM_TYPE_ERR,
)


LOG = logging.getLogger("timestreamlib")


def traypos_to_chamber_index(traypos, tray_cap=20, col_cap=5):
    if not isinstance(traypos, str):
        msg = PARAM_TYPE_ERR.format(func='traypos_to_chamber_index',
                                    param='traypos', type='str')
        LOG.error(msg)
        raise TypeError(msg)
    extractor = re.compile(r'^(\d{1,2})([a-zA-Z])([1-9])$')
    match = extractor.match(traypos)
    if match is None:
        msg = "Tray Pos '{}' is invalid".format(traypos)
        LOG.error(msg)
        raise ValueError(msg)
    tray, col, row = match.groups()
    tray = int(tray)
    col = ord(col.upper()) - 65  # Numericise the col num, 0-based
    row = int(row)
    index = (tray - 1) * tray_cap + col * col_cap + row
    return index
