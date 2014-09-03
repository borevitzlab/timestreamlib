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

        # Setup first two columns
        self._ftc = BindingTable(self._ui.csv, self)
        self._ftc.c02RelationChange.connect(self.imgRefresh)

        # Button connection
        self._ui.bOpenCsv.clicked.connect(self._ftc.selectCsv)

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

            self._ftc.refreshCol0Header(self._activeTS)
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

        self._ftc.refreshCol0Header(self._activeTS)

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

    def imgRefresh(self):
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

class BindingTable(QtCore.QObject):
    E = "--empty--"
    RICN = 3 # Reserved Initial Column Number (RICN)
    RIRN = 1 # Reserved Initial Row Number (RIRN)
    c02RelationChange = QtCore.pyqtSignal() # Emit when col0 & col2 changes

    def __init__(self, csvTable, parent):
        """Class in charge of the first three columns in self._ui.csv

        The object gives access to selectCsv and refreshCol{0,1,2}Header.
        Attribures:
          _parent(QMainWindow): The parent window.
          _csvTable(QTableWidget): The table widget where everything is.
          _tst(TimeStreamTraverser): Current time stream traverser related to
            BindingTable
          _tscb(QComboBox): Combo box containing timestream data
          _csvcb(QComboBox): Combo box containing csv data
          _num0Rows(int): Number of rows in Column zero.
        """
        super(BindingTable, self).__init__(parent)
        self._parent = parent
        self._csvTable = csvTable

        # item(0,0) TimeStream pot id combobox
        self._tst = None
        self._num0Rows = 0
        self._tscb = QtGui.QComboBox(self._parent)
        self._csvTable.setCellWidget(0,0,self._tscb)
        self._tscb.setEditText("Select TS MetaID")
        self._tscb.currentIndexChanged.connect(self._colActionDispatcher)

        # item(0,1) TimeStream to CSV binding combobox
        self._csvcb = QtGui.QComboBox(self._parent)
        self._csvTable.setCellWidget(0,1, self._csvcb)
        self._csvcb.setEditText("Select CSV Column")
        self._csvcb.currentIndexChanged.connect(self._colActionDispatcher)

        # item(0.2) Derandomization parameter
        self._derandcb = QtGui.QComboBox(self._parent)
        self._csvTable.setCellWidget(0,2, self._derandcb)
        self._derandcb.setEditText("Select Derandomization Param")
        self._derandcb.currentIndexChanged.connect(self._colActionDispatcher)

        self._indSelect = [self._tscb.currentIndex(),
                           self._csvcb.currentIndex(),
                           self._derandcb.currentIndex()]

    def selectCsv(self):
        fname = QtGui.QFileDialog.getOpenFileName(self._parent,
                "Select CSV", "", "CSV (*.csv)")

        if fname == "":
            return

        f = file(fname, "r")
        csvreader = csv.reader(f, delimiter=",")
        csvFile = []
        maxCols = 0
        for row in csvreader:
            csvFile.append(row)
            if maxCols < len(row):
                maxCols = len(row)
        maxRows = len(csvFile)
        f.close()

        if self._csvTable.rowCount() < maxRows:
            self._csvTable.setRowCount(maxRows)
        if self._csvTable.columnCount() - BindingTable.RICN < maxCols:
            self._csvTable.setColumnCount(maxCols + BindingTable.RICN)
        for r in range(self._csvTable.rowCount()):
            for c in range(BindingTable.RICN, self._csvTable.columnCount()):
                try:
                    csvelem = csvFile[r][c-BindingTable.RICN]
                    item = QtGui.QTableWidgetItem(csvelem)
                except:
                    item = QtGui.QTableWidgetItem(" ")
                self._csvTable.setItem(r,c,item)

        # Fill the csv combobox
        self.refreshCol1Header()
        self.refreshCol2Header()

    def refreshCol0Header(self, tst):
        """Menu widget at position self._csvTable(0,0)"""
        # FIXME: We need to put the metaids in the TimeStream!!!!
        self._tst = tst

        if self._tst is not None:
            # Create an action per every metaid in TimeStream
            self._tscb.blockSignals(True)
            self._tscb.clear()
            img = self._tst.curr()
            mids = img.ipm.getPot(img.ipm.potIds[0]).getMetaIdKeys()
            mids.append("potid") # The default is original pot ids.
            for mid in mids:
                self._tscb.addItem(str(mid), QtCore.QVariant(mid))

            self._tscb.setCurrentIndex(0)
            self._indSelect[0] = -1
            self._tscb.blockSignals(False)
            self._colActionDispatcher()
        else:
            self._tscb.clear()

    def refreshCol1Header(self):
        """Menu widget at position self._csvTable(0,1)"""
        self._csvcb.blockSignals(True)
        self._csvcb.clear()
        for c in range(BindingTable.RICN, self._csvTable.columnCount()):
            colName = self._csvTable.item(0, c).text()
            self._csvcb.addItem(colName, c)
        self._csvcb.setCurrentIndex(0)
        self._indSelect[1] = -1
        self._csvcb.blockSignals(False)
        self._colActionDispatcher()

    def refreshCol2Header(self):
        self._derandcb.blockSignals(True)
        self._derandcb.clear()
        for c in range(BindingTable.RICN, self._csvTable.columnCount()):
            colName = self._csvTable.item(0,c).text()
            self._derandcb.addItem(colName, c)
        self._derandcb.setCurrentIndex(0)
        self._indSelect[2] = -1
        self._derandcb.blockSignals(False)
        self._colActionDispatcher()


    def _colActionDispatcher(self):
        """Will dispatch actions depending on changed column"""
        currSelect =  [self._tscb.currentIndex(),
                       self._csvcb.currentIndex(),
                       self._derandcb.currentIndex()]

        changedCol = [self._indSelect[i] != currSelect[i] for i in range(3)]

        # If there is no change return
        if True not in changedCol:
            return
        # We should only receive one change per callback
        if sum(changedCol) > 1:
            raise RuntimeError("Too many columns changed")

        if changedCol[0]: # Refresh cols{0,1,2}
            self._refreshCol0()
            self._refreshCol1()
            self._refreshCol2()

        elif changedCol[1]: # Refresh cols{1,2}
            self._refreshCol1()
            self._refreshCol2()

        elif changedCol[2]: # Refresh col2
            self._refreshCol2()

        else:
            raise RuntimeError("Unknown Error")

        self._indSelect =  [self._tscb.currentIndex(),
                            self._csvcb.currentIndex(),
                            self._derandcb.currentIndex()]

        # Emit col{0,2} signal if both not empty
        col0empty = self._tst is None or self._tscb.count() < 1 \
                or self._tscb.currentIndex() < 0
        col2empty = self._derandcb.count() < 1 \
                or self._derandcb.currentIndex() < 0
        if not col0empty and not col2empty:
            self.c02RelationChange.emit()

    def _refreshCol0(self):
        index = self._tscb.currentIndex()
        if self._tst is None or self._tscb.count() < 1 or index < 0:
            self._blankCol(0)
            self._num0Rows = 0
            return

        img = self._tst.curr()

        # Append sufficient rows.
        if img.ipm.numPots > self._csvTable.rowCount()-BindingTable.RIRN:
            self._csvTable.setRowCount( img.ipm.numPots + BindingTable.RIRN )

        # Fill first Column with active action mid
        self._num0Rows = 0
        mid = str(self._tscb.itemData(index).toPyObject())
        potIds = img.ipm.potIds

        for r in range(1, self._csvTable.rowCount()):
            item = QtGui.QTableWidgetItem(" ")
            if len(potIds) > 0:
                self._num0Rows += 1
                pot = img.ipm.getPot(potIds.pop(0))
                metaval = pot.id
                if mid != "potid":
                    metaval = pot.getMetaId(mid)
                item.setText(str(metaval))

            item.setTextAlignment(QtCore.Qt.AlignCenter)
            self._csvTable.setItem(r, 0, item)

    def _refreshCol1(self):
        index = self._csvcb.currentIndex()
        if self._csvcb.count() < 1 or index < 0:
            self._blankCol(1)
            return

        # If Column 0 is empty
        if self._num0Rows < 1 or self._tscb.count() < 1 \
                or self._tst is None:
            # Make sure we remove all "--empty--" rows.
            self._removeEmpties(1,self._csvTable.rowCount())
            return

        col = self._csvcb.itemData(index).toPyObject()
        self._copyCol(col, 1)

        # c1dict[element] = row number
        c1dict = {}
        for c1r in range(1, self._csvTable.rowCount()):
            item = self._csvTable.item(c1r,1)
            if str(item.data(QtCore.Qt.UserRole).toPyObject()) \
                    == BindingTable.E:
                continue
            c1dict[item.text()] = c1r

        for c0r in range(BindingTable.RIRN, self._num0Rows+1):
            c0item = self._csvTable.item(c0r,0)
            try:
                # c0item in c1
                c1r = c1dict[c0item.text()]
                self._swapRow(c0r, c1r)
                del c1dict[c0item.text()]

            except KeyError:
                # c0item not in c1
                c0data = str(c0item.data(QtCore.Qt.UserRole).toPyObject())
                if c0data != BindingTable.E:
                    # Not a empty row: Add null row and swap
                    self._csvTable.insertRow(self._csvTable.rowCount())
                    item = QtGui.QTableWidgetItem(" ")
                    item.setData(QtCore.Qt.UserRole, BindingTable.E)
                    self._csvTable.setItem(self._csvTable.rowCount()-1, 1, item)

                    self._swapRow(c0r, self._csvTable.rowCount()-1)
                continue

        self._removeEmpties(self._num0Rows+1, self._csvTable.rowCount())

    def _refreshCol2(self, index=0):
        if index == -1 or self._derandcb.count() < 1 or self._csvcb.count() < 1:
            self._blankCol(2)
            return

        col = self._derandcb.itemData(index).toPyObject()
        self._copyCol(col, 2)

    def _blankCol(self, c):
            for r in range(1, self._csvTable.rowCount()):
                item = QtGui.QTableWidgetItem(" ")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self._csvTable.setItem(r, c, item)

    def _removeEmpties(self, f, t):
        # Remove empty rows. In reverse to allow removal.
        for r in range (f,t)[::-1]:
            item = self._csvTable.item(r,1)
            if item is None:
                continue
            data = str(item.data(QtCore.Qt.UserRole).toPyObject())
            if data ==  BindingTable.E:
                self._csvTable.removeRow(r)

    def _copyCol(self, f, t):
        for r in range(BindingTable.RIRN, self._csvTable.rowCount()):
            # Don't copy for empty rows.
            item = self._csvTable.item(r,1)
            if item is not None \
                    and str(item.data(QtCore.Qt.UserRole).toPyObject()) \
                        == BindingTable.E:
                continue
            item = QtGui.QTableWidgetItem(self._csvTable.item(r, f))
            self._csvTable.setItem(r,t, item)

    def _swapRow(self, r1, r2):
        """Swap all columns except 0

        In general: Put r1 in temp, copy r2 to r1, copy temp to r2
        """
        if r1 < 0 or r2 < 0 \
                or r1 > self._csvTable.rowCount() \
                or r2 > self._csvTable.rowCount():
            msg = "Row number swap error"
            raise IndexError(msg)

        for c in range(1, self._csvTable.columnCount()):
            try:
                tmpr1 = QtGui.QTableWidgetItem(self._csvTable.item(r1,c))
            except:
                tmpr1 = QtGui.QTableWidgetItem(" ")
            self._csvTable.removeCellWidget(r1,c)
            try:
                tmpr2 = QtGui.QTableWidgetItem(self._csvTable.item(r2,c))
            except:
                tmpr2 = QtGui.QTableWidgetItem(" ")
            self._csvTable.removeCellWidget(r2,c)

            self._csvTable.setItem(r2, c, tmpr1)
            self._csvTable.setItem(r1, c, tmpr2)

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
