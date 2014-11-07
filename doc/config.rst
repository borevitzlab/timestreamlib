*******************
Configuration Files
*******************

Configuration Options
=====================

..  This section should be automatically generated. It should list all the
    configuration options and their meaning.

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
      enddate: {}
      startHourRange: { hour: 9, minute: 0, second: 0}
      endHourRange: { hour: 15, minute: 0, second: 0}
      timeInterval: 900
      visualise: False

