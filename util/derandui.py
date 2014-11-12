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
import yaml
import os.path
import random
import numpy as np
from PyQt4 import QtGui, QtCore, uic
from timestream import TimeStreamTraverser, TimeStream
from collections import OrderedDict
from timestream.manipulate.pipecomponents import DerandomizeTimeStreams
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
        """
        QtGui.QMainWindow.__init__(self)
        self._ui = uic.loadUi("derandui.ui")

        # Setup timestream & csvlist
        self._ui.tslist.horizontalHeader().resizeSection(0,20)
        self._ui.tslist.cellClicked.connect(self.onClickTimeStreamList)
        self.addTsItem = self._ui.tslist.item(0,0)
        self._ui.bAddTs.clicked.connect(self._addTS)
        self._ui.csvlist.horizontalHeader().resizeSection(0,20)
        self._ui.csvlist.cellClicked.connect(self.onClickCsvList)
        self.addCsvItem = self._ui.csvlist.item(0,0)
        self._ui.bAddCsv.clicked.connect(self._addCsv)

        # Comboboxes & genMaster
        self._origCbCsvMousePress = self._ui.cbCsv.mousePressEvent
        self._ui.cbCsv.mousePressEvent = self._pressCbCsv
        self._origCbTsMousePress = self._ui.cbTs.mousePressEvent
        self._ui.cbTs.mousePressEvent = self._pressCbTs
        self._origCbDerandMousePress = self._ui.cbderand.mousePressEvent
        self._ui.cbderand.mousePressEvent = self._pressCbDerand
        self._ui.cbderand.currentIndexChanged.connect(self._indexChangedCbDerand)
        self._ui.bGenMaster.clicked.connect(self._genMaster)

        # Add Additional buttons
        self._ui.bGenConf.clicked.connect(self._genConfig)
        self._ui.bDerand.clicked.connect(self._derandomize)
        self._ui.bPrevImg.clicked.connect(self._showPrev)

        # Hide the progress bar stuff
        self._ui.pbts.setVisible(False)
        self._ui.bCancelClicked = False
        self._ui.bCancel.setVisible(False)
        self._ui.bCancel.clicked.connect(self._cancelDerand)

        self._ui.show()

    def _showPrev(self):
        if self._ui.masterlist.columnCount() < 1 \
                or self._ui.masterlist.rowCount() < 1 \
                or self._ui.tslist.rowCount < 2 \
                or self._ui.csvlist.rowCount < 2:
            return

        derandStruct = self._createDerandStruct()
        if derandStruct is None:
            return

        # Get a random timestamp
        tsI = self._ui.tslist.item(0,1)
        tsD = tsI.data(QtCore.Qt.UserRole).toPyObject()
        if len(tsD.timestamps) < 2:
            return
        timestamp = tsD.timestamps[random.randrange(0,len(tsD.timestamps))]

        # Create the image
        derandTS = DerandomizeTimeStreams(None, derandStruct=derandStruct)
        img = derandTS.__exec__(None, timestamp)[0].pixels
        h,w,d = img.shape
        img2 = np.empty((h, w, 4), np.uint8, 'C')
        img2[...,0] = img[...,2]
        img2[...,1] = img[...,1]
        img2[...,2] = img[...,0]
        qimg = QtGui.QImage(img2.data,w,h,QtGui.QImage.Format_RGB32)

        prevWidget = QtGui.QDialog(parent=self)
        prevWidget.setGeometry(QtCore.QRect(0,0,700,700))
        layout = QtGui.QVBoxLayout()
        prevWidget.setLayout(layout)

        # Setup Image viewer
        scene = QtGui.QGraphicsScene()
        gvImg = PanZoomGraphicsView(parent=self)
        gvImg.setScene(scene)
        pixmap = QtGui.QPixmap(qimg)
        pixItem = scene.addPixmap(pixmap)
        pixItem.setZValue(-100)
        layout.addWidget(gvImg)

        prevWidget.exec_()

    def _indexChangedCbDerand(self, ind):
        if ind == -1:
            return
        c,_ = self._ui.cbderand.itemData(ind).toUInt()
        self._ui.masterlist.sortItems(c, QtCore.Qt.DescendingOrder)

    def _pressCbDerand(self, mouseEvent):
        if self._ui.masterlist.columnCount() < 1 \
                or self._ui.masterlist.rowCount() < 1:
            return
        self._ui.cbderand.clear()
        self._ui.cbderand.blockSignals(True)
        for c in range(self._ui.masterlist.columnCount()):
            hhi = self._ui.masterlist.horizontalHeaderItem(c)
            self._ui.cbderand.addItem(hhi.text(), QtCore.QVariant(c))
        self._ui.cbderand.blockSignals(False)

        self._origCbDerandMousePress(mouseEvent)

    def _pressCbCsv(self, mouseEvent):
        if self._ui.csvtable.columnCount() < 2:
            return
        self._ui.cbCsv.clear()
        for c in range(self._ui.csvtable.columnCount()):
            hhi = self._ui.csvtable.horizontalHeaderItem(c)
            self._ui.cbCsv.addItem(hhi.text(), QtCore.QVariant(c))

        self._origCbCsvMousePress(mouseEvent)

    def _pressCbTs(self, mouseEvent):
        if self._ui.tstable.columnCount() < 2:
            return
        self._ui.cbTs.clear()
        for c in range(self._ui.tstable.columnCount()):
            hhi = self._ui.tstable.horizontalHeaderItem(c)
            self._ui.cbTs.addItem(hhi.text(), QtCore.QVariant(c))

        self._origCbTsMousePress(mouseEvent)

    def _genMaster(self):
        # 0. Make sure we can create the master.
        errMsg = None
        if self._ui.tstable.columnCount() < 2 \
                or self._ui.csvtable.columnCount() < 2 \
                or self._ui.tslist.rowCount() < 2 \
                or self._ui.csvlist.rowCount() < 2:
            errMsg = "Add a csv file and at least one Time Stream"
        if self._ui.cbCsv.currentText() == "" \
                or self._ui.cbCsv.currentText() == "CSV Name" \
                or self._ui.cbTs.currentText() == "" \
                or self._ui.cbTs.currentText() == "TS Name":
            errMsg = "Please choose column relation"
        if errMsg is not None:
            errmsg = QtGui.QErrorMessage(self)
            errmsg.setWindowTitle("Error Generating Master")
            errmsg.showMessage(errMsg)
            return

        # 1. Initialize table
        self._ui.masterlist.setRowCount(0)
        self._ui.masterlist.setColumnCount(0)
        self._ui.masterlist.setColumnCount(self._ui.csvtable.columnCount()-1
                + self._ui.tstable.columnCount()-1)

        # set csv related headers
        for c in range(1,self._ui.csvtable.columnCount()):
            hName = self._ui.csvtable.horizontalHeaderItem(c).text()
            i = QtGui.QTableWidgetItem()
            i.setText(hName)
            self._ui.masterlist.setHorizontalHeaderItem(c-1,i)

        # set ts related headers
        cOffset = self._ui.csvtable.columnCount()-1
        for c in range(1,self._ui.tstable.columnCount()):
            hName = self._ui.tstable.horizontalHeaderItem(c).text()
            i = QtGui.QTableWidgetItem()
            i.setText(hName)
            self._ui.masterlist.setHorizontalHeaderItem(c-1+cOffset,i)


        # 2. Copy csv table. Not col 0. Ignore row where selected col is "".
        cInd = self._ui.cbCsv.currentIndex()
        selColNum,_ = self._ui.cbCsv.itemData(cInd).toUInt()

        masterR = 0
        for csvR in range(self._ui.csvtable.rowCount()):
            if self._ui.csvtable.item(csvR, selColNum).text() == "":
                continue

            self._ui.masterlist.insertRow(self._ui.masterlist.rowCount())
            for csvC in range(1,self._ui.csvtable.columnCount()):
                istr = self._ui.csvtable.item(csvR, csvC)
                if istr is not None:
                    istr = self._ui.csvtable.item(csvR, csvC).text()
                else:
                    istr = " "
                i = QtGui.QTableWidgetItem()
                i.setTextAlignment(QtCore.Qt.AlignCenter)
                i.setText(istr)
                i.setBackground(QtGui.QColor(220,220,220))
                self._ui.masterlist.setItem(masterR, csvC-1, i)
            masterR += 1

        # 3. Copy tstable rows to masterlist that agree with Relation
        cInd = self._ui.cbTs.currentIndex()
        tsColNum,_ = self._ui.cbTs.itemData(cInd).toUInt()
        cInd = self._ui.cbCsv.currentIndex()
        masterColNum,_ = self._ui.cbCsv.itemData(cInd).toUInt()
        masterColNum -= 1 # because we don't have CSV Name in master list.

        # valRow: given the val, returns the row in tstable
        valRow = {}
        for csvR in range(self._ui.tstable.rowCount()):
            val = self._ui.tstable.item(csvR, tsColNum)
            if val is not None:
                val = self._ui.tstable.item(csvR, tsColNum).text()
            else:
                val = " "
            valRow[val] = csvR

        # Copy all row values from tstable to masterlist.
        for mRow in range(self._ui.masterlist.rowCount()):
            masterVal = self._ui.masterlist.item(mRow, masterColNum).text()
            if masterVal not in valRow.keys():
                continue

            # Copy all tstable columns from tsRow to masterlist
            tsRow = valRow[masterVal]
            for tsCol in range(1, self._ui.tstable.columnCount()):
                tsI = self._ui.tstable.item(tsRow, tsCol)
                tsT = tsI.text()
                tsD = tsI.data(QtCore.Qt.UserRole)
                i = QtGui.QTableWidgetItem()
                i.setTextAlignment(QtCore.Qt.AlignCenter)
                i.setText(tsT)
                i.setData(QtCore.Qt.UserRole, tsD)
                self._ui.masterlist.setItem(mRow, cOffset-1+tsCol, i)

    def _cancelDerand(self):
        self._ui.bCancelClicked = True

    def _genConfig(self):
        if self._ui.cbderand.currentIndex() < 0:
            return

        cFile = QtGui.QFileDialog.getSaveFileName(self, \
                "Select Filename for Config File", "", \
                options=QtGui.QFileDialog.DontResolveSymlinks)

        if cFile == "": # Handle the cancel
            return

        derandStruct = self._createDerandStruct()

        # unique list of tsbasedir
        tsts = {}
        tsbds = list(set([x for _,l in derandStruct.iteritems() \
                                for x in l.keys()]))
        for i in range(len(tsbds)):
            tsts[tsbds[i]] = i

        for mid, midlist in derandStruct.iteritems():
            for p, _ in midlist.iteritems():
                newKey = tsts[p]
                derandStruct[mid][newKey] = derandStruct[mid].pop(p)

        # reverse tsts
        tsts = {y:x for x,y in tsts.iteritems()}

        f = file(cFile, "w")
        yaml.dump([tsts, derandStruct], f)
        f.close()

    def _createDerandStruct(self):
        if self._ui.masterlist.columnCount() < 1 \
                or self._ui.masterlist.rowCount() < 1 \
                or self._ui.cbderand.currentIndex() < 0:
            errmsg = QtGui.QErrorMessage(self)
            errmsg.setWindowTitle("Error while generating derand struct")
            errmsg.showMessage(
                    "Generate Master and select derandomization column")
            return

        derandStruct = {}

        # Column in master list where mids are located
        cInd = self._ui.cbderand.currentIndex()
        midCol,_ = self._ui.cbderand.itemData(cInd).toUInt()

        # Data in the last column of master list should contain potId and ts
        tsCol = self._ui.masterlist.columnCount()-1

        for mRow in range(self._ui.masterlist.rowCount()):
            midItem = self._ui.masterlist.item(mRow, midCol)
            tsItem = self._ui.masterlist.item(mRow, tsCol)

            if midItem is None or str(midItem.text()) is "" \
                    or tsItem is None or str(tsItem.text()) is "" \
                    or tsItem.data(QtCore.Qt.UserRole) is None:
                continue

            mid = str(midItem.text())
            potid, tsbasedir = tsItem.data(QtCore.Qt.UserRole).toPyObject()

            # Construct the pot string.
            potStr = ""
            for c in range(self._ui.masterlist.columnCount()):
                i = self._ui.masterlist.item(mRow,c)
                if not i.isSelected():
                    continue
                potStr = potStr+"|"+str(i.text().toUtf8())

            if mid not in derandStruct.keys():
                derandStruct[mid] = {}
            if tsbasedir not in derandStruct[mid]:
                derandStruct[mid][tsbasedir] = []
            if (potid, potStr) not in derandStruct[mid][tsbasedir]:
                derandStruct[mid][tsbasedir].append((potid,potStr))

        return derandStruct

    def _derandomize(self):
        # 0. Get the output directory
        tsoutpath = QtGui.QFileDialog.getExistingDirectory(self, \
                    "Select Output Derandomization Directory", "", \
                    QtGui.QFileDialog.ShowDirsOnly \
                    | QtGui.QFileDialog.DontResolveSymlinks)
        tsoutpath = str(tsoutpath)

        if tsoutpath == "": # Handle the cancel
            return

        # 1. Gather all timestamps
        timestamps = []
        for r in range(self._ui.tslist.rowCount()-1):
            i = self._ui.tslist.item(r,1)
            tst = i.data(QtCore.Qt.UserRole).toPyObject()
            timestamps = timestamps + tst.timestamps
        timestamps = sorted(set(timestamps))

        # 2. Get derandStruct
        derandStruct = self._createDerandStruct()

        # 3. Create pipeline components
        plc = pipeconf.PCFGSection("--")
        plc.setVal("pipeline._0.name", "derandomize")
        plc.setVal("pipeline._0.derandStruct", derandStruct)
        plc.setVal("pipeline._1.name", "imagewrite")
        plc.setVal("pipeline._1.outstream", "outts")

        outts = TimeStream()
        outts.name = "derandomized"
        outts.create(tsoutpath)

        ctx = pipeconf.PCFGSection("--")
        ctx.setVal("outts.outts", outts)

        pl = pipeline.ImagePipeline(plc.pipeline, ctx)

        # 4. Execute pipeline
        self._ui.bCancelClicked = False
        self._ui.pbts.setVisible(True)
        self._ui.bCancel.setVisible(True)
        self._ui.pbts.setMinimum(0)
        self._ui.pbts.setMaximum(len(timestamps))
        self._ui.pbts.reset()
        for i in range(len(timestamps)):
            self._ui.pbts.setValue(i)
            QtGui.qApp.processEvents()
            ts = timestamps[i]
            try:
                result = pl.process(ctx, [ts], True)
            except Exception as e:
                errmsg = QtGui.QErrorMessage(self)
                errmsg.setWindowTitle("Error Derandomizing to ". \
                        format(tsoutpath))
                errmsg.showMessage(str(e))
                break

            if self._ui.bCancelClicked:
                break

        self._ui.pbts.setValue(self._ui.pbts.maximum())
        self._ui.pbts.setVisible(False)
        self._ui.bCancel.setVisible(False)


    # col: Column to add the list
    # row: Row where we will start adding
    # l: List of values
    # d: List of data
    # t: Talbe to add to.
    def _addListTable_asCol(self, col, row, l, t, d=None, colName=None):
        if d is not None:
            if len(l) is not len(d):
                raise RuntimeError("Lengths do not agree")
        # Grow Rows
        fromRow = row
        toRow = fromRow+len(l)
        if t.rowCount() < toRow:
            t.setRowCount(toRow)
        rowNums = range(fromRow, toRow)

        # Grow Cols
        if t.columnCount() < col+1:
            t.setColumnCount(col+1)

        if colName is not None:
            i = QtGui.QTableWidgetItem()
            i.setText(QtCore.QString(str(colName)))
            t.setHorizontalHeaderItem(col, i)

        # add list as column
        for ri in range(len(l)):
            rowNum = rowNums[ri]
            i = QtGui.QTableWidgetItem()
            i.setText(str(l[ri]))
            i.setTextAlignment(QtCore.Qt.AlignCenter)
            if d is not None:
                i.setData(QtCore.Qt.UserRole, d[ri])
            t.setItem(rowNum, col, i)

    def _addTS(self):
        # 1. Get location of Time Stream
        tsdir = QtGui.QFileDialog.getExistingDirectory(self, \
                "Select Time Stream", "", \
                QtGui.QFileDialog.ShowDirsOnly \
                | QtGui.QFileDialog.DontResolveSymlinks)
        if tsdir == "": # Handle the cancel
            return

        tsbasedir = os.path.basename(str(tsdir))
        try: # See if TS has needed information.
            tst = TimeStreamTraverser(str(tsdir))
            if "settings" not in tst.data.keys():
                msg = "settings needs to be defined in Timestream %s" \
                        % tst.name
                raise RuntimeError(msg)
            if "metas" not in tst.data["settings"]["general"].keys():
                msg = "metas needs to be defined in TS {} settings.".\
                        format(tst.name)
                raise RuntimeError(msg)
            if len(tst.data["settings"]["general"]["metas"].keys()) < 1:
                msg = "There are no meta ids in Timestream %s" % tst.path
                raise RuntimeError(msg)
            # if 10 random img don't have ipms, we assume we can't derandomize
            tmsps = [tst.timestamps[x]
                        for x in random.sample(xrange(len(tst.timestamps)), 10)]
            for i in range(len(tmsps)):
                tmsp = tmsps[i]
                img = tst.getImgByTimeStamp(tmsp)
                if img.ipm is not None:
                    break
                if i == len(tmsps)-1:
                    msg = "Not enough data in %s" % tst.path
                    raise RuntimeError(msg)
        except Exception as e:
            errmsg = QtGui.QErrorMessage(self)
            errmsg.setWindowTitle("Error Opening Time Stream {}". \
                    format(tsbasedir))
            errmsg.showMessage(str(e))
            return
        tsbasedir = os.path.basename(tst.path)

        # 2. Insert Time Stream
        self._ui.tslist.insertRow(0)

        i = QtGui.QTableWidgetItem("-")
        i.setTextAlignment(QtCore.Qt.AlignCenter)
        self._ui.tslist.setItem(0,0,i)

        i = QtGui.QTableWidgetItem(tsbasedir)
        i.setTextAlignment(QtCore.Qt.AlignLeft)
        i.setData(QtCore.Qt.UserRole, tst)
        self._ui.tslist.setItem(0,1,i)

        # 3. Append Time Stream data to tstable
        # Metadata IDs in tst.data
        mids = tst.data["settings"]["general"]["metas"].keys()

        # Pot Ids in tst.data. We make sure we have a set of potIds that are in
        # every mid dict
        potIds = set(tst.data["settings"]["general"]["metas"][mids[0]].keys())
        for mid in mids:
            potIds = potIds \
                    & set(tst.data["settings"]["general"]["metas"][mid].keys())

        # column names from Timestream and table
        colNames = []
        for c in range(self._ui.tstable.columnCount()):
            hhi = self._ui.tstable.horizontalHeaderItem(c)
            colNames.append(str(hhi.text()))
        for mid in mids:
            if mid not in colNames:
                colNames.append(mid)

        # Append from this row.
        fromRow = self._ui.tstable.rowCount()

        # Add Time Stream Name
        l = [tsbasedir] * len(potIds)
        self._addListTable_asCol(0, fromRow, l, self._ui.tstable)

        for ci in range(len(colNames)):
            mid = colNames[ci]
            if mid not in mids:
                continue

            colNum = colNames.index(mid)
            midDict = tst.data["settings"]["general"]["metas"][mid]
            mvals = [midDict[x] for x in potIds]
            mobjs = [(x,tst.path) for x in potIds]
            self._addListTable_asCol(colNum, fromRow, mvals,
                    self._ui.tstable, d=mobjs, colName=mid)

    def onClickTimeStreamList(self, row, column):
        # Adding
        if self._ui.tslist.item(row,column) is self.addTsItem:
            self._addTS()

        # Deleting
        elif column == 0 \
                and self._ui.tslist.item(row,column) is not self.addTsItem:
            i = self._ui.tslist.item(row,1)
            tst = i.data(QtCore.Qt.UserRole).toPyObject()
            tsbasedir = os.path.basename(tst.path)
            for ri in reversed(range(self._ui.tstable.rowCount())):
                item = self._ui.tstable.item(ri, 0)
                if item.text() == tsbasedir:
                    self._ui.tstable.removeRow(ri)
            self._ui.tslist.removeRow(row)
            if self._ui.tslist.rowCount() < 2:
                self._ui.tstable.clearContents()
                self._ui.tstable.setColumnCount(1)
                self._ui.masterlist.setColumnCount(0)
                self._ui.masterlist.setRowCount(0)
                self._ui.cbTs.clear()
                self._ui.cbCsv.clear()
                self._ui.cbderand.clear()

    def _addCsv(self):
        # 1. Get location of csv file.
        csvPath = QtGui.QFileDialog.getOpenFileName(self,
                "Select CSV", "", "CSV (*.csv)")
        if csvPath == "":
            return
        csvName = os.path.split(str(csvPath))[1].split(".")[0]

        # 2. Insert Csv
        self._ui.csvlist.insertRow(0)
        i = QtGui.QTableWidgetItem("-")
        i.setTextAlignment(QtCore.Qt.AlignCenter)
        self._ui.csvlist.setItem(0,0,i)

        i = QtGui.QTableWidgetItem(csvName)
        i.setTextAlignment(QtCore.Qt.AlignLeft)
        i.setData(QtCore.Qt.UserRole, csvName)
        self._ui.csvlist.setItem(0,1,i)

        # 3. csv per column
        f = file(csvPath, "r")
        csvreader = csv.reader(f, delimiter=",")
        csvCol = {}

        # first row is always header
        hIndexes = csvreader.next() # header index
        for i in range(len(hIndexes)):
            hIndexes[i] = unicode(hIndexes[i], "utf-8", errors="ignore")
            csvCol[hIndexes[i]] = []

        rowNum = 0
        for l in csvreader:
            rowNum += 1
            for hIndex in hIndexes:
                lOffset = hIndexes.index(hIndex) # Line offset for hIndex
                csvCol[hIndex].append(unicode(l[lOffset], "utf-8",
                        errors="ignore"))

        # column names from csv file and table
        colNames = []
        for c in range(self._ui.csvtable.columnCount()):
            hhi = self._ui.csvtable.horizontalHeaderItem(c)
            colNames.append(str(hhi.text()))
        for h in csvCol.keys():
            if h not in colNames:
                colNames.append(h)

        # Add Csv name
        fromRow = self._ui.csvtable.rowCount()
        l = [csvName] * rowNum
        self._addListTable_asCol(0, fromRow, l, self._ui.csvtable)

        # Add each csv column to csv list
        for key, l in csvCol.iteritems():
            colNum = colNames.index(key)
            self._addListTable_asCol(colNum, fromRow, l,
                    self._ui.csvtable, colName=key)

    def onClickCsvList(self, row, column):
        # Adding
        if self._ui.csvlist.item(row,column) is self.addCsvItem:
            self._addCsv()

        elif column == 0 \
                and self._ui.csvlist.item(row,column) is not self.addCsvItem:
            i = self._ui.csvlist.item(row,1)
            csvname = i.data(QtCore.Qt.UserRole).toPyObject()
            for ri in reversed(range(self._ui.csvtable.rowCount())):
                i = self._ui.csvtable.item(ri,0)
                if i.text() == csvname:
                    self._ui.csvtable.removeRow(ri)
            self._ui.csvlist.removeRow(row)
            if self._ui.csvlist.rowCount() < 2:
                self._ui.csvtable.clearContents()
                self._ui.csvtable.setColumnCount(1)
                self._ui.masterlist.setColumnCount(0)
                self._ui.masterlist.setRowCount(0)
                self._ui.cbTs.clear()
                self._ui.cbCsv.clear()
                self._ui.cbderand.clear()

class PanZoomGraphicsView(QtGui.QGraphicsView):

    def __init__(self, parent=None):
        super(PanZoomGraphicsView, self).__init__(parent=parent)
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

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = DerandomizeGUI()
    app.exec_()
    app.deleteLater()
    sys.exit()
