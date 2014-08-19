"""
Created on Mon Jun 16 2014

@author: Chuong Nguyen, chuong.nguyen@anu.edu.au

"""
from __future__ import absolute_import, division, print_function

import sys
from PyQt4 import QtGui, QtCore

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
import matplotlib.pyplot as plt

import os, shutil
import cv2
import numpy as np
import timestream
import timestream.manipulate.correct_detect as cd
import yaml
from timestream.manipulate import pipeline

class Window(QtGui.QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.hide()

        # Timestream info
        self.timestreamLabel = QtGui.QLabel('Time-stream root path:')
        self.timestreamText = QtGui.QLineEdit('')
        self.timestreamText.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

        self.timestreamDateLabel = QtGui.QLabel('Start date (yyyy_mm_dd_hh_mm_ss):')
        self.timestreamDateText = QtGui.QLineEdit('')
        self.timestreamDateText.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

        self.timestreamTimeLabel = QtGui.QLabel('Time interval (seconds):')
        self.timestreamTimeText = QtGui.QLineEdit('')
        self.timestreamTimeText.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)

        self.initStreamTimeButton = QtGui.QPushButton('&Initialise timestream by time')
        self.initStreamTimeButton.clicked.connect(self.initialiseTimestreamByTime)

        self.initStreamFileButton = QtGui.QPushButton('&Initialise timestream by files')
        self.initStreamFileButton.clicked.connect(self.initialiseTimestreamByFiles)

        # Image loading and processing
        self.loadImageButton = QtGui.QPushButton('&Load (next) image')
        self.loadImageButton.clicked.connect(self.loadImage)

        self.rotateImageButton = QtGui.QPushButton('&Rotate 90-deg')
        self.rotateImageButton.clicked.connect(self.rotateImage90Degrees)

        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.slider.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        self.slider.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.slider.setMinimum(-16)
        self.slider.setMaximum(16)
        self.slider.setValue(0)
        self.slider.setTickInterval(4)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.rotateSmallAngle)

        self.applySmallRotationButton = QtGui.QPushButton('&Apply')
        self.applySmallRotationButton.clicked.connect(self.applySmallRotation)

        self.loadCamCalibButton = QtGui.QPushButton('Load &cam. param.')
        self.loadCamCalibButton.clicked.connect(self.loadCamCalib)

        self.colorcardRadioButton = QtGui.QRadioButton('Select color car&d')
        self.colorcardRadioButton.setChecked(False)
        self.colorcardRadioButton.clicked.connect(self.selectWhat)

        self.trayRadioButton = QtGui.QRadioButton('Select &tray')
        self.trayRadioButton.setChecked(False)
        self.trayRadioButton.clicked.connect(self.selectWhat)

        self.trayRoundCheckBox = QtGui.QCheckBox('Round')
        self.trayRoundCheckBox.setChecked(True)

        self.potRadioButton = QtGui.QRadioButton('Select &pot')
        self.potRadioButton.setChecked(False)
        self.potRadioButton.clicked.connect(self.selectWhat)

        self.zoomButton = QtGui.QPushButton('&Zoom')
        self.zoomButton.setCheckable(True)
        self.zoomButton.clicked.connect(self.zoom)

        self.panButton = QtGui.QPushButton('&Pan')
        self.panButton.setCheckable(True)
        self.panButton.clicked.connect(self.pan)

        self.homeButton = QtGui.QPushButton('&Home')
        self.homeButton.clicked.connect(self.home)

        self.correctColorButton = QtGui.QPushButton('Correct colo&r')
        self.correctColorButton.clicked.connect(self.correctColor)

        self.save2PipelineButton = QtGui.QPushButton('&Save as pipeline settings')
        self.save2PipelineButton.clicked.connect(self.savePipelineSettings)

        self.testPipelineButton = QtGui.QPushButton('Test &pipeline processing')
        self.testPipelineButton.clicked.connect(self.testPipeline)

        self.status = QtGui.QTextEdit('')
        self.status.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        self.mousePosition = QtGui.QLabel('')

        # set the layout
        layout = QtGui.QHBoxLayout()
        rightWidget = QtGui.QWidget()
        buttonlayout = QtGui.QVBoxLayout(rightWidget)
        buttonlayout.addWidget(self.timestreamLabel)
        buttonlayout.addWidget(self.timestreamText)
        buttonlayout.addWidget(self.timestreamDateLabel)
        buttonlayout.addWidget(self.timestreamDateText)
        buttonlayout.addWidget(self.timestreamTimeLabel)
        buttonlayout.addWidget(self.timestreamTimeText)
        buttonlayout.addWidget(self.initStreamTimeButton)
        buttonlayout.addWidget(self.initStreamFileButton)
        buttonlayout.addWidget(self.loadImageButton)
        buttonlayout.addWidget(self.loadCamCalibButton)
        buttonlayout.addWidget(self.rotateImageButton)

        layoutSmallRotation = QtGui.QHBoxLayout()
        layoutSmallRotation.addWidget(self.slider)
        layoutSmallRotation.addWidget(self.applySmallRotationButton)
        buttonlayout.addLayout(layoutSmallRotation)

        buttonlayout.addWidget(self.colorcardRadioButton)

        layoutTrayShape = QtGui.QHBoxLayout()
        layoutTrayShape.addWidget(self.trayRadioButton)
        layoutTrayShape.addWidget(self.trayRoundCheckBox)
        buttonlayout.addLayout(layoutTrayShape)

        buttonlayout.addWidget(self.potRadioButton)
        buttonlayout.addWidget(self.zoomButton)
        buttonlayout.addWidget(self.panButton)
        buttonlayout.addWidget(self.homeButton)
        buttonlayout.addWidget(self.correctColorButton)
        buttonlayout.addWidget(self.save2PipelineButton)
        buttonlayout.addWidget(self.testPipelineButton)
        buttonlayout.addWidget(self.status)
        buttonlayout.addWidget(self.mousePosition)
        rightWidget.setMaximumWidth(250)
        leftLayout = QtGui.QVBoxLayout()
        leftLayout.addWidget(self.toolbar)
        leftLayout.addWidget(self.canvas)

        layout.addWidget(rightWidget)
        layout.addLayout(leftLayout)
        self.setLayout(layout)

        self.group = QtGui.QButtonGroup()
        self.group.addButton(self.colorcardRadioButton)
        self.group.addButton(self.trayRadioButton)
        self.group.addButton(self.potRadioButton)

        self.loadPreviousInputs()

        self.panMode = False
        self.zoomMode = False

        self.ts = None
        self.tsImages = None
        self.ax = None
        self.plotRect = None
        self.plotImg = None
        self.image = None
        self.potTemplate = None
        self.UndistMapX = None
        self.UndistMapY = None
        self.trayAspectRatio = 0.835
        self.colorcardAspectRatio = 1.5
        self.potAspectRatio = 1.0
        self.leftClicks = []
        self.colorcardParams = None
        self.scriptPath = os.path.dirname(os.path.realpath(__file__))
        self.timestreamRootPath = None
        self.pl = None

        # Ouput parameters
        self.ImageSize = None
        self.colorcardList = []
        self.trayList = []
        self.potList = []
        self.rotationAngle = 0.0
        self.smaleRotationAngle = 0.0
        self.CameraMatrix = None
        self.DistCoefs = None
        self.isDistortionCorrected = False
        self.settingFileName = None

    def selectWhat(self):
        if self.trayRadioButton.isChecked():
            self.status.append('Start selecting tray.')
        elif self.colorcardRadioButton.isChecked():
            self.status.append('Start selecting color bar.')
        else:
            self.status.append('Start selecting pot.')

    def home(self):
        self.toolbar.home()
    def zoom(self):
        self.toolbar.zoom()
        if not self.zoomMode:
            self.zoomMode = True
            self.panMode = False
            self.panButton.setChecked(False)
        else:
            self.zoomMode = False
    def pan(self):
        self.toolbar.pan()
        if not self.panMode:
            self.panMode = True
            self.zoomMode = False
            self.zoomButton.setChecked(False)
        else:
            self.panMode = False

    def initialiseTimestreamByTime(self):
        self.timestreamRootPath = str(self.timestreamText.text())
        if len(self.timestreamRootPath) > 0:
            self.status.append('Initialise a timestream at ' + str(self.timestreamRootPath))
            self.ts = timestream.TimeStream()
            self.ts.load(self.timestreamRootPath)
            self.status.append('Done')
            startDate = None
            timeInterval = None
            date = str(self.timestreamDateText.text())
            if len(date) > 0:
                startDate = timestream.parse.ts_parse_date(date)
            time = str(self.timestreamTimeText.text())
            if len(time) > 0:
                timeInterval = int(eval(time))
            self.tsImages = self.ts.iter_by_timepoints(start = startDate, interval = timeInterval, remove_gaps=False)
            self.loadImage()
        else:
            self.status.append('Please provide timestream root path.')

    def initialiseTimestreamByFiles(self):
        self.timestreamRootPath = str(self.timestreamText.text())
        if len(self.timestreamRootPath) > 0:
            self.status.append('Initialise a timestream at ' + str(self.timestreamRootPath))
            self.ts = timestream.TimeStream()
            self.ts.load(self.timestreamRootPath)
            self.status.append('Done')
            self.tsImages = self.ts.iter_by_files()
            self.loadImage()
        else:
            self.status.append('Please provide timestream root path.')

    def loadImage(self):
        ''' load and show an image'''
        if self.tsImages != None:
            try:
                tsImage = self.tsImages.next()
                if tsImage.pixels == np.array([]):
                    self.status.append('Missing image.')
            except:
                tsImage.pixels == np.array([])
                self.status.append('There is no more images.')

            if tsImage.pixels == np.array([]):
                self.image = None
                self.updateFigure()
                return
            self.image = tsImage.pixels
            fname = tsImage.path
        else:
            fname = QtGui.QFileDialog.getOpenFileName(self, 'Open image', '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-orig/2014/2014_06/2014_06_24/2014_06_24_08/')
            app.processEvents()
            if len(fname) == 0:
                return
            self.image = cv2.imread(str(fname))[:,:,::-1]
        self.status.append('Loaded image from ' + str(fname))

        # reset all outputs
#        self.colorcardList = []
#        self.trayList = []
#        self.potList = []
        self.isDistortionCorrected = False

        if self.rotationAngle != None:
            self.image = cd.rotateImage(self.image, self.rotationAngle + self.smaleRotationAngle)

        # Undistort image if mapping available
        if not self.isDistortionCorrected and self.UndistMapX != None and self.UndistMapY != None:
            self.image = cv2.remap(self.image.astype(np.uint8), self.UndistMapX, self.UndistMapY, cv2.INTER_CUBIC)
            self.isDistortionCorrected = True

        self.updateFigure()

    def changeCursor(self, event):
#        cursor = Cursor(self.ax, useblit=True, color='red', linewidth=1)
        self.canvas.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor ))

    def updateFigure(self, image = None, resetFigure = False):
        if self.image != None:
            if image == None:
                image = self.image
            if self.ax == None:
                self.ax = self.figure.add_subplot(111)
                self.ax.figure.canvas.mpl_connect('button_press_event', self.onMouseClicked)
                self.ax.figure.canvas.mpl_connect('motion_notify_event', self.onMouseMoves)
                self.ax.figure.canvas.mpl_connect('figure_enter_event', self.changeCursor)
            self.ax.hold(False)
            if self.plotImg == None or resetFigure:
                self.plotImg = self.ax.imshow(image)
            else:
                self.plotImg.set_data(image)
            self.figure.tight_layout()

        xs, ys = [], []
        for Rect in self.colorcardList:
            tl, bl, br, tr = Rect
            xs = xs + [tl[0], bl[0], br[0], tr[0], tl[0], np.nan]
            ys = ys + [tl[1], bl[1], br[1], tr[1], tl[1], np.nan]
        for Rect in self.trayList:
            tl, bl, br, tr = Rect
            xs = xs + [tl[0], bl[0], br[0], tr[0], tl[0], np.nan]
            ys = ys + [tl[1], bl[1], br[1], tr[1], tl[1], np.nan]
        for Rect in self.potList:
            tl, bl, br, tr = Rect
            xs = xs + [tl[0], bl[0], br[0], tr[0], tl[0], np.nan]
            ys = ys + [tl[1], bl[1], br[1], tr[1], tl[1], np.nan]
        for x,y in self.leftClicks:
            xs = xs + [x]
            ys = ys + [y]
#        if self.crosshair != None:
#            xs = xs + [np.nan, 0, self.image.shape[1], np.nan, self.crosshair[0], self.crosshair[0], np.nan]
#            ys = ys + [np.nan, self.crosshair[1], self.crosshair[1], np.nan, 0, self.image.shape[0], np.nan]
        if len(xs) > 0 and len(ys) > 0:
            if self.plotRect == None:
                self.ax.hold(True)
                self.plotRect, = self.ax.plot(xs, ys, 'b')
                self.ax.hold(False)
                self.ax.set_xlim([0,self.image.shape[1]])
                self.ax.set_ylim([0,self.image.shape[0]])
                self.ax.invert_yaxis()
            else:
                self.plotRect.set_data(xs, ys)
        self.canvas.draw()

        app.processEvents()


    def loadCamCalib(self):
        ''' load camera calibration image and show an image'''
        calibPath = os.path.join(self.scriptPath, './data')
        CalibFile = QtGui.QFileDialog.getOpenFileName(self, 'Open image', calibPath)
        self.ImageSize, SquareSize, self.CameraMatrix, self.DistCoefs, RVecs, TVecs = cd.readCalibration(CalibFile)
        self.status.append('Loaded camera parameters from ' + CalibFile)
        print('CameraMatrix =', self.CameraMatrix)
        print('DistCoefs =', self.DistCoefs)
        self.UndistMapX, self.UndistMapY = cv2.initUndistortRectifyMap(self.CameraMatrix, self.DistCoefs, \
            None, self.CameraMatrix, self.ImageSize, cv2.CV_32FC1)

        if self.image != None:
            self.image = cv2.remap(self.image.astype(np.uint8), self.UndistMapX, self.UndistMapY, cv2.INTER_CUBIC)
            self.isDistortionCorrected = True
            self.status.append('Corrected image distortion.')
            self.updateFigure()

#    def loadPotTemplate(self):
#        ''' load pot template image'''
#        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open image', '/home/chuong/Workspace/traitcapture-bin/unwarp_rectify/data')
#        self.status.append('Loading image...')
#        app.processEvents()
#        self.potTemplate = cv2.imread(str(fname))[:,:,::-1]
#        if len(self.potList) > 0:

    def correctColor(self):
        if self.colorcardParams == None:
            if len(self.colorcardList) > 0:
                medianSize = cd.getMedianRectSize(self.colorcardList)
                capturedColorcards = cd.rectifyRectImages(self.image, self.colorcardList, medianSize)
                self.colorcardColors, _ = cd.getColorcardColors(capturedColorcards[0], GridSize = [6, 4])
                self.colorcardParams = cd.estimateColorParameters(cd.CameraTrax_24ColorCard, self.colorcardColors)
            else:
                self.status.append('Need to select a color card first.')
                return

        colorMatrix, colorConstant, colorGamma = self.colorcardParams
        self.imageCorrected = cd.correctColorVectorised(self.image.astype(np.float), colorMatrix, colorConstant, colorGamma)
        self.imageCorrected[np.where(self.imageCorrected < 0)] = 0
        self.imageCorrected[np.where(self.imageCorrected > 255)] = 255
        self.imageCorrected = self.imageCorrected.astype(np.uint8)
        self.updateFigure(self.imageCorrected)

    def savePipelineSettings(self):
        ''' save to pipeline setting file'''
        self.settingFileName = str(QtGui.QFileDialog.getSaveFileName(self, \
            'Save selection (default in ./_data)', self.timestreamRootPath))
        if len(self.settingFileName) == 0:
            return
        self.settingPath = os.path.relpath(os.path.dirname(self.settingFileName), self.timestreamRootPath)

        self.settings = {}
        if self.ImageSize != None and self.CameraMatrix != None and self.DistCoefs != None:
            undistortDic = {'cameraMatrix': self.CameraMatrix.tolist(), \
                          'distortCoefs': self.DistCoefs.tolist(), \
                          'imageSize': list(self.ImageSize),
                          'rotationAngle': self.rotationAngle + self.smaleRotationAngle
                         }
        else:
            undistortDic = {}
        self.settings['undistort'] = undistortDic

        if len(self.colorcardList) > 0:
            medianSize = cd.getMedianRectSize(self.colorcardList)
            capturedColorcards = cd.rectifyRectImages(self.image, self.colorcardList, medianSize)
            colorCardFile = 'CapturedColorcard.png'
            cv2.imwrite(os.path.join(self.timestreamRootPath, self.settingPath, colorCardFile), capturedColorcards[0][:,:,::-1].astype(np.uint8))
            colorcardColors, colorStd  = cd.getColorcardColors(capturedColorcards[0], GridSize = [6,4])
            colorcardPosition, Width, Height, Angle = cd.getRectangleParamters(self.colorcardList[0])
            colorcardDic = {'colorcardFile': colorCardFile,\
                            'colorcardPosition': colorcardPosition.tolist(),\
                            'colorcardTrueColors': cd.CameraTrax_24ColorCard,\
                            'settingPath': '_data'
                            }
        else:
            colorcardDic = {}
        self.settings['colorcarddetect'] = colorcardDic

        self.settings['colorcorrect'] = {'minIntensity': 15}

        if len(self.trayList) > 0:
            trayMedianSize = cd.getMedianRectSize(self.trayList)
            trayImages = cd.rectifyRectImages(self.image, self.trayList, trayMedianSize)
            trayDict = {}
            trayDict['settingPath'] = '_data'
            trayDict['trayNumber'] = len(self.trayList)
            trayDict['trayFiles'] = 'Tray_%02d.png'
            trayPositions = []
            for i,tray in enumerate(trayImages):
                cv2.imwrite(os.path.join(self.timestreamRootPath, self.settingPath, trayDict['trayFiles'] %i), tray[:,:,::-1].astype(np.uint8))
                trayPosition, Width, Height, Angle = cd.getRectangleParamters(self.trayList[i])
                trayPositions.append(trayPosition.tolist())
            trayDict['trayPositions'] = trayPositions
        else:
            trayDict = {}
        self.settings['traydetect'] = trayDict

        if len(self.potList) > 0:
            trayMedianSize = cd.getMedianRectSize(self.trayList)
            potPosition, Width, Height, Angle = cd.getRectangleParamters(self.potList[0])
            Width, Height = int(Width), int(Height)
            topLeft = [int(self.potList[0][0][0]), int(self.potList[0][0][1])]
            self.potImage = self.image[topLeft[1]:topLeft[1]+Height, topLeft[0]:topLeft[0]+Width, :]
            potFile = 'Pot.png'
            cv2.imwrite(os.path.join(self.timestreamRootPath, self.settingPath, potFile), self.potImage[:,:,::-1].astype(np.uint8))
            potDict = {}
            potDict['potPositions'] = potPosition.tolist()
            potDict['potSize'] = [int(Width), int(Height)]
            potDict['traySize'] = [int(trayMedianSize[0]), int(trayMedianSize[1])]
            potDict['potFile'] = potFile
            potDict['potTemplateFile'] = 'PotTemplate.png'
            potDict['settingPath'] = '_data'
            potTemplatePathIn = os.path.join(self.scriptPath, './data/PotTemplate.png')
            potTemplatePathOut = os.path.join(self.timestreamRootPath, self.settingPath, potDict['potTemplateFile'])
            shutil.copyfile(potTemplatePathIn, potTemplatePathOut)
            if self.potTemplate != None:
                potTemplateFile = 'potTemplate.png'
                cv2.imwrite(os.path.join(self.timestreamRootPath, self.settingPath, potTemplateFile), self.potTemplate[:,:,::-1])
                potDict['potTemplateFile'] = potTemplateFile
        else:
            potDict = {}
        self.settings['potdetect'] = potDict

        self.settings['plantextract'] = {'meth': 'method1',
                                         'methargs': {'threshold' : 0.6,
                                         'kSize' : 5, 'blobMinSize' : 50} }

        with open(self.settingFileName, 'w') as outfile:
            outfile.write( yaml.dump(self.settings, default_flow_style=None) )
            self.status.append('Saved initial data to ' + self.settingFileName)

    def testPipeline(self):
        ''' try running processing pipeline based on user inputs'''
        if self.tsImages != None:
            # load setting file if missing
            if self.settingFileName == None:
                settingFileName = str(QtGui.QFileDialog.getOpenFileName(self, 'Open pipeline setting file', self.ts.path))
                if len(settingFileName) > 0:
                    self.settingFileName = settingFileName
                else:
                    return
            # initialise pipeline
            if self.pl == None:
                f = file(self.settingFileName)
                self.settings = yaml.load(f)
                self.ts.data["settings"] = self.settings
                self.pl = pipeline.ImagePipeline(self.settings)
                # process only from undistortion to pot detection
                self.pl.pipeline = self.pl.pipeline[:5]

            # read next image instant of pipeline
            try:
                tsImage = self.tsImages.next()
                if tsImage == None:
                    self.status.append('Missing image.')
                    return
            except:
                tsImage = None
                self.status.append('There is no more images.')
                return
            self.status.append('Processing ' + tsImage.path)
            context = {"rts":self.ts, "wts":None, "img":tsImage}
            result = self.pl.process(context, [tsImage])
            self.image, potPosList2 = result
            potSize = self.settings[4][1]["potSize"]
            self.potList = []
            for potPosList in potPosList2:
                if potPosList == None:
                    continue
                for potPos in potPosList:
                    tl = [potPos[0] - potSize[0]//2, potPos[1] - potSize[1]//2]
                    bl = [potPos[0] - potSize[0]//2, potPos[1] + potSize[1]//2]
                    br = [potPos[0] + potSize[0]//2, potPos[1] + potSize[1]//2]
                    tr = [potPos[0] + potSize[0]//2, potPos[1] - potSize[1]//2]
                    self.potList.append([tl, bl, br, tr])
            self.updateFigure()
            self.status.append('Done')
        else:
            self.status.append('Pipeline or setting file is missing.')

    def rotateImage90Degrees(self):
        if self.image == None:
            self.status.append('No image to rotate.')
            return
        self.rotationAngle = self.rotationAngle + 90
        if self.rotationAngle >= 360:
            self.rotationAngle = self.rotationAngle - 360
        self.image = np.rot90(self.image) #.astype(uint8)
        self.status.append('Rot. angle = %d deg' %self.rotationAngle)
        self.updateFigure(resetFigure = True)

    def rotateSmallAngle(self, value):
        self.smaleRotationAngle = float(value)/4.0
        if self.image != None:
            self.rotatedImage = cd.rotateImage(self.image, self.smaleRotationAngle)
            self.updateFigure(self.rotatedImage)
            self.status.append('Rot. angle = %f deg' %(self.rotationAngle + self.smaleRotationAngle))

    def applySmallRotation(self):
        if self.image != None:
            self.image = cd.rotateImage(self.image, self.smaleRotationAngle)
            self.updateFigure()
            self.status.append('Apply small angle rotation')

    def onMouseClicked(self, event):
        if self.panMode or self.zoomMode:
            return
        print('click', event.button, event.xdata, event.ydata)

        if event.button == 1 and event.xdata != None and event.ydata != None:
            self.leftClicks.append([event.xdata, event.ydata])
            print('self.leftClicks =', self.leftClicks)
            Rect = []
            AspectRatio = None
            if self.trayRadioButton.isChecked():
                AspectRatio = self.trayAspectRatio
            elif self.colorcardRadioButton.isChecked():
                AspectRatio = self.colorcardAspectRatio
            elif self.potRadioButton.isChecked():
                AspectRatio = self.potAspectRatio

            if len(self.leftClicks) == 2 and AspectRatio != None:
                if self.colorcardRadioButton.isChecked():
                    Rect = cd.getRectCornersFrom2Points(self.image, self.leftClicks, AspectRatio)
                if self.trayRadioButton.isChecked():
                    Rect = cd.getRectCornersFrom2Points(self.image, self.leftClicks, AspectRatio, Rounded = self.trayRoundCheckBox.isChecked())
                elif self.potRadioButton.isChecked():
                    Rect = cd.getRectCornersFrom2Points(self.image, self.leftClicks, AspectRatio, Rounded = True)
                self.leftClicks = []
            elif len(self.leftClicks) == 4:
                Rect = [[x,y] for x,y in self.leftClicks]
                Rect = cd.correctPointOrder(Rect)
                self.leftClicks = []

            if len(Rect) > 0:
                if self.trayRadioButton.isChecked():
                    self.trayList.append(Rect)
                    self.status.append('Added tray selection.')
                elif self.colorcardRadioButton.isChecked():
                    self.colorcardList.append(Rect)
                    self.status.append('Added color card selection.')
                else:
                    self.potList.append(Rect)
                    self.status.append('Added pot selection.')
            self.updateFigure()
        elif event.button == 3:
            # remove the last selection
            if len(self.leftClicks) > 0:
                self.leftClicks = self.leftClicks[:-1]
                self.status.append('Removed a previous click')
            else:
                if self.trayRadioButton.isChecked() and len(self.trayList) > 0:
                    self.trayList = self.trayList[:-1]
                    self.status.append('Removed a previous tray selection')
                elif self.colorcardRadioButton.isChecked() and len(self.colorcardList) > 0:
                    self.colorcardList = self.colorcardList[:-1]
                    self.status.append('Removed a previous color card selection.')
                elif self.potRadioButton.isChecked() and len(self.potList) > 0:
                    self.potList = self.potList[:-1]
                    self.status.append('Removed a previous pot selection')
            self.updateFigure()
        else:
            print('Ignored click')

    def onMouseMoves(self, event):
        if event.inaxes == self.ax:
            self.mousePosition.setText('x=%d, y=%d' %(event.xdata, event.ydata))
#            self.crosshair = [event.xdata, event.ydata]
        else:
            self.mousePosition.setText('')
#            self.crosshair = None
#        self.updateFigure()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):

        quit_msg = "Are you sure you want to exit the program?"
        reply = QtGui.QMessageBox.question(self, 'Message',
                         quit_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.saveInputs()
            event.accept()
        else:
            event.ignore()

    def saveInputs(self):
        with open('./.inputs.yml', 'w') as myfile:
            dicInputs = {'rootPath': str(self.timestreamText.text()),
                         'startDate': str(self.timestreamDateText.text()),
                         'timeInterval': str(self.timestreamTimeText.text()),
                        }
            myfile.write( yaml.dump(dicInputs, default_flow_style=None) )

    def loadPreviousInputs(self):
        try:
            with open('./.inputs.yml', 'r') as myfile:
                dicInputs = yaml.load(myfile)
                self.timestreamText.setText(dicInputs['rootPath'])
                self.timestreamDateText.setText(dicInputs['startDate'])
                self.timestreamTimeText.setText(dicInputs['timeInterval'])
        except:
            pass
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    main = Window()
    main.setWindowTitle('Select Color Card, Trays, and Pot')
    main.show()

    sys.exit(app.exec_())