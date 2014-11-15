import csv
from docopt import docopt
from timestream.util.layouts import traypos_to_chamber_index


CLI_DOC = """
USAGE:
    fixChamberPos.py [-n] -c COLUMN -i INPUT

OPTIONS:
    -n          CSV has no header
    -c COLUMN   Column to convert.
    -i INPUT    Input CSV

"""

def main(opts):
    ifh = open(opts['-i'])
    rdr = csv.reader(ifh)
    col = int(opts['-c']) - 1
    if not opts['-n']:
        print(','.join(next(rdr)))
    for line in rdr:
        if col < 0 or col > len(line) - 1:
            print "Invalid column", opts['-c']
            exit(1)
        line[col] = str(traypos_to_chamber_index(line[col]))
        print(','.join(line))

if __name__ == "__main__":
    opts = docopt(CLI_DOC)
    main(opts)
