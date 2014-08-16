import csv
import sys
from PyQt4 import QtGui, QtCore, uic

class DerandomizeGUI(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.ui = uic.loadUi("derandui.ui")

        # Set the Graphics View for the img.
        self._scene = QtGui.QGraphicsScene()
        self.expImg = PanZoomGraphicsView()
        self.expImg.setScene(self._scene)

        pixmap = QtGui.QPixmap(500,500)
        pixItem = self._scene.addPixmap(pixmap)
        pixItem.setZValue(-100)

        sp = self.expImg.sizePolicy()
        sp.setVerticalPolicy(QtGui.QSizePolicy.Preferred)
        sp.setVerticalStretch(1)
        self.expImg.setSizePolicy(sp)

        self.ui.vRight.addWidget(self.expImg)

        self.ui.bOpenFile.clicked.connect(self.selectFile)
        self.ui.bOpenCsv.clicked.connect(self.selectCsv)

        self.ui.show()

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
