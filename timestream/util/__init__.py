
# Error string constants
PARAM_TYPE_ERR = "Param `{param}` to `{func}` must be a `{type}`"


def dict_unicode_to_str(dct):
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
        elif isinstance(val, list):
            lst = []
            for item in val:
                lst.append(str(item))
            val = lst
        elif isinstance(val, dict):
            val = dict_unicode_to_str(val)
        output[key] = val
    return output
