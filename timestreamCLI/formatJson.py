from copy import deepcopy
from glob import glob
import json
from os import path
from timestream import TimeStream

ists = lambda d: path.isdir(d) and not d.startswith("_")
isfullres = lambda d: d.endswith("fullres-orig")
is640 = lambda d: d.endswith("640-orig")
tsname = lambda d: d.split("~")[0]
splitname = lambda ts: ts.split("-")
expts_fmt = [{"experiments": []}]
expt_fmt = {
    "expt_id": None,
    "user": None,
    "spp": None,
    "location": None,
    "end_date": None,
    "end_time": None,
    "start_date": None,
    "start_time": None,
    "timestreams": [ ],
}

def main():
    dirs = filter(ists, glob(r'*/*'))
    fullres = filter(isfullres, dirs)
    lowres = filter(is640, dirs)
    expts = []
    expt_dict = {}
    ts_dict = {}
    user = "Borevitz"

    ts = TimeStream()
    for fr_path in fullres:
        fr = path.basename(fr_path.rstrip("/"))
        ts_name = tsname(fr)
        ts.load(fr_path)
        expt, loc, cam = splitname(ts_name)
        try:
            expt_dict[expt]["expt_id"] = expt
        except KeyError:
            expt_dict[expt] = deepcopy(expt_fmt)
            expt_dict[expt]["expt_id"] = expt
        expt_dict[expt]["user"] = user
        expt_dict[expt]["spp"] = "Unknown Species"
        expt_dict[expt]["location"] = loc
        expt_dict[expt]["start_date"] = ts.start_datetime.strftime("%Y-%m-%d")
        expt_dict[expt]["start_time"] = ts.start_datetime.strftime("%H:%M")
        expt_dict[expt]["end_date"] = ts.end_datetime.strftime("%Y-%m-%d")
        expt_dict[expt]["end_time"] = ts.end_datetime.strftime("%H:%M")
        expt_dict[expt]["timestreams"].append(fr)
        #print("TS at {} updates dict for {} to:\n{!r}".format(fr, expt,
        #      expt_dict[expt]))
    for expt, dct in expt_dict.items():
        expts.append(dct)
    expts_fmt[0]["experiments"] = expts
    print(json.dumps(expts_fmt, indent=4))

if __name__ == "__main__":
    main()
