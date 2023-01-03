from app_globals import *


import os,sys
import time
import math
import yaml

from PyQt5 import QtCore, QtWidgets, QtGui
import urllib
import urllib.request
import main_painter
import main_capture
import model_editor
from fileManagement import *
import numpy as np
import audio_receiver
import audio_creator
from optparse import OptionParser
import logging


if ACTIVE:
    import functions
    import models

APP_NAME = "openai-app"

logging.basicConfig()
log = logging.getLogger(APP_NAME)


# function connectors

def speak(text):
    audio_creator.speak(text)

def get_response_text(prompt,engine=DEFAULT_TEXT_CHOICE):
    if ACTIVE:
        return functions.get_response(prompt,engine=engine)
    return 'App is disabled.'

def get_response_code(prompt,engine=DEFAULT_CODE_CHOICE):
    if ACTIVE:
        return functions.get_response(prompt,engine=engine)
    return 'App is disabled.'

def get_response_image(prompt,size=DEFAULT_IMAGE_SIZE,n=DEFAULT_IMAGE_RESULTS):
    if ACTIVE:
        return functions.create_image(prompt,size=size,n=n)
    return None

def get_response_image_variation(image,size=DEFAULT_IMAGE_SIZE,n=DEFAULT_IMAGE_RESULTS):
    if ACTIVE:
        return functions.create_image_variation(image,size=size,n=n)
    return None

def get_response_image_edit(prompt,rgb_byte_array_or_file,alpha_byte_array_or_file,size=DEFAULT_IMAGE_SIZE,n=DEFAULT_IMAGE_RESULTS):
    if ACTIVE:
        return functions.create_edit_image(prompt,rgb_byte_array_or_file,alpha_byte_array_or_file,size=size,n=n)
    return None

def get_saved_model_list():
    return models.get_saved_model_list() 

def get_model_list(code=True, text=True):
    """    This function takes in a boolean for code and text, and returns a list of models.
            If code is True, it returns a list of code models.
            If text is True, it returns a list of text models.
            If both are True, it returns a list of all models."""
    if not ACTIVE:
        return []
    models = functions.get_model_list()
    ret_list = []
    
    for i in models:
        if code:
            if 'code' in i:
                ret_list.append(i)
        if text:
            if 'code' not in i:
                ret_list.append(i)

    return ret_list

def sanitized_prompt(prompt):
    """    This function takes in a prompt and removes all special characters.
    The function returns a sanitized prompt."""
    for i in '`~!@#$%^&*()+=?,.<>:;"\'/|}{][)(':
        prompt=prompt.replace(i,'')
    prompt= prompt.replace(' ','_')
    return prompt

def launch_usage_statistics_page():
    import webbrowser
    return webbrowser.open(OPENAPI_USAGE_PAGE)
    
def launch_playground_page():
    import webbrowser
    return webbrowser.open(OPENAPI_PLAYGROUND_PAGE)

def launch_fauxking_page():
    import webbrowser
    return webbrowser.open(FAUXKING_PAGE)
    
def auto_version(image_file):
    ret_image_file = image_file
    if os.path.isfile(image_file):
         ret_image_file=image_file.replace(".png","_1.png")
    return ret_image_file

def download_image(image_url, image_name, path=DOWNLOADS_DIR):
    """     This function takes in an image url, an image name, and a path.
            The function downloads the image and returns the image file. """

    if os.path.isfile(image_url):
        return image_url
    file = image_url
    if not os.path.isfile(file):
        #if its not a file, then try converting it to abs dirs.
        file = os.path.join(os.path.dirname(os.path.abspath(__file__)),image_url)
    if os.path.isfile(file):
        #if the converted file is exists url is now the file
        #print("Already downloaded.. ", image_url)
        return image_url


    #print("Downloading.. ", image_url)
    image_file = "{}{}".format(path,image_name)
    image_file = auto_version(image_file)
    functions.download_image(image_url, image_file)
    #time.sleep(0.01)
    if os.path.isfile(image_file):
        print("Saved to ", image_file)
        pass
    else:
        print("Could not download..")
        pass
    return image_file

def isImageFile(file):
    """     This function takes in a file and checks if it is an image file.
            The function returns a boolean."""
    if not isinstance(file,str):
        return False
    f = file.lower()
    img_file_types = ['.png','.jpg','jpeg']
    for i in img_file_types:
        if f.endswith(i):
            return True
    return False



# threads

class DownloadThread(QtCore.QThread):
    donloaded = QtCore.pyqtSignal(str)
    def __init__(self, parent, url, name, path):
        super(DownloadThread,self).__init__(parent)
        self.parent = parent
        self.url   = url
        self.active = True
        self.name = name
        self.path = path

    def stop(self):
        self.wait()

    def download_call(self):
        file = download_image(self.url, self.name, path=self.path)
        self.donloaded.emit( file )
        return

    def run(self):
        self.download_call()
        return

class SpeakerThread(QtCore.QThread):
    #audioReceived = QtCore.pyqtSignal(dict)
    def __init__(self, parent, currentText):
        super(SpeakerThread,self).__init__(parent)
        self.parent = parent
        self.active = True
        self.currentText = currentText

    def stop(self):
        self.quit()

    def run(self):
        speak(self.currentText)
        return

class MicrophoneThread(QtCore.QThread):
    audioReceived = QtCore.pyqtSignal(dict)
    def __init__(self, parent):
        super(MicrophoneThread,self).__init__(parent)
        self.parent = parent
        self.active = True

    def stop(self):
        self.wait()

    def get_audio(self):
        audio = audio_receiver.get_audio()
        #print(audio)
        self.audioReceived.emit( audio )
        return

    def run(self):
        self.get_audio()
        return

# GPT / CODEX Response Thread
class ResponseThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, model, model_type):#,response_type):
        super(ResponseThread,self).__init__(parent)
        self.parent = parent
        self.user_prompt   = user_prompt
        self.active = True
        self.model = model
        self.model_type = model_type
        #self.response_type = response_type

    def stop(self):
        self.wait()

    def request_call(self):
        response = self.model.getResponse(self.user_prompt, engine=self.model_type)

        self.responseReceived.emit( response )

        return

    def run(self):
        self.request_call()
        return

# DALLE Image Creation Response Thread
class ImageThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, size, num):#,response_type):
        super(ImageThread,self).__init__(parent)
        self.parent = parent
        self.user_prompt   = user_prompt
        self.active = True
        self.size = size
        self.num = num
        #self.response_type = response_type

    def stop(self):
        self.wait()

    def request_call(self):

        response = get_response_image(self.user_prompt,size=self.size,n=self.num)
        self.responseReceived.emit( response )
        return

    def run(self):
        self.request_call()
        return

# DALLE Image Variation Response Thread
class ImageVariationThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, size, num):#,response_type):
        super(ImageVariationThread,self).__init__(parent)
        self.parent = parent
        self.user_prompt   = user_prompt
        self.active = True
        self.size = size
        self.num = num
        #self.response_type = response_type

    def stop(self):
        self.wait()

    def request_call(self):

        #response = get_response_image(self.user_prompt,size=self.size,n=self.num)
        response = get_response_image_variation(self.user_prompt,size=self.size,n=self.num)
        self.responseReceived.emit( response )
        return

    def run(self):
        self.request_call()
        return

# DALLE Image Edit Response Thread
class ImageEditThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, rgb_byte_array, alpha_byte_array, size, num):#,response_type):
        super(ImageEditThread,self).__init__(parent)
        self.parent = parent
        self.user_prompt   = user_prompt
        self.active = True
        self.size = size
        self.num = num
        self.rgb_byte_array = rgb_byte_array
        self.alpha_byte_array = alpha_byte_array
        #self.response_type = response_type

    def stop(self):
        self.wait()

    def request_call(self):

        #response = get_response_image(self.user_prompt,size=self.size,n=self.num)
        #response = get_response_image_variation(self.user_prompt,size=self.size,n=self.num)
        response = get_response_image_edit(self.user_prompt,self.rgb_byte_array,self.alpha_byte_array,size=self.size,n=self.num)
        self.responseReceived.emit( response )
        return

    def run(self):
        self.request_call()
        return

# DALLE Image Edit Response Thread
class ImageEditedVariationThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, size, num):#,response_type):
        super(ImageEditedVariationThread,self).__init__(parent)
        self.parent = parent
        self.user_prompt   = user_prompt
        self.active = True
        self.size = size
        self.num = num

    def stop(self):
        self.wait()

    def request_call(self):

        response = get_response_image_variation(image,size=self.size,n=self.num)
        self.responseReceived.emit( response )
        return

    def run(self):
        self.request_call()
        return


# ui elements.

class ResultsTable(QtWidgets.QWidget):
    imageClicked = QtCore.pyqtSignal(str)
    variationRequested = QtCore.pyqtSignal(str)
    networkPushRequested = QtCore.pyqtSignal(list)
    promptSaveRequested = QtCore.pyqtSignal(list)
    sendToPromptRequested = QtCore.pyqtSignal(str)
    def __init__(self, *args, **kwargs):
        super(ResultsTable, self).__init__(*args, **kwargs)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addStretch()
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        layout_widget = QtWidgets.QWidget()
        layout_widget.setLayout(self.layout)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        #scrollbar_layout = QtWidgets.QVBoxLayout()
        scrollbar = QtWidgets.QScrollArea(widgetResizable=True)
        scrollbar.setWidget(layout_widget)
        main_layout.addWidget(scrollbar)



        self.setLayout(main_layout)

    def deleteAll(self):     
        for i in reversed(range(self.layout.count())): 
            widget = self.layout.itemAt(i).widget()
            if widget: 
                widget.setParent(None)

    def deleteWidget(self, widget):
        if widget:
            widget.setParent(None)

    def addResult(self,response_dict):
        """ appends the given data_str to the result table
                response_str    = response str OR response strs[] retrieved from openai
                sent_from       = "app" or "user"
                response_type   = "Code" or "Image" or "Text"

                blockPushToNetwork should be set to True when loading items from existing document. THis way existing items from older documents cant pushed back into the wrong model.
        """

        #response_type = GPT3
        response_type = response_dict.get('engine', GPT3)# dalle produces DALLE.

        sent_from  = response_dict.get('sent_from')
        alignRight = sent_from != FROM_APP
        #alignRight = False
        widget = None
        blockPushToNetwork = not response_dict.get('new', False)



        if response_type not in [DALLE,GPT3,CODEX]:
            if response_type in get_model_list(code=False, text=True):
                response_type = GPT3
            elif response_type in get_model_list(code=True, text=False):
                response_type = CODEX
            else:
                response_type = GPT3 # <-- fall back to text.




        if response_type in [GPT3, CODEX]:
            widget = TextResult()
            # when loading from an existing file, the item should never push into the model, so the connection should be made after the widget has loaded.
            if blockPushToNetwork:
                widget.inNetwork = True
            widget.networkPushRequested[list].connect(self.emitSaveToNetworkRequested)
            widget.promptSaveRequested[list].connect(self.emitSaveToExternalNetworkRequested)
            widget.sendToPromptRequested[str].connect(self.emitSendToPromptRequested)
            widget.deleteItemRequested[object].connect(self.deleteWidget)
            widget.setData(response_dict)


        else:

            images = response_dict.get('images')
            prompt = response_dict.get('prompt')
            widget = ImageResult()
            if prompt:
                widget.setPrompt(prompt)
            widget.addImages(images)
            widget.setResponseType(response_type)
            widget.setSentFrom(sent_from)

            #self.setRowHeight(0,widget.rowCount()*150)
            widget.sourceChanged[str].connect(self.emitImageClicked)
            widget.variationRequested[str].connect(self.emitVariationRequested)
            widget.deleteItemRequested[object].connect(self.deleteWidget)

        if widget:
            self.layout.insertWidget(0,widget)

    def getData(self):
        """returns a list of dicts that represents each row in the results table. """

        out_list = []

        for i in reversed(range(self.layout.count())): 
            widget= self.layout.itemAt(i).widget()        
            if widget:
                data_dict = widget.getData().copy()
                out_list.append(data_dict)

        return out_list

    def buildFromData(self,data_dicts):
        """ builds from a given list of dicts"""
        for data_dict in data_dicts:

            self.addResult(data_dict)

    def emitSendToPromptRequested(self,text_input):
        self.sendToPromptRequested.emit(text_input)

    def emitSaveToExternalNetworkRequested(self,prompt_and_response):
        self.promptSaveRequested.emit(prompt_and_response)

    def emitSaveToNetworkRequested(self,prompt_and_response):
        self.networkPushRequested.emit(prompt_and_response)

    def emitVariationRequested(self,source):

        self.variationRequested.emit(source)

    def emitImageClicked(self,source):

        self.imageClicked.emit(source)

class ResizingTextEdit(QtWidgets.QTextEdit):
    returnPressed = QtCore.pyqtSignal(bool)
    ctrlReturnPressed = QtCore.pyqtSignal(bool)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.computeHint)
        self._sizeHint = super().sizeHint()
        self.installEventFilter(self)

    def computeHint(self):
        hint = super().sizeHint()
        height = self.document().size().height()
        height += (self.frameWidth() * 2) 
        self._sizeHint.setHeight(max(int(height+10), int(hint.height())+10))

        self.setMinimumHeight(int(height))  # good if you want to insert this into a layout
        #self.resize(hint.width(), int(height))  # good if you want to insert this into a layout
        self.setMaximumHeight(400)
        self.updateGeometry()
        self.adjustSize()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress and obj is self:#(keyEvent -> modifiers() & Qt::ShiftModifier)
            if event.key() == QtCore.Qt.Key_Return and self.hasFocus() and not event.modifiers():
                #print('Enter pressed')
                self.returnPressed.emit(True)
                return True
            elif event.key() == QtCore.Qt.Key_Return and self.hasFocus() and event.modifiers() == QtCore.Qt.ControlModifier:
                #print('Enter pressed')
                self.ctrlReturnPressed.emit(True)
                return True

        return super().eventFilter(obj, event)


    def sizeHint(self):
        return self._sizeHint

class TextEditWindow(QtWidgets.QDialog):
    def __init__(self):
        #super().__init__()
        super(TextEditWindow, self).__init__()
        self.setWindowTitle("Edit text")

        layout = QtWidgets.QVBoxLayout()
        self.textEdit = QtWidgets.QPlainTextEdit()
        layout.addWidget(self.textEdit)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def getValue(self):
        return str(self.textEdit.toPlainText())

    def setValue(self, value):
        self.textEdit.setPlainText(str(value))

class ModelViewerWindow(QtWidgets.QDialog):
    def __init__(self, model):
        #super().__init__()
        super(ModelViewerWindow, self).__init__()
        
        main_layout = QtWidgets.QVBoxLayout()
        layout  = QtWidgets.QHBoxLayout()
        layout1 = QtWidgets.QVBoxLayout()
        layout2 = QtWidgets.QVBoxLayout()
        layout.addLayout(layout1)
        layout.addLayout(layout2)
        main_layout.addLayout(layout)


        self.model = model

        self.setWindowTitle("Current Model : {}".format(self.model.name))


        self.textEdit = QtWidgets.QPlainTextEdit()
        self.textEdit = model_editor.CodeEditor()
        self.textEdit.setPlainText(self.model.prompt)

        layout1.addWidget(QtWidgets.QLabel("{}: {}".format("Name", self.model.name)))
        layout1.addWidget(QtWidgets.QLabel("{}: {}".format("Path", self.model.model_path)))
        layout1.addWidget(self.textEdit)


        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Options File", self.model.optionsFile)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Prompt File", self.model.promptFile)))

        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Engine", self.model.engine)))
        
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Temperature", self.model.temperature)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Top P", self.model.top_p)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Max Length", self.model.max_tokens)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Frequency Penalty", self.model.frequency_penalty)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Presence Penalty", self.model.presence_penalty)))

        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Inject Start Text", self.model.inject_start_text)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Inject Restart Text", self.model.inject_restart_text)))

        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Stop Sequence", self.model.stop)))
        layout2.addWidget(QtWidgets.QLabel("{}: {}".format("Best Of", self.model.best_of)))


        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)# | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        #self.buttonBox.rejected.connect(self.reject)
        main_layout.addWidget(self.buttonBox)


        self.setLayout(main_layout)





class APIKeyWindow(QtWidgets.QDialog):
    def __init__(self):
        #super().__init__()
        super(APIKeyWindow, self).__init__()
        self.setWindowTitle("Set your API Key")

        layout = QtWidgets.QVBoxLayout()
        self.textEdit = QtWidgets.QLineEdit()
        self.textEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.textEdit)

        try:
            current_credentials = str(read_credentials())
        except:
            current_credentials = ''

        self.setValue(current_credentials)


        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.acceptSave)
        self.buttonBox.rejected.connect(self.reject)

        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def acceptSave(self):
        api_key = self.getValue()
        save_credentials(api_key)
        return self.accept()

    def getValue(self):
        return str(self.textEdit.text())

    def setValue(self, value):
        self.textEdit.setText(str(value))


class TextResult(QtWidgets.QWidget):

    # this will be emitted when the result needs to be pushed back to the model, first item is the request from the user, second is the response from the app
    networkPushRequested = QtCore.pyqtSignal(list)

    # this will be emitted when only the prompt/response of this widget needs to be saved
    promptSaveRequested = QtCore.pyqtSignal(list)

    #when an item needs to be pushed back to the prompter
    sendToPromptRequested = QtCore.pyqtSignal(str)

    deleteItemRequested = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(TextResult, self).__init__(*args, **kwargs)
        #self._sizeHint = super().sizeHint()
        self.prompt = ""
        self.response = ""
        self.sent_from = None
        self.response_type = "Text"
        self.speakThread = None
        self.model_path = None
        self.engine = None

        self.data = {} # this will hold all the original info passed down to this widget so we can rebuild it from a saved file.


        self.inNetwork = False
        self.extNetwork = False
        layout = QtWidgets.QHBoxLayout()

        #self.textArea = ResizingTextEdit()
        self.textArea = QtWidgets.QLabel()
        #self.textArea = QtWidgets.QTextEdit()


        self.textArea.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.textArea.setWordWrap(True)

        layout.addWidget(self.textArea)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)


        self.deleteCheckbox = QtWidgets.QCheckBox(self) 
        self.deleteCheckbox.setToolTip("Delete this item.")
        self.deleteCheckbox.setGeometry(4, 0, 14, 20)
        self.deleteCheckbox.setStyleSheet(CLOSE_CHECKBOX_STYLE)


        self.networkCheckbox = QtWidgets.QCheckBox(self) 
        self.networkCheckbox.setToolTip("Feed back to Internal Network, uses this current response to generate future responses for this session.")
        self.networkCheckbox.setGeometry(19, 0, 29, 20)
        self.networkCheckbox.setStyleSheet(INTERNAL_NETWORK_CHECKBOX_STYLE)

        self.ext_networkCheckbox = QtWidgets.QCheckBox(self) 
        self.ext_networkCheckbox.setToolTip("Feed back to External Network, seves this respone to Ai model to be used in the future, outside of this session.")
        self.ext_networkCheckbox.setGeometry(34, 0, 44, 20)
        self.ext_networkCheckbox.setStyleSheet(EXTERNAL_NETWORK_CHECKBOX_STYLE)



        self.textArea.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.textArea.customContextMenuRequested.connect(self.responseContextMenu)

        self.networkCheckbox.clicked.connect(self.saveToInternalNetwork)
        self.ext_networkCheckbox.clicked.connect(self.saveToExternalNetwork)
        self.deleteCheckbox.clicked.connect(self.deleteCall)

        self.setMinimumHeight(50)

    def responseContextMenu(self):

        menu = QtWidgets.QMenu()
        #menu.addAction('Copy')


        # currently implemented as bad as possible.
        speakrompt = QtWidgets.QAction('Speak', self.textArea)
        speakrompt.triggered.connect( self.speakCall )
        menu.addAction(speakrompt)

        #stopSpeakPrompt = QtWidgets.QAction('Stop Speaking', self.textArea)
        #stopSpeakPrompt.triggered.connect( self.stopSpeakCall )
        #menu.addAction(stopSpeakPrompt)



        sendToPrompt = QtWidgets.QAction('Send back to user prompt', self.textArea)
        sendToPrompt.triggered.connect( self.sendToPromptCall )
        menu.addAction(sendToPrompt)

        editPrompt = QtWidgets.QAction('Edit', self.textArea)
        editPrompt.triggered.connect( self.editCall )
        menu.addAction(editPrompt)

        #menu.addAction('Edit')
        #menu.addAction('Select All')
        #menu.addAction('Remove')
        menu.addSeparator()
        #menu.addAction('Feed back to Network')


        saveToNetworkAction = QtWidgets.QAction('Feed back to Internal Network', self.textArea)
        saveToNetworkAction.triggered.connect( self.saveToInternalNetwork )
        menu.addAction(saveToNetworkAction)
        if self.inNetwork:
            saveToNetworkAction.setDisabled(True)

        saveToExternalNetworkAction = QtWidgets.QAction('Feed back to External Network', self.textArea)
        saveToExternalNetworkAction.triggered.connect( self.saveToExternalNetwork )
        menu.addAction(saveToExternalNetworkAction)
        if self.extNetwork:
            saveToExternalNetworkAction.setDisabled(True)

        menu.exec_(QtGui.QCursor.pos())

    def stopSpeakCall(self):
        if self.speakThread:
            self.speakThread.stop()

    def speakCall(self):
        currentText = self.getText()

        self.speakThread = SpeakerThread(self, currentText)
        self.speakThread.start()

    def editCall(self):
        dlg = TextEditWindow()
        dlg.setValue(self.getText())
        if dlg.exec_():
            value = dlg.getValue()
            self.setResponse(value)
        return

    def deleteCall(self):
        self.deleteItemRequested.emit( self )
        return

    def sendToPromptCall(self):
        currentText = self.getText()
        self.sendToPromptRequested.emit(currentText)

    def autoSaveToExternalNetworkOnLoad(self):
        if SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE:
            self.saveToExternalNetwork()

    def autoSaveToInternalNetworkOnLoad(self):
        if AUTO_FEED_NETWORK:
            self.saveToInternalNetwork()

    def saveToExternalNetwork(self):
        if self.extNetwork:
            return
        if self.sent_from != FROM_APP:
            return
        if not self.prompt or self.prompt == "":
            return
        if not self.response or self.response == "":
            return


        self.extNetwork = True

        # push the response back to the active model.
        emit_list = [self.prompt, self.response]
        #print (emit_list)
        self.promptSaveRequested.emit( emit_list )


        self.parseExtNetworkIcon()
        if VERBOSE:
            print("----- SAVING PROMPT TO EXTERNAL NETWORK")
        return

    def saveToInternalNetwork(self):
        if self.inNetwork:
            return
        if self.sent_from != FROM_APP:
            return
        if not self.prompt or self.prompt == "":
            return
        if not self.response or self.response == "":
            return


        self.inNetwork = True

        # push the response back to the active model.
        emit_list = [self.prompt, self.response]
        #print (emit_list)
        self.networkPushRequested.emit( emit_list )


        self.parseInNetworkIcon()

        if VERBOSE:
            print("----- SAVING PROMPT TO INTERNAL NETWORK")
        return

    def parseExtNetworkIcon(self):
        self.ext_networkCheckbox.setChecked(self.extNetwork)
        if self.extNetwork:
            self.ext_networkCheckbox.setDisabled(True)
            self.ext_networkCheckbox.setVisible(False)
        if self.sent_from != FROM_APP:
            self.ext_networkCheckbox.setVisible(False)

    def parseInNetworkIcon(self):
        self.networkCheckbox.setChecked(self.inNetwork)
        if self.inNetwork:
            self.networkCheckbox.setDisabled(True)
            self.networkCheckbox.setVisible(False)
        if self.sent_from != FROM_APP:
            self.networkCheckbox.setVisible(False)

    def updateStyleSheet(self):
        style = APP_RESPONSE_STYLESHEET
        if self.sent_from:
            if self.sent_from != FROM_APP:
                style = USER_PROMPT_STYLESHEET
        self.textArea.setStyleSheet(style)

    # older

    def setAlignment(self, alignment):
        self.textArea.setAlignment(alignment)

    def setResponseType(self,response_type):
        self.response_type = response_type
        #self.autoSaveToInternalNetworkOnLoad()
        #self.autoSaveToExternalNetworkOnLoad()

    def setResponse(self,text):
        self.response = text
        self.setText(text)
        #self.autoSaveToInternalNetworkOnLoad()
        #self.autoSaveToExternalNetworkOnLoad()

    def setPrompt(self, prompt):
        self.prompt = prompt
        #self.autoSaveToInternalNetworkOnLoad()
        #self.autoSaveToExternalNetworkOnLoad()

    def setSentFrom(self,sent_from):
        self.sent_from = sent_from
        self.updateStyleSheet()
        self.parseInNetworkIcon()
        self.parseExtNetworkIcon()
        #self.autoSaveToInternalNetworkOnLoad()
        #self.autoSaveToExternalNetworkOnLoad()

    def setText(self, text):
        #self.textArea.setHtml(text)
        #self.textArea.setPlainText(text)
        self.textArea.setText(text)


        self.updateSize()

    def getText(self):
        #return str(self.textArea.toPlainText())
        return str(self.textArea.text())

    def updateSize(self):

        

        #self.resize(self.sizeHint().width(), int(self.textArea.sizeHint().height()))  # good if you want to insert this into a layout
        self.setMinimumHeight(self.textArea.sizeHint().height()+20)
        self.sizeHint().setHeight(self.textArea.sizeHint().height()+20)
        #self.updateGeometry()
        #self.adjustSize()


    def getData(self):
        """returns a dict containinf info for th items contained in this widget"""
        prompt = self.prompt
        model_path = self.model_path
        response = self.getText()
        sent_from = self.sent_from
        response_type = self.response_type
        model_path = self.model_path
        engine = self.engine
        ret_dict =  {
                        "prompt":prompt,
                        "response":response,
                        "sent_from":sent_from,
                        "response_type":response_type,
                        "engine":engine,
                        "model_path":model_path
                    }
        return ret_dict


    def setData(self, data_dict):
        if VERBOSE:
            print("Processing Item:",data_dict)
        self.data = data_dict

        self.prompt          = data_dict.get('prompt')

        self.response        = data_dict.get('response')
        #FROM USER:
        self.sent_from       = data_dict.get('sent_from')
        #alignRight = sent_from != FROM_APP
        alignRight = False
        if self.sent_from == FROM_USER:
            alignRight = True
            self.response = self.prompt

        else:
            if not self.response:
                if "choices" in data_dict:
                    self.response = data_dict["choices"][0]["text"]
                else:
                    self.response = COULD_NOT_FETCH_MESSAGE

        alignRight = False # THis is because when pasting in code, things needs to be formatted.

        self.response_type    = GPT3

        is_new           = data_dict.get('new', False) # this will NOT be sent back when the getData method is executed.

        if not is_new:
            self.inNetwork = False

        self.model_path = data_dict.get('model_path')
        
        self.engine  = data_dict.get('engine')
        #self.temperature = data_dict.get('temperature')

        self.setResponse(self.response)
        self.setResponseType(self.response_type)
        self.setSentFrom(self.sent_from)

        if self.prompt and self.sent_from != FROM_USER:
            self.setPrompt(self.prompt)

        if alignRight:
            self.setAlignment(QtCore.Qt.AlignRight)

        if is_new:
            self.autoSaveToInternalNetworkOnLoad()
            self.autoSaveToExternalNetworkOnLoad()

class ImageResult(QtWidgets.QWidget):
    sourceChanged = QtCore.pyqtSignal(str)
    variationRequested = QtCore.pyqtSignal(str)
    deleteItemRequested = QtCore.pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        super(ImageResult, self).__init__(*args, **kwargs)
        self.prompt = "image"
        self.urls = None
        self.sent_from = None
        self.response_type = DALLE

        self.data = {}

        layout = QtWidgets.QVBoxLayout()

        self.imageTable = QtWidgets.QTableWidget()
        layout.addWidget(self.imageTable)
        layout.addStretch()

        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.deleteCheckbox = QtWidgets.QCheckBox(self) 
        self.deleteCheckbox.setToolTip("Delete this item.")
        self.deleteCheckbox.setGeometry(4, 0, 14, 20)
        self.deleteCheckbox.setStyleSheet(CLOSE_CHECKBOX_STYLE)

        self.imageTable.cellClicked[int,int].connect(self.emitSourceChanged)
        self.deleteCheckbox.clicked.connect(self.deleteCall)

    def deleteCall(self):
        self.deleteItemRequested.emit( self )
        return

    def updateStyleSheet(self):
        style = APP_RESPONSE_STYLESHEET
        if self.sent_from:
            if self.sent_from != FROM_APP:
                style = USER_PROMPT_STYLESHEET
        self.imageTable.setStyleSheet(style)

    def setResponseType(self,response_type):
        self.response_type = response_type

    def setPrompt(self,prompt):
        self.prompt = prompt

    def addImages(self,urls):
        """ builds the table from a given urls"""
        self.imageTable.cellClicked[int,int].disconnect(self.emitSourceChanged)
        self.urls = urls
        #rows = math.floor(math.sqrt(len(urls)))
        #columns = math.ceil(math.sqrt(len(urls)))

        _len = len(urls)
        if _len<=4:
            rows = 1
            columns = _len
        elif _len<=8:
            rows=2
            columns = 4
        elif _len<=12:
            rows=3
            columns = 4
        else:
            rows = math.floor(math.sqrt(len(urls)))
            columns = math.ceil(math.sqrt(len(urls)))

        self.imageTable.verticalHeader().hide()
        self.imageTable.horizontalHeader().hide()
        self.imageTable.setColumnCount(columns)
        self.imageTable.setRowCount(rows)
        self.imageTable.setFixedHeight(rows*164)

        ind=0
        for row in range(rows):
            for column in range(columns):
                if ind < len(urls):
                    table_image = ImagePreview(urls[ind])
                    table_image.setPrompt(self.prompt)
                    self.imageTable.setCellWidget(row,column,table_image)
                    if AUTO_DOWNLOAD_IMAGE_RESULTS and not table_image.downloaded():
                        #filename = "{}_{}.png".format(sanitized_prompt(self.prompt), getTimeStamp())
                        #download_image(urls[ind], filename)
                        table_image.download()
                ind+=1

        self.imageTable.resizeRowsToContents()
        self.imageTable.resizeColumnsToContents() 
        self.imageTable.cellClicked[int,int].connect(self.emitSourceChanged)

    def setSentFrom(self,sent_from):
        self.sent_from = sent_from
        self.updateStyleSheet()

    def emitSourceChanged(self,row,column):
        widget = self.imageTable.cellWidget(row,column)
        if widget:
            source = widget.getSource()
            self.sourceChanged.emit(source)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self.imageTable)

        generateVariationsAction = QtWidgets.QAction('Generate Variations', self.imageTable)
        generateVariationsAction.triggered.connect(lambda: self.generateVariationsEvent(event))
        self.menu.addAction(generateVariationsAction)

        downloadAction = QtWidgets.QAction('Download Selected', self.imageTable)
        downloadAction.triggered.connect(lambda: self.downloadEvent(event))
        self.menu.addAction(downloadAction)


        downloadCustomAction = QtWidgets.QAction('Download Selected to Folder..', self.imageTable)
        downloadCustomAction.triggered.connect(lambda: self.downloadCustomEvent(event))
        self.menu.addAction(downloadCustomAction)


        inspectAction = QtWidgets.QAction('Inspect Element', self.imageTable)
        inspectAction.triggered.connect(lambda: self.inspectEvent(event))
        self.menu.addAction(inspectAction)

        # add other required actions
        self.menu.popup(QtGui.QCursor.pos())

    def getSelectedWidgets(self):
        sources = []
        for item in self.imageTable.selectedIndexes():
            row,col=item.row(), item.column()
            widget = self.imageTable.cellWidget(row,col)
            if widget:
                sources.append(widget)
        return sources
    
    def getSelectedSources(self):
        sources = []
        for item in self.imageTable.selectedIndexes():
            row,col=item.row(), item.column()
            widget = self.imageTable.cellWidget(row,col)
            if widget:
                source = widget.getSource()
                sources.append(source)
        return sources

    def getWidgets(self):
        widgets = []
        for row in range(self.imageTable.rowCount()):
            for column in range(self.imageTable.columnCount()):
                widget = self.imageTable.cellWidget(row,column)
                if widget:
                    widgets.append(widget)
        return widgets

    def getSources(self):
        sources = []
        for widget in self.getWidgets():
            if widget:
                source=widget.getSource()
                sources.append(source)
        return sources

    def getData(self):
        """returns a dict containinf info for th items contained in this widget"""
        prompt = self.prompt
        response = self.getSources()
        sent_from = self.sent_from
        response_type = self.response_type

        ret_dict =  {
                        "prompt":prompt,
                        "response":response,
                        "sent_from":sent_from,
                        "response_type":response_type
                    }
        return ret_dict

    def getData(self):
        return self.data

    def getData(self):
        """returns a dict containinf info for th items contained in this widget"""
        prompt = self.prompt
        #model_path = self.model_path
        response = self.getSources()
        images = self.getSources()
        sent_from = self.sent_from
        response_type = self.response_type
        #model_path = self.model_path
        engine = DALLE
        #engine = self.engine
        ret_dict =  {
                        "images":images,
                        "prompt":prompt,
                        "response":response,
                        "sent_from":sent_from,
                        "response_type":response_type,
                        "engine":engine,
                    }
        return ret_dict


    def setData(self, data_dict):
        self.data = data_dict

    def inspectEvent(self,event):

        selected = self.getSelectedWidgets()
        if not len(selected):
            return
        selected = selected[0]

        source = selected.getSource()

        QtWidgets.QMessageBox.about(self, "Source:", source)

    def generateVariationsEvent(self, event):
        # this is broken. if tis not downloaded, then we need a thread to submit it like we do from the editor, using the rgb information.
        prompt = self.prompt

        selected = self.getSelectedWidgets()
        if not len(selected):
            return
        selected = selected[0]

        if not selected.downloaded():
            source = selected.download()
        else:
            source = selected.getSource()
        #source = "C:\\Sandbox\\Python\\openai\\saved\\futuristic_cars_1671933376.png"
        self.variationRequested.emit(source)

    def downloadCustomEvent(self, event):

        dialog = QtWidgets.QFileDialog(self.imageTable, 'Choose a folder to save into', DOWNLOADS_DIR)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setSidebarUrls([QtCore.QUrl.fromLocalFile(DOWNLOADS_DIR)])

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            path = dialog.selectedFiles()[0]
            if not path.endswith('\\'):
                path = path+'\\'

        for source in self.getSelectedWidgets():
            source.download(path=path)

    def downloadEvent(self, event):
        for source in self.getSelectedWidgets():
            source.download()


class ImagePreview(QtWidgets.QWidget):

    def __init__(self, source):
        super(ImagePreview, self).__init__()
        self.image_widget = QtWidgets.QLabel(self)
        #self.setStyleSheet("border: 1px solid black; border-radius: 1px; padding: 1px;")
        self.source = None
        self.prompt = None
        self.preview_size = 104#116#124
        self.isDownloaded = False


        layout=QtWidgets.QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.image_widget)
        #self.downloaded_checkbox.move(30,30)
        
        self.setLayout(layout)

        self.downloaded_checkbox = QtWidgets.QCheckBox(self) 
        self.downloaded_checkbox.setGeometry(10, 2, 30, 30)

        if source:
            self.setSource(source)

        self.downloaded_checkbox.clicked.connect(self.download)
        self.downloaded_checkbox.setToolTip('Downloaded')
        self.setStyleSheet(IMAGE_PREVIEW_STYLESHEET)

    def setPrompt(self, prompt):
        if self.prompt == prompt:
            return False
        self.prompt = prompt
        return True

    def getPrompt(self):

        return self.prompt

    def setSource(self,source):
        if self.source == source:
            return False

        file = source
        if not os.path.isfile(file):
            #if its not a file, then try converting it to abs dirs.
            file = os.path.join(os.path.dirname(os.path.abspath(__file__)),source)
            if os.path.isfile(file):
                #if the converted file is exists url is now the file
                source = file

        self.source = source
        #print ('--------',self.source)
        if not self.source.startswith('http'):
            source = self.source
            if not os.path.isfile(self.source):
                #data = urllib.request.urlopen(self.source).read()
                source = DELETED_IMAGE
            image = QtGui.QImage()
            image.load(source)
            pixmap = QtGui.QPixmap(image)
            pixmap_resized = pixmap.scaled(self.preview_size, self.preview_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.image_widget.setPixmap(pixmap_resized)
            self.isDownloaded = True

            
        else:
            try:
                data = urllib.request.urlopen(self.source).read()
                image = QtGui.QImage()
                image.loadFromData(data)
            except:
                image = QtGui.QImage()
                image.load(MISSING_IMAGE)

            pixmap = QtGui.QPixmap(image)
            pixmap_resized = pixmap.scaled(self.preview_size, self.preview_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.image_widget.setPixmap(pixmap_resized)

        self.setToolTip(self.source)
        self.downloaded_checkbox.setChecked(self.isDownloaded)
        self.downloaded_checkbox.setDisabled(self.isDownloaded)
        self.downloaded_checkbox.setVisible(not self.isDownloaded)

        return True

    def getSource(self):

        return self.source

    def download(self,path=None):
        #ignore booleans!!!!
        if path is True or path is False:
            path = DOWNLOADS_DIR

        path = path or DOWNLOADS_DIR
        """ downloads the source if its an url, and uses the new downlaoded image instead of the url"""
        if os.path.isfile(self.source) and path is None:
            #if the source is already downloaded, and no new path is given return early
            return

        
        prompt = self.getPrompt()
        if not prompt:
            prompt = 'image'
        else:
            prompt = sanitized_prompt(prompt)
        filename = "{}_{}.png".format(prompt, getTimeStamp())
        #if not path:
        #    path = DOWNLOADS_DIR


        thread = DownloadThread(self, self.source, filename, path)
        thread.donloaded[str].connect(self.downloadFinished)
        thread.start()


        """
        file = download_image(self.source,filename,path=path)
        
        if file:
            self.setSource(file)
            self.isDownloaded = True
            
        self.downloaded_checkbox.setChecked(self.isDownloaded)
        self.downloaded_checkbox.setDisabled(self.isDownloaded)
        """
        return# self.getSource()

    def downloadFinished(self, file):


        if file:
            self.setSource(file)
            self.isDownloaded = True
            
        self.downloaded_checkbox.setChecked(self.isDownloaded)
        self.downloaded_checkbox.setDisabled(self.isDownloaded)
        self.downloaded_checkbox.setVisible(not self.isDownloaded)

        return self.getSource()

    def downloaded(self):
        
        return self.isDownloaded

class ResonseRequesetButton(QtWidgets.QWidget):

    #emits a request dict when a reply is requested
    requestResponseClicked  = QtCore.pyqtSignal(dict)

    #emits a request dict when image generation is requested
    requestImageClicked     = QtCore.pyqtSignal(dict)

    #emits a str for the path of the chosen model
    modelChanged            = QtCore.pyqtSignal(str)


    def __init__(self, *args, **kwargs):
        super(ResonseRequesetButton, self).__init__(*args, **kwargs)

        self.resolution = DEFAULT_IMAGE_SIZE
        self.number     = DEFAULT_IMAGE_RESULTS
        self.model_name = ''
        self.model_path = ''
        self.engine     = DEFAULT_TEXT_CHOICE
        self.icon       = DEFAULT_MODEL_ICON


        layout=QtWidgets.QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.setAlignment(QtCore.Qt.AlignTop)


        self.model_button = QtWidgets.QPushButton()
        layout.addWidget(self.model_button,0,0)
        self.model_button.setFixedHeight(50)
        self.model_button.setFixedWidth(75)
        self.model_button.setIcon(QtGui.QIcon(self.icon))
        self.model_button.setIconSize(QtCore.QSize(60,40))
        self.model_button.setToolTip("Click to generate a response to your prompt.")


        self.image_button = QtWidgets.QPushButton()
        layout.addWidget(self.image_button,1,0)
        self.image_button.setFixedHeight(25)
        self.image_button.setFixedWidth(75)
        self.image_button.setIcon(QtGui.QIcon(DALLE2_ICON))
        self.image_button.setIconSize(QtCore.QSize(65,20))
        self.image_button.setToolTip("Click to generate an image from your prompt.")
        

        self.model_settings_button = QtWidgets.QPushButton()
        self.model_settings_button.setFixedHeight(50)
        self.model_settings_button.setFixedWidth(20)
        self.model_settings_button.setToolTip("Choose a model.")
        layout.addWidget(self.model_settings_button,0,1)


        self.image_settings_button = QtWidgets.QPushButton()
        self.image_settings_button.setFixedHeight(25)
        self.image_settings_button.setFixedWidth(20)
        self.image_settings_button.setToolTip("Modify Image Settings.")
        layout.addWidget(self.image_settings_button,1,1)
        


        self.model_menu = QtWidgets.QMenu()
        self.model_settings_button.setMenu(self.model_menu)
        self.image_menu  = QtWidgets.QMenu()
        self.image_settings_button.setMenu(self.image_menu)
        self.resolution_menu = self.image_menu.addMenu('Resolution')
        self.number_menu = self.image_menu.addMenu('Number')

        self.setModelMenus()
        self.setImageMenus()

        self.setLayout(layout)

        self.model_button.clicked.connect(self.requestResponseClickedEmitter)
        self.image_button.clicked.connect(self.requestImageClickedEmitter)


    def setModelMenus(self):

        self.model_menu.clear()
        for i in ['']+get_saved_model_list() :
            loadSavedModelAction = QtWidgets.QAction(i, self)
            loadSavedModelAction.setCheckable(True)
            if str(i) == str(self.model_name):
                loadSavedModelAction.setChecked(True)
            else:
                loadSavedModelAction.setChecked(False)

            icon = os.path.join(str(models.get_model_path(i)), 'icon.png')
            if os.path.isfile(icon):
                loadSavedModelAction.setIcon(QtGui.QIcon(icon))
            else:
                loadSavedModelAction.setIcon(QtGui.QIcon(DEFAULT_MODEL_ICON))

            self.model_menu.addAction(loadSavedModelAction)
            loadSavedModelAction.triggered.connect(self._updateModelName)

        return

    def setImageMenus(self):

        self.resolution_menu.clear()
        for i in IMAGE_SIZES:
            resolutionAction = QtWidgets.QAction(i, self)
            resolutionAction.setCheckable(True)
            if str(i) == str(self.resolution):
                resolutionAction.setChecked(True)
            else:
                resolutionAction.setChecked(False)
            self.resolution_menu.addAction(resolutionAction)
            resolutionAction.triggered.connect(self._updateResolution)


        self.number_menu.clear()
        for i in [str(x) for x in range(1,11)] :
            numberAction = QtWidgets.QAction(i, self)
            numberAction.setCheckable(True)
            if str(i) == str(self.number):
                numberAction.setChecked(True)
            else:
                numberAction.setChecked(False)
            self.number_menu.addAction(numberAction)
            numberAction.triggered.connect(self._updateNumber)

        return

    def requestResponseClickedEmitter(self):
        """ emits a signal containging a dict of values from the selected options """
        request_dict = {'model_path':self.model_path, 'model_name':self.model_name}
        self.requestResponseClicked.emit(request_dict)
        print(request_dict)

    def requestImageClickedEmitter(self):
        request_dict = {'number':self.number,'resolution':self.resolution}
        self.requestImageClicked.emit(request_dict)
        print(request_dict)

    def _updateModelName(self):
        
        self.model_name = self.sender().text()

        self.model_path = models.get_model_path(self.model_name)
        if self.model_path is None:
            self.model_path = ''
        self.icon = os.path.join(self.model_path, 'icon.png')
        if not os.path.isfile(self.icon):
            self.icon = DEFAULT_MODEL_ICON
        self.model_button.setIcon(QtGui.QIcon(self.icon))
        self.setModelMenus()

        self.modelChanged.emit(self.model_path)
        print(self.model_path)




    def _updateResolution(self,resolution=None):
        self.resolution = self.sender().text()
        self.setImageMenus()

    def _updateNumber(self):
        self.number = int(self.sender().text())
        self.setImageMenus()


    def getResolution(self):

        return self.resolution

    def getNumber(self):

        return self.number


    def reloaModelList(self):

        self.setModelMenus()

    def setModel(self,model_name):

        self.model_name = model_name
        
        self.model_path = models.get_model_path(self.model_name)
        if self.model_path is None:
            self.model_path = ''
        self.icon = os.path.join(self.model_path, 'icon.png')
        if not os.path.isfile(self.icon):
            self.icon = DEFAULT_MODEL_ICON
        self.model_button.setIcon(QtGui.QIcon(self.icon))
        self.setModelMenus()

        self.modelChanged.emit(self.model_path)
        print(self.model_path)

class Window(QtWidgets.QWidget):

    def __init__(self):
        super(Window, self).__init__()

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(APP_ICON))
        self.setGeometry(0, 0, 700, 1024)
        #self.setStyleSheet(APP_STYLE)
        self.currentFile = None
        self.documentModified = False
        self.model = models.Model()
        self.engine = DEFAULT_TEXT_CHOICE

        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.mainMenu = QtWidgets.QMenuBar()
        
        layout.setMenuBar(self.mainMenu)
        if CHAT_MODE:
            self.mainMenu.setVisible(False)
 


        fileMenu = self.mainMenu.addMenu("File")

        # creating save action
        saveAction = QtWidgets.QAction("Save", self)
        # adding short cut for save action
        saveAction.setShortcut("Ctrl+S")
        # adding save to the file menu
        fileMenu.addAction(saveAction)
        # adding action to the save
        saveAction.triggered.connect(self.saveCall)
 

        # creating save as action
        saveAction = QtWidgets.QAction("Save-As", self)
        # adding short cut for save action
        saveAction.setShortcut("Ctrl+Shift+S")
        # adding save to the file menu
        fileMenu.addAction(saveAction)
        # adding action to the save
        saveAction.triggered.connect(self.saveAsCall)


        # creating open action
        openAction = QtWidgets.QAction("Open", self)
        # adding short cut for save action
        openAction.setShortcut("Ctrl+O")
        # adding save to the file menu
        fileMenu.addAction(openAction)
        # adding action to the save
        openAction.triggered.connect(self.openCall)

        # creating open action
        importAction = QtWidgets.QAction("Import", self)
        # adding short cut for save action
        importAction.setShortcut("Ctrl+I")
        # adding save to the file menu
        fileMenu.addAction(importAction)
        # adding action to the save
        importAction.triggered.connect(self.importCall)


        # creating revert action
        revertAction = QtWidgets.QAction("Revert", self)
        # adding short cut to the clear action
        #revertAction.setShortcut("Ctrl + C")
        # adding clear to the file menu
        fileMenu.addAction(revertAction)
        # adding action to the clear
        revertAction.triggered.connect(self.revertCall)


        # creating clear action
        clearAction = QtWidgets.QAction("Clear", self)
        # adding short cut to the clear action
        #clearAction.setShortcut("Ctrl + C")
        # adding clear to the file menu
        fileMenu.addAction(clearAction)
        # adding action to the clear
        clearAction.triggered.connect(self.clearCall)



        prefsMenu = self.mainMenu.addMenu("Preferences")

        # creating save action
        autoSaveImagesAction = QtWidgets.QAction("Always Save Generated Images", self)
        autoSaveImagesAction.setCheckable(True)
        autoSaveImagesAction.setChecked(AUTO_DOWNLOAD_IMAGE_RESULTS)
        # adding save to the file menu
        prefsMenu.addAction(autoSaveImagesAction)
        # adding action to the save
        autoSaveImagesAction.triggered.connect(self.autoSaveImagesCall)


        
        autoFeedNetworkAction = QtWidgets.QAction("Always Feed the Network with Generated Results", self)
        autoFeedNetworkAction.setCheckable(True)
        #autoFeedNetworkAction.setVisible(False)
        autoFeedNetworkAction.setChecked(AUTO_FEED_NETWORK)
        # adding save to the file menu
        prefsMenu.addAction(autoFeedNetworkAction)
        # adding action to the save
        autoFeedNetworkAction.triggered.connect(self.autoFeedNetworkCall)


        autoSaveNetworkAction = QtWidgets.QAction("Always Save the Network after each Generated Result", self)
        autoSaveNetworkAction.setCheckable(True)
        autoSaveNetworkAction.setChecked(SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE)
        # adding save to the file menu
        prefsMenu.addAction(autoSaveNetworkAction)
        # adding action to the save
        autoSaveNetworkAction.triggered.connect(self.autoSaveNetworkPromptCall)


        # creating save action
        setDownloadsDirectory = QtWidgets.QAction("Set Downloads Directory..", self)
        # adding save to the file menu
        prefsMenu.addAction(setDownloadsDirectory)
        # adding action to the save
        setDownloadsDirectory.triggered.connect(self.setDownloadsDirectoryCall)


        # creating save action
        setModelsDirectory = QtWidgets.QAction("Set Models Directory..", self)
        # adding save to the file menu
        prefsMenu.addAction(setModelsDirectory)
        # adding action to the save
        setModelsDirectory.triggered.connect(self.setModelsDirectoryCall)


        # creating save action
        setApiKey = QtWidgets.QAction("Set API Key..", self)
        # adding save to the file menu
        prefsMenu.addAction(setApiKey)
        # adding action to the save
        setApiKey.triggered.connect(self.setApiKeyCall)


        # creating save action
        savaCurrentPreferences = QtWidgets.QAction("Save Current Choices as App Defaults", self)
        # adding save to the file menu
        prefsMenu.addAction(savaCurrentPreferences)
        # adding action to the save
        savaCurrentPreferences.triggered.connect(self.savaCurrentPreferencesCall)


        # creating save action
        openSettings = QtWidgets.QAction("Settings..", self)
        # adding save to the file menu
        prefsMenu.addAction(openSettings)
        # adding action to the save
        openSettings.triggered.connect(self.openSettingsCall)




        self.engineMenu = self.mainMenu.addMenu("Engine")
        for engine in get_model_list(code=True, text=True) :
            engineAction = QtWidgets.QAction(engine, self)
            engineAction.setCheckable(True)
            if engine == self.engine:
                engineAction.setChecked(True)
            self.engineMenu.addAction(engineAction)
            engineAction.triggered.connect(self.setCurrentEngineCall)



        
        self.windowMenu = self.mainMenu.addMenu("Window")

        """
        self.showChatWindowAction = QtWidgets.QAction(CHAT, self)
        #self.showChatWindowAction.setShortcut("F1")
        self.showChatWindowAction.setCheckable(True)
        self.showChatWindowAction.setChecked(CHAT_WINDOW)
        self.windowMenu.addAction(self.showChatWindowAction)
        self.showChatWindowAction.triggered.connect(self.parseWindowVisiblitiesCall)
        """


        self.showModelEditorAction = QtWidgets.QAction(GPT_EDITOR, self)
        self.showModelEditorAction.setShortcut("F2")
        self.showModelEditorAction.setCheckable(True)
        self.showModelEditorAction.setChecked(GPT_EDITOR_WINDOW)
        self.windowMenu.addAction(self.showModelEditorAction)
        self.showModelEditorAction.triggered.connect(self.parseWindowVisiblitiesCall)
        


        self.showImageEditorAvtion = QtWidgets.QAction(IMAGE_EDITOR, self)
        self.showImageEditorAvtion.setShortcut("F3")
        self.showImageEditorAvtion.setCheckable(True)
        self.showImageEditorAvtion.setChecked(IMAGE_EDITOR_WINDOW)
        self.windowMenu.addAction(self.showImageEditorAvtion)
        self.showImageEditorAvtion.triggered.connect(self.parseWindowVisiblitiesCall)
        

        self.inspectCurrentModel = QtWidgets.QAction("Inspect Current Model..", self)
        self.inspectCurrentModel.setShortcut("F4")
        self.windowMenu.addAction(self.inspectCurrentModel)
        self.inspectCurrentModel.triggered.connect(self.showCurrentModelParameters)
        

        automateMenu = self.mainMenu.addMenu("Automate")

        instagram_commenter_action = QtWidgets.QAction("Launch Instagram Commenter", self)
        instagram_commenter_action.triggered.connect(self.launchInstagramCommenterWindow)
        automateMenu.addAction(instagram_commenter_action)



        aboutMenu = self.mainMenu.addMenu("About")


        statistics_page_action = QtWidgets.QAction("Launch Usage Statistics Page", self)
        statistics_page_action.triggered.connect(launch_usage_statistics_page)
        aboutMenu.addAction(statistics_page_action)


        playground_page_action = QtWidgets.QAction("Launch OpenAi Web Playground", self)
        playground_page_action.triggered.connect(launch_playground_page)
        aboutMenu.addAction(playground_page_action)

        aboutMenu.addSeparator()

        author_page_action = QtWidgets.QAction("Contact Alican Sesli (asesli@gmail.com) for support", self)
        author_page_action.setDisabled(True)
        aboutMenu.addAction(author_page_action)

        fauxking_page_action = QtWidgets.QAction("www.FauxKing.ca", self)
        fauxking_page_action.triggered.connect(launch_fauxking_page)
        aboutMenu.addAction(fauxking_page_action)

        ###################################################################################################

        output_layout = QtWidgets.QVBoxLayout()
        #results_layout = QtWidgets.QHBoxLayout()
        editor_layout = QtWidgets.QHBoxLayout()
        input_layout = QtWidgets.QHBoxLayout()
        input_layout.setContentsMargins(0,0,0,5)
        input_layout.setSpacing(2)
        #left_options_layout = QtWidgets.QVBoxLayout()
        #left_options_layout.setContentsMargins(0,0,0,0)
        #input_layout.addLayout(left_options_layout)

        self.microphone_button = QtWidgets.QPushButton()
        self.microphone_button.setFixedWidth(20)
        self.microphone_button.setFixedHeight(75) 
        self.microphone_button.setIcon(QtGui.QIcon('icons/mic-active.png'))
        self.microphone_button.setToolTip('Talk into the microphone to record your prompt.')


        #self.user_input_widget = QtWidgets.QTextEdit()
        self.user_input_widget = ResizingTextEdit()
        self.user_input_widget.setPlaceholderText("Enter your prompt")
        self.user_input_widget.setFocusPolicy(QtCore.Qt.StrongFocus)
        #self.user_input_widget.setFocus()
        #self.user_input_widget.setSizeHint(QtCore.)
        #self.user_input_widget.setMinimumHeight(75)


        self.generate_button = ResonseRequesetButton()
        self.generate_button.setFixedHeight(75)
        

        input_layout.setAlignment(QtCore.Qt.AlignTop)
        output_layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setAlignment(QtCore.Qt.AlignTop)

        input_layout.addWidget(self.microphone_button)
        input_layout.addWidget(self.user_input_widget)
        input_layout.addWidget(self.generate_button)

        input_layout_widget = QtWidgets.QWidget()
        input_layout_widget.setLayout(input_layout)
        #input_layout_widget.setFixedHeight(80)

        #output_layout.addWidget(input_layout_widget)
        input_layout.setAlignment(QtCore.Qt.AlignTop)
        output_layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.table = ResultsTable()
        #output_layout.addWidget(self.table)



        self.input_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.input_splitter.setHandleWidth(1)
        self.input_splitter.setStyleSheet("QSplitter::handle {background-color: #666;}")
        output_layout.addWidget(self.input_splitter)

        self.input_splitter.addWidget(input_layout_widget)
        self.input_splitter.addWidget(self.table)

        self.input_splitter.setCollapsible(0,False)
        #print(self.input_splitter.sizes())
        self.input_splitter.setSizes([80,1024])
        #self.input_splitter.mo


        #output_layout.addWidget(input_layout_widget)
        #output_layout.addWidget(self.table)


        self.model_editor = model_editor.ModelEditor()
        #self.model_editor.menuBar().setHidden(True)
        self.model_editor.setStandalone(False)
        self.model_editor.setMinimumWidth(512)

        self.image_editor = main_painter.Window()
        self.image_editor.setFixedWidth(1024)
        self.image_editor.setFixedHeight(1024)


        self.chat_window = QtWidgets.QWidget()
        self.chat_window.setLayout(output_layout)
        self.chat_window.setMinimumWidth(512)

        
        #self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        #self.splitter.setHandleWidth(1)
        #self.splitter.setStyleSheet("QSplitter::handle {background-color: #666;}")
        #layout.addWidget(self.splitter)


        #self.splitter.addWidget(self.chat_window)




        #editor_layout.addWidget(self.image_editor)
        #editor_layout.addWidget(self.model_editor)
        #editor_layout_widget = QtWidgets.QWidget()
        #editor_layout_widget.setLayout(editor_layout)
        #self.splitter.addWidget(editor_layout_widget)
        self.instagramCommenter = None


        layout.addWidget(self.chat_window)
        layout.addWidget(self.image_editor)
        layout.addWidget(self.model_editor)


        self.chat_window.setVisible(CHAT_WINDOW)
        self.model_editor.setVisible(GPT_EDITOR_WINDOW)
        self.image_editor.setVisible(IMAGE_EDITOR_WINDOW)


        self.setLayout(layout)

        self.loadModel(DEFAULT_MODEL)


        self.user_input_widget.setFocus()

        
        self.generate_button.requestResponseClicked[dict].connect(self.generateResponseCall)
        self.generate_button.requestImageClicked[dict].connect(self.generateImageCall)
        self.generate_button.modelChanged[str].connect(self.updateModelFromChoiceCall)

        self.user_input_widget.returnPressed.connect(self.generateResponseFromReturnPressedCall)
        self.user_input_widget.ctrlReturnPressed.connect(self.generateImageFromReturnPressedCall)

        self.microphone_button.clicked.connect(self.startMicrophoneThread)
        self.table.imageClicked[str].connect(self.updateImageFromUrl)
        self.table.variationRequested[str].connect(self.generateImageVariations)
        self.table.networkPushRequested[list].connect(self.pushResposeToNetwork)
        self.table.promptSaveRequested[list].connect(self.saveResponseToNetwork)
        self.table.sendToPromptRequested[str].connect(self.appendInput)

        self.image_editor.variationRequested.connect(self.generateEditedImageVariations)
        self.image_editor.editRequested.connect(self.generateImageEdit)
        #self.model_preset_choice_widget.currentTextChanged.connect(self.updateModelFromChoice)

        self.model_editor.modelReloadRequested[str].connect(self.updateModelFromEditorCall)

        #self.splitter.setSizes([1,0])
    
    def launchInstagramCommenterWindow(self):
        self.instagramCommenter = main_capture.Window()
        self.instagramCommenter.show()

    def showCurrentModelParameters(self):
        dlg = ModelViewerWindow(self.model)
        if dlg.exec_():
            return
        return


    def invalidApiKeyCall(self):
        QtWidgets.QMessageBox.about(self, "Invalid API Key!", "API Key is not valid. Set your API Key.")

        return self.setApiKeyCall()

    def setApiKeyCall(self):

        dlg = APIKeyWindow()
        if dlg.exec_():
            #value = dlg.getValue()
            #print ("")
            return QtWidgets.QMessageBox.about(self, "API Key Updated!", "API Key updated.\n\nRestart application.")
        return
    
    def generateResponseFromReturnPressedCall(self):
        self.generate_button.requestResponseClickedEmitter()
        return

    def generateImageFromReturnPressedCall(self):
        self.generate_button.requestImageClickedEmitter()
        return


    def parseWindowVisiblitiesCall(self):
        """ parses the visibilites, chat can always be open, 
            but  the model editor and the image editor cant be active at the same time,
            this is due to not having enough window space, also provides a cleaner layout. 

            this is only to be called from the menu actions.
            
            """

        sender = self.sender()

        if sender.text() == CHAT:
            self.chat_window.setVisible(sender.isChecked())
            

        elif sender.text() == GPT_EDITOR:
            self.model_editor.setVisible(sender.isChecked())
            if sender.isChecked():
                self.image_editor.setVisible(not sender.isChecked())
                self.showImageEditorAvtion.setChecked(False)
            

        elif sender.text() == IMAGE_EDITOR:
            self.image_editor.setVisible(sender.isChecked())
            if sender.isChecked():
                self.model_editor.setVisible(not sender.isChecked())
                self.showModelEditorAction.setChecked(False)
            

        '''
        if not self.showModelEditorAction.isChecked() and not self.showImageEditorAvtion.isChecked():
            self.splitter.setSizes([1,0])

        else:
            self.splitter.setSizes([1,1])

        '''

        self.updateGeometry()
        self.adjustSize()


        return

    def setEngine(self,engine):
        """ sets the engine var, also updates the menus"""
        self.engine = engine

        print('Engine updated:',self.engine)

        for i in self.engineMenu.actions():
            if i.isCheckable():
                if i.text() == self.engine:
                    i.setChecked(True)
                else:
                    i.setChecked(False)

    #def updateModelFromPath(self, model_path):

    def loadModel(self, model_name):
        model_path = models.get_model_path(model_name)
        self.generate_button.setModel(model_name)
        self.updateModelFromChoiceCall(model_path)

    def updateModelFromEditorCall(self, model_name):
        """ only updates the model if the current model is same as the model_path."""
        if self.model.name == model_name:
            model_path = models.get_model_path(model_name)
            self.updateModelFromChoiceCall(model_path)

    def updateModelFromChoiceCall(self, model_path):
        #print ('-->',model_path)


        response_type = GPT3
        if model_path:
            self.model.load(model_path)
            #print(model_name)
            self.setEngine(self.model.engine)
            icon = os.path.join(model_path, 'icon.png')

            if os.path.isfile(icon):
                self.setWindowIcon(QtGui.QIcon(icon))
                self.setWindowTitle(self.model.name)
            else:
                self.setWindowIcon(QtGui.QIcon(APP_ICON))
                self.setWindowTitle(APP_NAME)
        else:
            self.model.default()
            self.setEngine(self.model.engine)
            self.setWindowIcon(QtGui.QIcon(APP_ICON))
            self.setWindowTitle(APP_NAME)

        print('Model updated:',model_path)
        return

    #Main functions

    def generateResponseCall(self, data_dict):
        # This gets called from the Preset Button
        user_input    = data_dict.get('prompt', self.user_input_widget.toPlainText())
        if user_input.strip() == '':
            return

        # add user response to the chat box
        from_user_dict = {'sent_from':FROM_USER, 'prompt':user_input}
        self.table.addResult(from_user_dict)

        #always get the model from the app since it has overrides for taht.
        thread = ResponseThread(self, user_input, self.model, self.engine)#, GPT3)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()

        self.setDocumentModified(True)
        self.user_input_widget.setText('')
        self.user_input_widget.setFocus()

    def generateImageCall(self, data_dict):
        # This gets called from the Image Button
        user_input    = data_dict.get('prompt', self.user_input_widget.toPlainText())
        if user_input.strip() == '':
            return
        number        = data_dict.get('number', DEFAULT_IMAGE_RESULTS)
        resolution    = data_dict.get('resolution', DEFAULT_IMAGE_RESULTS)
        ####self.table.addResult(user_input,response_type=GPT3,sent_from=FROM_USER)
        from_user_dict = {'sent_from':FROM_USER, 'prompt':user_input}
        self.table.addResult(from_user_dict)



        thread = ImageThread(self, user_input, resolution, number)#, DALLE)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()

        self.user_input_widget.setFocus()
        self.setDocumentModified(True)

    def generateImageVariations(self,image_file):
        #response_type = DALLE
        image = image_file
        if not os.path.isfile(image):
            image = os.path.join(os.path.dirname(os.path.abspath(__file__)),image_file)
        #print (image)
        #return
        size = str( self.generate_button.getResolution())
        num = int(self.generate_button.getNumber())

        from_user_dict = {'images':[image],'sent_from':FROM_USER, 'prompt':'', 'engine':DALLE}
        self.table.addResult(from_user_dict)

        thread = ImageVariationThread(self, image, size, num)#, DALLE)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()

        #self.table.addResult(retrieved_image_urls,response_type=response_type)#,prompt=user_input)  
        self.setDocumentModified(True)      

    def generateImageEdit(self):

        user_input    = self.user_input_widget.toPlainText()
        if user_input.strip() == '':
            return

        size = str( self.generate_button.getResolution())
        num = int(self.generate_button.getNumber())
        rgb_byte_array      = self.image_editor.getByteArray()
        alpha_byte_array    = self.image_editor.getAlphaByteArray()

        ####self.table.addResult(user_input,response_type=GPT3,sent_from=FROM_USER)
        from_user_dict = {'sent_from':FROM_USER, 'prompt':user_input}
        self.table.addResult(from_user_dict)

        thread = ImageEditThread(self, user_input, rgb_byte_array, alpha_byte_array, size, num)#, DALLE)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()

        ######retrieved_image_urls = get_response_image_edit(user_input,rgb_byte_array,alpha_byte_array,size=size,n=num)
        #print('Image Edit', retrieved_image_urls)
        
        #self.table.addResult(retrieved_image_urls,response_type=response_type)#,prompt=user_input)  
        self.setDocumentModified(True)  

    def generateEditedImageVariations(self):

        size = str( self.generate_button.getResolution())
        num = int(self.generate_button.getNumber())
        byte_array = self.image_editor.getByteArray()
        image=byte_array#will be 1 so 

        thread = ImageVariationThread(self, image, size, num)#, DALLE)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()
   
        self.setDocumentModified(True)


    def startMicrophoneThread(self):

        thread = MicrophoneThread(self)
        thread.audioReceived[dict].connect(self.setPromptFromAudio)
        thread.start()
        self.microphone_button.setDisabled(True)
        self.user_input_widget.setDisabled(True)
        self.generate_button.setDisabled(True)

    def setPromptFromAudio(self, audio_data):

        response = audio_data.get('response')
        success  = audio_data.get('success')
        return_code = audio_data.get('return_code')
        response_type = audio_data.get('response_type') # this is so we can track which button called for the microphone. If image buttons microphoneis triggered, then it will submit for that engine/model type.
        self.microphone_button.setDisabled(False)
        self.user_input_widget.setDisabled(False)
        self.generate_button.setDisabled(False)

        if return_code == audio_receiver.SUCCESS:
           

            if not response_type:#prompt
                if RESPONSE_FROM_MICROPHONE:
                    self.user_input_widget.setText(response)
                    self.generateOutput(GPT3)
                else:
                    if self.user_input_widget.toPlainText():
                        self.user_input_widget.setText(self.user_input_widget.toPlainText()+' '+response)
                    else:
                        self.user_input_widget.setText(response)
            else:
                self.user_input_widget.setText(response)
                self.generateOutput(response_type,keepPropmpt=True)
                #self.user_input_widget.setText(response)

            return

        elif return_code == audio_receiver.UNSURE:
            return

        else:
            return QtWidgets.QMessageBox.about(self, "Warning!", response)


    def setCurrentEngineCall(self):
        engine_name = self.sender().text()
        if engine_name == '':
            engine_name = None
        self.setEngine(engine_name)
        #print(engine_name)

    def setCurrentModelCall(self):
        """This function sets the current model to the model that was clicked on in the model list."""
        model_name = self.sender().text()
        response_type = GPT3
        if model_name:
            model_path = models.get_model_path(model_name)
            if model_path:
                self.model.load(model_path)
                engine = self.model.engine
                if response_type in [CODEX,GPT3]:
                    if response_type == CODEX:
                        self.code_model_choice_widget.setCurrentText(engine)
                    else:
                        self.text_model_choice_widget.setCurrentText(engine)
            icon = os.path.join(model_path, 'icon.png')
            if os.path.isfile(icon):
                self.setWindowIcon(QtGui.QIcon(icon))
            else:
                self.setWindowIcon(QtGui.QIcon(APP_ICON))

        return

    #all model threads feed back to this method, and it then gets added to the chatbox table
    def processReceivedResponse(self, response_dict):
        if VERBOSE:
            print ('Received:',response_dict)

        #user_input = response_dict.get('prompt')
        #response_type = response_dict.get('response_type')
        #response = response_dict.get('response')

        #if response_type in [GPT3,CODEX]:
        self.table.addResult(response_dict)#,response_type=response_type,prompt=user_input)

        #elif response_type == DALLE:

        #self.table.addResult(response_dict,response_type=response_type,prompt=user_input)
        #######self.updateImageFromUrl(response[0])

        #else:
        #    return

        self.setDocumentModified(True)
        return

    # appends the prompt/response to the internal model
    def saveResponseToNetwork(self, prompt_and_response):
        # Appends the promt and the response to the prompt.txt file.

        prompt   = prompt_and_response[0]
        response = prompt_and_response[1]

        #pstr = prompt_and_response[0]+prompt_and_response[1]
        #self.model.appendPrompt(pstr)
        self.model.appendPrompt(prompt, response)
        if VERBOSE:
            print('Saved Model Prompts')

    # appends the prompt/response to the internal model
    def pushResposeToNetwork(self, prompt_and_response):
        # Appends the promt and the response to the current active model.


        #print(prompt_and_response)
        #['hey how are you?', "\nMarv: I'm doing great, thanks for asking. Now, can we please talk about something else? eeeeeeyyyy!"]

        # This part needs to use the Insert Start Text and Insert Restart Text parameters of the model prior to feeding it back into the network.
        #"You: " is added here fo the Marv/Marv-ey example.
        #pstr = 'You: '+prompt_and_response[0]+prompt_and_response[1]
        
        prompt   = prompt_and_response[0]
        response = prompt_and_response[1]
        self.model.updatePrompt(prompt, response)
        if VERBOSE:
            print('Updated Model Prompts')
            print (self.model.prompt)
        '''
        if SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE:

            # THIS IS BAD> YOU NEED A mode.appendPrompt function. imagine 10 people are working, they start at 9AM, they finish at 10. the person that saved last will have saved the last version of the model. 
            # so it wont actually gather everyones prompts, and the entire network will just learn from a single persons commands at a time. which is very very terrible and not the intended purpose.
            #self.model.save(options=False,prompt=True)

            self.model.appendPrompt(pstr)

            if VERBOSE:
                print('Saved Model Prompts')
        '''
   
    def updateModelFromChoice(self):
        #if not model_name:
        model_name = self.model_preset_choice_widget.currentText()
        response_type = self.user_input_choice_widget.currentText()
        if model_name:
            model_path = models.get_model_path(model_name)
            if model_path:
                self.model.load(model_path)
                #print(model_name)
                engine = self.model.engine
                if response_type in [CODEX,GPT3]:
                    if response_type == CODEX:
                        self.code_model_choice_widget.setCurrentText(engine)
                    else:
                        self.text_model_choice_widget.setCurrentText(engine)

    def openSettingsCall(self):
        return

    def savaCurrentPreferencesCall(self):
        return

    def setModelsDirectoryCall(self):
        global MODELS_DIR
        dialog = QtWidgets.QFileDialog(self, 'Choose a folder to read the Models from', MODELS_DIR)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setSidebarUrls([QtCore.QUrl.fromLocalFile(MODELS_DIR)])

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            path = dialog.selectedFiles()[0]
            if os.path.isdir(path):
                if not path.endswith('\\'):
                    path = path+'\\'
                MODELS_DIR = path
        print('Models Directory set to ',MODELS_DIR)
        return

    def setDownloadsDirectoryCall(self):
        global DOWNLOADS_DIR

        dialog = QtWidgets.QFileDialog(self, 'Choose a folder to save the Generated Images', DOWNLOADS_DIR)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setSidebarUrls([QtCore.QUrl.fromLocalFile(DOWNLOADS_DIR)])

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            path = dialog.selectedFiles()[0]
            if os.path.isdir(path):
                if not path.endswith('\\'):
                    path = path+'\\'
                DOWNLOADS_DIR = path
        print('Downloads Directory set to ',DOWNLOADS_DIR)
        return

    def updateWindowTitle(self):

        title = APP_NAME

        filename = self.currentFile
        if not filename:
            filename = 'untitled'

        title = title + ' - ' + filename

        if self.documentModified:
            title = title+' *'

        self.setWindowTitle(title)
    
    def autoSaveNetworkPromptCall(self):
        global SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE
        SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE = self.sender().isChecked()
        if VERBOSE:
            print ('Save model prompt after each response:',SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE)
        return

    def autoFeedNetworkCall(self):
        global AUTO_FEED_NETWORK
        AUTO_FEED_NETWORK = self.sender().isChecked()
        if VERBOSE:
            print ('Update loaded model with each response:',AUTO_FEED_NETWORK)
        return

    def autoSaveImagesCall(self):
        global AUTO_DOWNLOAD_IMAGE_RESULTS
        AUTO_DOWNLOAD_IMAGE_RESULTS = self.sender().isChecked()
        if VERBOSE:
            print ('Donwload images after generating them:',AUTO_DOWNLOAD_IMAGE_RESULTS)
        return
    
    # Document

    def saveCall(self):

        if not self.currentFile:
            self.saveAsCall()

        else:
            data = self.getData()
            save_yaml(data,self.currentFile)
            self.setDocumentModified(False)
        return

    def saveAsCall(self):
        data = self.getData()

        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Document", "",
                          "YAML(*.yaml);;All Files(*.*) ")
 
        if filePath == "":
            return

        save_yaml(data,filePath)

        self.currentFile = filePath
        self.setDocumentModified(False)

        return

    def getData(self):
        document_data = self.getDocumentData()
        response_data = self.getResponseData()
        data = document_data+response_data
        return data

    def getResponseData(self):
        return self.table.getData()

    def getDocumentData(self):

        doc_data = {}
        doc_data['auto_feed_network'] = AUTO_FEED_NETWORK
        doc_data['auto_save_network'] = SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE
        doc_data['auto_download_images'] = AUTO_DOWNLOAD_IMAGE_RESULTS
        doc_data['current_model']     = self.model.name
        doc_data['image_resolution']  = self.generate_button.getResolution()
        doc_data['image_number']      = self.generate_button.getNumber()

        return [doc_data]


    def importCall(self):

        self.openCall(is_import=True)

    def openCall(self,is_import=False,filePath=None):
        if is_import:
            title = "Import Document"
        else:
            title = "Open Document"
        if filePath is None:
            filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, title, "",
                              "YAML(*.yaml);;PNG(*.png);;All Files(*.*) ")
     
        if filePath == "":
            return
        #print(filePath)
        if isImageFile(filePath):
            file_data = [{
                            'response' : [filePath],
                            'response_type' : DALLE,
                            'sent_from' : FROM_USER,
                            'prompt' : 'image'
                        }]
        else:
            file_data = read_yaml(filePath)

        if file_data:
            if not is_import:
                self.clearCall()


            document_data = file_data[0]
            response_data = file_data[1:]

            self.table.buildFromData(response_data)
            if is_import:
                self.setDocumentModified(True)
            else:
                self.currentFile = filePath
                self.setDocumentModified(False)

        return

    def loadDocument(self, doc_path):
        """ loads a file taht was saved from this app """

        return



    
    def revertCall(self):
        if not self.currentFile:
            return
        self.openCall(filePath=self.currentFile)

    def clearCall(self):
        self.table.deleteAll()
        self.image_editor.clear()

        self.currentFile = None
        self.setDocumentModified(False)


    def appendInput(self, text_to_append):
        if self.user_input_widget.toPlainText():
            self.user_input_widget.setText(self.user_input_widget.toPlainText()+' '+text_to_append)
        else:
            self.user_input_widget.setText(text_to_append)

    def updateImageFromUrl(self,url):
        #url="https://oaidalleapiprodscus.blob.core.windows.net/private/org-GLLh6119suKdY6uEweJO1Oqd/user-3SDg1N3IXZh7jBMOnBMdq2u0/img-CzD7qmX6Pl5pde61kWfIjrtD.png?st=2022-12-24T16%3A40%3A23Z&se=2022-12-24T18%3A40%3A23Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png&skoid=6aaadede-4fb3-4698-a8f6-684d7786b067&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2022-12-24T16%3A39%3A12Z&ske=2022-12-25T16%3A39%3A12Z&sks=b&skv=2021-08-06&sig=bvZpsqOyL00KrMbFhcBnWe0sli7W2A8g/j8i1Nr9y0g%3D"

        self.image_editor.setFromUrl(url)

    def setDocumentModified(self,isModified):
        self.documentModified = isModified
        self.updateWindowTitle()


def getOptions():
    usage  = "Usage: %prog [MODEL NAME]"
    epilog = "For bugs contac: Alican Sesli (asesli@gmail.com)"
    parser = OptionParser(usage=usage)

    parser.add_option('-o','--open', dest='open', default='', action='store')

    parser.add_option('-c', '--continueLast', dest='continueLast', default=False, action='store_true')

    parser.add_option('-m','--modelName', dest='modelName', default='', action='store')#,help=optparse.SUPPRESS_HELP)
    
    parser.add_option('-p','--modelPath', dest='modelName', default='', action='store')

    parser.add_option('-s','--simple', dest='simple', default=False, action='store_true')

    parser.add_option('-v','--verbose', dest='verbose', default=False, action='store_true')

    parser.add_option('-e','--editor', dest='editor', default=False, action='store_true')

    (options, args) = parser.parse_args()
    return options, args



def main():

    global DEFAULT_MODEL
    global CHAT_MODE
    global CONTINUE_FROM_LAST
    global VERBOSE

    options, args = getOptions()

    DEFAULT_MODEL      = options.modelName
    CHAT_MODE          = options.simple
    CONTINUE_FROM_LAST = options.continueLast
    VERBOSE            = options.verbose


    App = QtWidgets.QApplication(sys.argv)

    if options.editor:
        window = model_editor.ModelEditor()
        window.show()
    else:

        window = Window()

        window.show()

        if not functions.check_if_credentials_exist():
            window.setApiKeyCall()

        elif not functions.check_if_credentials_are_valid():
            window.invalidApiKeyCall()


    sys.exit(App.exec())



if __name__ == "__main__":
    main()
