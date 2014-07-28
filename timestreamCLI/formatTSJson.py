from __future__ import print_function
from copy import deepcopy
import csv
from glob import glob
import json
from os import path
from timestream import TimeStream

def main(csv_path):
    lst = []
    ifh = open(csv_path)
    rdr = csv.DictReader(ifh)
    for line in rdr:
        lst.append(deepcopy(line))
    print(json.dumps(lst))
    ifh.close()

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
