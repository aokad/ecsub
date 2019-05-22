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

def _to_log_prefix(prefix):
    return "ecsub-" + prefix

def _to_cluster_name(log_group_name):
    cluster_name = re.sub(r'^ecsub-', "", log_group_name)
    ecsub.tools.info_message(TITLE, None, "cluser-name: %s" % (cluster_name))
    return cluster_name
    
def _describe_log_groups(logGroupNamePrefix, nextToken, limit):
    
    if nextToken == None:
        ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').describe_log_groups(logGroupNamePrefix = '%s', limit = %d)" % (
                logGroupNamePrefix, limit
            )
        )
        
        groups = boto3.client('logs').describe_log_groups(
            limit = limit, 
            logGroupNamePrefix = logGroupNamePrefix
        )
        ecsub.tools.info_message(TITLE, None, "log-groups: %d" % (len(groups["logGroups"])))
        
    else:
        groups = boto3.client('logs').describe_log_groups(
            limit = limit, 
            logGroupNamePrefix = logGroupNamePrefix,
            nextToken = nextToken
        )
    
    return groups

def _describe_log_streams(logGroupName, nextToken, limit, logStreamNamePrefix='ecsub'):
    
    if nextToken == None:
        ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').describe_log_streams(logGroupName = '%s', logStreamNamePrefix = 'ecsub', limit = %d)" % (
                logGroupName, limit
            )
        )
        
        streams = boto3.client('logs').describe_log_streams(
            logGroupName = logGroupName,
            logStreamNamePrefix = logStreamNamePrefix,
            limit = limit
        )
        ecsub.tools.info_message(TITLE, None, "log-streams: %d" % (len(streams["logStreams"])))
        
    else:
        streams = boto3.client('logs').describe_log_streams(
            logGroupName = logGroupName,
            logStreamNamePrefix = logStreamNamePrefix,
            limit = limit,
            nextToken = nextToken
        )
    
    return streams

def _get_log_events(logGroupName, logStreamName, nextToken):
    
    if nextToken == None:
        ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').get_log_events(logGroupName = '%s', logStreamName = '%s', startFromHead = True)" % (
                logGroupName, logStreamName
            )
        )
        
        events = boto3.client('logs').get_log_events(
            logGroupName = logGroupName,
            logStreamName = logStreamName,
            startFromHead = True
        )
        ecsub.tools.info_message(TITLE, None, "log-events: %d" % (len(events["events"])))
        
    else:
        events = boto3.client('logs').get_log_events(
            logGroupName = logGroupName,
            logStreamName = logStreamName,
            startFromHead = True,
            nextToken = nextToken
        )

    return events

def _specify_log_group(group_name_prefix):

    groups = _describe_log_groups(group_name_prefix, None, 50)
    
    if len(groups["logGroups"]) == 0:
        ecsub.tools.error_message(TITLE, None, 
            "logGroupName-Prefix '%s' is none." % (group_name_prefix)
        )
        return None
    if len(groups["logGroups"]) > 1:
        group_names = []
        for g in groups["logGroups"]:
            group_names.append(g["logGroupName"])
        
        ecsub.tools.error_message(TITLE, None, 
            "logGroupName-Prefix '%s' is unspecified. \n%s" % (group_name_prefix, "\n".join(group_names))
        )
        
        return None
        
    return groups["logGroups"][0]
    
# specify Log stream
def _download_log_stream(log_group_name, stream, wdir, cluster_name):

    output_dir = "%s/%s/cloud_watch" % (wdir.rstrip("/"), cluster_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    f = open("%s/%s-%s.log" % (
        output_dir,
        stream["logStreamName"].split("/")[1],
        _timestamp(stream["creationTime"])), "w")
    
    events = None
    while(1):
        if events != None and len(events["events"]) == 0:
            break

        if events == None:
            events = _get_log_events(log_group_name, stream["logStreamName"], None)
        else:
            events = _get_log_events(log_group_name, stream["logStreamName"], events["nextForwardToken"])
            
        for event in events["events"]:
            f.write("%s\t%s\n" % (_timestamp(event["timestamp"]), event["message"].encode('utf-8')))
            
    f.close()
        
def download_log(wdir, prefix):
        
    log_group_name = _to_log_prefix(prefix)
    
    group = _specify_log_group(log_group_name)
    if group == None:
        return
    
    cluster_name = _to_cluster_name(group["logGroupName"])
     
    stream = None
    while(1):
        if stream != None and not "nextToken" in stream.keys():
            break

        if stream == None:
            stream = _describe_log_streams(group["logGroupName"], None, 1)
        else:
            stream = _describe_log_streams(group["logGroupName"], stream["nextToken"], 1)
        
        if len(stream["logStreams"]) == 0:
            break
        
        _download_log_stream(group["logGroupName"], stream["logStreams"][0], wdir, cluster_name)
            
def download_logs(wdir, prefix):
    
    group_name_prefix = _to_log_prefix(prefix)
    group = None
    while(1):
        if group != None and not "nextToken" in group.keys():
            break

        if group == None:
            group = _describe_log_groups(group_name_prefix, None, 1)
        else:
            group = _describe_log_groups(group_name_prefix, group["nextToken"], 1)
        
        if len(group["logGroups"]) == 0:
            break
        
        cluster_name = _to_cluster_name(group["logGroups"][0]["logGroupName"])
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
            
            _download_log_stream(group["logGroups"][0]["logGroupName"], stream["logStreams"][0], wdir, cluster_name)

# specify Log Group
def remove_log(wdir, prefix):
    
    group_name_prefix = _to_log_prefix(prefix)
    group = _specify_log_group(group_name_prefix)
    if group == None:
        return
        
    streams = _describe_log_streams(group["logGroupName"], None, 50)
    for stream in streams["logStreams"]:
        ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').delete_log_stream(logGroupName = '%s', logStreamName = '%s')" % (
                group["logGroupName"], stream["logStreamName"]
            )
        )
        
        boto3.client('logs').delete_log_stream(
            logGroupName = group["logGroupName"],
            logStreamName = stream["logStreamName"]
        )

    streams = _describe_log_streams(group["logGroupName"], None, 50)
    if len(streams["logStreams"]) == 0:
        ecsub.tools.info_message(TITLE, None, 
            "boto3.client('logs').delete_log_group(logGroupName = '%s')" % (
                group["logGroupName"]
            )
        )
        
        boto3.client('logs').delete_log_group(
            logGroupName = group["logGroupName"]
        )
    else:
        ecsub.tools.error_message(TITLE, None, 
            "Could not delete logGroupName '%s'." % (group_name_prefix)
        )
                
def remove_logs(wdir, prefix):
    
    group_name_prefix = _to_log_prefix(prefix)
    safe_groups = []
    while(1):
        groups = _describe_log_groups(group_name_prefix, None, 50)
        
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
            
            streams = _describe_log_streams(group["logGroupName"], None, 50)
            for stream in streams["logStreams"]:
                ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').delete_log_stream(logGroupName = '%s', logStreamName = '%s')" % (
                        group["logGroupName"], stream["logStreamName"]
                    )
                )
                
                boto3.client('logs').delete_log_stream(
                    logGroupName = group["logGroupName"],
                    logStreamName = stream["logStreamName"]
                )
        
            streams = _describe_log_streams(group["logGroupName"], None, 50)
            if len(streams["logStreams"]) == 0:
                ecsub.tools.info_message(TITLE, None, 
                    "boto3.client('logs').delete_log_group(logGroupName = '%s')" % (
                        group["logGroupName"]
                    )
                )
                
                boto3.client('logs').delete_log_group(
                    logGroupName = group["logGroupName"]
                )
            else:
                safe_groups.append(group["logGroupName"])
            
def main(params):
    
    if params["download"]:
        ecsub.tools.info_message(TITLE, None, "=== download log files start ===")
        download_logs(params["wdir"], params["prefix"])
        ecsub.tools.info_message(TITLE, None, "=== download log files end ===")
    
    if params["remove"]:
        ecsub.tools.info_message(TITLE, None, "=== remove log streams start ===")
        remove_logs(params["wdir"], params["prefix"])
        ecsub.tools.info_message(TITLE, None, "=== remove log streams end ===")
    
    if params["download"] == False and  params["remove"] == False:
        ecsub.tools.warning_message(TITLE, None, "Set either --rm (remove) or --dw (download) or both.")
        
def entry_point(args, unknown_args):
    if len(unknown_args) > 0:
        ecsub.tools.warning_message(TITLE, None, "Set the correct option.")
        return
        
    params = {
        "wdir": args.wdir,
        "prefix": args.prefix,
        "remove": args.rm,
        "download": args.dw,
    }
    main(params)
    
if __name__ == "__main__":
    pass
