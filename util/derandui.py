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
from timestream import TimeStreamTraverser
from collections import namedtuple

class DerandomizeGUI(QtGui.QMainWindow):
    def __init__(self):
        """Main window for derandomization user interaction

        Attributes:
          _ui(QMainWindow): What we get from the ui file created by designer
          _scene(QGraphicsScene): Where we put the pixmap
          _gvImg(GraphicsView): A GraphicsView implementation that adds fast pan
            and zoom.
          _activeTS(TimeStreamTraverser): Holds all active instances related to a TS
        """
        QtGui.QMainWindow.__init__(self)

        self._activeTS = None
        self._ui = uic.loadUi("derandui.ui")

        # Setup Image viewer
        # GraphicsView(GraphicsScene(GraphicsItem(Pixmap)))
        self._scene = QtGui.QGraphicsScene()
        self._gvImg = PanZoomGraphicsView()
        self._gvImg.setScene(self._scene)
        self.showImage(None)

        # self._ui.csv and self._gvImg take up 50-50 of the vertical space
        sp = self._gvImg.sizePolicy()
        sp.setVerticalPolicy(QtGui.QSizePolicy.Preferred)
        sp.setVerticalStretch(1)
        self._gvImg.setSizePolicy(sp)
        self._ui.vRight.addWidget(self._gvImg)

        # Setup the timestream list
        self._ui.tslist.horizontalHeader().resizeSection(0,20)
        self._ui.tslist.cellClicked.connect(self.onClickTimeStreamList)
        self.addTsItem = self._ui.tslist.item(0,0)
        self._ui.tslist.setColumnHidden(2,True) # TimeStream 3rd column (hidden)

        # Setup the csv table, item(0,0) of _ui.csv will be a combobox
        self._tscb = QComboBox_TS(self._ui.csv, self)
        self._ui.csv.setCellWidget(0,0,self._tscb)

        # item(0,1) of _ui.csv will be a combobox
        self._csvcb = QComboBox_CSV(self._ui.csv, self)
        self._ui.csv.setCellWidget(0,1, self._csvcb)

        # Button connection
        self._ui.bOpenCsv.clicked.connect(self.selectCsv)

        self._ui.show()

    def onClickTimeStreamList(self, row, column):
        # Adding
        if self._ui.tslist.item(row,column) is self.addTsItem:
            tsdir = QtGui.QFileDialog.getExistingDirectory(self, \
                    "Select Time Stream", "", \
                    QtGui.QFileDialog.ShowDirsOnly \
                    | QtGui.QFileDialog.DontResolveSymlinks)

            if tsdir == "": # Handle the cancel
                return

            tsbasedir = os.path.basename(str(tsdir))

            # Check to see if selected TS has needed information.
            try:
                tst = TimeStreamTraverser(str(tsdir))

                if tst.curr().ipm is None:
                    msg = "TimeStream {} needs an ImagePotMatrix.".\
                            format(tst.name)
                    raise RuntimeError(msg)
            except Exception as e:
                errmsg = QtGui.QErrorMessage(self)
                errmsg.setWindowTitle("Error Opening Time Stream {}". \
                        format(tsbasedir))
                errmsg.showMessage(str(e))
                return

            self._ui.tslist.insertRow(0)

            i = QtGui.QTableWidgetItem("-")
            i.setTextAlignment(QtCore.Qt.AlignCenter)
            self._ui.tslist.setItem(0,0,i)

            i = QtGui.QTableWidgetItem(tsbasedir)
            i.setTextAlignment(QtCore.Qt.AlignLeft)
            i.setData(QtCore.Qt.UserRole, tst)
            self._ui.tslist.setItem(0,1,i)

            # Show if it is the first.
            if self._activeTS is None:
                self.selectRowTS(0)

        # Deleting
        elif column == 0 \
                and self._ui.tslist.item(row,column) is not self.addTsItem:
            item = self._ui.tslist.item(row,1)
            dtst = item.data(QtCore.Qt.UserRole).toPyObject()
            self._ui.tslist.removeRow(row)
            if self._activeTS is dtst:
                self._activeTS = None
                if self._ui.tslist.rowCount() > 1:
                    nitem = self._ui.tslist.item(0,1)
                    self._activeTS = nitem.data(QtCore.Qt.UserRole).toPyObject()

            self._tscb.assignTst(self._activeTS)
            self.showImage(self._activeTS)

        # Selecting
        elif row != self._ui.tslist.rowCount()-1:
            self.selectRowTS(row)

        else:
            pass

    def selectRowTS(self, row):
        # Clear all cell coloring
        #FIXME: Clearing with a forloop, but there must be a better way!!!
        for r in range(self._ui.tslist.rowCount()-1):
            for c in range(2):
                self._ui.tslist.item(r,c).setBackground(QtGui.QColor(255,255,255))

        for c in range(2):
            self._ui.tslist.item(row,c).setBackground(QtGui.QColor(100,100,200))

        # select in self._activeTS
        item = self._ui.tslist.item(row,1)
        self._activeTS = item.data(QtCore.Qt.UserRole).toPyObject()

        self._tscb.assignTst(self._activeTS)

        # Show image of self._activeTS
        img = self._activeTS.curr()
        self.showImage(img.path)

    def showImage(self, path=None):
        if path is None:
            pixmap = QtGui.QPixmap(0,0)
        else:
            pixmap = QtGui.QPixmap(path)

        self._scene.clear()
        pixItem = self._scene.addPixmap(pixmap)
        pixItem.setZValue(-100)


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

        if self._ui.csv.rowCount() < maxRows:
            self._ui.csv.setRowCount(maxRows)
        if self._ui.csv.columnCount() < maxCols + 2:
            self._ui.csv.setColumnCount(maxCols + 2)
        for r in range(self._ui.csv.rowCount()):
            for c in range(2, self._ui.csv.columnCount()):
                try:
                    item = QtGui.QTableWidgetItem(csvFile[r][c])
                except:
                    item = QtGui.QTableWidgetItem(" ")
                self._ui.csv.setItem(r,c,item)

        # Fill the csv combobox
        self._csvcb.fill()

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

class QComboBox_TS(QtGui.QComboBox):
    def __init__(self, csvTable, *args, **kwargs):
        super(QComboBox_TS, self).__init__(*args, **kwargs)
        self._csvTable = csvTable
        self._tst = None
        self.setEditText("Select TS MetaID")
        self.currentIndexChanged.connect(self.onChange)

    def assignTst(self, tst):
        """Menu widget at position self._csvTable(0,0) and init column vals"""

        # if we get a None it means to clear everything.
        if tst is None:
            self._tst = None
            self.clear()
            for r in range(1, self._csvTable.rowCount()):
                item = QtGui.QTableWidgetItem(" ")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self._csvTable.setItem(r, 0, item)
            return

        #FIXME: We need to put the metaids in the TimeStream!!!!
        self.clear() # start from an empty menu

        # Create an action per every metaid in TimeStream
        self._tst = tst
        img = self._tst.curr()
        mids = img.ipm.getPot(img.ipm.potIds[0]).getMetaIdKeys()
        mids.append("potid") # The default is original pot ids.
        for mid in mids:
            self.addItem(str(mid), QtCore.QVariant(mid))

        # Append sufficient rows. first row is menu (+1)
        if img.ipm.numPots+1 > self._csvTable.rowCount():
            self._csvTable.setRowCount( img.ipm.numPots + 1)

        self.onChange(self.currentIndex())

    def onChange(self, index):
        if self._tst is None:
            return

        img = self._tst.curr()

        # Fill first Column with active action mid
        mid = str(self.itemData(index).toPyObject())
        potIds = img.ipm.potIds

        for r in range(1, self._csvTable.rowCount()):
            item = QtGui.QTableWidgetItem(" ")
            if len(potIds) > 0:
                pot = img.ipm.getPot(potIds.pop(0))
                metaval = pot.id
                if mid != "potid":
                    metaval = pot.getMetaId(mid)
                item.setText(str(metaval))

            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._csvTable.setItem(r, 0, item)

class QComboBox_CSV(QtGui.QComboBox):
    def __init__(self, csvTable, *args, **kwargs):
        super(QComboBox_CSV, self).__init__(*args, **kwargs)
        self._csvTable = csvTable
        self.setEditText("Select CSV Column")
        self.currentIndexChanged.connect(self.onChange)

    def fill(self):
        # Put colnames (2,end).
        self.clear()

        for c in range(2, self._csvTable.columnCount()):
            colName = self._csvTable.item(0, c).text()
            self.addItem(colName, QtCore.QVariant(c))


    def onChange(self, index):
        if index == -1:
            return

        # Column to display (col)
        col = self.itemData(index).toPyObject()

        for r in range(1, self._csvTable.rowCount()):
            item = QtGui.QTableWidgetItem(self._csvTable.item(r, col))
            self._csvTable.setItem(r,1, item)


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
