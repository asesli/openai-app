
import os,sys
import time
import math
import yaml
from PyQt5 import QtCore, QtWidgets, QtGui
import urllib
import urllib.request
from AppGlobals import *
from FileManagement import *
import json
import numpy as np
import OpenAIConnector as functions
import Models


APP_NAME = "openai-app gpt3-codex editor"

# tooltips

FREQUENCY_PENALTY_TOOLTIP = "How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood to repeat the same line verbatim."
PRESENCE_PRNALTY_TOOLTIP  = "How much to penalize new tokens based on whether they appear in the text so far. Increases the model's likelihood to talk about new topics."
TOP_P_TOOLTIP = "Controls diversity via nucleus sampling: 0.5 means half of all likelihood-weighted options are considered."
MAXIMUM_LENGTH_TOOLTIP = "The maximum number of tokens to generate. Requests can use up to 2,048 or 4,000 tokens shared between prompt and completion. The exact limit varies by model. (One token is roughly 4 characters for normal English text)"
TEMPERATURE_TOOLTIP = "Controls randomness: Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive."
INJECT_START_TEXT_TOOLTIP = "Text to append after the user's input to format the model for a response.\nGETS INSERTED AFTER USER INPUT, BUT BEFORE THE TEXT GENERATION"
INJECT_RESTART_TEXT_TOOLTIP = "Text to append after the model's generation to continue the patterned structure.\nGETS INSERTED BEFORE USER INPUT"
MODEL_ENGINE_TOOLTIP = "Choose one of the engines provided by GPT3 / CODEX to be used in your model."
MODEL_PRESET_TOOLTIP = "Choose an existing model."
TRAINED_PROMPT_TOOLTIP = "Everything in this text editor will be calculated for future responses, the results can be altered to force the network to respond in a specific way. All undesired question/response pairs should be removed or modified to the desired results."
REQUEST_PROMPT_TOOLTIP = "Generate a response to the text entered into this field."
GENERATE_RESPONSE_TOOLTIP = "Generate a response to the user prompt. The user prompt and the generated response will both be appended to the Trained Prompts to be used for future responses."
PASTE_VALUES_TOOLTIP = "Copy/Paste values to be used externally, or use it to import it to current model."
SAVE_PROMPTS_TOOLTIP = "Saves the Trained Prompts. Does not save the options above."
SAVE_OPTIONS_TOOLTIP = "Saves the Options defined above to the model. Does not save the Trained Prompts."
SAVE_AS_NEW_TOOLTIP = "Save a new model from the current Options and Trained Prompts"
STOP_SEQUENCES_TOOLTIP = "Up to four sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence."
BEST_OF_TOOLTIP = "Generates multiple completions server-side, and displays only the best. Streaming only works when set to 1. Since it acts as a multiplier on the number of completions, this parameters can eat into your token quota very quickly – use caution!"
REVERT_TOOLTIP = "Reverts the model settings to last saved."
# connectors

def get_model_list(code=True, text=True):
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



# GPT / CODEX Response Thread - more indepth, we can pass model settings to this.
class ResponseThread(QtCore.QThread):
    responseReceived = QtCore.pyqtSignal(dict)
    def __init__(self,parent,user_prompt, model, engine=None):#,response_type):
        super(ResponseThread,self).__init__(parent)
        self.parent        = parent
        self.user_prompt   = user_prompt
        self.active        = True
        self.model         = model

        self.engine        = engine or self.model.engine # engine override
        #self.response_type = response_type

    def stop(self):
        self.wait()

    def request_call(self):
        response = self.model.getResponse(self.user_prompt, engine=self.engine)

        self.responseReceived.emit( response )

        return

    def run(self):
        self.request_call()
        return


# ui elements

class LineNumberArea(QtWidgets.QWidget):


    def __init__(self, editor):
        super().__init__(editor)
        self.myeditor = editor


    def sizeHint(self):
        return QtCore.Qsize(self.editor.lineNumberAreaWidth(), 0)


    def paintEvent(self, event):
        self.myeditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QtWidgets.QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)

        #self.connect(self, SIGNAL('blockCountChanged(int)'), self.updateLineNumberAreaWidth)
        #self.connect(self, SIGNAL('updateRequest(QRect,int)'), self.updateLineNumberArea)
        #self.connect(self, SIGNAL('cursorPositionChanged()'), self.highlightCurrentLine)

        self.blockCountChanged[int].connect(self.updateLineNumberAreaWidth)
        self.updateRequest[QtCore.QRect,int].connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)


    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space


    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)


    def updateLineNumberArea(self, rect, dy):

        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(),
                       rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


    def resizeEvent(self, event):
        super().resizeEvent(event)

        cr = self.contentsRect();
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                    self.lineNumberAreaWidth(), cr.height()))


    def lineNumberAreaPaintEvent(self, event):
        mypainter = QtGui.QPainter(self.lineNumberArea)

        mypainter.fillRect(event.rect(), QtCore.Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure I use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                mypainter.setPen(QtCore.Qt.black)
                mypainter.drawText(0, int(top), int(self.lineNumberArea.width()), int(height),
                 QtCore.Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1


    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()

            lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class Slider(QtWidgets.QWidget):

    edited = QtCore.pyqtSignal(float) 

    def __init__(self, label='', minimum=0, maximum=10, default=0):
        super(Slider, self).__init__()

        self.label = label
        #self.multiplier = 1
        self.minimum = minimum*100
        self.maximum = maximum*100
        self.default = default*100

        self._int = False

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        temperature_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(temperature_layout)
        self.label_widget = QtWidgets.QLabel(label)
        self.number_widget = QtWidgets.QLabel()
        self.number_widget.setAlignment(QtCore.Qt.AlignRight)
        temperature_layout.addWidget(self.label_widget)
        temperature_layout.addWidget(self.number_widget)
        self.slider_widget = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_widget.setMinimum(self.minimum)
        self.slider_widget.setMaximum(self.maximum)
        #self.slider_widget.setTickPosition(QtWidgets.QSlider.TicksBelow)
        #self.slider_widget.valueChanged.connect(lambda: self.number_widget.setText( str(self.slider_widget.value()/100) ))
        self.slider_widget.valueChanged.connect(self.updateStrValue)
        self.slider_widget.valueChanged.connect(self.emitEdited)
        #self.slider_widget.setTickInterval(32)
        self.number_widget.setText(str(self.slider_widget.value()))
        layout.addWidget(self.slider_widget)
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.setLayout(layout)
        self.updateStrValue()

    def updateStrValue(self):
        if self._int:
            self.number_widget.setText( str(int(self.slider_widget.value()/100)) )
        else:
            self.number_widget.setText( str(self.slider_widget.value()/100) )

    def setInt(self, value_is_integer):
        self._int = value_is_integer

    def setFloat(self, value_is_float):
        self._int = not value_is_float


    def setValue(self, value):
        value = float(float(value)*100)
        self.slider_widget.setValue(int(value))
        #print( self.label, int(value))
        #print(self.slider_widget.value())

    def setLabel(self,label):
        self.label = label
        self.label_widget.setText(self.label)

    def setRanges(self,minimum,maximum):
        self.minimum = minimum*100
        self.maximum = maximum*100
        self.slider_widget.setMinimum(self.minimum)
        self.slider_widget.setMaximum(self.maximum)

    def value(self):
        if self._int:
            return int(self.slider_widget.value()/100)
        else:
            return self.slider_widget.value()/100

    def emitEdited(self):

        self.edited.emit( self.value() )

class ResizingTextEdit(QtWidgets.QTextEdit):
    returnPressed = QtCore.pyqtSignal(bool)
    ctrlReturnPressed = QtCore.pyqtSignal(bool)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.computeHint)
        self._sizeHint = super().sizeHint()
        #self.installEventFilter(self)

    def computeHint(self):
        hint = super().sizeHint()
        height = self.document().size().height()
        height += (self.frameWidth() * 2) 
        height = max(height, 23)
        self._sizeHint.setHeight(max(int(height+10), int(hint.height())+10))

        self.setFixedHeight(int(height))  # good if you want to insert this into a layout
        #self.resize(hint.width(), int(height))  # good if you want to insert this into a layout
        #self.setMinimumHeight(20)
        self.setMaximumHeight(200)
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

class ResizingTextEditUserPrompt(QtWidgets.QTextEdit):
    returnPressed = QtCore.pyqtSignal(bool)
    ctrlReturnPressed = QtCore.pyqtSignal(bool)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.computeHint)
        self._sizeHint = super().sizeHint()
        #self.installEventFilter(self)

    def computeHint(self):
        hint = super().sizeHint()
        height = self.document().size().height()
        height += (self.frameWidth() * 2) 
        height = max(height, 23)
        self._sizeHint.setHeight(max(int(height+10), int(hint.height())+10))

        self.setFixedHeight(int(height))  # good if you want to insert this into a layout
        #self.resize(hint.width(), int(height))  # good if you want to insert this into a layout
        #self.setMinimumHeight(20)
        self.setMaximumHeight(200)
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

class CheckBoxText(QtWidgets.QWidget):

    edited = QtCore.pyqtSignal(float) 

    def __init__(self, label='', isChecked=False, text=''):
        super(CheckBoxText, self).__init__()

        self.label = label

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        bottom_layout = QtWidgets.QHBoxLayout()
        
        self.label_widget = QtWidgets.QLabel(self.label)
       
        layout.addWidget(self.label_widget)

        layout.addLayout(bottom_layout)

        self.checkbox = QtWidgets.QCheckBox()
        #self.lineedit = QtWidgets.QLineEdit()
        self.lineedit = QtWidgets.QTextEdit()
        self.lineedit.setFixedHeight(46)
        #self.lineedit = ResizingTextEdit()

        bottom_layout.addWidget(self.checkbox)
        bottom_layout.addWidget(self.lineedit)


        layout.setAlignment(QtCore.Qt.AlignTop)

        self.setLayout(layout)

    def setText(self,text):
        #self.lineedit.setText(text)
        self.lineedit.setPlainText(text)

    def text(self):
        #return str(self.lineedit.text())
        return str(self.lineedit.toPlainText())

class PastePresetsWindow(QtWidgets.QDialog):
    def __init__(self):
        #super().__init__()
        super(PastePresetsWindow, self).__init__()
        self.setWindowTitle("Copy / Paste script")

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

class Delegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        #option.text = option.text.replace('\n', '::')
        option.text = f"{index.row() + 1}. {option.text}"

class ModelEditor(QtWidgets.QMainWindow):
    #emits a name of the current model when model files are altered
    modelReloadRequested = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()
 
        # setting title
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(APP_ICON))



        # creating menu bar
        mainMenu = self.menuBar()
 
        # creating file menu for save and clear action
        fileMenu = mainMenu.addMenu("Model")
 
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

        fileMenu.addSeparator()

        saveOptionsAction = QtWidgets.QAction("Save Options Only", self)
        fileMenu.addAction(saveOptionsAction)
        saveOptionsAction.triggered.connect(self.saveModelOptions)


        savePromptsAction = QtWidgets.QAction("Save Prompts Only", self)
        fileMenu.addAction(savePromptsAction)
        savePromptsAction.triggered.connect(self.saveModelPrompts)

        fileMenu.addSeparator()
        # creating open action
        openAction = QtWidgets.QAction("Open", self)
        # adding short cut for save action
        openAction.setShortcut("Ctrl+O")
        # adding save to the file menu
        fileMenu.addAction(openAction)
        # adding action to the save
        openAction.triggered.connect(self.openCall)

        # creating open action
        importAction = QtWidgets.QAction("Copy/Paste", self)
        # adding short cut for save action
        #importAction.setShortcut("Ctrl+I")
        # adding save to the file menu
        fileMenu.addAction(importAction)
        # adding action to the save
        importAction.triggered.connect(self.importCall)


        # creating revert action
        revertAction = QtWidgets.QAction("Reload", self)
        # adding short cut to the clear action
        #revertAction.setShortcut("Ctrl + C")
        # adding clear to the file menu
        fileMenu.addAction(revertAction)
        # adding action to the clear
        revertAction.triggered.connect(self.revertCall)



        # about menut
        aboutMenu = mainMenu.addMenu("About")
        aboutMenu.addAction(QtWidgets.QAction("Contact Alican Sesli (asesli@gmail.com) for support", self))
        aboutMenu.addAction(QtWidgets.QAction("Powered by OpenAi", self))
        aboutMenu.addAction(QtWidgets.QAction("Usage Statistics Page", self))


        # model init
        self.model = Models.Model()



        self.main_layout = QtWidgets.QHBoxLayout()
        #self.main_layout.setContentsMargins(0,0,0,0)

        prompt_layout = QtWidgets.QVBoxLayout()
        prompt_layout.setContentsMargins(0,0,0,0)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout_widget=QtWidgets.QWidget()
        layout_widget.setLayout(layout)

        saved_model_label = QtWidgets.QLabel('Preset Model')
        saved_model_label.setToolTip(MODEL_PRESET_TOOLTIP)
        layout.addWidget(saved_model_label)
        self.saved_model_choice = QtWidgets.QComboBox()
        saved_models = self.getSavedModelsList()
        self.saved_model_choice.addItems(saved_models)
        self.saved_model_choice.setToolTip(MODEL_PRESET_TOOLTIP)
        layout.addWidget(self.saved_model_choice)

        model_engine_label = QtWidgets.QLabel('Model Engine')
        model_engine_label.setToolTip(MODEL_ENGINE_TOOLTIP)
        layout.addWidget(model_engine_label)
        self.model_engine_choice = QtWidgets.QComboBox()
        code = get_model_list(code=True, text=False)
        text = get_model_list(code=False, text=True)
        modes = text+code
        self.model_engine_choice.addItems(modes)
        self.model_engine_choice.setToolTip(MODEL_ENGINE_TOOLTIP)
        self.model_engine_choice.currentTextChanged.connect(self.updateModelEngine)
        layout.addWidget(self.model_engine_choice)

        self.temperature_widget = Slider('Temperature', 0,1,0.5)
        self.temperature_widget.edited.connect(self.updateModelTemperature)
        self.temperature_widget.setToolTip(TEMPERATURE_TOOLTIP)
        layout.addWidget(self.temperature_widget)

        self.maximum_length_widget = Slider('Maximum length', 0,4000,60)
        self.maximum_length_widget.setInt(True)
        self.maximum_length_widget.edited.connect(self.updateModelMaximumLength)
        self.maximum_length_widget.setToolTip(MAXIMUM_LENGTH_TOOLTIP)
        layout.addWidget(self.maximum_length_widget)

        self.top_p_widget = Slider('Top p', 0,1,0)
        self.top_p_widget.edited.connect(self.updateModelTopP)
        self.top_p_widget.setToolTip(TOP_P_TOOLTIP)
        layout.addWidget(self.top_p_widget)

        self.frequency_penalty_widget = Slider('Frequency penalty', 0,2,0)
        self.frequency_penalty_widget.edited.connect(self.updateModelFrequencyPenalty)
        self.frequency_penalty_widget.setToolTip(FREQUENCY_PENALTY_TOOLTIP)
        layout.addWidget(self.frequency_penalty_widget)

        self.presence_penalty_widget = Slider('Presence penalty', 0,2,0)
        self.presence_penalty_widget.edited.connect(self.updateModelPresencePenalty)
        self.presence_penalty_widget.setToolTip(PRESENCE_PRNALTY_TOOLTIP)
        layout.addWidget(self.presence_penalty_widget)


        self.inject_start_text = CheckBoxText('Inject start text')
        self.inject_start_text.lineedit.textChanged.connect(self.updateModelInjectStartText)
        self.inject_start_text.setToolTip(INJECT_START_TEXT_TOOLTIP)
        layout.addWidget(self.inject_start_text)

        self.inject_restart_text = CheckBoxText('Inject restart text')
        self.inject_restart_text.lineedit.textChanged.connect(self.updateModelInjectRetartText)
        self.inject_restart_text.setToolTip(INJECT_RESTART_TEXT_TOOLTIP)
        layout.addWidget(self.inject_restart_text)

        stop_label = QtWidgets.QLabel('Stop Sequences')
        stop_label.setToolTip(STOP_SEQUENCES_TOOLTIP)
        layout.addWidget(stop_label)
        self.stop_widget = QtWidgets.QListWidget()
        self.stop_widget.setToolTip(STOP_SEQUENCES_TOOLTIP)
        self.stop_widget.addItems(['','','',''])
        self.stop_widget.setFixedHeight(72)
        #self.stop_widget.currentTextChanged.connect(self.updateModelStopSequence)
        self.stop_widget.itemChanged.connect(self.updateModelStopSequence)
        delegate = Delegate(self.stop_widget)
        self.stop_widget.setItemDelegate(delegate)

        for index in range(self.stop_widget.count()):
            item = self.stop_widget.item(index)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        layout.addWidget(self.stop_widget)

        self.best_of_widget = Slider('Best of', 1,12,1)
        self.best_of_widget.setInt(True)
        self.best_of_widget.edited.connect(self.updateBestOf)
        self.best_of_widget.setToolTip(BEST_OF_TOOLTIP)
        layout.addWidget(self.best_of_widget)


        layout.addStretch()

        save_options_button = QtWidgets.QPushButton('Save Current Options')
        save_options_button.setToolTip(SAVE_OPTIONS_TOOLTIP)
        layout.addWidget(save_options_button)

        save_prompts_button = QtWidgets.QPushButton('Save Prompts')
        save_prompts_button.setToolTip(SAVE_PROMPTS_TOOLTIP)
        layout.addWidget(save_prompts_button)


        save_new_button = QtWidgets.QPushButton('Save as New Model')
        save_new_button.setToolTip(SAVE_AS_NEW_TOOLTIP)
        layout.addWidget(save_new_button)


        revert_button = QtWidgets.QPushButton('Reload Model')
        revert_button.setToolTip(REVERT_TOOLTIP)
        layout.addWidget(revert_button)



        paste_Values_button = QtWidgets.QPushButton('Copy/Paste Values')
        paste_Values_button.setToolTip(PASTE_VALUES_TOOLTIP)
        layout.addWidget(paste_Values_button)


        generate_button = QtWidgets.QPushButton('Generate Response')
        generate_button.setToolTip(GENERATE_RESPONSE_TOOLTIP)
        generate_button.setFixedHeight(75)
        layout.addWidget(generate_button)

        layout.setAlignment(QtCore.Qt.AlignTop)


        prompt_label = QtWidgets.QLabel('Trained Prompt')
        prompt_label.setToolTip(TRAINED_PROMPT_TOOLTIP)
        prompt_layout.addWidget(prompt_label)

        #self.prompt_widget = QtWidgets.QTextEdit()
        self.prompt_widget = CodeEditor()
        self.prompt_widget.setMinimumWidth(450)
        self.prompt_widget.setToolTip(TRAINED_PROMPT_TOOLTIP)
        self.prompt_widget.textChanged.connect(self.updateModelPrompt)
        prompt_layout.addWidget(self.prompt_widget)


        user_prompt_label = QtWidgets.QLabel('User Prompt')
        user_prompt_label.setToolTip(REQUEST_PROMPT_TOOLTIP)
        prompt_layout.addWidget(user_prompt_label)
        self.user_prompt = QtWidgets.QTextEdit()
        #self.user_prompt = ResizingTextEditUserPrompt()
        self.user_prompt.setFixedHeight(75)
        self.user_prompt.setToolTip(REQUEST_PROMPT_TOOLTIP)
        prompt_layout.addWidget(self.user_prompt)


        layout_widget.setFixedWidth(200)

        self.main_layout.addWidget(layout_widget)
        self.main_layout.addLayout(prompt_layout)

        #self.setLayout(self.main_layout)
        #self.main_layout.setParent(self)

        layout_widget = QtWidgets.QWidget()
        layout_widget.setLayout(self.main_layout)
        self.setCentralWidget(layout_widget)

        self.saved_model_choice.currentTextChanged[str].connect(self.loadModelPreset)
        save_options_button.clicked.connect(self.saveModelOptions)
        save_prompts_button.clicked.connect(self.saveModelPrompts)
        generate_button.clicked.connect(self.startRequestResponseThread)
        save_new_button.clicked.connect(self.saveAsCall)
        paste_Values_button.clicked.connect(self.pasteValuesCall)
        revert_button.clicked.connect(self.revertCall)

        self.loadModelPreset(None)
        self.resize(800,800)

    def setStandalone(self, isStandAlone):

        if not isStandAlone:
            self.menuBar().setHidden(True)
            self.showShortcutButtons()
        else:
            self.menuBar().setHidden(False)
            self.hideShortcutButtons()


    def showShortcutButtons(self):

        return

    def hideShortcutButtons(self):

        return


    def saveCall(self):
        current_path = self.model.model_path
        if not current_path:
            self.saveAsCall()
            return
        else:
            self.saveModel(current_path)
        return
    
    def saveAsCall(self):
        dialog = QtWidgets.QFileDialog(self, 'Choose a folder to save into', )
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setSidebarUrls([QtCore.QUrl.fromLocalFile(MODELS_DIR)])

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            path = dialog.selectedFiles()[0]
            full_path = path
            self.saveModel(full_path)
        return

    def saveModel(self, model_path):
        self.model.save(model_path)
        QtWidgets.QMessageBox.about(self, "Model Saved!", model_path)
        name = os.path.basename(os.path.abspath(model_path))
        saved_models = self.getSavedModelsList()
        self.saved_model_choice.clear()
        self.saved_model_choice.addItems(saved_models)
        self.saved_model_choice.setCurrentText(name)

    def openCall(self):
        dialog = QtWidgets.QFileDialog(self, 'Choose the model folder you would like to load.', )
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        dialog.setSidebarUrls([QtCore.QUrl.fromLocalFile(MODELS_DIR)])

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            path = dialog.selectedFiles()[0]
            full_path = path
            self.loadModel(full_path)
        return
    
    def importCall(self):
        self.pasteValuesCall()
        return
    
    def revertCall(self):
        #current_path = self.model.model_path
        current_name = self.model.name
        self.loadModelPreset(current_name)

        return
    
    def setButtonsVisible(self,isVisible):
        """hides/shows the buttons"""
        return


    def toJson(self):
        """ returns this model as a json """

        """
        {
          "model": "text-davinci-003",
          "prompt": "Correct this to standard English:\n\nShe no went to the market.",
          "temperature": 0,
          "max_tokens": 60,
          "top_p": 1,
          "frequency_penalty": 0,
          "presence_penalty": 0
        }
        """
        #self.getName()


        out_dict = {
                        'prompt' : self.getPrompt(),
                        'model' : self.getEngine(),
                        'temperature' : self.getTemperature(),
                        'max_tokens' : self.getMaximumLength(),
                        'top_p' : self.getTopP(),
                        'frequency_penalty' : self.getFrequencyPenalty(),
                        'presence_penalty' : self.getPresencePenalty()
                    }

        best_of = self.getBestOf()
        if best_of > 1:
            out_dict['best_of'] = best_of
        stop_sequence = self.getStopSequence()
        if stop_sequence:
             out_dict['stop'] = stop_sequence

        json_object = json.dumps(out_dict, indent = 4)

        return json_object

    def fromJson(self, value):
        """ sets the model parameters from json data """

        json_object = json.loads(value)

        if not json_object:
            print("Nothing to parse.")
            return

        self.setPrompt( json_object.get('prompt') )
        self.setEngine( json_object.get('model') )
        self.setTemperature( json_object.get('temperature') )
        self.setMaximumLength( json_object.get('max_tokens') )
        self.setTopP( json_object.get('top_p') )
        self.setFrequencyPenalty( json_object.get('frequency_penalty') )
        self.setPresencePenalty( json_object.get('presence_penalty') )
        stop = json_object.get('stop')
        if stop:
            self.setStopSequence(stop)
        else:
            self.setStopSequence([])
        best_of = json_object.get('best_of')
        if best_of:
            self.setBestOf(best_of)
        else:
            self.setBestOf(1)



        return


    def pasteValuesCall(self):
        """ opens a window where the user can paste existing values from a json format, or copy the values in json format"""
        dlg = PastePresetsWindow()
        dlg.setValue(self.toJson())
        if dlg.exec_():
            value = dlg.getValue()
            self.fromJson(value)
        return

    def getSavedModelsList(self):
        return ['']+Models.get_saved_model_list()


    def requestResponse(self):
        """ generates a response for the user prompt using the model settings """

        #user text
        user_text = self.user_prompt.toPlainText()

        #existing prompts
        trained_prompts = self.prompt_widget.toPlainText()
        self.model.setPrompt(trained_prompts)

        #print (self.model.prompt)
        #retrieved response
        new_response = self.model.getResponse(user_text)

        # combine user text and the response, and push it back into the network 
        # so the future responses can use the newly generated response
        new_prompt = "You: {}{}".format(user_text, new_response)
        if not new_response.endswith('\n'):
            new_prompt+='\n'

        # we dont need to update prompt since we are reading from the trained prompt widget priot to each request
        # by design, all responses wll be fed back into the network, the user will delete it if they dont like the question/response
        #self.model.updatePrompt(new_prompt)


        #add the user text and the response to the widget
        if not trained_prompts.endswith('\n'):
            trained_prompts+='\n'
        trained_prompts = '{}{}'.format(trained_prompts,new_prompt)

        self.setPrompt( trained_prompts )

        self.clearUserInput()


    def startRequestResponseThread(self):

        #user text
        user_text = self.user_prompt.toPlainText()

        #existing prompts 
        trained_prompts = self.prompt_widget.toPlainText()
        self.model.setPrompt(trained_prompts)


        #engine = self.getEngine()
        thread = ResponseThread(self, user_text, self.model)
        thread.responseReceived[dict].connect(self.processReceivedResponse)
        thread.start()


        #decorate the user input with inject start/restart texts
        decorated_prompt = self.model.decoratePrompt(user_text)

        #take the current prompts, and add the decorated prompts
        trained_prompts = '{}{}'.format(self.model.prompt,decorated_prompt)
        self.setPrompt( trained_prompts )
        self.clearUserInput()

        return

    def processReceivedResponse(self,data_dict):
        print (data_dict)
        if "choices" in data_dict:
            response = data_dict["choices"][0]["text"]
        else:
            response = COULD_NOT_FETCH_MESSAGE

        #trained_prompts = self.prompt_widget.toPlainText()
        trained_prompts = self.model.prompt
        new_prompt = '{}{}'.format(trained_prompts,response)

        self.setPrompt( new_prompt )
        return

    def scrollToBottom(self):
        self.prompt_widget.verticalScrollBar().setValue(self.prompt_widget.verticalScrollBar().maximum())

    def clearUserInput(self):
        self.user_prompt.setPlainText('')

    # get knob values

    def getTemperature(self):
        return self.temperature_widget.value()

    def getBestOf(self):
        return self.best_of_widget.value()

    def getMaximumLength(self):
        return self.maximum_length_widget.value()

    def getTopP(self):
        return self.top_p_widget.value()

    def getStopSequence(self):
        stops = []
        for index in range(self.stop_widget.count()):
            item = self.stop_widget.item(index)
            if item.text():
                if item.text() != '':
                    stops.append(item.text())
        if not len(stops):
            stops = None
        return stops

    def getFrequencyPenalty(self):
        return self.frequency_penalty_widget.value()

    def getPresencePenalty(self):
        return self.presence_penalty_widget.value()

    def getEngine(self):
        return self.model_engine_choice.currentText()

    def getName(self):
        return self.saved_model_choice.currentText()

    def getPrompt(self):
        return self.prompt_widget.toPlainText()

    def getInjectStartText(self):
        return self.inject_start_text.text()

    def getInjectRestartText(self):
        return self.inject_restart_text.text()

    # set knob values

    def setTemperature(self, value):
        return self.temperature_widget.setValue(value)

    def setMaximumLength(self, value):
        return self.maximum_length_widget.setValue(value)

    def setBestOf(self, value):
        return self.best_of_widget.setValue(value)

    def setTopP(self, value):
        return self.top_p_widget.setValue(value)

    def setStopSequence(self,values):


        v = ['','','','']
        if values is None:
            values = v
        else:
            values = values+v
            values = values[:4]

        self.stop_widget.clear()
        self.stop_widget.addItems(values)
        for index in range(self.stop_widget.count()):
            item = self.stop_widget.item(index)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

        return

    def setFrequencyPenalty(self, value):
        return self.frequency_penalty_widget.setValue(value)

    def setPresencePenalty(self, value):
        return self.presence_penalty_widget.setValue(value)

    def setEngine(self, value):
        return self.model_engine_choice.setCurrentText(value)

    def setPrompt(self, value):
        self.prompt_widget.setPlainText(value)
        self.scrollToBottom()
        return 

    def setInjectStartText(self, value):
        return self.inject_start_text.setText(value)

    def setInjectRestartText(self, value):
        return self.inject_restart_text.setText(value)

    #def setName(self, value):
    #    return self.saved_model_choice.setCurrentText(value)

    # knob callbacks to update the model

    def updateBestOf(self):
        self.model.best_of = self.getBestOf()

    def updateModelTemperature(self):
        self.model.temperature = self.getTemperature()

    def updateModelMaximumLength(self):
        self.model.max_tokens = self.getMaximumLength()

    def updateModelTopP(self):
        self.model.top_p = self.getTopP()

    def updateModelFrequencyPenalty(self):
        self.model.frequency_penalty = self.getFrequencyPenalty()

    def updateModelPresencePenalty(self):
        self.model.presence_penalty  = self.getPresencePenalty()

    def updateModelEngine(self):
        self.model.engine  = self.getEngine()

    def updateModelPrompt(self):
        self.model.prompt = self.getPrompt()

    def updateModelInjectStartText(self):
        text = self.getInjectStartText()
        if text is None:
            self.model.inject_start_text = ''
        else:
            self.model.inject_start_text = text

    def updateModelInjectRetartText(self):
        text = self.getInjectRestartText()
        if text is None:
            self.model.inject_restart_text = ''
        else:
            self.model.inject_restart_text = text

    def updateModelStopSequence(self):
        stops = []
        for index in range(self.stop_widget.count()):
            item = self.stop_widget.item(index)
            if item.text():
                if item.text() != '':
                    stops.append(item.text())
        if not len(stops):
            stops = None

        self.model.stop = stops

    #def updateModelName(self, value):
    #    self.saved_model_choice.setCurrentText(value)

    def updateModel(self):
        """ updates the entire model from the knob values"""

        self.model.prompt               = self.getPrompt()
        self.model.engine               = self.getEngine()
        self.model.max_tokens           = self.getMaximumLength()
        self.model.temperature          = self.getTemperature()
        self.model.best_of              = self.getBestOf()
        self.model.top_p                = self.getTopP()
        self.model.stop                 = self.getStopSequence()
        self.model.frequency_penalty    = self.getFrequencyPenalty()
        self.model.presence_penalty     = self.getPresencePenalty()
        self.model.inject_start_text    = self.getInjectStartText()
        self.model.inject_restart_text  = self.getInjectRestartText()

    def loadModelPreset(self,model_name):
        """ executed first time when ui loads, and everytime the user selects one of the saved models """
        if model_name:
            model_path = Models.get_model_path(model_name)

            self.model.load(model_path)
        else:
            self.model.default()

        self.updateKnobsFromCurrentModel()

        return

    def updateKnobsFromCurrentModel(self):

        self.setPrompt(str(self.model.prompt))

        self.setEngine(self.model.engine)

        self.setMaximumLength(self.model.max_tokens)

        self.setTemperature(self.model.temperature)

        self.setBestOf(self.model.best_of)

        self.setTopP(self.model.top_p)

        self.setStopSequence(self.model.stop)

        self.setFrequencyPenalty(self.model.frequency_penalty)

        self.setPresencePenalty(self.model.presence_penalty)

        self.setInjectStartText(self.model.inject_start_text)

        self.setInjectRestartText(self.model.inject_restart_text)


    def loadModel(self, model_path):

        self.model.load(model_path)

        self.updateKnobsFromCurrentModel()

    def saveModelOptions(self):
        if self.model.model_path:
            self.model.save(options=True,prompt=False)
            self.modelReloadRequested.emit(self.model.name)
            QtWidgets.QMessageBox.about(self, "Saved Model Options", "Saved Model Options for {}".format(self.model.name))
        else:
            ask = QtWidgets.QMessageBox.question(self, "Model not found", "No model loaded. Would you like to save a new model using the current settings?")
            if ask:
                self.saveAsCall()
        return

        return

    def saveModelPrompts(self):
        if self.model.model_path:
            self.model.save(options=False,prompt=True)
            self.modelReloadRequested.emit(self.model.name)
            QtWidgets.QMessageBox.about(self, "Saved Model Prompts", "Saved Model Prompts for {}".format(self.model.name))
        else:
            ask = QtWidgets.QMessageBox.question(self, "Model not found", "No model loaded. Would you like to save a new model using the current settings?")
            if ask:
                self.saveAsCall()
        return



def main():
    # create pyqt5 app
    App = QtWidgets.QApplication(sys.argv)
     
    # create the instance of our Window
    window = ModelEditor()
     
    # showing the window
    window.show()
     
    # start the app
    sys.exit(App.exec())



if __name__ == "__main__":
    main()
