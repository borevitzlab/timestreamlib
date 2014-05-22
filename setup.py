from setuptools import setup

desc = """
timestream: Utilities and a python library for manipulating timelapses in the
            TimeStream format
"""

install_requires = [
        "ExifRead==1.4.2",
        "docopt==0.6.1",
        "voluptuous==0.8.4",
        ]

test_requires = [
        "coverage==3.7.1",
        "nose==1.3.0",
        "pep8==1.4.6",
        "pylint==1.0.0",
        ]

setup(
    name="timestream",
    packages=[
        'timestream',
        'timestream.parse',
        'timestream.util',
        ],
    version="0.1a2",
    install_requires=install_requires,
    tests_require=test_requires,
    description=desc,
    author="Kevin Murray",
    author_email="spam@kdmurray.id.au",
    url="https://github.com/borevitzlab/timestream",
    keywords=["timestream", "timelapse", "photography", "video"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: GNU General Public License v3 or later " +
            "(GPLv3+)",
        ],
    test_suite="test",
    )
