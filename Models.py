"""
The model class provides control over the gpt3/codex models

d={"engine":"text-davinci-003","max_tokens":60,"temperature":0.5,"top_p":0.3,"frequency_penalty":0.5,"presence_penalty":0.0}
f="C:\\Sandbox\\Python\\openai\\saved_models\\marv\\model.yaml"

"""
import os,sys
from AppGlobals import *
from FileManagement import *
import OpenAIConnector as functions

#MODELS_DIR = "saved_models\\"
PROMPT = ''
ENGINE = 'text-davinci-003'
MAX_TOKENS = 1600
TEMPERATURE = 0.7
TOP_P = 1
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0
INJECT_START_TEXT = '\n'
INJECT_RESTART_TEXT = '\n'
STOP = None
BEST_OF = 1
NAME = 'Untitled'

def get_saved_model_list(path=None):
    """ gets a list of saved models"""
    if path is None:
        path = MODELS_DIR
    folders = os.listdir(path)
    folders = [i for i in folders if '.' not in i]
    return folders

def get_model_path(model_name,path=None):
    """ returns a path for the model files """
    if path is None:
        path = MODELS_DIR
    folders = os.listdir(path)
    folders = [i for i in folders if '.' not in i]
    for f in folders:
        if f == model_name:
            return os.path.join(path,model_name)
    return None

def getResponseFromModel(prompt, model):
    model_path = get_model_path(model)
    model = Model(model_path)
    response = model.getResponeString(prompt)
    return response 

def get_model_name(model_path):
    return os.path.basename(os.path.normpath((model_path)))

class Model:

    def __init__(self,model_path=None):

        self.model_path          = model_path
        self.name                = None

        self.prompt              = None
        self.engine              = None
        self.max_tokens          = None
        self.temperature         = None
        self.top_p               = None
        self.best_of             = None
        self.frequency_penalty   = None
        self.presence_penalty    = None
        self.stop                = None
        self.inject_start_text   = None
        self.inject_restart_text = None

        self.optionsFile         = None
        self.promptFile          = None

        if self.model_path:
            self.load()
        else:
            self.default()

    def default(self):
        """ sets the values to defaults so that its ready to use without loading an exisiting model """
        self.model_path = None
        self.name       = NAME

        self.prompt              = PROMPT
        self.engine              = ENGINE
        self.max_tokens          = MAX_TOKENS
        self.temperature         = TEMPERATURE
        self.top_p               = TOP_P
        self.best_of             = BEST_OF
        self.frequency_penalty   = FREQUENCY_PENALTY
        self.presence_penalty    = PRESENCE_PENALTY
        self.stop                = STOP
        self.inject_start_text   = INJECT_START_TEXT
        self.inject_restart_text = INJECT_RESTART_TEXT

        self.optionsFile         = None
        self.promptFile          = None
        return

    def load(self,model_path=None):
        """ loads model 
             prompt.txt (trained prompts) 
             options.yaml (model settings)"""

        if not model_path:
            model_path = self.model_path
        if not model_path:
            return

        self.model_path=model_path

        if os.path.isdir(self.model_path):
            self.promptFile         = os.path.join(self.model_path,'prompt.txt')
            self.optionsFile        = os.path.join(self.model_path,'options.yaml')
            options                 = read_yaml(self.optionsFile)
            self.prompt             = str(read_text(self.promptFile))
            self.name               = os.path.basename(os.path.normpath( self.model_path ))
            self.updateOptions(options)

            #print( 'Model Loaded: {}'.format(self.name) )
            pass


    def appendPrompt(self, prompt, response):
        """ appends a str to the prompts.txt file of the current model """
        if self.promptFile:
            prompt_and_response = self.combinePromptAndResponse(prompt,response)
            #if not prompt_and_response.startswith('\n'):
            #    prompt_and_response = '\n'+prompt_and_response


            save_text(prompt_and_response, self.promptFile, mode='a')
        return


    def save(self,model_path=None,options=True,prompt=True):
        """ saves model files
             model_path = directory to save into (incase saving a new model)

             prompt.txt (trained prompts) 
             options.yaml (model settings)"""

        if model_path:
            options=True
            prompt=True
            # if a model_path is passed, then create the folder if it doesnt already exist.
            #if not os.path.isdir(model_path):
            #    #create the model folder if it doesnt exist:
            #    os.


            self.model_path  = model_path
            self.name        = os.path.basename(os.path.normpath( self.model_path ))  
            self.promptFile  = os.path.join(self.model_path,'prompt.txt')
            self.optionsFile = os.path.join(self.model_path,'options.yaml')

        if self.model_path:
            if options:
                options_dict = {
                                'engine' : self.engine,
                                'max_tokens' : self.max_tokens,
                                'temperature' : self.temperature,
                                'top_p' : self.top_p,
                                'best_of': self.best_of,
                                'frequency_penalty' : self.frequency_penalty,
                                'presence_penalty' : self.presence_penalty,
                                'stop' : self.stop,
                                'inject_start_text': self.inject_start_text,
                                'inject_restart_text':self.inject_restart_text,
                                }

                save_yaml(options_dict, self.optionsFile)

            if prompt:
                save_text(self.prompt, self.promptFile)
        else:
            #print('No model loaded.')
            pass

        return

    def setPrompt(self,prompt):
        """ sets the  pretraining prompt text to generate future responses from"""
        ##if not prompt.endswith('\n'):
        ##    prompt += '\n'
        self.prompt = prompt

    def updatePromptOLD(self,prompt):
        """ add new prompts to the existing training model for the model to use when generating future responses, 
            the prompt should be the the question and the answer. 
                example prompt str: 'You: What should I do?\nMarv: Don't know. Don't care. But maybe drink some water.' """
        if not self.prompt:
            self.prompt = ''

        if not self.prompt.endswith('\n'):
            prompt = '\n'+prompt
        self.prompt += prompt

        self.prompt=str(self.prompt)
        
        #save_text(str(prompt), self.promptFile, mode='a')

    def updatePrompt(self,prompt,response):
        """ add new prompts to the existing training model for the model to use when generating future responses, 
            the prompt should be the the question and the answer. 
                example prompt str: 'You: What should I do?\nMarv: Don't know. Don't care. But maybe drink some water.' """
        prompt_and_response = self.combinePromptAndResponse(prompt,response)
        self.prompt += prompt_and_response
        self.prompt = str(self.prompt)
        #save_text(str(prompt), self.promptFile, mode='a')


    def decoratePrompt(self, prompt):
        """"Hey, whats your name?" <-- in
            "You: Hey, whats your name?" <-- out
            """
        prompt = self.injectRestartText(prompt)
        """"You: Hey, whats your name?" <-- in
           "You: Hey, whats your name?" 
           "AI: <-- out
           """                      
        prompt = self.injectStartText(prompt)



        #adds a new line if the current prompt doesnt end with one. This is to assure all entires start on a new line.
        #this need to be automated using ONLY the inject start/restart text
        ##if not self.prompt.endswith('\n') and not prompt.startswith('\n') :
        ##    prompt='\n'+prompt

        return prompt

    def combinePromptAndResponse(self,prompt,response):

        if not self.prompt:
            self.prompt = ''

        prompt = self.decoratePrompt(prompt)

        return str(prompt) + str(response)


    def updateOptions(self,options):
        """ updates the options from a given options dict """
        self.engine             = options.get('engine')
        self.max_tokens         = options.get('max_tokens')
        self.temperature        = options.get('temperature')
        self.top_p              = options.get('top_p')
        self.best_of            = options.get('best_of')
        self.frequency_penalty  = options.get('frequency_penalty')
        self.presence_penalty   = options.get('presence_penalty')
        self.stop               = options.get('stop')
        self.inject_start_text  = options.get('inject_start_text')
        self.inject_restart_text= options.get('inject_restart_text')


    def injectStartText(self,prompt):
        """ adds inject_start_text after the users input"""
        if self.inject_start_text is not None:
            return prompt + self.inject_start_text
        return prompt

    def injectRestartText(self,prompt):
        """ adds inject_start_text after the users input"""
        if self.inject_restart_text is not None:
            return self.inject_restart_text + prompt
        return prompt

    # NEW - RETURNS DICT
    def getResponse(self, new_prompt, engine=None, add_to_results=False):
        """ using the data in this class, retrieve respose from openai 

            add_to_results : adds the received response and the prompt to models prompts.  
        """


        raw_user_input = new_prompt
        if not self.prompt:
            self.prompt = ''


        new_prompt = self.decoratePrompt(new_prompt)



        prompt = self.prompt + new_prompt
        engine = engine or self.engine
        response_data = functions.get_response(prompt,engine=engine,max_tokens=self.max_tokens,temperature=self.temperature,top_p=self.top_p,frequency_penalty=self.frequency_penalty,presence_penalty=self.presence_penalty,stop=self.stop,best_of=self.best_of)
        

        response_data["model_path"] = self.model_path
        response_data["sent_from"]  = FROM_APP
        response_data["new"]        = True
        response_data["prompt"]     = raw_user_input
        response_data["engine"]     = engine


        #print('Response data:',response_data)
        #print (type(response_data))
        if response_data:
            #response_data["response"]   = response_data["choices"][0]["text"]
            # it should always add its result to the internal mode.
            #THIS PART IS BROKEN>
            if add_to_results:
                # this is BAD!
                #prompt_to_add = 'You: {}\n{}'.format(new_prompt, response)
                # this is BAD too but better than above
                response = response_data["choices"][0]["text"]
                prompt_to_add = '{}{}'.format(new_prompt, response)
                self.updatePrompt(prompt_to_add)
            #return response
        else:
            print ('\nCould not retrieve the results, try again.')
            pass


        
        return response_data


    def getResponeString(self, new_prompt):
        #returns only string.
        response = self.getResponse(new_prompt)
        if response:
            response = response["choices"][0]["text"]
            return response
        return None






'''
f = "C:\\Sandbox\\Python\\openai\\saved_models\\harinder-from-surrey"
m = Model(f)
m.load()
#print(m.prompt)
#pstr="""You: What should I do?\nMarv: Don't know. Don't care. But maybe drink some water."""
#m.updatePrompt(pstr)
#print(m.prompt)
q = "How are you?"
print(q)
print(m.getResponse(q,add_to_results=False))


print (get_saved_model_list())
'''

# Example functions.




"""


### -- Example 1 - ask harinder something:
def harinder(prompt):
    return getResponseFromModel(prompt, 'harinder-from-surrey')
print(harinder("Anything exciting tonight?"))



### -- Example 2 - use the singleton model to produce a boolean from a prompt
def singleton(prompt):
    response= getResponseFromModel(prompt, 'singletons')
    if 'True' in response:
        return True
    elif 'False' in response:
        return False
    else:
        return None

check to see if what you said was True or False
print(singleton("Sky is blue."))



### -- Example 3 - same example to be expanded to run a specific script or whatever
if singleton("Sky is blueish."):
    print ("Yes, this is correct. Executing reward.py")
else:
    print ("Nope, incorrect. Executing punish.py")


"""


#Create a model, and feed data into it so that it learns from given reponses.


