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
.. module:: timestream.util.validation
    :platform: Windows, Unix
    :synopsis: Utility functions to aide in validation of things.

.. moduleauthor:: Kevin Murray
"""

import datetime

# Functions to parse to Voluptuous Schemas to validate fields
# All are prefixed with v_ to indicate this intended usage


def v_date(x, format="%Y_%m_%d"):
    """Validate string contains a date in ``fmt`` strptime-compatible format,
    and coerce to a ``datetime.datetime`` object.

    :arg str x: String to validate.
    :keyword str fmt: String date format to strip time with.
    :returns:  the parsed object
    :rtype: datetime.datetime
    :raises: ``ValueError``
    """
    if isinstance(x, datetime.datetime):
        return x
    else:
        return datetime.datetime.strptime(x, format)


def v_datetime(x, format="%Y_%m_%d_%H_%M_%S"):
    """Validate string contains a date in ``fmt`` strptime-compatible format,
    and coerce to a ``datetime.datetime`` object.

    :arg str x: String to validate.
    :keyword str fmt: String date format to strip time with.
    :returns:  the parsed object
    :rtype: datetime.datetime
    :raises: ``ValueError``
    """
    if isinstance(x, datetime.datetime):
        return x
    else:
        return datetime.datetime.strptime(x, format)


def v_num_str(x):
    """Validate an object that can be coerced to an ``int``."""
    return int(x)
