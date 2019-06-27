# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 11:46:34 2018

@author: Okada
"""

import glob
import json
import os

import ecsub.tools

def _print(info, header, length):
    
    text = ""
    for i in range(len(header)):
        f = "|%" + str(length[header[i]]) + "s"
        text += f % str(info[header[i]])
    print (text + "|")

def _glob(glob_text):
    
    files = []
    if type(glob_text) == type([]):
        for text in glob_text:
            files.extend(glob.glob(text))
    else:
        files = glob.glob(glob_text)
    return files

def _glob_to_dict(glob_text):
    
    files = _glob(glob_text)
        
    dic = {}
    for log in files:
        
        cluster_name = os.path.basename(os.path.dirname(os.path.dirname(log)))
        name_split = os.path.basename(log).split(".")
        index = int(name_split[1])
        key = "%s@%03d" % (cluster_name, index)
        if key in dic:
            if os.stat(dic[key]).st_mtime < os.stat(log).st_mtime:
                dic[key] = log
        else:
            dic[key] = log
               
    return dic

def _run_instance_info(glob_text):
    
    dic_logs = _glob_to_dict(glob_text)
    dic_info = {}
    
    for key in sorted(dic_logs.keys()):
        log = dic_logs[key]
    
        if os.path.getsize(log) == 0:
            continue
        
        spot = ""
        itype = ""
        createAt = ""
        instanceId = ""
        
        data = json.load(open(log))
            
        if "describe-spot-instance-requests" in os.path.basename(log):
            spot = "T"
            itype = "NA"
            try:
                instanceId = data["SpotInstanceRequests"][0]["InstanceId"]
                itype = data["SpotInstanceRequests"][0]["LaunchSpecification"]["InstanceType"]
                createAt = data["SpotInstanceRequests"][0]["CreateTime"]
            except Exception:
                continue
            
        else:
            spot = "F"
            itype = "NA"
            try:
                instanceId = data["Instances"][0]["InstanceId"]
                itype = data["Instances"][0]["InstanceType"]
                createAt = data["Instances"][0]["LaunchTime"]
            except Exception:
                continue
            
        createAt = ecsub.tools.isoformat_to_datetime(createAt)
            
        dic_info[key] = {
            "instanceId": instanceId,
            "createdAt": createAt,
            "Spot": spot,
            "iType": itype,
            "stoppedAt": None,
            "Code": None,
            "Name": None
        }
        
    return dic_info

def _terminate_instance_info(glob_text, dic_info):
    
    files = _glob(glob_text)

    for log in files:
        if os.path.getsize(log) == 0:
            continue
        data = json.load(open(log))
        log_timestamp = os.stat(log).st_mtime
               
        for instance in data["TerminatingInstances"]:
            
            for key in sorted(dic_info.keys()):
                if dic_info[key]["instanceId"] != instance["InstanceId"]:
                    continue
                
                if dic_info[key]["stoppedAt"] == None or dic_info[key]["stoppedAt"] > log_timestamp:
                    dic_info[key]["stoppedAt"] = log_timestamp
                    dic_info[key]["Code"] = instance["CurrentState"]["Code"]
                    dic_info[key]["Name"] = instance["CurrentState"]["Name"]
               
    return dic_info

def _load_logs(params, task_logs, dic_info):

    info_dict = {}
            
    for tkey in sorted(dic_info.keys()):
        
        Start = "NA"
        if dic_info[tkey]["createdAt"] != None:
            if params["to_date"] != None and params["to_date"] > dic_info[tkey]["createdAt"]:
                continue
            if params["from_date"] != None and params["from_date"] < dic_info[tkey]["createdAt"]:
                continue
            Start = ecsub.tools.datetime_to_standardformat(dic_info[tkey]["createdAt"])
            
        End = "NA"
        if dic_info[tkey]["stoppedAt"] != None:
            End = ecsub.tools.datetime_to_standardformat(ecsub.tools.timestamp_to_datetime(dic_info[tkey]["stoppedAt"]))
            
        info = {
            "taskname": tkey.split("@")[0],
            "no": tkey.split("@")[-1],
            "Spot": dic_info[tkey]["Spot"],
            "instance_type": dic_info[tkey]["iType"],
            "createdAt": Start,
            "stoppedAt": End,
            "exitCode": "NA",
            "cpu": "NA",
            "memory": "NA",              
            "disk_size": "NA",                  
            "log_local": "NA",
        }
        if tkey in task_logs:
            tlog = task_logs[tkey]
            task = json.load(open(tlog))["tasks"][0]
            for ckey in info.keys():
                if ckey == "exitCode":
                    if "exitCode" in task["containers"][0]:
                        value = task["containers"][0]["exitCode"]
                    else:
                        continue
                elif ckey in ["taskname", "no", "Spot", "instance_type", "createdAt", "stoppedAt"]:
                    continue

                else:
                    value = task[ckey]
                    
                info[ckey] = str(value)
            
        info_dict[tkey] = info
    
    return info_dict

def main_past(params):
    
    dic_info = _run_instance_info([params["wdir"] + "/*/log/run-instances.*.log", 
                                       params["wdir"] + "/*/log/describe-spot-instance-requests.*.log"])
    
    dic_info1 = _terminate_instance_info(params["wdir"] + "/*/log/terminate-instances.*.log", dic_info)
    
    task_logs = _glob_to_dict(params["wdir"] + "/*/log/describe-tasks.*.log")
    
    dic_info2 = _load_logs(params, task_logs, dic_info1)
    
    header = [
        "exitCode",
        "taskname",
        "no",
        "Spot",
        "cpu",
        "memory",
        "instance_type",
        "disk_size",
        "createdAt",
        "stoppedAt",
        "log_local",
    ]

    info_wmax = {}
    header_dic = {}
    for ckey in header:
        header_dic[ckey] = ckey
        wsize = [len(header_dic[ckey])]
        for tkey in dic_info2.keys():
            wsize.append(len(dic_info2[tkey][ckey]))
        info_wmax[ckey] = max(wsize)
    
    _print(header_dic, header, info_wmax)
    for tkey in sorted(dic_info2.keys()):
        if params["fail"]:
            if dic_info2[tkey]["exitCode"] == "0":
                continue
        _print(dic_info2[tkey], header, info_wmax)

def _load_summary(params, dic_summary):

    dic_info = {}
            
    for key in sorted(dic_summary.keys()):
        if params["max"] > 0 and len(dic_info) >= params["max"]:
            break
        
        if os.path.getsize(dic_summary[key]) == 0:
            continue
        
        info = {
            "exitCode": "NA",
            "taskname": key.split("@")[0],
            "no": key.split("@")[-1],
            "Spot": "", 
            "job_startAt": "",
            "job_endAt": "",
            "disk_size": "",
            "cpu": "",
            "memory": "",
            "instance_type": "",
            "instance_createAt": "",
            "instance_stopAt": "",
            "log_local": "",
        }
        
        data = None
        try:
            data = json.load(open(dic_summary[key]))
        except Exception as e:
            #print ("[%s] %s" % (dic_summary[key], e))
            pass
        
        if data != None:
            start_t = ecsub.tools.standardformat_to_datetime(data["Start"])
            if start_t != None:
                if params["to_date"] != None and params["to_date"] > start_t:
                    continue
                if params["from_date"] != None and params["from_date"] < start_t:
                    continue
            
            if data["Spot"]:
                info["Spot"] = "T"
            else:
                info["Spot"] = "F"
                
            info["job_startAt"] = data["Start"]
            info["job_endAt"] = data["End"]
            if info["job_endAt"] == None:
                info["job_endAt"] = ""
            info["disk_size"] = str(data["Ec2InstanceDiskSize"])
            
            try:
                exit_code = str(data["Jobs"][-1]["ExitCode"])
                if params["fail"] and exit_code == "0":
                    continue
                info["exitCode"] = str(data["Jobs"][-1]["ExitCode"])
                info["instance_type"] = data["Jobs"][-1]["Ec2InstanceType"]
                info["instance_createAt"] = data["Jobs"][-1]["Start"]
                info["instance_stopAt"] = data["Jobs"][-1]["End"]
                info["cpu"] = str(data["Jobs"][-1]["vCpu"])
                info["memory"] = str(data["Jobs"][-1]["Memory"])
                info["log_local"] = data["Jobs"][-1]["LogLocal"]
                
            except Exception:
                pass
        
        dic_info[key] = info
        
    return dic_info

def sort_dic(dic, key_name):
    sorted_dic = {}
    for key in sorted(dic.keys()):
        value = dic[key][key_name]
        if value == "":
            value = "z"
        new_key = str(value) + key
        sorted_dic[new_key] = dic[key]
    return sorted_dic
 
def main(params):
    
    dic_summary = _glob_to_dict(params["wdir"] + "/*/log/summary.*.log")
    dic_info = _load_summary(params, dic_summary)
    
    header = [
        "exitCode",
        "taskname",
        "no",
        "Spot",
        "job_startAt",
        "job_endAt",
        "instance_type",
        "cpu",
        "memory",
        "disk_size",
        "instance_createAt",
        "instance_stopAt",
        "log_local",
    ]

    info_wmax = {}
    header_dic = {}
    for ckey in header:
        header_dic[ckey] = ckey
        wsize = [len(header_dic[ckey])]
        for tkey in dic_info.keys():
            if dic_info[tkey][ckey] == None:
                continue
            else:
                wsize.append(len(dic_info[tkey][ckey]))
            
        info_wmax[ckey] = max(wsize) + 1
    
    if params["sortby"] == "taskname":
        sorted_dic = dic_info
    else:
        sorted_dic = sort_dic(dic_info, params["sortby"])        
    
    _print(header_dic, header, info_wmax)
    for tkey in sorted(sorted_dic.keys()):
        _print(sorted_dic[tkey], header, info_wmax)
        
def entry_point(args):
    
    begin = None
    if args.begin != "":
        begin = ecsub.tools.plainformat_to_datetime(args.begin)
        if begin == None:
            print ("Unexpected input %s" % (args.begin))
            return 1
    
    end = None
    if args.end != "":
        end = ecsub.tools.plainformat_to_datetime(args.end)
        if end == None:
            print ("Unexpected input %s" % (args.end))
            return 1
    
    params = {
        "wdir": args.wdir.rstrip("/"),
        "fail": args.failed,
        "to_date": begin,
        "from_date": end,
        "max": args.max,
        "sortby": args.sortby,
    }
    if args.past:
        main_past(params)
    
    else:
        main(params)
    
    return 0

if __name__ == "__main__":
    params = {
        "wdir": "/tmp/ecsub/",
        "fail": True,
    }
    main(params)
