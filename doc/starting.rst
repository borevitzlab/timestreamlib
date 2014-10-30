***************
Getting Started
***************

Installing Timestreamlib
========================


Windows
-------

.. _installing-windows-dependencies:

**Dependencies**

 * ``Python 2.x``: You will need python 2.x. We have not tested with python 3.x.
   You can download for windows `Here <https://www.python.org/downloads/windows/>`_.

 * ``Qt for Python``: This is needed if you are going to run the timestreamlib
   GUI. Download it from `here <http://www.riverbankcomputing.com/software/pyqt/download>`_.

 * ``GIT``: Download it `here <http://git-scm.com/download/win>`_.

 * ``pip-win``: To aid with pip install. Download it `here
   <https://sites.google.com/site/pydatalog/python/pip-for-windows>`_.

 * ``numpy``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy>`_.

 * ``matplotlib``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#matplotlib>`_.

 * ``scipy``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy>`_.

 * ``pip``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pip>`_.

 * ``python-opencv``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv>`_.

 * ``netcdf4``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#netcdf4>`_.

 * ``scikit-image``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-image>`_.

 * ``python-dateutil``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#python-dateutil>`_.

 * ``pyyaml``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyyaml>`_.

 * ``six``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#six>`_.

 * ``pyparsing``: `Here <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyparsing>`_.

.. _installing-windows-timestreamlib:

**Installing timestreamlib**

 We use pip to install from our git repository. We suggest you install the
 master branch as it is more stable. You  can also select the branch to install
 from by replacing `master` with `next`. To run `pip install` execute `pip-win`
 and enter `pip install -e
 git://github.com/borevitzlab/timestreamlib@master#egg=timestreamlib` in the
 command prompt

.. _installing-linux-dependencies:

Linux
-----

Linux installation instructions
