import time
import json


def wait(sec, debug=False):
    for i in range(0, sec):
        if debug:
            print("= ", end='')
        time.sleep(1)
    if debug:
        print("")


def load_json_attributes():
    with open('attributes.json') as json_file:
        attributes = json.load(json_file)
    return attributes
