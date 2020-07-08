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

def _load_summary(params, dic_summary, header):

    def __header_to_info (header):
        info = {}
        for key in header:
            info[key] = ""
        return info
    
    dic_info = {}
            
    for key in sorted(dic_summary.keys()):
        if params["max"] > 0 and len(dic_info) >= params["max"]:
            break
        
        if os.path.getsize(dic_summary[key]) == 0:
            continue
        
        info = __header_to_info (header)
        
        info["exit_code"] = "NA"
        info["taskname"] = key.split("@")[0]
        info["no"] = key.split("@")[-1]
        
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
                info["spot"] = "T"
            else:
                info["spot"] = "F"
                
            info["task_startAt"] = data["Start"]
            info["task_endAt"] = data["End"]
            if info["task_endAt"] == None:
                info["task_endAt"] = ""
            info["disk_size"] = str(data["Ec2InstanceDiskSize"])
            if "Price" in data:
                info["price"] = str(data["Price"])
            
            try:
                exit_code = str(data["Jobs"][-1]["ExitCode"])
                if params["fail"] and exit_code == "0":
                    continue
                info["exit_code"] = str(data["Jobs"][-1]["ExitCode"])
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
    
    header = [
        "exit_code",
        "taskname",
        "no",
        "spot",
        "task_startAt",
        "task_endAt",
        "instance_type",
        "cpu",
        "memory",
        "disk_size",
        "price",
        "instance_createAt",
        "instance_stopAt",
        "log_local",
    ]
    
    dic_summary = _glob_to_dict(params["wdir"] + "/*/log/summary.*.log")
    dic_info = _load_summary(params, dic_summary, header)
    
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
    main(params)
    
    return 0

if __name__ == "__main__":
    params = {
        "wdir": "/tmp/ecsub/",
        "fail": True,
    }
    main(params)
