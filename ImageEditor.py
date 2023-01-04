import os,sys
import time
import math
from PyQt5 import QtCore, QtWidgets, QtGui
import urllib
# ui to generate text or image from a givdn prompt.
#import requests
import urllib.request
from AppGlobals import *
#import ssl
#ssl._create_default_https_context = ssl._create_unverified_context

APP_NAME = "openai-app image editor"

class Window(QtWidgets.QMainWindow):

    editRequested = QtCore.pyqtSignal(bool) 
    variationRequested = QtCore.pyqtSignal(bool) 

    def __init__(self):
        super().__init__()
 
        # setting title
        self.setWindowTitle(APP_NAME)
 
        # setting geometry to main window
        self.setGeometry(0, 0, 1024, 1024)
 
        # creating image object
        self.image = QtGui.QImage(self.size(), QtGui.QImage.Format_ARGB32)

 
        # making image color to white
        #self.image.fill(QtCore.Qt.white)
        self.image.fill(QtCore.Qt.transparent)
 
        # variables
        # drawing flag
        self.drawing = False
        # default brush size
        self.brushSize = 50
        # default color
        self.brushColor = QtCore.Qt.white
 
        # QPoint object to tract the point
        self.lastPoint = QtCore.QPoint()
 
        # creating menu bar
        mainMenu = self.menuBar()
 
        # creating file menu for save and clear action
        fileMenu = mainMenu.addMenu("File")
 
        # adding brush size to main menu
        b_size = mainMenu.addMenu("Brush Size")
 
        # adding brush color to ain menu
        b_color = mainMenu.addMenu("Brush Color")

        generateMenu =  mainMenu.addMenu("Generate")
 
        # creating save action
        variationAction = QtWidgets.QAction("Variations", self)
        generateMenu.addAction(variationAction)
        variationAction.triggered.connect(self.variationCall)
 
        recreateAction = QtWidgets.QAction("Deleted Area", self)
        generateMenu.addAction(recreateAction)
        recreateAction.triggered.connect(self.editCall)


        # creating save action
        saveAction = QtWidgets.QAction("Save", self)
        # adding short cut for save action
        saveAction.setShortcut("Ctrl + S")
        # adding save to the file menu
        fileMenu.addAction(saveAction)
        # adding action to the save
        saveAction.triggered.connect(self.save)
 
        # creating save action
        importAction = QtWidgets.QAction("Import", self)
        # adding short cut for save action
        #importAction.setShortcut("Ctrl + S")
        # adding save to the file menu
        fileMenu.addAction(importAction)
        # adding action to the save
        importAction.triggered.connect(self.importCall)

        # creating save action
        importUrlAction = QtWidgets.QAction("Import URL", self)
        # adding short cut for save action
        #importUrlAction.setShortcut("Ctrl + S")
        # adding save to the file menu
        fileMenu.addAction(importUrlAction)
        # adding action to the save
        importUrlAction.triggered.connect(self.importUrlCall)

        # creating clear action
        clearAction = QtWidgets.QAction("Clear", self)
        # adding short cut to the clear action
        clearAction.setShortcut("Ctrl + C")
        # adding clear to the file menu
        fileMenu.addAction(clearAction)
        # adding action to the clear
        clearAction.triggered.connect(self.clear)
 
        # creating options for brush sizes
        # creating action for selecting pixel of 4px
        pix_10 = QtWidgets.QAction("10px", self)
        # adding this action to the brush size
        b_size.addAction(pix_10)
        # adding method to this
        pix_10.triggered.connect(self.Pixel_10)
 
        # similarly repeating above steps for different sizes
        pix_20 = QtWidgets.QAction("20px", self)
        b_size.addAction(pix_20)
        pix_20.triggered.connect(self.Pixel_20)
 
        pix_30 = QtWidgets.QAction("30px", self)
        b_size.addAction(pix_30)
        pix_30.triggered.connect(self.Pixel_30)

        pix_40 = QtWidgets.QAction("40px", self)
        b_size.addAction(pix_40)
        pix_40.triggered.connect(self.Pixel_40)
 
        pix_50 = QtWidgets.QAction("50px", self)
        b_size.addAction(pix_50)
        pix_50.triggered.connect(self.Pixel_50)
 



        # creating options for brush color
        # creating action for black color
        black = QtWidgets.QAction("Black", self)
        # adding this action to the brush colors
        b_color.addAction(black)
        # adding methods to the black
        black.triggered.connect(self.blackColor)
 
        # similarly repeating above steps for different color
        white = QtWidgets.QAction("White", self)
        b_color.addAction(white)
        white.triggered.connect(self.whiteColor)
 
        green = QtWidgets.QAction("Green", self)
        b_color.addAction(green)
        green.triggered.connect(self.greenColor)
 
        yellow =QtWidgets. QAction("Yellow", self)
        b_color.addAction(yellow)
        yellow.triggered.connect(self.yellowColor)
 
        red = QtWidgets.QAction("Red", self)
        b_color.addAction(red)
        red.triggered.connect(self.redColor)

        self.pixmap = QtGui.QPixmap()#"savedimage_2.png")
    
    def editCall(self):
        self.editRequested.emit(True)
        return

    def variationCall(self):
        self.variationRequested.emit(True)
        return

    def getByteArray(self):
        # convert QPixmap to bytes
        ba = QtCore.QByteArray()
        buff = QtCore.QBuffer(ba)
        buff.open(QtCore.QIODevice.WriteOnly) 
        ok = self.pixmap.save(buff, "PNG")
        assert ok
        byte_array = ba.data()
        print(type(byte_array))
        return byte_array

    def getAlphaByteArray(self):
        # convert QPixmap to bytes
        #self.image.invertPixels(mode=QtGui.QImage.InvertRgb)
        self.image.invertPixels(mode=QtGui.QImage.InvertRgba)

        ba = QtCore.QByteArray()
        buff = QtCore.QBuffer(ba)
        buff.open(QtCore.QIODevice.WriteOnly) 
        ok = self.image.save(buff, "PNG")
        assert ok
        byte_array = ba.data()
        print(type(byte_array))
        #self.image.invertPixels(mode=QtGui.QImage.InvertRgb)
        self.image.invertPixels(mode=QtGui.QImage.InvertRgba)
        
        return byte_array

    def setFromByteArray(self,byte_array):
        """     This function takes in a byte array and converts it to a QPixmap.
                The function returns nothing, but sets the pixmap attribute of the class."""
        # convert bytes to QPixmap
        ba = QtCore.QByteArray(byte_array)
        #self.pixmap = QtGui.QPixmap()
        ok = self.pixmap.loadFromData(ba, "PNG")
        assert ok
        print(type(pixmap))

    # method for checking mouse cicks
    def mousePressEvent(self, event):
 
        # if left mouse button is pressed
        if event.button() == QtCore.Qt.LeftButton:
            # make drawing flag true
            self.drawing = True
            # make last point to the point of cursor
            o_point = event.pos()
            g_point = self.mapToGlobal(event.pos())
            l_point = self.mapFromGlobal(g_point)
            #print (g_point, l_point, o_point)
            the_point = o_point

            self.lastPoint = the_point
 
    # method for tracking mouse activity
    def mouseMoveEvent(self, event):
         
        # checking if left button is pressed and drawing flag is true
        if (event.buttons() & QtCore.Qt.LeftButton) & self.drawing:
             
            # creating painter object
            painter = QtGui.QPainter(self.image)
             
            # set the pen of the painter
            painter.setPen(QtGui.QPen(self.brushColor, self.brushSize,
                            QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
             
            # draw line from the last point of cursor to the current point
            # this will draw only one step
            o_point = event.pos()
            g_point = self.mapToGlobal(event.pos())
            l_point = self.mapFromGlobal(g_point)
            #print (g_point, l_point, o_point)
            the_point = o_point

            #offset = self.image.pos()

            painter.drawLine(self.lastPoint, the_point)

            #painter.translate(-offset)
            



            # change the last point
            self.lastPoint = the_point
            # update
            self.update()
 
    # method for mouse left button release
    def mouseReleaseEvent(self, event):
 
        if event.button() == QtCore.Qt.LeftButton:
            # make drawing flag false
            self.drawing = False
 
    # paint event
    def paintEvent(self, event):
        # create a canvas
        canvasPainter = QtGui.QPainter(self)

        canvasPainter.drawPixmap(self.rect(), self.pixmap)

        # draw rectangle  on the canvas
        canvasPainter.drawImage(self.rect(), self.image, self.image.rect())

    def setFromUrl(self, url):
        """sets the pixmap to the url"""
        if not url.startswith("http"):

            if not os.path.isfile(url):
                url = DELETED_IMAGE

            self.setFromFile(url)
            return


        else:
            try:
                data = urllib.request.urlopen(url).read()
                image = QtGui.QImage()
                image.loadFromData(data)
            except:
                image = QtGui.QImage()
                image.load(MISSING_IMAGE)

            self.pixmap = QtGui.QPixmap(image)
            self.image.fill(QtCore.Qt.transparent)
            self.update()




    def setFromFile(self,file):
        """sets the pixmap to the file"""

        self.pixmap = QtGui.QPixmap(file)
        w,h = self.pixmap.width(), self.pixmap.height()
        self.image.fill(QtCore.Qt.transparent)
        self.image=self.image.scaled( w,h, QtCore.Qt.KeepAspectRatio)

        #self.
        #self.setGeometry(0, 0, w, h)
        self.setFixedWidth(w)
        self.setFixedHeight(h)
        self.update()


    def importUrlCall(self):
        filePath, _ = QtWidgets.QInputDialog.getText(
             self, 'Image URL', 'Enter Image URL:')
        if filePath == "":
            return

        self.setFromUrl(str(filePath))
       

    def importCall(self):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Image", "",
                          "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
 
        if filePath == "":
            return
        #self.image.save(filePath)
        #pixmap = QtGui.QPixmap(filePath)
        #print (dir(self.image))
        
        #self.image.fill(pixmap.toImage())
        


        self.pixmap = QtGui.QPixmap(filePath)
        w,h = self.pixmap.width(), self.pixmap.height()
        self.image.fill(QtCore.Qt.transparent)
        self.image=self.image.scaled( w,h, QtCore.Qt.KeepAspectRatio)
        #self.setGeometry(0, 0, w, h)
        self.setFixedWidth(w)
        self.setFixedHeight(h)

        self.update()

    # method for saving canvas
    def save(self):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Image", "",
                          "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ")
 
        if filePath == "":
            return

        self.pixmap.save(filePath)

        self.image.invertPixels(mode=QtGui.QImage.InvertRgb)
        self.image.invertPixels(mode=QtGui.QImage.InvertRgba)

        self.image.save(filePath.replace('.png','_mask.png'))
        
        self.image.invertPixels(mode=QtGui.QImage.InvertRgb)
        self.image.invertPixels(mode=QtGui.QImage.InvertRgba)

    def clearStrokes(self):
        self.image.fill(QtCore.Qt.transparent)
        self.update()

    def clearBackground(self):
        self.pixmap = QtGui.QPixmap()
        self.update()

    # method for clearing every thing on canvas
    def clear(self):
        # make the whole canvas white
        #self.image.fill(QtCore.Qt.white)
        self.pixmap = QtGui.QPixmap()
        self.image.fill(QtCore.Qt.transparent)
        # update
        self.update()
 
    # methods for changing pixel sizes
    def Pixel_10(self):
        self.brushSize = 10
 
    def Pixel_20(self):
        self.brushSize = 20
 
    def Pixel_40(self):
        self.brushSize = 40
 
    def Pixel_50(self):
        self.brushSize = 50
 
    def Pixel_30(self):
        self.brushSize = 30

    # methods for changing brush color
    def blackColor(self):
        self.brushColor = QtCore.Qt.black
 
    def whiteColor(self):
        self.brushColor = QtCore.Qt.white
 
    def greenColor(self):
        self.brushColor = QtCore.Qt.green
 
    def yellowColor(self):
        self.brushColor = QtCore.Qt.yellow
 
    def redColor(self):
        self.brushColor = QtCore.Qt.red
 
 
def main():
	# create pyqt5 app
	App = QtWidgets.QApplication(sys.argv)
	 
	# create the instance of our Window
	window = Window()
	 
	# showing the window
	window.show()
	 
	# start the app
	sys.exit(App.exec())



if __name__ == "__main__":
	main()
