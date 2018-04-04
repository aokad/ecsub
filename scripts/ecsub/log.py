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

def _describe_log_groups(logGroupNamePrefix, nextToken, limit):
    
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
        print (ecsub.tools.info_message(TITLE, None, "data-length: %d" % (len(groups["logGroups"]))))
        
    else:
        groups = boto3.client('logs').describe_log_groups(
            limit = limit, 
            logGroupNamePrefix = logGroupNamePrefix,
            nextToken = nextToken
        )
    
    return groups

def _describe_log_streams(logGroupName, nextToken, limit):
    
    if nextToken == None:
        mesg = ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').describe_log_streams(logGroupName = '%s', logStreamNamePrefix = 'ecsub', limit = %d)" % (
                logGroupName, limit
            )
        )
        print (mesg)
        
        streams = boto3.client('logs').describe_log_streams(
            logGroupName = logGroupName,
            logStreamNamePrefix = 'ecsub',
            limit = limit
        )
        print (ecsub.tools.info_message(TITLE, None, "data-length: %d" % (len(streams["logStreams"]))))
        
    else:
        streams = boto3.client('logs').describe_log_streams(
            logGroupName = logGroupName,
            logStreamNamePrefix = 'ecsub',
            limit = limit,
            nextToken = nextToken
        )
    
    return streams

def _get_log_events(logGroupName, logStreamName, nextToken):
    
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
        print (ecsub.tools.info_message(TITLE, None, "data-length: %d" % (len(events["events"]))))
        
    else:
        events = boto3.client('logs').get_log_events(
            logGroupName = logGroupName,
            logStreamName = logStreamName,
            startFromHead = True,
            nextToken = nextToken
        )

    return events

def _download_log(params):
    
    group = None
    while(1):
        if group != None and not "nextToken" in group.keys():
            break

        if group == None:
            group = _describe_log_groups(params["group_name_prefix"], None, 1)
        else:
            group = _describe_log_groups(params["group_name_prefix"], group["nextToken"], 1)
        
        if len(group["logGroups"]) == 0:
            break
        
        cluster_name = re.sub(r'^ecsub-', "", group["logGroups"][0]["logGroupName"])
        print (ecsub.tools.info_message(TITLE, None, ("cluser-name: %s" % (cluster_name))))
        
        stream = None
        while(1):
            if stream != None and not "nextToken" in stream.keys():
                break

            if stream == None:
                stream = _describe_log_streams(group["logGroups"][0]["logGroupName"], None, 1)
            else:
                stream = _describe_log_streams(group["logGroups"][0]["logGroupName"], stream["nextToken"], 1)
            
            if len(stream["logStreams"]) == 0:
                break
            
            output_dir = "%s/%s/cloud_watch" % (params["wdir"], cluster_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            f = open("%s/%s-%s.log" % (
                output_dir,
                stream["logStreams"][0]["logStreamName"].split("/")[1],
                _timestamp(stream["logStreams"][0]["creationTime"])), "w")
            
            events = None
            while(1):
                if events != None and len(events["events"]) == 0:
                    break
    
                if events == None:
                    events = _get_log_events(group["logGroups"][0]["logGroupName"], stream["logStreams"][0]["logStreamName"], None)
                else:
                    events = _get_log_events(group["logGroups"][0]["logGroupName"], stream["logStreams"][0]["logStreamName"], events["nextForwardToken"])
                    
                for event in events["events"]:
                    f.write("%s\t%s\n" % (_timestamp(event["timestamp"]), event["message"].encode('utf-8')))
            f.close()
            
def _remove_log(params):

    safe_groups = []
    while(1):
        groups = _describe_log_groups(params["group_name_prefix"], None, 50)
        
        if len(groups["logGroups"]) == 0:
            break
        
        count = 0
        for group in groups["logGroups"]:
            if group["logGroupName"] in safe_groups:
                count += 1
                continue
        if count == len(safe_groups) and len(safe_groups) > 0:
            break
        
        for group in groups["logGroups"]:
            cluster_name = re.sub(r'^ecsub-', "", group["logGroupName"])
            print (ecsub.tools.info_message(TITLE, None, "cluser-name: %s" % (cluster_name)))
            
            streams = _describe_log_streams(group["logGroupName"], None, 50)
            for stream in streams["logStreams"]:
                mesg = ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').delete_log_stream(logGroupName = '%s', logStreamName = '%s')" % (
                        group["logGroupName"], stream["logStreamName"]
                    )
                )
                print (mesg)
                
                boto3.client('logs').delete_log_stream(
                    logGroupName = group["logGroupName"],
                    logStreamName = stream["logStreamName"]
                )
        
            streams = _describe_log_streams(group["logGroupName"], None, 50)
            if len(streams["logStreams"]) == 0:
                mesg = ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').delete_log_group(logGroupName = '%s')" % (
                        group["logGroupName"]
                    )
                )
                print (mesg)
                
                boto3.client('logs').delete_log_group(
                    logGroupName = group["logGroupName"]
                )
            else:
                safe_groups.append(group["logGroupName"])
            
def main(params):
    
    print (ecsub.tools.info_message(TITLE, None, "=== download log files start ==="))
    _download_log(params)
    print (ecsub.tools.info_message(TITLE, None, "=== download log files end ==="))
    
    if params["remove"]:
        print (ecsub.tools.info_message(TITLE, None, "=== remove log streams start ==="))
        _remove_log(params)
        print (ecsub.tools.info_message(TITLE, None, "=== remove log streams end ==="))
            
def entry_point(args):
    params = {
        "wdir": args.wdir.rstrip("/"),
        "group_name_prefix": args.prefix,
        "remove": args.remove
    }
    main(params)
    
if __name__ == "__main__":
#    params = {
#        "wdir": "/tmp/ecsub/",
#        "group_name_prefix": "ecsub",
#        "remove": True
#    }
#    main(params)
    pass
