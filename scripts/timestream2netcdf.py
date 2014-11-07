#!/usr/bin/env python

# NB: this additionally requires the netCDF4 package
from itertools import izip, imap
import logging
import netCDF4 as ncdf
from netCDF4 import date2num

from timestream.manipulate import (
    NOEOL,
)
from timestream.parse import (
    ts_iter_images,
    ts_parse_date_path,
    read_image,
)

def ts_to_tsnc(ts_path, tsnc_path):
    log = logging.getLogger("timestreamlib")
    # Get timestream images
    imgs = list(ts_iter_images(ts_path))
    # Make netcdf4 file
    root = ncdf.Dataset(tsnc_path, 'w', format="NETCDF4")
    root.createGroup('timestream')
    # Make dimensions
    # Kludge time!!!
    root.createDimension('y', mat0.shape[0])
    root.createDimension('x', mat0.shape[1])
    root.createDimension('z', mat0.shape[2])
    root.createDimension('t', None)
    mat0 = None
    mat_n = 0
    while mat0 is None:
        try:
            mat0 = read_image(imgs[mat_n])
            mat_n += 1
        except IndexError:
            raise ValueError("Didn't find a valid image in {}".format(ts_path))
    # setup variables
    times = root.createVariable("time", 'f8', ('t',))
    times.units = "seconds since 1970-01-01 00:00:00.0"
    times.calendar = "standard"
    root.createVariable("z", 'u1', ('z',))
    root.createVariable("y", 'u4', ('y',))
    root.createVariable("x", 'u4', ('x',))
    # create actual pixel array
    px_type = 'u{:d}'.format(mat0.dtype.itemsize)
    pixels = root.createVariable("pixel", px_type, ('t', 'y', 'x', 'z'),
                                 zlib=True)
    log.info("Created netcdf4 file {} with pixel array dimensions {!r}".format(
        tsnc_path, pixels.shape))
    # iteratively add images
    count = 0
    for img_n, mat in enumerate(imap(read_image, imgs)):
        img = imgs[img_n]
        if mat is None:
            continue
        n_dates = len(root.dimensions['t'])
        time = ts_parse_date_path(img)
        times[n_dates] = date2num([time, ], units=times.units,
                                  calendar=times.calendar)
        pixels[n_dates, :, :, :] = mat
        count += 1
        log.debug("Processed {}. Matrix shape is {!r}".format(img,
            pixels.shape))
        log.log(NOEOL, "Processed {: 5d} images.\r".format(count))
    log.info("Processed {: 5d} images. ts_to_tsnc finished!".format(count))
    root.close()
