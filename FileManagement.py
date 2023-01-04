import os,sys
import yaml
from datetime import datetime
from AppGlobals import CREDENTIALS_FILE

def getTimeStamp():
    curr_dt = datetime.now()
    timestamp = int(round(curr_dt.timestamp()))
    return timestamp

def save_yaml(data,filePath):
    with open(filePath, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)
    return

def read_yaml(filePath):
    with open(filePath, "r") as stream:
        try:
            data = yaml.safe_load(stream)
            return data
            #print()
        except yaml.YAMLError as exc:
            print(exc)
    return []

def read_text(filePath):
    with open(filePath, "r") as stream:
        ret_str=stream.read()
        return ret_str
    return ''

def save_text(text,filePath,mode='w'):
    with open(filePath, mode) as outfile:
        #yaml.dump(data, outfile, default_flow_style=False)
        outfile.write(text)
    return

def read_lines(filePath):
    with open(filePath, "r") as stream:
        ret_str=stream.readlines()
        return ret_str
    return []

def save_credentials(api_key):
    return save_text(api_key, CREDENTIALS_FILE)

def read_credentials():
    return read_text(CREDENTIALS_FILE)