*******************
Configuration Files
*******************

Configuration Options
=====================

.. _configuration_options:

pipeline
--------

Expects a list of pipeline components. Is required. Defaults to a list
with no components. Is a list of pipeline components that take action on a Time
Stream

Example:

::

    pipeline:
    - name: undistort
      mess: '---Perform optical undistortion---'
    - name: colorcarddetect
      mess: '---Perform color card detection---'

outstreams
----------

Expects type list of outstream names. Is optional. Defaults to a list with no
outstreams. A list of output stream names that get translated into output stream
directories. These names are to be used with output components such as the image
writer.

Example:

::

    outstreams:
    - { name: cor }
    - { name: seg }

general
-------

Expects type named list of configuration elements. Is required. Defaults to not
configuration elements. List of general settings that will define the behavior
of the pipeline. Some of these include date range, time range and time interval.

Example:

::

    general:
      timeInterval: 900
      visualise: False

general.startDate
-----------------

Expects date values. Is optional. Defaults to None. The starting date of the
Time Stream. All prior dates will be ignored. It contains six elements: year,
month, day, hour, minute, second.

Example:

::

    startDate: { year: 2014, month: 06, day: 25, hour: 9, minute: 0, second: 0 }

general.endDate
---------------

Expects date values. is optional. Defaults to None. The ending date of the Time
Stream. Ignore all posterior dates. It contains six elements: year, month, day,
hour, minute, second.

Example:

::

    endDate: { year: 2014, month: 06, day: 25, hour: 9, minute: 0, second: 0 }

general.startHourRange
----------------------

Expects time values. Is optional. Defaults to None. Specific range within each
day can be specified. All previous hours for each day will be ignored. Contains
three elements: hour, minute, second

Example:

::

    startHourRange: { hour: 0, minute: 0, second: 0}

general.endHourRange
--------------------

Expects time values. Is optional. Defaults to None. A specific range within each
day can be specified. All posterior hours for each day will be ignored. It
contains three elements: hour, minute, second

Example:

::

    endHourRange: { hour: 15, minute: 0, second: 0}

general.timeInterval
--------------------

Expects a number. Is optional. Defaults to None. A step interval starting from
general.startDate. The interval is in seconds

Example:

::

    timeInterval: 900

general.visualise
-----------------

Expects boolean. Is optional. Defaults to False. This is mostly for debugging.
When True, the pipeline will pause at each component and visualize the step.
This is discouraged for normal use as it stops the pipeline.

Example:

::

    visualise: True

general.metas
-------------

Expects a named list. Is optional. Defaults to empty list. Each element detected
in the image will have an id based on order of detection. This id will be the
same for all images. general.metas allows the customization of this id into
something more relevant. Each element in general.metas is a dictionary that
contains the ImageId / CustomId relation.

Example:

::

    metas:
      tlpid : {1: 09A1, 2: 09A2, 3: 09A3, 4: 09A4}
      plantid: {1: 16161, 2: 16162, 3: 16163, 4: 16164}

general.inputRootPath
---------------------

Expects a string. Is required. Defaults to None. The directory that holds the
input Time Stream

Example:

::

    ~/Experiments/BVZ0036/BVZ0036-GC02R-C01~fullres-orig

general.outputRootPath
----------------------

Expects a string. Is optional. Defaults to None. Directory where resulting
directories will be put

Example:

::

    outputRootPath: BVZ0036-GC02R-C01~fullres

general.outputPrefix
--------------------

Expects a string. Is optional. Defaults to None. By default the output will have
the same name as the input directory plus a relevant suffix. This variable
overrides this behavior and uses a custom name. The output Time Stream suffix is
still added.

Example:

::

    outputPrefix: BVZ0036-GC02R-C01~fullres


Configuration Examples
======================

.. _configuration_examples:

The timestreamlib library can manage two configuration files: (i) one that
handles specifics of each time stream and (ii) a more general one that can be
associated with more than one time stream. Both are in `YAML
<http://www.yaml.org/>`_ format; the first is usually named ``timestream.yml``
while the second is named ``pipeline.yml``.

timestream.yml example
----------------------

::

    undistort:
      cameraMatrix:
      - [4234.949389, 0.0, 2591.5]
      - [0.0, 4234.949389, 1727.5]
      - [0.0, 0.0, 1.0]
      distortCoefs: [-0.166191, 0.142034, 0.0, 0.0, 0.0]
      imageSize: [5184, 3456]
      rotationAngle: 180
    colorcarddetect:
      colorcardFile: CapturedColorcard.png
      colorcardPosition: [2692.3015027273236, 1573.2581105092597]
      colorcardTrueColors:
      - [115.0, 196.0, 91.0, 94.0, 129.0, 98.0, 223.0, 58.0, 194.0, 93.0, 162.0, 229.0,
        49.0, 77.0, 173.0, 241.0, 190.0, 0.0, 242.0, 203.0, 162.0, 120.0, 84.0, 50.0]
      - [83.0, 147.0, 122.0, 108.0, 128.0, 190.0, 124.0, 92.0, 82.0, 60.0, 190.0, 158.0,
        66.0, 153.0, 57.0, 201.0, 85.0, 135.0, 243.0, 203.0, 163.0, 120.0, 84.0, 50.0]
      - [68.0, 127.0, 155.0, 66.0, 176.0, 168.0, 47.0, 174.0, 96.0, 103.0, 62.0, 41.0,
        147.0, 71.0, 60.0, 25.0, 150.0, 166.0, 245.0, 204.0, 162.0, 120.0, 84.0, 52.0]
      settingPath: _data
    traydetect:
      settingPath: _data
      trayFiles: Tray_%02d.png
      trayNumber: 8
      trayPositions:
      - [818.0761402657033, 2462.1591636537523]
      - [1970.4242733553706, 2467.2637865082843]
      - [3117.65419882686, 2462.3500598446635]
      - [4269.311435725616, 2418.3133608083576]
      - [799.9851021748162, 1045.3911201462004]
      - [1967.556065737193, 1024.2273934825796]
      - [3133.567925490481, 1028.7864972916682]
      - [4311.802615716479, 1009.5636668189586]
    potdetect:
      potFile: Pot.png
      potPositions: [2980.8016283420193, 1944.1371163259664]
      potSize: [255, 262]
      potTemplateFile: PotTemplate.png
      settingPath: _data
      traySize: [1129, 1364]
    plantextract:
      meth: method1
      methargs: { threshold : 0.6, kSize : 5, blobMinSize : 50 } 

    outputPrefix: BVZ0036-GC02L-C01~fullres

pipeline.yml example
----------------------

::

    pipeline:
    - name: undistort
      mess: '---Perform optical undistortion---'
    - name: colorcarddetect
      mess: '---Perform color card detection---'
    - name: colorcorrect
      mess: '---Perform color correction---'
    - name: traydetect
      mess: '---Perform tray detection---'
    - name: potdetect
      mess: '---Perform pot detection---'
    - name: imagewrite
      mess: '---Writing Image---'
      outstream: cor
    - name: plantextract
      mess: '---Performing plant segmentation---'
    - name: featureextract
      mess: '---Extracting features---'
      features: ["all"]
    - name: imagewrite
      mess: '---Writing Image---'
      outstream: seg
      addStats: ["leafcount1"]
      masked: False
    - name: writefeatures
      mess: '---Writing Features---'

    outstreams:
      - { name: cor }
      - { name: seg }

    general:
      startDate: { year: 2014, month: 06, day: 25, hour: 9, minute: 0, second: 0}
      endDate: {}
      startHourRange: { hour: 9, minute: 0, second: 0}
      endHourRange: { hour: 15, minute: 0, second: 0}
      timeInterval: 900
      visualise: False

***********************
Component Configuration
***********************

Configuration Options
=====================

.. _component_configuration_options:


imagewrite
----------

::

  (Initializing Args)
    mess(optional): Output Message
    addStats(optional): List of statistics
    outstream(required): Name of stream to use
    masked(optional): Whether to output masked images
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    None

potdetect
---------

::

  (Initializing Args)
    potFile(required): File name of a pot image
    mess(optional): Detect pot position
    settingPath(required): Path to setting files
    potPositions(required): Estimated pot positions
    potSize(required): Estimated pot size
    potTemplateFile(required): File name of a pot template image
    traySize(required): Estimated tray size
  (Args Received)
    <class 'timestream.TimeStreamImage'>
    <type 'list'>
    <type 'list'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

potdetectglasshouse
-------------------

::

  (Initializing Args)
    mess(optional): Just set pot position fron config file
    potRectangle(required): Pot bounding box
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

derandomize
-----------

::

  (Initializing Args)
    mess(optional): Output Message
    derandStruct(required): Derandomization Structure
  (Args Received)
    <type 'datetime.datetime'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

traydetect
----------

::

  (Initializing Args)
    mess(optional): Detect tray positions
    trayNumber(required): Number of trays in given image
    settingPath(required): Path to setting files
    trayFiles(required): File name pattern for trays such as Trays_%02d.png
    trayPositions(required): Estimated tray positions
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>
    <type 'list'>
    <type 'list'>

writefeatures
-------------

::

  (Initializing Args)
    mess(optional): Default message
    timestamp(optional): Timestamp format
    ext(optional): Output Extension
    outname(optional): String to append to outputPrefixPath
    overwrite(optional): Whether to overwrite out files
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

resize
------

::

  (Initializing Args)
    mess(optional): Output Message
    resolution(optional): Resolution, scale factor or None
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

plantextract
------------

::

  (Initializing Args)
    mess(optional): Extract plant biometrics
    methargs(optional): Args: maxIter, epsilon, attempts
    meth(optional): Segmentation Method
    minIntensity(optional): Skip if intensity below value
    parallel(optional): Whether to run in parallel
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

colorcorrect
------------

::

  (Initializing Args)
    mess(optional): Correct image color
    fieldOfView(optional): Field of view in degrees
    minIntensity(optional): Skip when below this value
  (Args Received)
    <class 'timestream.TimeStreamImage'>
    <type 'tuple'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

undistort
---------

::

  (Initializing Args)
    mess(required): Apply lens distortion correction
    cameraMatrix(required): 3x3 matrix that maps physical to screen coordinates
    distortCoefs(required): 5x1 matrix for image distortion
    rotationAngle(required): rotation angle for the image
    imageSize(required): 2x1 matrix: [width, height]
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>

colorcarddetect
---------------

::

  (Initializing Args)
    colorcardFile(required): Path to the color card file
    backgroundWindow(optional): top-left and botom-right points of background region
    settingPath(required): Path to setting files
    minIntensity(optional): Skip colorcard detection if intensity below this value
    mess(required): Detect color card
    maxIntensity(optional): Max intensity when using white background
    useWhiteBackground(optional): Use white background as reference
    colorcardTrueColors(required): Matrix with 'true' color card colors
    colorcardPosition(required): (x,y) of the colorcard
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>
    <type 'tuple'>

featureextract
--------------

::

  (Initializing Args)
    mess(optional): Default message
    features(optional): Features to extract
  (Args Received)
    <class 'timestream.TimeStreamImage'>
  (Args Returned)
    <class 'timestream.TimeStreamImage'>
