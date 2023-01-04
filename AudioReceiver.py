#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class

import speech_recognition as sr



SUCCESS = 0
UNSURE = 1
ERROR = 2

def get_audio():
    # obtain audio from the microphone
    r = sr.Recognizer()

    success  = False
    return_code = SUCCESS
    response = ''

    with sr.Microphone() as source:
        #print("Say something!")
        audio = r.listen(source, 3, 30 )

    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        response = r.recognize_google(audio)
        #print("Google Speech Recognition thinks you said " + response)
        success = True
        return_code = SUCCESS


    except sr.UnknownValueError:
        #print("Google Speech Recognition could not understand audio")
        response = "Google Speech Recognition could not understand audio"
        return_code = UNSURE

    except sr.RequestError as e:
        return_code = ERROR
        response = "Could not request results from Google Speech Recognition service; {0}".format(e)

    except sr.WaitTimeoutError as e:
        return_code = ERROR
        response = "Microphone timed out."
    except Exception as e:
        return_code = ERROR
        response = "Unknown Error"

    return {'response':response, 'success':success, 'return_code':return_code}


#print(get_audio())