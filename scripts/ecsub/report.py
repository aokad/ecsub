# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 11:46:34 2018

@author: Okada
"""

import glob
import json
import os

def _print(info, header, length):
    #import pprint
    #pprint.pprint(length)
    
    text = ""
    for i in range(len(header)):
        f = "|%" + str(length[header[i]]) + "s"
        text += f % str(info[header[i]])
    print (text + "|")

def _glob_to_dict(glob_text):
    
    files = []
    if type(glob_text) == type([]):
        for text in glob_text:
            files.extend(glob.glob(text))
    else:
        files = glob.glob(glob_text)
        
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

def _load_logs(instances, tasks):

    info_dict = {}
            
    for tkey in sorted(instances.keys()):
        ilog = instances[tkey]
        spot = ""
        itype = ""
        
        if "request-spot-instances" in os.path.basename(ilog):
            spot = "T"
            itype = "NA"
            try:
                itype = json.load(open(ilog))["SpotInstanceRequests"][0]["LaunchSpecification"]["InstanceType"]
            except Exception:
                pass
        else:
            spot = "F"
            itype = "NA"
            try:
                itype = json.load(open(ilog))["Instances"][0]["InstanceType"]
            except Exception:
                pass
        
        info = {
            "exitCode": "NA",
            "taskname": tkey.split("@")[0],
            "no": tkey.split("@")[-1],
            "Spot": spot,
            "cpu": "NA",
            "memory": "NA",
            "instance_type": itype,
            "disk_size": "NA",
            "createdAt": "NA",
            "stoppedAt": "NA",
            "log_local": "NA",
        }
        if tkey in tasks:
            tlog = tasks[tkey]
            task = json.load(open(tlog))["tasks"][0]
            for ckey in info.keys():
                if ckey == "exitCode":
                    if "exitCode" in task["containers"][0]:
                        value = task["containers"][0]["exitCode"]
                    else:
                        continue
                elif ckey == "taskname":
                    continue
                elif ckey == "no":
                    continue
                elif ckey == "Spot":
                    value = spot
                else:
                    value = task[ckey]
                    
                info[ckey] = str(value)
            
        info_dict[tkey] = info
    
    #json.dump(info_dict, open("inst.json", "w"), indent=4, separators=(',', ': '), sort_keys=True)
    return info_dict

def main(params):
    
    instance_logs = _glob_to_dict([params["wdir"] + "/*/log/run-instances.*.log", 
                                   params["wdir"] + "/*/log/request-spot-instances.*.log"])
    task_logs = _glob_to_dict(params["wdir"] + "/*/log/describe-tasks.*.log")

    info_dict = _load_logs(instance_logs, task_logs)
    
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
        for tkey in info_dict.keys():
            wsize.append(len(info_dict[tkey][ckey]))
        info_wmax[ckey] = max(wsize)
    
    _print(header_dic, header, info_wmax)
    for tkey in sorted(info_dict.keys()):
        if params["fail"]:
            if info_dict[tkey]["exitCode"] == "0":
                continue
        _print(info_dict[tkey], header, info_wmax)
    
def entry_point(args, unknown_args):

    params = {
        "wdir": args.wdir.rstrip("/"),
        "fail": args.fail,
    }
    main(params)
    
if __name__ == "__main__":
    params = {
        "wdir": "/tmp/ecsub/",
        "fail": True,
    }
    main(params)
