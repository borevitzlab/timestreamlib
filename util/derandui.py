#!/usr/bin/python
#coding=utf-8
# Copyright (C) 2014
# Author(s): Joel Granados <joel.granados@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import csv
import sys
import os.path
from PyQt4 import QtGui, QtCore, uic
from timestream import TimeStream

class DerandomizeGUI(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.ui = uic.loadUi("derandui.ui")

        # Setup Image viewer
        # GraphicsView(GraphicsScene(GraphicsItem(Pixmap)))
        pixmap = QtGui.QPixmap(500,500)
        self._scene = QtGui.QGraphicsScene()
        pixItem = self._scene.addPixmap(pixmap)
        pixItem.setZValue(-100)
        self.gvImg = PanZoomGraphicsView()
        self.gvImg.setScene(self._scene)

        # self.ui.csv and self.gvImg take up 50-50 of the vertical space
        sp = self.gvImg.sizePolicy()
        sp.setVerticalPolicy(QtGui.QSizePolicy.Preferred)
        sp.setVerticalStretch(1)
        self.gvImg.setSizePolicy(sp)
        self.ui.vRight.addWidget(self.gvImg)

        # Setup the timestream list
        self.timeStreams = {}
        self.ui.tslist.horizontalHeader().resizeSection(0,20)
        self.ui.tslist.cellClicked.connect(self.onClickTimeStreamList)
        self.addTsItem = self.ui.tslist.item(0,0)
        self.ui.tslist.setColumnHidden(2,True) # TimeStream 3rd column (hidden)

        # Button connection
        self.ui.bOpenFile.clicked.connect(self.selectFile)
        self.ui.bOpenCsv.clicked.connect(self.selectCsv)

        self.ui.show()

    def onClickTimeStreamList(self, row, column):
        if self.ui.tslist.item(row,column) is self.addTsItem:
            tsdir = QtGui.QFileDialog.getExistingDirectory(self, \
                    "Select Time Stream", "", \
                    QtGui.QFileDialog.ShowDirsOnly \
                    | QtGui.QFileDialog.DontResolveSymlinks)

            if tsdir == "": # Handle the cancel
                return

            tsbasedir = os.path.basename(str(tsdir))
            try:
                ts = TimeStream()
                ts.load(str(tsdir))
                tsid = str(id(ts))

                self.ui.tslist.insertRow(0)

                i = QtGui.QTableWidgetItem("-")
                i.setTextAlignment(QtCore.Qt.AlignCenter)
                self.ui.tslist.setItem(0,0,i)

                i = QtGui.QTableWidgetItem(tsbasedir)
                i.setTextAlignment(QtCore.Qt.AlignLeft)
                self.ui.tslist.setItem(0,1,i)

                i = QtGui.QTableWidgetItem(tsid)
                self.ui.tslist.setItem(0,2,i)
                self.timeStreams[tsid] = ts

            except Exception as e:
                errmsg = QtGui.QErrorMessage(self)
                errmsg.setWindowTitle("Error Opening Time Stream {}". \
                        format(tsbasedir))
                errmsg.showMessage(str(e))

        elif column == 0 \
                and self.ui.tslist.item(row,column) is not self.addTsItem:
            tsid = str(self.ui.tslist.item(row,2).text())
            del self.timeStreams[tsid]
            self.ui.tslist.removeRow(row)

        else:
            pass
            # Here we load First ts image


    def selectFile(self):
        self._imgfilename = QtGui.QFileDialog.getOpenFileName(self, "Select Image",
                "", "JPG (*.jpg);;PNG (*.png)")
        self._scene.clear()
        pixmap = QtGui.QPixmap(self._imgfilename)
        pixItem = self._scene.addPixmap(pixmap)
        pixItem.setZValue(-100)

        self.writeOnImage()

    def selectCsv(self):
        self._csvfilename = QtGui.QFileDialog.getOpenFileName(self,
                "Select CSV", "", "CSV (*.csv)")
        f = file(self._csvfilename, "r")
        csvreader = csv.reader(f, delimiter=",")
        csvFile = []
        maxCols = 0
        for row in csvreader:
            csvFile.append(row)
            if maxCols < len(row):
                maxCols = len(row)
        maxRows = len(csvFile)
        f.close()

        self.ui.csv.clear()
        self.ui.csv.setRowCount(maxRows)
        self.ui.csv.setColumnCount(maxCols)
        for i in range(maxRows):
            for j in range(maxCols):
                item = QtGui.QTableWidgetItem(csvFile[i][j])
                self.ui.csv.setItem(i,j,item)

    def writeOnImage(self):
        L = QtGui.QGraphicsTextItem('joel')
        font=QtGui.QFont('White Rabbit')
        font.setPointSize(30)
        C = QtGui.QColor("red")
        L.setFont(font)
        L.setZValue(-100)
        L.setPos(500,500)
        L.setOpacity(1)
        L.setDefaultTextColor(C)
        L.setZValue(100)
        self._scene.addItem(L)

class PanZoomGraphicsView(QtGui.QGraphicsView):

    def __init__(self):
        super(PanZoomGraphicsView, self).__init__()
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self._isPanning = False
        self._mousePressed = False

    def mousePressEvent(self,  event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mousePressed = True
            if self._isPanning:
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                self._dragPos = event.pos()
                event.accept()
            else:
                super(PanZoomGraphicsView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if event.modifiers() & QtCore.Qt.ControlModifier:
                self.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self._isPanning = False
                self.setCursor(QtCore.Qt.ArrowCursor)
            self._mousePressed = False
        super(PanZoomGraphicsView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._mousePressed and self._isPanning:
            newPos = event.pos()
            diff = newPos - self._dragPos
            self._dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            super(PanZoomGraphicsView, self).mouseMoveEvent(event)

    def wheelEvent(self,  event):
        factor = 1.2;
        if event.delta() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control and not self._mousePressed:
            self._isPanning = True
            self.setCursor(QtCore.Qt.OpenHandCursor)
        else:
            super(PanZoomGraphicsView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            if not self._mousePressed:
                self._isPanning = False
                self.setCursor(QtCore.Qt.ArrowCursor)
        else:
            super(PanZoomGraphicsView, self).keyPressEvent(event)

    #def mouseDoubleClickEvent(self, event): pass

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = DerandomizeGUI()
    app.exec_()
    app.deleteLater()
    sys.exit()
