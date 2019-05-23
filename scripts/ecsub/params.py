#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 23 15:29:17 2019

@author: aokada
"""

def summary_to_obj(path):
    import json
    
    summary = json.load(open(path))
    
    conf = {
        "setx": "set -x",
    }
    inst = {}

    inst["aws_key_name"] = summary["KeyName"]
    inst["aws_security_group_id"] = summary["SecurityGroupId"]
    conf["cluster_name"] = summary["ClusterName"]
    conf["shell"]  = summary["Shell"]
    conf["aws_ec2_instance_disk_size"] = summary["Ec2InstanceDiskSize"]
    conf["image"] = summary["Image"]
    conf["use_amazon_ecr"] = summary["UseAmazonEcr"]
    conf["spot"] = summary["Spot"]
    
    # no use
    conf["aws_ec2_instance_type_list"] = ['']
    conf["aws_ec2_instance_type"] = ""
    inst["aws_subnet_id"] = ""
    conf["retry_od"] = False
    conf["request_payer"] = []
    conf["setup_container_cmd"] = ""
    conf["dind"] = False
    
    return (conf, inst)

def args_to_obj(args):
    conf = {
        "wdir": args.wdir,
        "image": args.image,
        "shell": args.shell,
        "use_amazon_ecr": args.use_amazon_ecr,
        "script": args.script,
        "tasks": args.tasks,
        "task_name": args.task_name,
        "aws_ec2_instance_type": args.aws_ec2_instance_type,
        "aws_ec2_instance_type_list": args.aws_ec2_instance_type_list,
        "aws_ec2_instance_disk_size": args.disk_size,
        "aws_s3_bucket": args.aws_s3_bucket,
        "aws_security_group_id": args.aws_security_group_id,
        "aws_key_name": args.aws_key_name,
        "aws_subnet_id": args.aws_subnet_id,
        "spot": args.spot,
        "retry_od": args.retry_od,
        "setx": "set -x",
        "setup_container_cmd": args.setup_container_cmd,
        "dind": args.dind,
        "processes": args.processes,
        "request_payer": args.request_payer_bucket,
        "ignore_location": args.ignore_location
    }
    return conf

def _hour_delta(start_t, end_t):
    return (end_t - start_t).total_seconds()/3600.0

def set_job_info(task_param, start_t, end_t, task_log, exit_code):
    
    info = {
        "Ec2InstanceType": task_param["aws_ec2_instance_type"],
        "End": end_t,
        "ExitCode": exit_code,
        "LogLocal": task_log, 
        "OdPrice": task_param["od_price"],
        "Start": start_t,
        "Spot": task_param["spot"],
        "SpotAz": task_param["spot_az"],
        "SpotPrice": task_param["spot_price"],
        "WorkHours": _hour_delta(start_t, end_t),
        "InstanceId": "",
        "SubnetId": "",
        "Memory": 0,
        "vCpu": 0,
    }
    
    if task_log == None:
        return info
    
    task = json.load(open(task_log))["tasks"][0]
    info["InstanceId"] = task["instance_id"]
    info["SubnetId"] = task["subnet_id"]
    info["Memory"] = task["overrides"]["containerOverrides"][0]["memory"]
    info["vCpu"] = task["overrides"]["containerOverrides"][0]["cpu"]

    return info

def save_summary_file(job_summary, print_cost):
    
    template = " + instance-type %s (%s) %.3f USD (%s: %.3f USD), running-time %.3f Hour"
    costs = 0.0
    items = []
    for job in job_summary["Jobs"]:
        wtime = _hour_delta(job["Start"], job["End"])
        
        if job["Spot"]:
            costs += job["SpotPrice"] * wtime
            items.append(template % (job["Ec2InstanceType"], "spot", job["SpotPrice"], "od", job["OdPrice"], wtime))
        else:
            costs += job["OdPrice"] * wtime
            items.append(template % (job["Ec2InstanceType"], "ondemand", job["OdPrice"], "spot", job["SpotPrice"], wtime))            
        
        job["Start"] = ecsub.tools.datetime_to_standardformat(job["Start"])
        job["End"] = ecsub.tools.datetime_to_standardformat(job["End"])

    if print_cost:        
        message = "The cost of this job is %.3f USD. \n%s" % (costs, "\n".join(items))
        print (ecsub.tools.info_message (job_summary["ClusterName"], job_summary["No"], message))
    
    log_file = "%s/log/summary.%03d.log" % (job_summary["Wdir"], job_summary["No"]) 
    json.dump(job_summary, open(log_file, "w"), indent=4, separators=(',', ': '), sort_keys=True)
 
class Config():
    def __init__ (self, args):
        self.wdir = args.wdir
        self.image = args.image
        self.shell = args.shell
        self.use_amazon_ecr = args.use_amazon_ecr
        self.script = args.script
        self.tasks = args.tasks
        self.task_name = args.task_name
        self.aws_ec2_instance_type = args.aws_ec2_instance_type
        self.aws_ec2_instance_type_list = args.aws_ec2_instance_type_list
        self.aws_ec2_instance_disk_size = args.disk_size
        self.aws_s3_bucket = args.aws_s3_bucket
        self.aws_security_group_id = args.aws_security_group_id
        self.aws_key_name = args.aws_key_name
        self.aws_subnet_id = args.aws_subnet_id
        self.spot = args.spot
        self.retry_od = args.retry_od
        self.setx = "set -x"
        self.setup_container_cmd = args.setup_container_cmd
        self.dind = args.dind
        self.processes = args.processes
        self.request_payer = args.request_payer_bucket
        self.ignore_location = args.ignore_location
    
class Resource():
    def __init__ (self, summary):
        self.aws_key_name = ""
        self.aws_security_group_id = ""
        self.aws_subnet_id = ""
        if summary != None:
            self.aws_key_name = summary["KeyName"]
            self.aws_security_group_id = summary["SecurityGroupId"]
    
class Parameter():
    def __init__(self, conf, resource = None):
        self.CONF = Config(conf)
        self.resource = Resource(resource)
        
def main():
    pass

if __name__ == "__main__":
    main()

