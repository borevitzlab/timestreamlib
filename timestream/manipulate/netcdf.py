import netCDF4 as ncdf
from netCDF4 import num2date, date2num, date2index
from timestream.parse import ts_iter_images
from timestream.parse import ts_iter_numpy
from timestream.parse import ts_parse_date_path

def ts_to_tsnc(ts_path, tsnc_path):
    # Get timestream images
    imgs = list(ts_iter_images(ts_path))
    mats = ts_iter_numpy(imgs)
    # Make netcdf4 file
    root = ncdf.Dataset(tsnc_path, 'w', format="NETCDF4")
    ts = root.createGroup('timestream')
    # Make dimensions
    # Kludge time!!!
    mat0 = next(ts_iter_numpy([imgs[0], ]))[1]
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
    pixels = root.createVariable("pixel", 'u1', ('t', 'y', 'x', 'z'), zlib=True)
    # iteratively add images
    for img, mat in mats:
        n_dates = len(root.dimensions['t'])
        time = ts_parse_date_path(img)
        times[n_dates] = date2num([time,], units=times.units,
                calendar=times.calendar)
        pixels[n_dates, :, :, :] = mat
    root.close()
