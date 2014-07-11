from itertools import izip, imap
import logging
import netCDF4 as ncdf
from netCDF4 import num2date, date2num, date2index

from timestream.manipulate import (
        NOEOL,
        )
from timestream.parse import (
        ts_iter_images,
        read_image,
        ts_parse_date_path,
        )

def ts_to_tsnc(ts_path, tsnc_path):
    log = logging.getLogger("CONSOLE")
    # Get timestream images
    imgs = list(ts_iter_images(ts_path))
    # Make netcdf4 file
    root = ncdf.Dataset(tsnc_path, 'w', format="NETCDF4")
    ts = root.createGroup('timestream')
    # Make dimensions
    # Kludge time!!!
    mat0 = None
    mat_n = 0
    while mat0 is None:
        try:
            mat0 = read_image(imgs[mat_n])
            mat_n += 1
        except IndexError:
            raise ValueError("Didn't find a valid image in {}".format(ts_path))
    dimy = root.createDimension('y', mat0.shape[0])
    dimx = root.createDimension('x', mat0.shape[1])
    dimz = root.createDimension('z', mat0.shape[2])
    dimt = root.createDimension('t', None)
    # setup variables
    times = root.createVariable("time", 'f8', ('t',))
    times.units = "seconds since 1970-01-01 00:00:00.0"
    times.calendar = "standard"
    zs = root.createVariable("z", 'u1', ('z',))
    ys = root.createVariable("y", 'u4', ('y',))
    xs = root.createVariable("x", 'u4', ('x',))
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
        times[n_dates] = date2num([time,], units=times.units,
                calendar=times.calendar)
        pixels[n_dates, :, :, :] = mat
        count += 1
        log.debug("Processed {}. Matrix shape is {!r}".format(img,
            pixels.shape))
        log.log(NOEOL, "Processed {: 5d} images.\r".format(count))
    log.info("Processed {: 5d} images. ts_to_tsnc finished!".format(count))
    root.close()
