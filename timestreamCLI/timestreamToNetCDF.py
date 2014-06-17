#!/usr/bin/python
from __future__ import print_function
import docopt
from timestream.manipulate import setup_console_logger
from timestream.manipulate.netcdf import ts_to_tsnc


CLI = """
USAGE:
timestreamToNetCDF.py -i IN_TIMESTREAM -o OUT_NETCDF

OPTIONS:
    -i IN_TIMESTREAM    Input timestream
    -o OUT_NETCDF       Output timestream as netcdf.
"""


def main(opts):
    setup_console_logger()
    ts_to_tsnc(opts['-i'], opts['-o'])

if __name__ == "__main__":
    main(docopt.docopt(CLI))
