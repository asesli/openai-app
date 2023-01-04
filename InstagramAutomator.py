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
#from selenium import webdriver
#from matplotlib import pyplot as plt
import os,sys
import numpy as np
import pyautogui
import imutils
import cv2
import time
from mss import mss
try:
    from PIL import Image
except ImportError:
    import Image
import subprocess
import random
import Models
import pyperclip
import FileManagement



WINDOW_OPACITY      = 0.6
LIKE                = True
COMMENT             = True
SAVE                = True
SCREENSHOT          = True
FOLLOW              = True
NEXT                = True
DEFAULT_MODEL       = "harinder-from-surrey"
HEART_WHITE_ICON    = "icons\\instagram\\heart_w.png"
HEART_RED_ICON      = "icons\\instagram\\heart_r.png"
OPTIONS_DOTS_ICON   = "icons\\instagram\\optdots.png"
COMMENT_ICON        = "icons\\instagram\\comment.png"
NEXT_ICON           = "icons\\instagram\\next.png"
PREVIOUS_ICON       = "icons\\instagram\\previous.png"
MESSAGE_ICON        = "icons\\instagram\\message.png"
SHARE_ICON          = "icons\\instagram\\share.png"
FOLLOW_ICON         = "icons\\instagram\\follow.png"
SAVE_ICON           = "icons\\instagram\\save.png"
SAVED_ICON          = "icons\\instagram\\saved.png"
APP_NAME            = "openai-app image editor"

INSTAGRAM_ICONS     = [HEART_WHITE_ICON,COMMENT_ICON,NEXT_ICON]
ALL_INSTAGRAM_ICONS = [HEART_WHITE_ICON, HEART_RED_ICON, OPTIONS_DOTS_ICON, COMMENT_ICON, NEXT_ICON, PREVIOUS_ICON, MESSAGE_ICON, FOLLOW_ICON, SAVE_ICON, SAVED_ICON, SHARE_ICON]
INSTAGRAM_ICONS     = ALL_INSTAGRAM_ICONS

EXACT_IMAGE_DETECTION_THRESHOLD = 0.95

# keyboard mouse

def mouse_click(x,y,wait=0.15):
    time.sleep(wait)
    pyautogui.click(x=x,y=y)
    time.sleep(wait)

def key_press(key,interval=0.15):
    pyautogui.press('enter')
    time.sleep(interval)

def ctrl_a(interval=0.15):
    time.sleep(interval)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(interval)

def ctrl_c(interval=0.15):
    time.sleep(interval)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(interval)

def type_text(text,interval=0.15):
    pyautogui.write(text, interval=interval)

# model connectors

def get_prompt_from_instagram_page():
    """ uses the clipboard data to filter out relevant things 
        Clipboard should contain a str that is created using ctrl+a and ctrl+c

        keep in mind, clipboard data from instagram has \r\n at the end of each line.
        """
    content_str = str(pyperclip.paste())
    content_str = content_str.replace("\r","")
    content_str = content_str.split(" likes\n")[-1]
    content_str = content_str.split(" others\n")[-1]

    content_lines = content_str.split("\n")
    content_lines = content_lines[2:]
    content_lines = [i for i in content_lines if i.strip() != '']
    content_lines = [i for i in content_lines if i.strip().lower() != 'verified']
    for c in "!@#$%^&*()_-=+.><,":
        content_lines = [i for i in content_lines if not i.strip().startswith(c)]
    #content_lines = [i for i in content_lines if i.strip() not in "!@#$%^&*()_-=+.><,"] # this should really be regex...
    new_lines = []
    stop = "profile picture"
    for i in content_lines:
        if not i.endswith(stop):
            new_lines.append(i)
        else:
            break
    #print(new_lines)
    if len(new_lines) <=2:
        new_lines = new_lines[:-1]
    else:
        new_lines = new_lines[:-2]
    ret_line = "\n".join(new_lines)

    print ("PROMPT:", ret_line)
    return ret_line

def get_response(prompt, model_name):
    """ returns a response to the prompt using a saved model"""
    try:
        response = Models.getResponseFromModel(prompt, model_name)
    except Exception as e:
        print("ERROR:",str(e))
        response = ""
    print ("RESPONSE:", response)
    return response

def get_saved_model_list():
    return Models.get_saved_model_list()

# image processing

def find_instagram_icons_in_frame(images_to_find,left,top,width,height,local=False):

    with mss() as sct: #live screenshot feed
        mon = {'top': top, 'left': left, 'width': width, 'height': height}
        img = np.array(sct.grab(mon))
        found = {}
        for image in images_to_find:
            positions = get_matched_image_position(img, image)
            if positions:
                if local:
                    found[image] = positions
                else:
                    found[image] = (positions[0]+left, positions[1]+top)
        return found
    return {}

def image_file_to_np(img_file):
    """     This function takes in an image file, and converts it to a numpy array.
            The function returns the numpy array."""
    #return cv2.imread(img_file,0)
    image = cv2.imread(img_file,0)
    #image = np.array(image)
    #print (type(image))
    return image

def convert_to_grayscale(np_img):
    """     This function takes in a numpy image, and converts it to grayscale.
            The function returns the grayscale image."""
    return cv2.cvtColor(np.array(np_img), cv2.COLOR_BGR2GRAY)

def get_matched_image_position(np_img, image_file_to_match, threshold=EXACT_IMAGE_DETECTION_THRESHOLD):
    """     This function takes in a numpy image, and an image file to match.
            The function returns the position of the matched image. """
    img_gray = convert_to_grayscale(np_img)
    optdots_template = image_file_to_np(image_file_to_match)
    w, h = optdots_template.shape[::-1]
    res = cv2.matchTemplate(img_gray,optdots_template,cv2.TM_CCOEFF_NORMED)
    optdot_loc = np.where( res >= threshold)
    matched_xy = None#[]#optdots_xy = None
    for pt in zip(*optdot_loc[::-1]):
        #img = cv2.rectangle(np.array(img), pt, (pt[0] + w, pt[1] + h), (0,0,255), 2) #comment
        matched_xy = pt

    return matched_xy

# ui classes

class Locator(QtWidgets.QWidget):
    def __init__(self,name,parent=None):
        super(Locator,self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        layout=QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.image = QtWidgets.QLabel()

        self.pixmap = QtGui.QPixmap(name)



        self.image.setPixmap(self.pixmap)
        self.image.setStyleSheet("border:3px solid lightgreen;")
        layout.addWidget(self.image)
        self.image.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        layout.addWidget(self.image)
        self.setLayout(layout)

        self.image.setFixedWidth(self.pixmap.width())
        self.image.setFixedHeight(self.pixmap.height())


    def getImageRect(self):
        return self.pixmap.rect()

class ProcessorWindow(QtWidgets.QWidget):

    editRequested = QtCore.pyqtSignal(bool) 
    variationRequested = QtCore.pyqtSignal(bool) 

    def __init__(self,parent=None):
        super(ProcessorWindow,self).__init__(parent)
        self.parent=parent
        self.screenshot=None
        self.lastSize = None
        self.locators = []
        self.locator_dict = None
        self.active = False
        self.opacity = WINDOW_OPACITY

        self.process_like = LIKE
        self.process_follow = FOLLOW
        self.process_comment = COMMENT
        self.process_add_to_saved = SAVE
        self.process_screenshot = SCREENSHOT
        self.process_go_to_next = NEXT
        self.current_model = DEFAULT_MODEL

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
        self.setWindowTitle("Capture Window -- Position this window over the area to process.")
        #self.setAttribute(0,QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setStyleSheet("QDialog {background:transparent;}")

        self.image = QtWidgets.QLabel()
        self.image.setVisible(False)
        layout.addWidget(self.image)

        self.bg = QtWidgets.QLabel()
        self.bg.setParent(self)
        self.bg.setStyleSheet("background-color: grey; border:3px solid lightskyblue;")
        self.bg.setVisible(False)


        #bottom_layout = QtWidgets.QHBoxLayout()

        #self.bottom_menu = QtWidgets.QWidget()
        #self.bottom_menu.setLayout(bottom_layout)
        #self.setStyleSheet("border:1px solid lightgreen;")

        #self.size_presets = QtWidgets.QComboBox()
        #self.size_presets.addItems(IMAGE_SIZES)

        #self.find_icons = QtWidgets.QPushButton("Find Icons")
        #self.start_instagram_process_button = QtWidgets.QPushButton("GO!")
        #self.process_page_button = QtWidgets.QPushButton("Process Page")
        #self.reset_button = QtWidgets.QPushButton("Reset")
        #self.ok_button = QtWidgets.QPushButton("Ok")
        #self.model_choice = QtWidgets.QComboBox()
        #self.model_choice.addItems(get_saved_model_list())
        #self.model_choice.setCurrentText(DEFAULT_MODEL)


        #self.slider_widget = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        #self.slider_widget.setMinimum(30)
        #self.slider_widget.setMaximum(100)
        #self.slider_widget.setValue(int(self.opacity*100))
        #self.slider_widget.valueChanged.connect(self.updateOpacityCall)


        #bottom_layout.addWidget(self.size_presets)
        #bottom_layout.addWidget(self.slider_widget)
        #bottom_layout.addWidget(self.model_choice)
        #bottom_layout.addStretch()
        #bottom_layout.addWidget(self.start_instagram_process_button)
        #bottom_layout.addWidget(self.process_page_button)
        #bottom_layout.addWidget(self.find_icons)
        #bottom_layout.addWidget(self.reset_button)
        #bottom_layout.addWidget(self.ok_button)

        
        #layout.addStretch()
        #layout.addWidget(self.bottom_menu)
        #self.bottom_menu.setVisible(False)


        #self.reset_button.clicked.connect(self.resetCall)
        #self.ok_button.clicked.connect(self.okCall)
        #self.size_presets.currentIndexChanged[int].connect(self.setPresetSize)
        #self.find_icons.clicked.connect(self.findIconsCall)
        #self.start_instagram_process_button.clicked.connect(self.startInstagramCommenter)
        #self.process_page_button.clicked.connect(self.processInstagramPage)


        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.opacity)
        self.setLayout(layout)
        self.resize(800,800)

    def setOpacity(self,value):
        self.setWindowOpacity(value)

    def getLocator(self,locator_name):
        for i in self.locators:
            if i.toolTip() == locator_name:
                return i
        return None

    def getClickCoordinatesFromWidget(self, widget):
        center = widget.rect().center()
        point  = QtCore.QPoint(widget.pos().x()+center.x(), widget.pos().y()+center.y())
        pos = self.mapToGlobal(point)
        return pos

    def startInstagramCommenter(self):
        self.active = True
        while self.active:
            self.active = self.processInstagramPage()

    def stopInstagramCommenter(self):
        self.active = False

    def processInstagramPage(self):
        """    This function processes the current Instagram page.
                The function returns nothing."""

        self.locator_dict = self.findInstagramIcons()
        self.hide()

        heart_w  =    self.locator_dict.get(HEART_WHITE_ICON)
        heart_r  =    self.locator_dict.get(HEART_RED_ICON)
        optdots  =    self.locator_dict.get(OPTIONS_DOTS_ICON)
        comment  =    self.locator_dict.get(COMMENT_ICON)
        next_img =    self.locator_dict.get(NEXT_ICON)
        follow   =    self.locator_dict.get(FOLLOW_ICON)
        save_img =    self.locator_dict.get(SAVE_ICON)
        previous_img= self.locator_dict.get(PREVIOUS_ICON)

        #Only operate on posts taht you haven't liked.
        if not heart_r and heart_w:
            #Like the picture
            if heart_w and self.process_like:
                widget = self.getLocator(HEART_WHITE_ICON)
                if widget:
                    pos = self.getClickCoordinatesFromWidget(widget)
                    mouse_click(pos.x(),pos.y(),0.15)


            #comment on the picture
            if comment and self.process_comment:
                widget = self.getLocator(COMMENT_ICON)
                if widget:

                    #select the entire page
                    ctrl_a(1)
                    #copy to clipboard
                    ctrl_c(1)
                    #clean up the clipboard str so taht it only contains relevant data
                    prompt   = get_prompt_from_instagram_page()
                    #generate a response using the current selected model
                    response = get_response(prompt, self.current_model)

                    #harinder-from-surrey replies everything with Harinder: prefix, so lets remove that.
                    if self.current_model == "harinder-from-surrey":
                        response = response.replace("Harinder: ","")


                    #Click the comment area
                    pos = self.getClickCoordinatesFromWidget(widget)
                    mouse_click(pos.x(),pos.y(),0.15)
                    #Type out the comment
                    #response = "This is an interesting idea, keep it up!"
                    type_text(response,0.15)
                    time.sleep(1)
                    key_press("enter")
                    #Press enter
                    
                    
                    mouse_click(pos.x()+50,pos.y()-60, 0.15)
                    time.sleep(5)

            time.sleep(0.8)

            if save_img and self.process_add_to_saved:
                widget = self.getLocator(SAVE_ICON)
                if widget:
                    pos = self.getClickCoordinatesFromWidget(widget)
                    mouse_click(pos.x(),pos.y(),0.15)

            time.sleep(0.5)

            if follow and self.process_follow:
                widget = self.getLocator(FOLLOW_ICON)
                if widget:
                    pos = self.getClickCoordinatesFromWidget(widget)
                    mouse_click(pos.x(),pos.y(),0.15)


        #save a screenshot of your handy work.
        if self.process_screenshot and optdots and comment and next_img and previous_img:
            self.takeScreenShot()
            pass



        #Click the white area so the text editor of the comment is not active, otherwise right button wont work.
        #Go to next image
        #time.sleep(1)
        #key_press("right",0.2)
        time.sleep(1)
        if next_img and self.process_go_to_next:
            widget = self.getLocator(NEXT_ICON)
            if widget:
                pos = self.getClickCoordinatesFromWidget(widget)
                mouse_click(pos.x(),pos.y(),0.15)

        time.sleep(3)


        self.deleteLocators()
        self.show()

        if next_img:
            return True
        return False

    def resetCall(self):
        #print("Reset")
        #self.setWindowOpacity(self.opacity)
        self.image.clear()
        self.image.adjustSize()
        self.image.setVisible(False)
        if self.lastSize:
            self.move(self.lastSize[0],self.lastSize[1])
            self.resize(self.lastSize[2],self.lastSize[3])
        self.deleteLocators()
        return

    def getXYWH(self):

        #print( [self.geometry().x(),self.geometry().y(),self.geometry().width(),self.geometry().height()]) #<-- returns entire windows coordinates.
        return [self.pos().x(),self.pos().y(), self.size().width(), self.size().height()] #<-- returns the size of this widget

    #old
    def screenShot(self):

        xywh = self.getXYWH()
        self.lastSize = xywh
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        screen = app.primaryScreen()
        self.setVisible(False)
        screenshot = screen.grabWindow(0, xywh[0],xywh[1],xywh[2],xywh[3])
        #self.screenshot = screenshot
        self.setVisible(True)
        self.move(xywh[0],xywh[1]-26)
        self.resize(xywh[2],xywh[3]+26)

        self.image.setVisible(True)
        self.image.setPixmap(QtGui.QPixmap(screenshot))
        self.image.adjustSize()

        self.setWindowOpacity(1)


    def getScreenShotBBox(self):
        #returns coordinates for the bg box for the screenshot.
        x,y,w,h=self.getXYWH()
        #print( [self.geometry().x(),self.geometry().y(),self.geometry().width(),self.geometry().height()]) #<-- returns entire windows coordinates.
        return [self.bg.pos().x()+x,self.bg.pos().y()+y+30, self.bg.size().width(), self.bg.size().height()] #<-- returns the size of this widget


    def takeScreenShot(self):
        #takes screenshot of using the coordinates from bg bbox
        app = QtWidgets.QApplication.instance()
        screen = app.primaryScreen()
        #self.setVisible(False)

        xywh = self.getScreenShotBBox()

        time.sleep(0.2)
        screenshot = screen.grabWindow(0, xywh[0],xywh[1],xywh[2],xywh[3])
        img_file = "saved_instagram\\{}_{}.jpg".format(self.current_model, str(FileManagement.getTimeStamp()))
        screenshot.save(img_file, 'jpg')
        return


    def drawScreenShotBox(self, locator_dict):
        #using the output from findInstagramIcons(), figure out the bbox for the screenshot.

        #heart_w  =    self.locator_dict.get(HEART_WHITE_ICON)
        #heart_r  =    self.locator_dict.get(HEART_RED_ICON)
        optdots      =    locator_dict.get(OPTIONS_DOTS_ICON)
        comment      =    locator_dict.get(COMMENT_ICON)
        next_img     =    locator_dict.get(NEXT_ICON)
        previous_img =    locator_dict.get(PREVIOUS_ICON)
        #follow       =    self.locator_dict.get(FOLLOW_ICON)
        #save_img =    self.locator_dict.get(SAVE_ICON)
        self.update()
        if optdots and comment and next_img and previous_img:

            x = previous_img[0]
            x_widget = self.getLocator(PREVIOUS_ICON)
            if x_widget:
                x += x_widget.rect().width()/2

            w = next_img[0] - x
            w_widget = self.getLocator(NEXT_ICON)
            if w_widget:
                w -= w_widget.rect().width()/2

            y = optdots[1]
            y_widget = self.getLocator(OPTIONS_DOTS_ICON)
            if y_widget:
                y -= y_widget.rect().height()/2
            
            h = comment[1] - y
            h_widget = self.getLocator(COMMENT_ICON)
            if h_widget:
                #print("asd")
                h += h_widget.rect().height()/2

            w=int(w)
            y=int(y)
            x=int(x)
            h=int(h)

            
            self.bg.setVisible(True)
            self.bg.setFixedWidth(w)
            self.bg.setFixedHeight(h)
            self.bg.move(x,y)
            self.bg.show()
            self.update()
            
            return x,y,w,h

        return 0,0,10,10

    def findInstagramIcons(self,images=INSTAGRAM_ICONS):
        self.setVisible(False)
        xywh = self.getXYWH()
        time.sleep(0.3)
        locator_dict =find_instagram_icons_in_frame(images,xywh[0],xywh[1],xywh[2],xywh[3],local=True)
        self.setVisible(True)

        

        self.addLocators(locator_dict)

        self.drawScreenShotBox(locator_dict)

        return locator_dict

    def addLocator(self,name,x,y):
        w = QtWidgets.QLabel()

        #pixmap = QtGui.QPixmap(name)
        #pixmap_resized = pixmap.scaled(self.preview_size, self.preview_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        pixmap = QtGui.QPixmap(name)
        w.setPixmap(pixmap)
        w.setStyleSheet("border:3px solid lightgreen;")
        w.setParent(self)
        w.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        pixmap_rect = pixmap.rect()
        w.setFixedWidth(pixmap_rect.width())
        w.setFixedHeight(pixmap_rect.height())
        w.move(x,y)
        w.setToolTip(name)
        w.show()
        self.update()
        self.locators.append(w)
        return w

    def addLocators(self, locator_dict):
        self.deleteLocators()
        for i in locator_dict.keys():
            pos = locator_dict[i]
            self.addLocator(i,pos[0]-5,pos[1]-30)

    def deleteLocators(self):
        for i in self.locators:
            i.deleteLater()
        self.locators = []
        self.bg.setVisible(False)
        self.update()
    
    """
        def updateOpacityCall(self):
            sliderval = float(self.slider_widget.value())/100.0
            self.setWindowOpacity(sliderval)

        def getModelName(self):
            return str(self.model_choice.currentText())

        def goToCall(self):
            self.hide()
            for i in self.locators:
                center = i.rect().center()
                point = QtCore.QPoint(i.pos().x()+center.x(), i.pos().y()+center.y())
                pos = self.mapToGlobal(point)
                time.sleep(0.15)
                mouse_click(pos.x(),pos.y())
                time.sleep(0.15)
            self.show()
        
        def findIconsCall(self):
            self.setVisible(False)
            xywh = self.getXYWH()
            time.sleep(0.3)
            images = INSTAGRAM_ICONS
            self.locator_dict =find_instagram_icons_in_frame(images,xywh[0],xywh[1],xywh[2],xywh[3],local=True)
            self.setVisible(True)
            self.addLocators(self.locator_dict)
        
        def setPresetSize(self, value):
            item = IMAGE_SIZES[value]
            res = int(item.split('x')[0])
            self.resize(res,res)

        def findInstagramButtonsFromWindow(self,images=INSTAGRAM_ICONS):
            self.setVisible(False)
            xywh = self.getXYWH()
            time.sleep(0.3)
            self.locator_dict =find_instagram_icons_in_frame(images,xywh[0],xywh[1],xywh[2],xywh[3],local=True)
            self.setVisible(True)
            self.addLocators(self.locator_dict)

        def okCall(self):
            #print("OK")
            self.screenShot()
            return

    """

class ProcessorWindowController(QtWidgets.QWidget):

    editRequested = QtCore.pyqtSignal(bool) 
    variationRequested = QtCore.pyqtSignal(bool) 

    processStartRequested = QtCore.pyqtSignal(bool) 
    processStopRequested  = QtCore.pyqtSignal(bool) 

    def __init__(self,parent=None):
        super(ProcessorWindowController,self).__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.setWindowTitle("Instagram Automator")
        #self.setAttribute(0,QtCore.Qt.WindowStaysOnTopHint)

        self.active = False

        self.model_choice = QtWidgets.QComboBox()
        self.model_choice.addItems(get_saved_model_list())
        self.model_choice.setCurrentText(DEFAULT_MODEL)

        self.like_checkbox = QtWidgets.QCheckBox()
        self.like_checkbox.setText("Like")
        self.like_checkbox.setChecked(LIKE)

        self.follow_checkbox = QtWidgets.QCheckBox()
        self.follow_checkbox.setText("Follow")
        self.follow_checkbox.setChecked(FOLLOW)

        self.comment_checkbox = QtWidgets.QCheckBox()
        self.comment_checkbox.setText("Comment")
        self.comment_checkbox.setChecked(COMMENT)

        self.add_to_saved_checkbox = QtWidgets.QCheckBox()
        self.add_to_saved_checkbox.setText("Add to Saved")
        self.add_to_saved_checkbox.setChecked(SAVE)

        self.next_page_checkbox = QtWidgets.QCheckBox()
        self.next_page_checkbox.setText("Go to Next")
        self.next_page_checkbox.setChecked(NEXT)

        self.save_checkbox = QtWidgets.QCheckBox()
        self.save_checkbox.setText("Save as screenshot")
        self.save_checkbox.setChecked(SCREENSHOT)










        self.test_button = QtWidgets.QPushButton("Test")

        self.process_page_button = QtWidgets.QPushButton("Process Current Page")


        self.start_process_button = QtWidgets.QPushButton("Start")
        self.start_process_button.setCheckable(True)

        self.message_text = QtWidgets.QTextEdit()
        self.message_text.setVisible(False)


        self.window_control_widget = QtWidgets.QWidget()
        window_control_layout = QtWidgets.QHBoxLayout()
        window_control_layout.setContentsMargins(0,0,0,0)
        self.window_control_widget.setLayout(window_control_layout)
        self.opacity = WINDOW_OPACITY
        self.show_process_window_button = QtWidgets.QPushButton("Show Process Window")
        self.hide_process_window_button = QtWidgets.QPushButton("Hide Process Window")
        self.show_process_window_button.setVisible(False)
        self.processor_window_opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.processor_window_opacity_slider.setMinimum(30)
        self.processor_window_opacity_slider.setMaximum(100)
        self.processor_window_opacity_slider.setValue(int(self.opacity*100))

        window_control_layout.addWidget(self.show_process_window_button)
        window_control_layout.addWidget(self.hide_process_window_button)
        window_control_layout.addWidget(self.processor_window_opacity_slider)

        layout.addWidget(self.model_choice)

        layout.addWidget(self.like_checkbox)
        layout.addWidget(self.follow_checkbox)
        layout.addWidget(self.comment_checkbox)
        layout.addWidget(self.add_to_saved_checkbox)
        layout.addWidget(self.next_page_checkbox)
        layout.addWidget(self.save_checkbox)
        layout.addWidget(self.message_text)
        layout.addWidget(self.window_control_widget)
        layout.addStretch()
        layout.addWidget(self.test_button)
        layout.addWidget(self.process_page_button)
        layout.addWidget(self.start_process_button)
        self.setLayout(layout)

        self.processor_window = None
        self.initProcessorWindow()

        self.test_button.clicked.connect(self.testCall)
        self.start_process_button.clicked.connect(self.processCall)
        self.process_page_button.clicked.connect(self.processPageCall)


        self.model_choice.currentTextChanged.connect(self.updateProcessorWindowSettings)
        self.like_checkbox.clicked.connect(self.updateProcessorWindowSettings)
        self.follow_checkbox.clicked.connect(self.updateProcessorWindowSettings)
        self.comment_checkbox.clicked.connect(self.updateProcessorWindowSettings)
        self.add_to_saved_checkbox.clicked.connect(self.updateProcessorWindowSettings)
        self.save_checkbox.clicked.connect(self.updateProcessorWindowSettings)
        self.next_page_checkbox.clicked.connect(self.updateProcessorWindowSettings)

        self.show_process_window_button.clicked.connect(self.showProcessorWindow)
        self.hide_process_window_button.clicked.connect(self.hideProcessorWindow) 
        self.processor_window_opacity_slider.valueChanged[int].connect(self.setProcessorWindowOpacity)


    def updateProcessorWindowSettings(self):
        if not self.processor_window:
            self.initProcessorWindow()

        self.processor_window.current_model         = self.model_choice.currentText()
        self.processor_window.process_like          = self.like_checkbox.isChecked()
        self.processor_window.process_follow        = self.follow_checkbox.isChecked()
        self.processor_window.process_comment       = self.comment_checkbox.isChecked()
        self.processor_window.process_add_to_saved  = self.add_to_saved_checkbox.isChecked()
        self.processor_window.process_screenshot    = self.save_checkbox.isChecked()
        self.processor_window.process_go_to_next    = self.next_page_checkbox.isChecked()

    def initProcessorWindow(self):
        self.processor_window = ProcessorWindow()
        self.showProcessorWindow()
        self.updateProcessorWindowSettings()

    def testCall(self):
        self.updateProcessorWindowSettings()
        text = ""
        icons_dict = self.processor_window.findInstagramIcons(ALL_INSTAGRAM_ICONS)
        if icons_dict:
            text = "\n".join(icons_dict.keys())
        self.message_text.setText(text)

    def setProcessorWindowOpacity(self, value):
        self.processor_window.setWindowOpacity(float(value)/100.0)

    def showProcessorWindow(self):
        self.show_process_window_button.setVisible(False)
        self.hide_process_window_button.setVisible(True)
        self.processor_window_opacity_slider.setVisible(True)

        self.processor_window.show()

    def hideProcessorWindow(self):
        self.show_process_window_button.setVisible(True)
        self.hide_process_window_button.setVisible(False)
        self.processor_window_opacity_slider.setVisible(False)

        self.processor_window.hide()

    def processPageCall(self):
        self.updateProcessorWindowSettings()

        self.processor_window.processInstagramPage()

    def processCall(self):
        self.updateProcessorWindowSettings()

        self.active =  self.start_process_button.isChecked()
        button_label = "Stop" if self.active else "Start"
        self.start_process_button.setText(button_label)

        if not self.processor_window:
            return

        # if the app was set to active. Start the instagram recoreder, othewise stop it.
        if self.active:
            self.processor_window.startInstagramCommenter()
        else:
            self.processor_window.stopInstagramCommenter()

def main():
    # create pyqt5 app
    App = QtWidgets.QApplication(sys.argv)
     
    # create the instance of our Window
    window = ProcessorWindowController()
     
    # showing the window
    window.show()


    # start the app
    sys.exit(App.exec())


if __name__ == "__main__":
    main()



#print(get_response("Anything exciting tonight?",'harinder-from-surrey'))
