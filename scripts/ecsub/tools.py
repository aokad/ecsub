# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 10:41:12 2018

@author: Okada
"""

import ecsub.ansi
import datetime
import pytz
import dateutil

def get_title_color (no):
    return ecsub.ansi.colors.roll_list[no % len(ecsub.ansi.colors.roll_list)]
        
def message (title, no, messages):
    text = "%s " % (str(datetime.datetime.now()))
    if no != None:     
        text += ecsub.ansi.colors.paint("[%s:%03d]" % (title, no), get_title_color(no))
    else:
        text += "[%s]" % (title)
        
    for m in messages:
        if "color" in m.keys():
            text += ecsub.ansi.colors.paint(m["text"], m["color"])
        else:
            text += m["text"]

    return text

def warning_message (title, no, text):
    return message (title, no, [{"text": " [WARNING] %s" % (text), "color": ecsub.ansi.colors.WARNING}])

def error_message (title, no, text):
    return message (title, no, [{"text": " [ERROR] %s" % (text), "color": ecsub.ansi.colors.FAIL}])

def info_message (title, no, text):
    return message (title, no, [{"text": " %s" % (text)}])

def base64_encode(text):
    import six
    
    if six.PY2:
        return text.encode('base64')
    
    import base64
    return base64.b64encode(text.encode('utf-8'))

def plainformat_to_datetime(text, utc=False):
    if len(text) != 12:
        return None
    
    try:
        dt = datetime.datetime.strptime(text + "00", '%Y%m%d%H%M%S')
        if utc:
            return dt.replace(tzinfo=pytz.utc).astimezone(dateutil.tz.tzlocal())
        return dt.replace(tzinfo=dateutil.tz.tzlocal())
    except Exception:
        pass
    return None

def isoformat_to_datetime2(text):
    return datetime.datetime.strptime(text.rstrip("Z"), '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=pytz.utc).astimezone(dateutil.tz.tzlocal())

def isoformat_to_datetime(text):
    try:
        return datetime.datetime.strptime(text.rstrip("Z"), '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=pytz.utc).astimezone(dateutil.tz.tzlocal())
    except Exception:
        pass
    
    return isoformat_to_datetime2(text)

def standardformat_to_datetime(text):
    try:
        return datetime.datetime.strptime(" ".join(text.split(" ")[0:2]), "%Y/%m/%d %H:%M:%S").replace(tzinfo=dateutil.tz.tzlocal())
    except Exception:
        pass
    
    try:
        return datetime.datetime.strptime(" ".join(text.split(" ")[0:2]), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=dateutil.tz.tzlocal())
    except Exception:
        pass
    
    return isoformat_to_datetime(text)

def timestamp_to_datetime(st_mtime):
    return datetime.datetime.fromtimestamp(st_mtime).replace(tzinfo=dateutil.tz.tzlocal())

def datetime_to_isoformat(dt):
    return dt.isoformat() + "Z"
    
def datetime_to_standardformat(dt):
    return dt.strftime("%Y/%m/%d %H:%M:%S %Z")

def is_request_payer_bucket(path, payer_buckets):

    bucket = path.replace("s3://", "").split("/")[0]
    
    if payer_buckets.count(bucket) > 0:
        return True
    return False

def main():
    pass

if __name__ == "__main__":
    main()

