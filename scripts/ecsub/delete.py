# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import ecsub.aws
import ecsub.submit
import ecsub.tools
import glob

def main(params):
    
    params["wdir"] =  params["wdir"].rstrip("/")
    summary_list = glob.glob("%s/%s/log/summary.*.log" % (params["wdir"], params["task_name"]))
    if len(summary_list) == 0:
        print (ecsub.tools.error_message (params["task_name"], None, "task-name %s is not find in directory %s." % (params["task_name"], params["wdir"])))
        return 1
    
    params["wdir"] =  "%s/%s" % (params["wdir"].rstrip("/"), params["task_name"])
    
    import json
    summary = json.load(open(summary_list[0]))

    params["cluster_name"] = summary["ClusterName"]
    
    aws_instance = ecsub.aws.Aws_ecsub_control(params, 1)
    aws_instance.aws_key_name = summary["KeyName"]
    aws_instance.aws_security_group_id = summary["SecurityGroupId"]
    aws_instance.spot = summary["Spot"]
    aws_instance.aws_key_auto = summary["AutoKey"]
    aws_instance.cluster_arn = summary["ClusterArn"]
    aws_instance.task_definition_arn = summary["TaskDefinitionAn"]
    
    aws_instance.clean_up()
    
    return 0
    
def entry_point(args):
    params = ecsub.submit.set_param(args)
    return main(params)
    
if __name__ == "__main__":
    pass
