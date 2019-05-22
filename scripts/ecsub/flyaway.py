#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 22 12:11:29 2019

@author: aokada
"""

import datetime
import ecsub.aws
import ecsub.aws_config
import ecsub.tools
import ecsub.metrics
import ecsub.pre_submit

class FlyAway:

    def __init__(self):
        self.aws_instance = None
        self.log_fp = None

    def land_on(self, args):
    
        params = {
            "wdir": args.wdir,
            "task_name": args.task_name,
            "setx": "set -x"
        }
        
        import json
        summary = json.load(open(params["summary"]))
        params["aws_key_name"] = summary["KeyName"]
        params["aws_security_group_id"] = summary["SecurityGroupId"]
        params["cluster_name"] = summary["ClusterName"]
        params["shell"]  = summary["Shell"]
        params["aws_ec2_instance_disk_size"] = summary["Ec2InstanceDiskSize"]
        params["image"] = summary["Image"]
        params["use_amazon_ecr"] = summary["UseAmazonEcr"]
        params["spot"] = summary["Spot"]
        
        # no use
        params["aws_ec2_instance_type_list"] = ['']
        params["aws_ec2_instance_type"] = ""
        params["aws_subnet_id"] = ""
        params["retry_od"] = False
        params["request_payer"] = []
        params["setup_container_cmd"] = ""
        params["dind"] = False
        
        # TODO:
        # aws s3 download configure
        # determine instance_id from s3 uploaded items
        instance_id = "xxxxxxxxx"
        no = 0
        
        self.aws_instance = ecsub.aws.Aws_ecsub_control(params, 1)
        self.aws_instance.terminate_instances(instance_id, no)
        if params["spot"]:
            self.aws_instance.cancel_spot_instance_requests (no = no, instance_id = instance_id)
        
        if True:
            self.aws_instance.aws_key_auto = summary["AutoKey"]
            self.aws_instance.cluster_arn = summary["ClusterArn"]
            self.aws_instance.task_definition_arn = summary["TaskDefinitionAn"]
            
            self.aws_instance.clean_up()
        
        # TODO: get exit_code from AWS ECS
        exit_code = 0
        
        # TODO: get start_t from summary-file
        start_t = datetime.datetime.now()
        # TODO: get task_log from summary-file
        task_log = ""
        
        job_summary = {
            "AccountId": self.aws_instance.aws_accountid,
            "AmiId": self.aws_instance.aws_ami_id,
            "AutoKey": self.aws_instance.aws_key_auto,
            "ClusterName": self.aws_instance.cluster_name,
            "ClusterArn": self.aws_instance.cluster_arn,
            "Ec2InstanceDiskSize": self.aws_instance.aws_ec2_instance_disk_size,
            "End": ecsub.tools.datetime_to_standardformat(datetime.datetime.now()),
            "Image": self.aws_instance.image,
            "KeyName": self.aws_instance.aws_key_name,
            "LogGroupName": self.aws_instance.log_group_name,
            "No": no,
            "Region": self.aws_instance.aws_region,
            "RequestPayerBucket": self.aws_instance.request_payer,
            "S3RunSh": self.aws_instance.s3_runsh,
            "S3Script": self.aws_instance.s3_script,
            "S3Setenv": self.aws_instance.s3_setenv[no],
            "SecurityGroupId": self.aws_instance.aws_security_group_id,
            "Shell": self.aws_instance.shell,
            "Spot": self.aws_instance.spot,
            "Start": ecsub.tools.datetime_to_standardformat(datetime.datetime.now()),
            "SubnetId": self.aws_instance.aws_subnet_id,
            "TaskDefinitionAn": self.aws_instance.task_definition_arn,
            "UseAmazonEcr": self.aws_instance.use_amazon_ecr,
            "Wdir": self.aws_instance.wdir,
            "Jobs":[ecsub.pre_submit.set_job_info(
                        self.aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
                    )]
        }
        ecsub.pre_submit.save_summary_file(job_summary, False)
        
        ecsub.metrics.entry_point(self.aws_instance.wdir, no)
    
        # TODO: upload metrics and log files
        
        return 0
    
def entry_point(args):
    
    fa_instance = FlyAway()
    return fa_instance.land_on(args)
    
if __name__ == "__main__":
    pass
