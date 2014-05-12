#Copyright 2014 Kevin Murray

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
.. module:: timestream.util.validation
    :platform: Windows, Unix
    :synopsis: Utility functions to aide in validation of things.

.. moduleauthor:: Kevin Murray <spam@kdmurray.id.au>
"""

import datetime

# Functions to parse to Voluptuous Schemas to validate fields
# All are prefixed with v_ to indicate this intended usage
def v_date(x, fmt="%Y-%m-%d"):
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
        try:
           return datetime.datetime.strptime(x, fmt)
        except:
            raise ValueError

def v_datetime(x, fmt="%Y_%m_%d_%H_%M_%S"):
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
        try:
           return datetime.datetime.strptime(x, fmt)
        except:
            raise ValueError

def v_num_str(x):
    """Validate an object that can be coerced to an ``int``."""
    return int(x)

def bool_str(x):
    if isinstance(x, bool):
        return x
    elif isinstance(x, int):
            return bool(int(x))
    elif isinstance(x, str):
        x = x.strip().lower()
        try:
            return bool(int(x))
        except:
            if x in {"t", "true", "y", "yes", "f", "false", "n", "no"}:
                return x in {"t", "true", "y", "yes"}
    raise ValueError

def int_time_hr_min(x):
    if isinstance(x, tuple):
        return x
    else:
        return (int(x)//100, int(x) % 100 )

def path_exists(x):
    if path.exists(x):
        return x
    else:
        raise ValueError("path '%s' doesn't exist" % x)

def sep_list(x, sep=","):
    try:
        return x.strip().split(sep)
    except:
        raise ValueError

def sep_in_list(x, accepted, sep=','):
    """

    """
    try:
        lst = x.strip().split(sep)
    except:
        raise ValueError("Bad '{}' seperated list {!s}".format(sep, x))
    for itm in lst:
        if itm not in accepted:
            raise ValueError("{} not in {!r}".format(x, accepted))
    return lst

def resolution_str(x):
    if not isinstance(x, str):
        raise ValueError
    xs = x.strip().split('~')
    res_list = []
    for res in xs:
        # First, attempt splitting into X and Y components. Non <X>x<Y>
        # resolutions will be returned as a single item in a list,
        # hence the len(xy) below
        xy = res.strip().lower().split("x")
        if res in FULLRES_CONSTANTS:
            res_list.append(res)
        elif len(xy) == 2:
            # it's an XxY thing, hopefully
            x, y = xy
            x, y = int(x), int(y)
            res_list.append((x,y))
        else:
            # we'll pretend it's an int, for X resolution, and any ValueError
            # triggered here will be propagated to the vaildator
            res_list.append((int(res), None))
    return res_list

def image_type_str(x):
    if isinstance(x, list):
        return x
    if not isinstance(x, str):
        raise ValueError
    types = x.lower().strip().split('~')
    for type in types:
        if not type in IMAGE_TYPE_CONSTANTS:
            raise ValueError
    return types

class InList(object):
    def __init__(self, valid_values):
        if isinstance(valid_values, list) or \
                isinstance(valid_values, tuple):
            self.valid_values = set(valid_values)
    def __call__(self, x):
        if not x in self.valid_values:
            raise ValueError
        return x
