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

import os
import cv2
import numpy as np
import timestream.manipulate.correct_detect as cd
import yaml

class Window(QtGui.QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.hide()

        # Just some button
        self.colorcardRadioButton = QtGui.QRadioButton('Select color car&d')
        self.colorcardRadioButton.setChecked(False)
        self.colorcardRadioButton.clicked.connect(self.selectWhat)

        self.trayRadioButton = QtGui.QRadioButton('Select &tray')
        self.trayRadioButton.setChecked(False)
        self.trayRadioButton.clicked.connect(self.selectWhat)

        self.potRadioButton = QtGui.QRadioButton('Select &pot')
        self.potRadioButton.setChecked(False)
        self.potRadioButton.clicked.connect(self.selectWhat)

        self.loadImageButton = QtGui.QPushButton('&Load image')
        self.loadImageButton.clicked.connect(self.loadImage)

        self.rotateImageButton = QtGui.QPushButton('&Rotate 90-deg')
        self.rotateImageButton.clicked.connect(self.rotateImage90Degrees)

        self.loadCamCalibButton = QtGui.QPushButton('Load &cam. param.')
        self.loadCamCalibButton.clicked.connect(self.loadCamCalib)

        self.save2PipelineButton = QtGui.QPushButton('&Save as pipeline settings')
        self.save2PipelineButton.clicked.connect(self.savePipelineSettings)

        self.zoomButton = QtGui.QPushButton('&Zoom')
        self.zoomButton.setCheckable(True)
        self.zoomButton.clicked.connect(self.zoom)

        self.panButton = QtGui.QPushButton('&Pan')
        self.panButton.setCheckable(True)
        self.panButton.clicked.connect(self.pan)

        self.homeButton = QtGui.QPushButton('&Home')
        self.homeButton.clicked.connect(self.home)

        self.status = QtGui.QTextEdit('')
        self.status.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        self.mousePosition = QtGui.QLabel('')

        # set the layout
        layout = QtGui.QHBoxLayout()
        rightWidget = QtGui.QWidget()
        buttonlayout = QtGui.QVBoxLayout(rightWidget)
        buttonlayout.addWidget(self.loadImageButton)
        buttonlayout.addWidget(self.rotateImageButton)
        buttonlayout.addWidget(self.loadCamCalibButton)
        buttonlayout.addWidget(self.colorcardRadioButton)
        buttonlayout.addWidget(self.trayRadioButton)
        buttonlayout.addWidget(self.potRadioButton)
        buttonlayout.addWidget(self.zoomButton)
        buttonlayout.addWidget(self.panButton)
        buttonlayout.addWidget(self.homeButton)
        buttonlayout.addWidget(self.save2PipelineButton)
        buttonlayout.addWidget(self.status)
        buttonlayout.addWidget(self.mousePosition)
        rightWidget.setMaximumWidth(200)
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

        self.panMode = False
        self.zoomMode = False

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

        self.ImageSize = None
        self.CameraMatrix = None
        self.DistCoefs = None

#        # change cursor shape
#        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor ))

        # Ouput parameters
        self.colorcardList = []
        self.trayList = []
        self.potList = []
        self.rotationAngle = 0
        self.isDistortionCorrected = False

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

    def loadImage(self):
        ''' load and show an image'''
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open image', '/mnt/phenocam/a_data/TimeStreams/Borevitz/BVZ0036/BVZ0036-GC02L-C01~fullres-orig/2014/2014_06/2014_06_24/2014_06_24_08/')
        if len(fname) == 0:
            return
        self.status.append('Loading image...')
        app.processEvents()
        self.image = cv2.imread(str(fname))[:,:,::-1]
        self.status.append('Loaded image from ' + str(fname))

        # reset all outputs
        self.colorcardList = []
        self.trayList = []
        self.potList = []
        self.rotationAngle = 0
        self.isDistortionCorrected = False

        # Undistort image if mapping available
        if not self.isDistortionCorrected and self.UndistMapX != None and self.UndistMapY != None:
            self.image = cv2.remap(self.image.astype(np.uint8), self.UndistMapX, self.UndistMapY, cv2.INTER_CUBIC)
            self.isDistortionCorrected = True

        if self.image != None:
            if self.ax == None:
                self.ax = self.figure.add_subplot(111)
                self.ax.figure.canvas.mpl_connect('button_press_event', self.onMouseClicked)
                self.ax.figure.canvas.mpl_connect('motion_notify_event', self.onMouseMoves)
                self.ax.figure.canvas.mpl_connect('figure_enter_event', self.changeCursor)
            self.ax.hold(False)
            if self.plotImg == None:
                self.plotImg = self.ax.imshow(self.image)
            else:
                self.plotImg.set_data(self.image)
            self.figure.tight_layout()
            self.canvas.draw()

    def changeCursor(self, event):
#        cursor = Cursor(self.ax, useblit=True, color='red', linewidth=1)
        self.canvas.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor ))

    def updateFigure(self):
        xs, ys = [], []
        for Rect in self.colorcardList:
            tl, bl, br, tr = Rect
            xs = xs + [tl[0], bl[0], br[0], tr[0], tl[0], np.nan]
            ys = ys + [tl[1], bl[1], br[1], tr[1], tl[1], np.nan]
        for Rect in self.trayList:chuong.nguyen@anu.edu.au
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
        CalibFile = QtGui.QFileDialog.getOpenFileName(self, 'Open image', '/home/chuong/Workspace/traitcapture-bin/unwarp_rectify/data')
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
            if self.plotImg == None:
                self.plotImg = self.ax.imshow(self.image)
            else:
                self.plotImg.set_data(self.image)
            self.canvas.draw()

#    def loadPotTemplate(self):
#        ''' load pot template image'''
#        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open image', '/home/chuong/Workspace/traitcapture-bin/unwarp_rectify/data')
#        self.status.append('Loading image...')
#        app.processEvents()
#        self.potTemplate = cv2.imread(str(fname))[:,:,::-1]
#        if len(self.potList) > 0:

    def savePipelineSettings(self):
        ''' save to pipeline setting file'''
        fname = QtGui.QFileDialog.getSaveFileName(self, 'Save selection to pipeline settings', '/home/chuong/Workspace/traitcapture-bin/unwarp_rectify/data')
        settingPath = os.path.dirname(str(fname))
        settings = []
        if self.ImageSize != None and self.CameraMatrix != None and self.DistCoefs != None:
            undistort = ['undistort', \
                         {'mess': '---perform optical undistortion---', \
                          'cameraMatrix': self.CameraMatrix.tolist(), \
                          'distortCoefs': self.DistCoefs.tolist(), \
                          'imageSize': list(self.ImageSize),
                          'rotationAngle': self.rotationAngle
                         } \
                        ]
        else:
            undistort = ['undistort', {'mess': '---skip optical undistortion---'}]
        settings.append(undistort)

        if len(self.colorcardList) > 0:
            medianSize = cd.getMedianRectSize(self.colorcardList)
            capturedColorcards = cd.rectifyRectImages(self.image, self.colorcardList, medianSize)
            colorCardFile = 'CapturedColorcard.png'
            cv2.imwrite(os.path.join(settingPath, colorCardFile), capturedColorcards[0][:,:,::-1].astype(np.uint8))
            colorcardColors, colorStd  = cd.getColorcardColors(capturedColorcards[0], GridSize = [6,4])
            colorcardPosition, Width, Height, Angle = cd.getRectangleParamters(self.colorcardList[0])
            colorcarddetect = ['colorcarddetect', \
                               {'mess': '---perform color card detection---', \
                                'colorcardFile': colorCardFile,\
                                'colorcardPosition': colorcardPosition.tolist(),\
                                'colorcardTrueColors': cd.CameraTrax_24ColorCard,
                                'settingPath': settingPath
                               }
                              ]
        else:
            colorcarddetect = ['colorcarddetect', {'mess': '---skip color card detection---',
                                                   'settingPath': settingPath}]
        settings.append(colorcarddetect)

        colorcorrect = ['colorcorrect', {'mess': '---perform color correction---'}]
        settings.append(colorcorrect)

        if len(self.trayList) > 0:
            trayMedianSize = cd.getMedianRectSize(self.trayList)
            trayImages = cd.rectifyRectImages(self.image, self.trayList, trayMedianSize)
            colorcardColors, colorStd  = cd.getColorcardColors(capturedColorcards[0], GridSize = [6,4])
            trayDict = {'mess': '---perform tray detection---'}
            trayDict['trayNumber'] = len(self.trayList)
            trayDict['trayFiles'] = 'Tray_%02d.png'
            trayDict['settingPath'] = settingPath
            trayPositions = []
            for i,tray in enumerate(trayImages):
                cv2.imwrite(os.path.join(settingPath, trayDict['trayFiles'] %i), tray[:,:,::-1].astype(np.uint8))
                trayPosition, Width, Height, Angle = cd.getRectangleParamters(self.trayList[i])
                trayPositions.append(trayPosition.tolist())
            trayDict['trayPositions'] = trayPositions
            traydetect = ['traydetect', trayDict]
        else:
            traydetect = ['traydetect', {'mess': '---skip tray detection---'}]
        settings.append(traydetect)

        if len(self.potList) > 0:
            trayMedianSize = cd.getMedianRectSize(self.trayList)
            potPosition, Width, Height, Angle = cd.getRectangleParamters(self.potList[0])
            Width, Height = int(Width), int(Height)
            topLeft = [int(self.potList[0][0][0]), int(self.potList[0][0][1])]
            self.potImage = self.image[topLeft[1]:topLeft[1]+Height, topLeft[0]:topLeft[0]+Width, :]
            potFile = 'Pot.png'
            cv2.imwrite(os.path.join(settingPath, potFile), self.potImage[:,:,::-1].astype(np.uint8))
            potDict = {'mess': '---perform pot detection---'}
            potDict['potPositions'] = potPosition.tolist()
            potDict['potSize'] = [int(Width), int(Height)]
            potDict['traySize'] = [int(trayMedianSize[0]), int(trayMedianSize[1])]
            potDict['potFile'] = potFile
            potDict['potTemplateFile'] = 'PotTemplate.png' # TODO: need to copy template file over settingPath
            potDict['settingPath'] = settingPath
            if self.potTemplate != None:
                potTemplateFile = 'potTemplate.png'
                cv2.imwrite(os.path.join(settingPath, potTemplateFile), self.potTemplate[:,:,::-1])
                potDict['potTemplateFile'] = potTemplateFile
            potdetect = ['potdetect', potDict]
        else:
            potdetect = ['potdetect', {'mess': '---skip pot detection---'}]
        settings.append(potdetect)

        plantextract = ['plantextract', {'mess': '---perfrom plant biometrics extraction---',
                                         'meth': 'k-means-square',
                                         'methargs': {}}]
        settings.append(plantextract)

        imagewrite = ['imagewrite', {'mess': '---writing image---'}]
        settings.append(imagewrite)

        with open(fname, 'w') as outfile:
            outfile.write( yaml.dump(settings, default_flow_style=None) )


    def rotateImage90Degrees(self):
        if self.image == None:
            self.status.append('No image to rotate.')
            return
        self.rotationAngle = self.rotationAngle + 90
        if self.rotationAngle >= 360:
            self.rotationAngle = self.rotationAngle - 360
        self.image = np.rot90(self.image) #.astype(uint8)
        self.status.append('Rot. angle = %d deg' %self.rotationAngle)
        if self.plotImg == None:
            self.plotImg = self.ax.imshow(self.image)
        else:
            self.plotImg.set_data(self.image)
        self.canvas.draw()

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
                if self.potRadioButton.isChecked():
                    Rect = cd.getRectCornersFrom2Points(self.image, self.leftClicks, AspectRatio, Rounded = True)
                else:
                    Rect = cd.getRectCornersFrom2Points(self.image, self.leftClicks, AspectRatio)
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
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    main = Window()
    main.setWindowTitle('Select Color Card, Trays, and Pot')
    main.show()

    sys.exit(app.exec_())