
# Error string constants
#: String to format when a function is called with a param of invalid type
PARAM_TYPE_ERR = "Param `{param}` to `{func}` must be a `{type}`"


def dict_unicode_to_str(dct):
    """Convert strings in a ``dict`` from ``unicode`` to ``str``

    :param str dct: A dictionary to convert, may or may not contain unicode
            keys/values, or nested dicts and lists.
    :returns: dict -- The de-``unicode``d version of ``dct``
    :raises: ValueError
    """
    try:
        isinstance(u"ABC", unicode)
        uc = unicode
    except NameError:
        uc = str
    output = {}
    for key, val in dct.items():
        if isinstance(key, uc):
            key = str(key)
        if isinstance(val, uc):
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
