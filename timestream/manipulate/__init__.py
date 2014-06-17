from itertools import (
        cycle,
        izip,
        )
import logging
import multiprocessing

CONSOLE = logging.getLogger("CONSOLE")

def ts_parallel_map(ts_iter, func, args, procs=None):
    """Map ``func(item, *args)`` for each item in ``ts_iter`` in parallel"""
    # Setup pool
    if procs == None:
        procs = int(multiprocessing.cpu_count() * 0.9)
    pool = multiprocessing.Pool(procs)
    CONSOLE.debug("Made pool with {:d} processes".format(procs))
    # Setup args
    func_args = [ts_iter,]
    func_args.extend([cycle(arg) for arg in args])
    func_args = izip(*func_args)
    CONSOLE.debug("Made argument list")
    # Run imap
    for ret in pool.imap(func, func_args):
        yield ret
    pool.close()
    pool.join()
