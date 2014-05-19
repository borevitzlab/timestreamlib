def date(x):
    if isinstance(x, struct_time):
        return x
    else:
        try:
           return strptime(x, "%Y_%m_%d")
        except:
            raise ValueError

def num_str(x):
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

def sep_in_list(x, ok_list, sep=","):




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



def validate_camera(camera):
    sch = Schema({
        Required(FIELDS["destination"]): path_exists,
        Required(FIELDS["expt"]): str,
        Required(FIELDS["expt_end"]): date,
        Required(FIELDS["expt_start"]): date,
        Required(FIELDS["image_types"]): image_type_str,
        Required(FIELDS["interval"], default=1): num_str,
        Required(FIELDS["location"]): str,
        Required(FIELDS["method"], default="archive"): InList(["copy", "archive",
            "move"]),
        Required(FIELDS["mode"], default="batch"): InList(["batch", "watch"]),
        # watch not implemented yet though
        Required(FIELDS["name"]): str,
        Required(FIELDS["resolutions"], default="fullres"): resolution_str,
        Required(FIELDS["source"]): path_exists,
        Required(FIELDS["use"]): bool_str,
        Required(FIELDS["user"]): str,
        FIELDS["archive_dest"]: path_exists,
        FIELDS["sunrise"]: int_time_hr_min,
        FIELDS["sunset"]: int_time_hr_min,
        FIELDS["timezone"]: int_time_hr_min,
        })
    cam = sch(camera)
    return cam


