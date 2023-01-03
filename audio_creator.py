import pyttsx3

def speak(text):
    try:
        engine = pyttsx3.init()

        engine.say(text)

        engine.runAndWait()
    except:
        pass

