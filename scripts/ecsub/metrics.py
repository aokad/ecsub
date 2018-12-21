# -*- coding: utf-8 -*-
"""
Created on Thu Aug 02 11:55:46 2018

@author: Okada
"""

import os
import boto3
import datetime
from dateutil.tz import tzutc
import ecsub.tools
import pytz

def _is_empty_responce(responce):
    
    if not 'Datapoints' in responce:
        return True
        
    if len(responce['Datapoints']) == 0:
        return True
        
    return False

def _responce_to_dict(responce):
    dict = {}
    
    if _is_empty_responce(responce):
        return dict
        
    for data in responce['Datapoints']:
        dict[data['Timestamp']] = {
            'Maximum': data['Maximum'],
            'Unit': data['Unit']
        }
    
    return dict

def _responce_to_txt(responce, start_date = None ):
    
    header = "Index\tTimestamp\tMaximum\tUnit"
    text = ""
    
    dic = _responce_to_dict(responce)
    
    if start_date == None:
        start_date = sorted(dic.keys())[0]
    
    for date in sorted(dic.keys()):
        text += "%d\t%s\t%d\t%s\n" % (
            int((date - start_date).total_seconds()/60),
            date.strftime("%Y/%m/%d %H:%M:%S"),
            dic[date]['Maximum'],
            dic[date]['Unit']
        )
    
    return [header, text, start_date]
    
def _download_metrics(params):
    
    now = pytz.timezone('UTC').localize(datetime.datetime.now())
    # 15 days ago
    d1 = now - datetime.timedelta(0, 60*60*24*15)
    # tomorrow
    d2 = now + datetime.timedelta(0, 60*60*24*1)
    
    dimensions = [
    {
        'Name': 'InstanceId',
        'Value': params['instanceId']
    },
    {
        'Name': 'ClusterName',
        'Value': params['clusterName']
    }]
    
    metric_range = boto3.client("cloudwatch").get_metric_statistics(
        Namespace = params['namespace'],
        MetricName = params['metric'],
        Dimensions = dimensions,
        Statistics = ['Maximum'],
        Period = 60*60*24,
        StartTime = datetime.datetime(d1.year, d1.month, d1.day, 0, 0, 0, tzinfo=tzutc()),
        EndTime = datetime.datetime(d2.year, d2.month, d2.day, 0, 0, 0, tzinfo=tzutc())
    )
    #print metric_range
    
    prefix = "%s/metrics" % (params["wdir"])
    if not os.path.exists(prefix):
        os.makedirs(prefix)

    f = open("%s/%s-%s.txt" % (prefix, params['instanceName'].split(".")[-1], params['metric']), "w")
    start_date = None

    for date in sorted(_responce_to_dict(metric_range).keys()):
        for i in range(24):
            s = datetime.datetime(date.year, date.month, date.day, i, 0, 0, tzinfo=tzutc())
            d = s + datetime.timedelta(0, 60*60)
            
            responce = boto3.client("cloudwatch").get_metric_statistics(
                Namespace = params['namespace'],
                MetricName = params['metric'],
                Dimensions = dimensions,
                Statistics = ['Maximum'],
                Period=60,
                StartTime=s,
                EndTime = datetime.datetime(d.year, d.month, d.day, d.hour, d.minute, 0, tzinfo=tzutc())
            )
     
            if _is_empty_responce(responce):
                continue
            [header, text, start_date1] = _responce_to_txt(responce, start_date)
            if start_date == None:
                f.write(header + "\n")
                start_date = start_date1
            f.write(text)

        print (ecsub.tools.info_message(params["title"], None, "downloaded %s %s %s" % (
            params['instanceName'], 
            params['metric'], 
            date.strftime("%Y/%m/%d")
        )))
        
    f.close()
    return
    
def main(params):
    
    print (ecsub.tools.info_message(params["title"], None, "=== download metrics files start ==="))
        
    for instance in params["instances"]:
        for metric in params["metrics"]:
            partial_params = {
                "title": params["title"],
                "wdir": params["wdir"],
                "namespace": params["namespace"],
                "clusterName": params["cluster"]["Name"],
                "clusterArn": params["cluster"]["Arn"],
                "metric": metric,
                "instanceId": instance["Id"],
                "instanceName": instance["Name"],
            }
            _download_metrics(partial_params)

    print (ecsub.tools.info_message(params["title"], None, "=== download metrics files end ==="))

def entry_point(wdir):
    import json
    import glob
    
    cluster = json.load(open("%s/log/create-cluster.0.log" % (wdir)))["cluster"]
    instance_list = []
    for tag_file in sorted(glob.glob("%s/log/create-tags*.log" % (wdir))):
        instance = json.load(open(tag_file))
        instance_list.append({"Id": instance["InstanceId"], "Name": instance["InstanceName"]})
    
    params = {
        "wdir": wdir,
        "namespace": "ECSUB",
        "metrics": ["CPUUtilization", "DataStorageUtilization", "MemoryUtilization", "MemoryUtilization_BK"],
        "instances": instance_list,
        "cluster": {"Name": cluster["clusterName"], "Arn": cluster["clusterArn"]},
        "title": cluster["clusterName"] + ":metrics"
    }
    # print params
    main(params)
    
if __name__ == "__main__":
#    params = {
#        "wdir": "/tmp/ecsub/",
#        "namespace": "ECSUB",
#        "metrics": ["CPUUtilization", "DataStorageUtilization", "MemoryUtilization"],
#        "instances": [{"Id": 'i-0b08e5e9eaacc6afd', "Name": "tasks-wordcount-FsXkH.2"}],
#        "cluster": {"Name": "tasks-wordcount-FsXkHt", 
#                    "Arn": 'arn:aws:ecs:ap-southeast-1:220286576909:cluster/tasks-wordcount-FsXkH',
#                    }
#    }
#    main(params)
#    entry_point("/tmp/ecsub/tasks-wordcount-bP7D8")
    pass
