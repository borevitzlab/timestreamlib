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
from timestream import TimeStreamTraverser, TimeStream
from collections import namedtuple
import timestream.manipulate.configuration as pipeconf
import timestream.manipulate.pipeline as pipeline

class DerandomizeGUI(QtGui.QMainWindow):
    def __init__(self):
        """Main window for derandomization user interaction

        Attributes:
          _ui(QMainWindow): What we get from the ui file created by designer
          _scene(QGraphicsScene): Where we put the pixmap
          _gvImg(GraphicsView): A GraphicsView implementation that adds fast pan
            and zoom.
          _activeTS(int): Selected offset in tstable. -1 is no tems
        """
        QtGui.QMainWindow.__init__(self)

        self._activeTS = -1
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
        self._ui.bDerand.clicked.connect(self._derandomize)

        self._ui.show()

    def _derandomize(self):
        # FIXME check if we have all the information.
        # 1.Temp struct to relate tspath with metaid list.
        tsts = {}
        timestamps = [] # needed for pipeline execution.
        for r in range(self._ui.tslist.rowCount()-1):
            i = self._ui.tslist.item(r,1)
            d = i.data(QtCore.Qt.UserRole).toPyObject()
            tspath = d[0].path
            # FIXME: make sure d[2] is within range
            # FIXME: make sure settings.general.metas.midname exists
            midname = str(d[1][d[2]])
            midlist = d[0].data["settings"]["general"]["metas"][midname]
            # switch key<->values in midlist
            midlist = {y:x for x,y in midlist.iteritems()}
            tsts[tspath] = midlist
            timestamps = timestamps + d[0].timestamps
        timestamps = sorted(set(timestamps))

        # 2. Create derandStruct needed for drandomize component.
        # Column 2 will have all the meta id names
        derandStruct = {}
        for r in range(1, self._ui.csv.rowCount()):
            # skip if empty
            r1cell = self._ui.csv.item(r,1)
            if str(r1cell.data(QtCore.Qt.UserRole).toPyObject()) \
                    == BindingTable.E:
                continue

            r2cell = self._ui.csv.item(r,2)
            mid = str(r2cell.text())

            # ingore if only whitespace
            if all(c in " " for c in mid):
                continue

            if mid not in derandStruct:
                derandStruct[mid] = {}

            # We search for r1cell.text() in every TS
            for path, midlist in tsts.iteritems():
                if str(r1cell.text()) in midlist:
                    if path not in derandStruct[mid]:
                        derandStruct[mid][path] = []
                    derandStruct[mid][path].append(midlist[str(r1cell.text())])
                    break

        # 3. Create pipeline components
        plc = pipeconf.PCFGSection("--")
        plc.setVal("pipeline._0.name", "derandomize")
        plc.setVal("pipeline._0.derandStruct", derandStruct)
        plc.setVal("pipeline._1.name", "imagewrite")
        plc.setVal("pipeline._1.outstream", "outts")

        # FIXME: we need to add a box that asks for the output dir.
        tsoutpath = "/home/joel/.Trash/derandomize"
        outts = TimeStream()
        outts.name = "derandomized"
        outts.create(tsoutpath)

        ctx = pipeconf.PCFGSection("--")
        ctx.setVal("outts.outts", outts)

        pl = pipeline.ImagePipeline(plc.pipeline, ctx)

        # 4. Execute pipeline
        for ts in timestamps:
            try:
                result = pl.process(ctx, [ts], True)
            except Exception as e:
                errmsg = QtGui.QErrorMessage(self)
                errmsg.setWindowTitle("Error Derandomizing to ". \
                        format(tsoutpath))
                errmsg.showMessage(str(e))
                break

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

            try: # See if TS has needed information.
                tst = TimeStreamTraverser(str(tsdir))
                if "metas" not in tst.data["settings"]["general"].keys():
                    msg = "metas needs to be defined in TS {} settings.".\
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
            midnames = tst.data["settings"]["general"]["metas"].keys()
            midnames.append("potid") # potid is the default.
            tstdata = [tst, midnames, 0] # TimeStream object, items, offset
            i.setData(QtCore.Qt.UserRole, tstdata)
            self._ui.tslist.setItem(0,1,i)

            # Show if it is the first.
            self.selectRowTS(self._activeTS+1)

        # Deleting
        elif column == 0 \
                and self._ui.tslist.item(row,column) is not self.addTsItem:
            self._ui.tslist.removeRow(row)
            self._activeTS = -1

            if self._ui.tslist.rowCount() > 1:
                self.selectRowTS(0)
            else:
                self.selectRowTS(self._activeTS)

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

        # Keep track of the combobox offset.
        if self._activeTS != -1:
            i = self._ui.tslist.item(self._activeTS,1)
            d = i.data(QtCore.Qt.UserRole).toPyObject()
            d[2] = self._ui.csv.cellWidget(0,0).currentIndex()
            i.setData(QtCore.Qt.UserRole, d)

        # change self._activeTS
        self._activeTS = row
        if self._activeTS >= 0:
            i = self._ui.tslist.item(self._activeTS,1)
            d = i.data(QtCore.Qt.UserRole).toPyObject()
            color = QtGui.QColor(100,100,200)
            for c in range(2):
                self._ui.tslist.item(self._activeTS,c).setBackground(color)
        else:
            d = [None, None, None]
        self._ftc.refreshCol0Header(d)

        # Show image of self._activeTS
        self.showImage(d[0])

    def showImage(self, tst=None):
        if tst is None:
            pixmap = QtGui.QPixmap(0,0)
        else:
            img = tst.curr()
            pixmap = QtGui.QPixmap(img.path)

        self._scene.clear()
        pixItem = self._scene.addPixmap(pixmap)
        pixItem.setZValue(-100)

    def imgRefresh(self):
        # FIXME: check to see if col{0,2} have elements.
        font=QtGui.QFont('White Rabbit')
        font.setPointSize(30)
        C = QtGui.QColor("red")

        # Remove all text items before rereshing
        for item in self._scene.items():
            if isinstance(item, QtGui.QGraphicsTextItem):
                self._scene.removeItem(item)

        for c0, c1, c2 in self._ftc.iter_active_rows():
            pot = c0.data(QtCore.Qt.UserRole).toPyObject()
            pRectList = pot.rect.asList()
            x = pRectList[0]
            y = pRectList[1]

            c0text = QtGui.QGraphicsTextItem(c0.text())
            c0text.setFont(font)
            c0text.setZValue(100)
            c0text.setOpacity(1)
            c0text.setDefaultTextColor(C)
            c0text.setPos(x,y)
            self._scene.addItem(c0text)

            c2text = QtGui.QGraphicsTextItem(c2.text())
            c2text.setFont(font)
            c2text.setZValue(100)
            c2text.setOpacity(1)
            c2text.setDefaultTextColor(C)
            c2text.setPos(x,y+50)
            self._scene.addItem(c2text)

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

    def getDerandId(self):
        if self._indSelect[2] < 0:
            raise RuntimeError("No derand offset selected")
        return str(self._derandcb.itemText(self._indSelect[2]))

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

    def refreshCol0Header(self, tstuple):
        # tstuple (tst, items, offset)
        """Menu widget at position self._csvTable(0,0)"""
        self._tst = tstuple[0]

        if self._tst is not None:
            if tstuple[1] is None:
                midnames = tst.data["settings"]["general"]["metas"].keys()
                midnames.append("potid")
                tstuple[1] = midnames
            if tstuple[2] is None or tstuple[2] < 0:
                tstuple[2] = offset

            self._tscb.blockSignals(True)
            self._tscb.clear()
            for item in tstuple[1]:
                self._tscb.addItem(str(item), QtCore.QVariant(item))
            self._tscb.setCurrentIndex(tstuple[2])
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

    # FIXME: We don't differentiate creating and uptating col0. When we update
    # we should be able to leave the data in each cell and just change the text.
    def _refreshCol0(self):
        index = self._tscb.currentIndex()
        if self._tst is None or self._tscb.count() < 1 or index < 0:
            self._blankCol(0)
            self._num0Rows = 0
            return

        # If we don't find an ipm in the first 10, something is wrong
        img = None
        for i in range(10):
            if self._tst.next().ipm is not None:
                img = self._tst.curr()
                break
        if img is None:
            msg = "Could not find pot specific metadata"
            raise IndexError(msg)

        # Append sufficient rows.
        if img.ipm.numPots > self._csvTable.rowCount()-BindingTable.RIRN:
            self._csvTable.setRowCount( img.ipm.numPots + BindingTable.RIRN )

        # Fill first Column with active action mid
        self._num0Rows = 0
        mid = str(self._tscb.itemData(index).toPyObject())
        if mid != "potid":
            mids = self._tst.data["settings"]["general"]["metas"][mid]
        potIds = img.ipm.potIds

        for r in range(1, self._csvTable.rowCount()):
            item = QtGui.QTableWidgetItem(" ")
            if len(potIds) > 0:
                self._num0Rows += 1
                pot = img.ipm.getPot(potIds.pop(0))
                metaval = pot.id
                if mid != "potid":
                    # Due to Json changing dict keys from int to str, We need to
                    # transform
                    metaval = mids[str(pot.id)]
                item.setText(str(metaval))
                item.setData(QtCore.Qt.UserRole, QtCore.QVariant(pot))

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

                # Update c1dict if necessary
                item = self._csvTable.item(c1r,1)
                if item.text() in c1dict.keys():
                    c1dict[item.text()] = c1r

            except KeyError:
                # c0item not in c1
                c0data = str(c0item.data(QtCore.Qt.UserRole).toPyObject())
                if c0data != BindingTable.E:
                    # Not a empty row: Add null row and swap
                    self._csvTable.insertRow(self._csvTable.rowCount())
                    lastRow = self._csvTable.rowCount()-1
                    item = QtGui.QTableWidgetItem(" ")
                    item.setData(QtCore.Qt.UserRole, BindingTable.E)
                    self._csvTable.setItem(lastRow, 1, item)

                    self._swapRow(c0r, lastRow)

                    # Update c1dict if necessary
                    item = self._csvTable.item(lastRow,1)
                    if item.text() in c1dict.keys():
                        c1dict[item.text()] = lastRow
                continue

        self._removeEmpties(self._num0Rows+1, self._csvTable.rowCount())

    def _refreshCol2(self):
        index = self._derandcb.currentIndex()
        if index == -1 or self._derandcb.count() < 1 or self._csvcb.count() < 1:
            self._blankCol(2)
            return

        # If Column 0 is empty
        if self._num0Rows < 1 or self._tscb.count() < 1 \
                or self._tst is None:
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

    def iter_active_rows(self):
        for r in range(1,self._num0Rows+BindingTable.RIRN):
            yield self._csvTable.item(r,0), \
                    self._csvTable.item(r,1), \
                    self._csvTable.item(r,2)


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
