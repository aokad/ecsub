# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 11:46:34 2018

@author: Okada
"""

import glob
import json

def _print(info, header, length):
    text = ""
    for i in range(len(header)):
        f = "|%" + str(length[header[i]]) + "s"
        text += f % str(info[header[i]])
    print (text + "|")

def main(params):
    logs = sorted(glob.glob(params["wdir"] + "/*/log/describe-tasks.*.log"))

    header = ["exitCode",
              "taskname",
              "no",
              "cpu",
              "memory",
              "instance_type",
              "disk_size",
              "createdAt",
              "stoppedAt",
              "log_local",
              ]

    info_list = []
    info_wmax = {}
    header_dic = {}
    for key in header:
        header_dic[key] = key
        info_wmax[key] = len(header_dic[key])
        
    for log in logs:
        info = {}
        for key in header:
            info[key] = ""
        
        task = json.load(open(log))["tasks"][0]
        for key in header:
            if key == "exitCode":
                if not "exitCode" in task["containers"][0]:
                    value = "NA"
                else:
                    value = task["containers"][0]["exitCode"]
            elif key == "taskname":
                value = task["containers"][0]["name"]
            elif key == "SCRIPT_ENVM_PATH":
                value = task["overrides"]["containerOverrides"][0]["environment"][0]["value"]
            else:
                value = task[key]
                
            info[key] = str(value)

            if info_wmax[key] < len(info[key]):
                info_wmax[key] = len(info[key])

        info_list.append(info)
    
    _print(header_dic, header, info_wmax)
    for info in info_list:
        _print(info, header, info_wmax)
    
def entry_point(args, unknown_args):

    params = {
        "wdir": args.wdir.rstrip("/"),
    }
    main(params)
    
if __name__ == "__main__":
    params = {
        "wdir": "/tmp/ecsub/",
    }
    main(params)

