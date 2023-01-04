#activate openai

ACTIVE=True
VERBOSE=False

# default app settings
DOWNLOADS_DIR = "saved\\"
MODELS_DIR    = "saved_models\\"


#Default mode to load in
DEFAULT_RESULT        = "Image"

#Default Engine to use when in Code (CODEX) mode
DEFAULT_CODE_CHOICE   = "code-davinci-002"

#Default Engine to use when in Text (GPT3) mode
DEFAULT_TEXT_CHOICE   = "text-davinci-003"

#Default resolution of the generated DALLE image
DEFAULT_IMAGE_SIZE    = "1024x1024"

#How many images should DALLE create when requested
DEFAULT_IMAGE_RESULTS = 4

#When DALLE is used, the generated images live in a server somewhere, enable it to always download the generated images.
AUTO_DOWNLOAD_IMAGE_RESULTS = True

#Feeds the network with the result it generated, each response will expand the dataset
AUTO_FEED_NETWORK = False

#Saves the response to the model file after each response, this is so that when the app is closed, and relaunched, the model that was used will retain its learned dataset
SAVE_MODEL_PROMPT_AFTER_EACH_RESPONSE = False

#Submits the speech from microphone directly to the network instead of entering it into the user text prompt area.
RESPONSE_FROM_MICROPHONE = False

#Enable Text-To-Speech
TEXT_TO_SPEACH = True

#Wen the app returns a response, itll always be text-to-speech
RESPOND_BY_SPEECH = True

#CHAT WINDOW IS VISIBLE ON LAUNCH
CHAT_WINDOW = True

#IMAGE EDITOR WINDOW IS VISIBLE ON LAUNCH
IMAGE_EDITOR_WINDOW = False

#GPT EDITOR WINDOW IS VISIBLE ON LAUNCH
GPT_EDITOR_WINDOW = False

DEFAULT_MODEL = None#'harinder-from-surrey'

# enables the option
CONTINUE_FROM_LAST = False

# contunues from this file when app is launched
LAST_FILE = None

CHAT_MODE = False

# definitions

DALLE = "Image"
GPT3  = "Text"
CODEX = "Code"
FROM_USER = "user"
FROM_APP  = "app"
RESOLUTION_1024 = "1024x1024"
RESOLUTION_512  = "512x512"
RESOLUTION_256  = "256x256"

IMAGE_EDIT = 'edit'
IMAGE_VARIATION = 'variation'
IMAGE_GENERATE = 'generate'

CHAT = "Chat Window"
GPT_EDITOR = "GPT Editor"
IMAGE_EDITOR = "Image Editor"
IMAGE_SIZES = [RESOLUTION_1024,RESOLUTION_512,RESOLUTION_256]
RESULT_CHOICES = [GPT3,CODEX,DALLE]
OPENAPI_USAGE_PAGE = "https://beta.openai.com/account/usage"
OPENAPI_PLAYGROUND_PAGE = "https://beta.openai.com/playground"
FAUXKING_PAGE = "https://fauxking.ca/"
APP_ICON = 'icons\\icon32.png'
DALLE2_ICON = 'icons\\dalle2_logo.png'
DEFAULT_MODEL_ICON = 'icons\\default_model.png'
MISSING_IMAGE = 'icons\\missing_image.png'
DELETED_IMAGE = 'icons\\deleted_image.png'
CREDENTIALS_FILE = 'credentials.cfg'
MISSING_IMAGE = DELETED_IMAGE = APP_ICON
COULD_NOT_FETCH_MESSAGE = "Could not fetch results.."
#styles

APP_RESPONSE_STYLESHEET  = "background-color: lightgreen; border: 1px solid black; border-radius: 10px; padding: 10px;"
USER_PROMPT_STYLESHEET   = "background-color: lightskyblue; border: 1px solid black; border-radius: 10px; padding: 10px;"
IMAGE_PREVIEW_STYLESHEET = "background-color: none; border: none; border-radius: 1px; padding: 1px;"
APP_STYLE = "background-color: #353535;"
INTERNAL_NETWORK_CHECKBOX_STYLE = """
QCheckBox::indicator::checked
    {
        border-image : url(icons/brain-active.png)
    }
QCheckBox::indicator::unchecked
    {
        border-image : url(icons/brain-inactive.png)
    }
"""

EXTERNAL_NETWORK_CHECKBOX_STYLE = """
QCheckBox::indicator::checked
    {
        border-image : url(icons/disk-active.png)
    }
QCheckBox::indicator::unchecked
    {
        border-image : url(icons/disk-inactive.png)
    }
"""

CLOSE_CHECKBOX_STYLE = """
QCheckBox::indicator
    {
        border-image : url(icons/close.png)
    }
"""
MICROPHONE_CHECKBOX_STYLE = """
QCheckBox::indicator {
     width: 18px;
     height: 18px;
 }
QCheckBox::indicator::checked
    {
        border-image : url(icons/mic-active.png)
    }
QCheckBox::indicator::unchecked
    {
        border-image : url(icons/mic-inactive.png)
    }
QCheckBox::indicator::unchecked::hover
    {
        border-image : url(icons/mic-hover.png)
    }
QCheckBox::indicator::checked::hover
    {
        border-image : url(icons/mic-active.png)
    }
"""


