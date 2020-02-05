# -*- coding: utf-8 -*-
"""
Created on Tue Apr 03 16:02:38 2018

@author: Okada
"""

import os
import re
import boto3
import datetime
import ecsub.tools

TITLE = "ecsub-logs"
def _timestamp(text):
   return datetime.datetime.fromtimestamp(int(text)/1000).strftime("%Y%m%d_%H%M%S")

def _to_cluster_name(log_group_name):
    cluster_name = re.sub(r'^ecsub-', "", log_group_name)
    print (ecsub.tools.info_message(TITLE, None, "cluser-name: %s" % (cluster_name)))
    return cluster_name
    
def _describe_log_groups(logGroupNamePrefix, nextToken, limit):

    for i in range(3):
        try:
            if nextToken == None:
                mesg = ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').describe_log_groups(logGroupNamePrefix = '%s', limit = %d)" % (
                        logGroupNamePrefix, limit
                    )
                )
                print (mesg)
            
                groups = boto3.client('logs').describe_log_groups(
                    limit = limit, 
                    logGroupNamePrefix = logGroupNamePrefix
                )
                print (ecsub.tools.info_message(TITLE, None, "log-groups: %d" % (len(groups["logGroups"]))))
                
            else:
                groups = boto3.client('logs').describe_log_groups(
                    limit = limit, 
                    logGroupNamePrefix = logGroupNamePrefix,
                    nextToken = nextToken
                )
            
            return groups
        
        except Exception:
            pass
    return None

def _describe_log_streams(logGroupName, logStreamNamePrefix, nextToken, limit):
    
    for i in range(3):
        try:
            if nextToken == None:
                mesg = ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').describe_log_streams(logGroupName = '%s', logStreamNamePrefix = '%s', limit = %d)" % (
                        logGroupName, logStreamNamePrefix, limit
                    )
                )
                print (mesg)
                
                streams = boto3.client('logs').describe_log_streams(
                    logGroupName = logGroupName,
                    logStreamNamePrefix = logStreamNamePrefix,
                    limit = limit
                )
                print (ecsub.tools.info_message(TITLE, None, "log-streams: %d" % (len(streams["logStreams"]))))
                
            else:
                streams = boto3.client('logs').describe_log_streams(
                    logGroupName = logGroupName,
                    logStreamNamePrefix = logStreamNamePrefix,
                    limit = limit,
                    nextToken = nextToken
                )
            
            return streams
        
        except Exception:
            pass
    return None

def _get_log_events(logGroupName, logStreamName, nextToken):
    
    for i in range(3):
        try:
            if nextToken == None:
                mesg = ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').get_log_events(logGroupName = '%s', logStreamName = '%s', startFromHead = True)" % (
                        logGroupName, logStreamName
                    )
                )
                print (mesg)
                
                events = boto3.client('logs').get_log_events(
                    logGroupName = logGroupName,
                    logStreamName = logStreamName,
                    startFromHead = True
                )
                print (ecsub.tools.info_message(TITLE, None, "log-events: %d" % (len(events["events"]))))
                
            else:
                events = boto3.client('logs').get_log_events(
                    logGroupName = logGroupName,
                    logStreamName = logStreamName,
                    startFromHead = True,
                    nextToken = nextToken
                )
        
            return events
        
        except Exception:
            pass
    return None

def _get_log_events_tail(logGroupName, logStreamName):

    for i in range(3):
        try:
            mesg = ecsub.tools.info_message(TITLE, None, 
                "boto3.client('logs').get_log_events(logGroupName = '%s', logStreamName = '%s', startFromHead = True)" % (
                    logGroupName, logStreamName
                )
            )
            print (mesg)
            
            events = boto3.client('logs').get_log_events(
                logGroupName = logGroupName,
                logStreamName = logStreamName,
                startFromHead = False
            )
            print (ecsub.tools.info_message(TITLE, None, "log-events: %d" % (len(events["events"]))))
        
            return events
        except Exception:
            pass
    return None

# specify Log stream
def _download_log_stream(log_group_name, stream, wdir, cluster_name, tail = False):

    output_dir = "%s/%s/cloud_watch" % (wdir.rstrip("/"), cluster_name)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception:
            pass
            
    f = open("%s/%s-%s.log" % (
        output_dir,
        stream["logStreamName"].split("/")[1],
        _timestamp(stream["creationTime"])), "w")
    
    if tail:
        events = _get_log_events_tail(log_group_name, stream["logStreamName"])
        if events  != None:
            for event in events["events"]:
                f.write("%s\t%s\n" % (_timestamp(event["timestamp"]), event["message"].encode('utf-8')))
    else:
        events = None
        while(1):
            if events != None and len(events["events"]) == 0:
                break
    
            if events == None:
                events = _get_log_events(log_group_name, stream["logStreamName"], None)
            else:
                events = _get_log_events(log_group_name, stream["logStreamName"], events["nextForwardToken"])
            
            if events  != None:
                for event in events["events"]:
                    f.write("%s\t%s\n" % (_timestamp(event["timestamp"]), event["message"].encode('utf-8')))
        
    f.close()

def download_logs(wdir, log_group_prefix, log_stream_prefix, tail):
    
    group = None
    while(1):
        if group != None and not "nextToken" in group.keys():
            break

        if group == None:
            group = _describe_log_groups(log_group_prefix, None, 1)
        else:
            group = _describe_log_groups(log_group_prefix, group["nextToken"], 1)
        
        if group == None:
            break
        if len(group["logGroups"]) == 0:
            break
        
        cluster_name = _to_cluster_name(group["logGroups"][0]["logGroupName"])
        stream = None
        while(1):
            if stream != None and not "nextToken" in stream.keys():
                break

            if stream == None:
                stream = _describe_log_streams(group["logGroups"][0]["logGroupName"], log_stream_prefix, None, 1)
            else:
                stream = _describe_log_streams(group["logGroups"][0]["logGroupName"], log_stream_prefix, stream["nextToken"], 1)
            
            if stream == None:
                break
            if len(stream["logStreams"]) == 0:
                break
            
            _download_log_stream(group["logGroups"][0]["logGroupName"], stream["logStreams"][0], wdir, cluster_name, tail)

def remove_log_groups(log_group_prefix):
    
    while(1):
        groups = _describe_log_groups(log_group_prefix, None, 50)
        if groups == None:
            break
        if len(groups["logGroups"]) == 0:
            break
        
        for group in groups["logGroups"]:
            for i in range(3):
                try:
                    mesg = ecsub.tools.info_message(TITLE, None, 
                        "boto3.client('logs').delete_log_group(logGroupName = '%s')" % (
                            group["logGroupName"]
                        )
                    )
                    print (mesg)
                    boto3.client('logs').delete_log_group(
                        logGroupName = group["logGroupName"]
                    )
                    break
                except Exception:
                    pass
                
def remove_log_streams(log_group_name, log_stream_prefix):
    
    groups = _describe_log_groups(log_group_name, None, 50)
    if groups == None:
        return
        
    find = False
    for group in groups["logGroups"]:
        if group["logGroupName"] == log_group_name:
            find = True
            break
    if not find:
        print ("not find log-group-name: %s" % (log_group_name))
        return
    
    while(1):
        streams = _describe_log_streams(log_group_name, log_stream_prefix, None, 50)
        if streams == None:
            break
        
        if len(streams["logStreams"]) == 0:
            mesg = ecsub.tools.info_message(TITLE, None, 
                "boto3.client('logs').delete_log_group(logGroupName = '%s')" % (
                    group["logGroupName"]
                )
            )
            print (mesg)
            break

        for stream in streams["logStreams"]:
            for i in range(3):
                try:
                    mesg = ecsub.tools.info_message(TITLE, None, 
                        "boto3.client('logs').delete_log_stream(logGroupName = '%s', logStreamName = '%s')" % (
                            log_group_name, stream["logStreamName"]
                        )
                    )
                    print (mesg)
            
                    boto3.client('logs').delete_log_stream(
                        logGroupName = log_group_name,
                        logStreamName = stream["logStreamName"]
                    )
                    break
                except Exception:
                    pass
            
def main(params):
    
    if params["mode"] == "download":
        log_group = "ecsub-"
        if params["log_group_prefix"] != "":
            log_group = params["log_group_prefix"]
        elif params["log_group_name"] != "":
            log_group = params["log_group_name"]
            
        if params["log_stream_prefix"] == "":
            params["log_stream_prefix"] = "ecsub/"
        
        print (ecsub.tools.info_message(TITLE, None, "=== download log files start ==="))
        download_logs(params["wdir"], log_group, params["log_stream_prefix"], params["tail"])
        print (ecsub.tools.info_message(TITLE, None, "=== download log files end ==="))
    
    if params["mode"] == "remove-log-group":
        if params["log_group_prefix"] == "":
            print ("set log-group-prefix")
            return
        
        print (ecsub.tools.info_message(TITLE, None, "=== remove log groups start ==="))
        remove_log_groups(params["log_group_prefix"])
        print (ecsub.tools.info_message(TITLE, None, "=== remove log groups end ==="))
    
    elif params["mode"] == "remove-log-stream":
        if params["log_group_name"] == "":
            print ("set log-group-name")
            return
    
        if params["log_stream_prefix"] == "":
            print ("set log-stream-prefix")
            return
        
        print (ecsub.tools.info_message(TITLE, None, "=== remove log streams start ==="))
        remove_log_streams(params["log_group_name"], params["log_stream_prefix"])
        print (ecsub.tools.info_message(TITLE, None, "=== remove log streams end ==="))
    
def entry_point(args):
    params = {
        "wdir": args.wdir,
        "log_group_prefix": args.log_group_prefix,
        "log_group_name": args.log_group_name,
        "log_stream_prefix": args.log_stream_prefix,
        "mode": args.mode,
        "tail": args.tail,
    }
    main(params)
    
if __name__ == "__main__":
    pass
