# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 10:41:12 2018

@author: Okada
"""

import ecsub.ansi

def _message (title, no, messages):
        
    text = "[%s]" % (title)
    if no != None:     
        text = ecsub.ansi.colors.paint("[%s:%03d]" % (title, no), ecsub.ansi.colors.roll_list[no % len(ecsub.ansi.colors.roll_list)])

    for m in messages:
        if "color" in m.keys():
            text += ecsub.ansi.colors.paint(m["text"], m["color"])
        else:
            text += m["text"]

    return text

def warning_message (title, no, text):
    return _message (title, no, [{"text": " [WARNING] %s" % (text), "color": ecsub.ansi.colors.WARNING}])

def error_message (title, no, text):
    return _message (title, no, [{"text": " [ERROR] %s" % (text), "color": ecsub.ansi.colors.FAIL}])

def info_message (title, no, text):
    return _message (title, no, [{"text": " %s" % (text)}])
    
    
def main():
    pass

if __name__ == "__main__":
    main()

