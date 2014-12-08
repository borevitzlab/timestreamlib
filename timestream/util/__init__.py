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
.. module:: timestream.util
    :platform: Unix, Windows
    :synopsis: Miscelanelous utilities

.. moduleauthor:: Kevin Murray
"""

import base64
import json
import logging
import numpy as np
from warnings import warn

# Error string constants
#: String to format when a function is called with a param of invalid type
PARAM_TYPE_ERR = "Param `{param}` to `{func}` must be a `{type}`"

LOG = logging.getLogger("timestreamlib")

try:
    isinstance(u"ABC", unicode)
    UC = unicode
except NameError:
    UC = str


def dict_unicode_to_str(dct):
    """Convert strings in a ``dict`` from ``unicode`` to ``str``

    :param str dct: A dictionary to convert, may or may not contain unicode
            keys/values, or nested dicts and lists.
    :returns: dict -- The de-``unicode``d version of ``dct``
    :raises: ValueError
    """
    output = {}
    for key, val in dct.items():
        if isinstance(key, UC):
            key = str(key)
        if isinstance(val, UC):
            val = str(val)
        elif isinstance(val, tuple):
            lst = []
            for item in val:
                lst.append(str(item))
            val = tuple(lst)
        elif isinstance(val, list):
            lst = []
            for item in val:
                lst.append(str(item))
            val = lst
        elif isinstance(val, dict):
            val = dict_unicode_to_str(val)
        output[key] = val
    return output


def numpy2str(array):
    """Stringify a numpy array, preserving the dtype and shape"""
    if not isinstance(array, np.ndarray):
        msg = "numpy2str must be given a numpy array"
        LOG.error(msg)
        raise TypeError(msg)
    arr_str = base64.b64encode(array.tostring())
    enc = [str(array.dtype), arr_str, array.shape, ]
    return json.dumps(enc)


def str2numpy(arr_str):
    """destringify a numpy array, preserving the dtype and shape"""
    if isinstance(arr_str, UC):
        arr_str = str(arr_str)
    if not isinstance(arr_str, str):
        msg = "str2numpy must be given a str or bytes"
        LOG.error(msg)
        raise TypeError(msg)
    unpacked = json.loads(arr_str)
    if len(unpacked) != 3:
        msg = "Bad numpy str {}. Should be (dtype, arr, shape)".format(arr_str)
        LOG.error(msg)
        raise ValueError(msg)
    dtype, arr_string, shape = unpacked
    arr = np.fromstring(base64.decodestring(arr_string), dtype)
    arr = arr.reshape(shape)
    return arr


def dejsonify_data(data):
    """Converd jsonified dict back to a real dict"""
    if not isinstance(data, str):
        msg = "dejsonify_data must be given a str`"
        LOG.error(msg)
        raise TypeError(msg)
    data = json.loads(data)
    clean_dict = {}
    for key, val in data.items():
        if key.startswith("NP_ARR."):
            val = str2numpy(val)
            key = key[7:]
        clean_dict[key] = val
    return clean_dict


def jsonify_data(data, recursive=False):
    """Jsonify a dict that may contain numpy arrays"""
    if not isinstance(data, dict):
        msg = "jsonify_data must be given a dict"
        LOG.error(msg)
        raise TypeError(msg)
    clean_dict = {}
    for key, val in data.items():
        if not isinstance(key, str):
            warn("All keys are coersed to strings")
            key = str(key)
        if isinstance(val, np.ndarray):
            key = "NP_ARR.{}".format(key)
            val = numpy2str(val)
        if isinstance(val, dict):
            val = jsonify_data(val, recursive=True)
        clean_dict[key] = val
    if recursive:
        return clean_dict
    else:
        return json.dumps(clean_dict)
