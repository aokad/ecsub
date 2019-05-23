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
import ecsub.submit

class FlyAway(ecsub.submit.Submit):

    def __init__(self):
        super.__init__()
        
        self.fly_away = True
    
    def take_off(self, args):
        
        params = ecsub.params.summary_to_obj(args.summary_path)   
        task_params =  self.preparation(params)
        if task_params == None:
            return 1
        
        if task_params["tasks"] == []:
            return 0
        
        return self.run_procs(params, task_params)
    
    def land_on(self, args):
    
        params = ecsub.params.summary_to_obj(args.summary_path)
        
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
            self.aws_instance.aws_key_auto = params["AutoKey"]
            self.aws_instance.cluster_arn = params["ClusterArn"]
            self.aws_instance.task_definition_arn = params["TaskDefinitionAn"]
            
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

def take_off(args):
    fa_instance = FlyAway()
    return fa_instance.take_off(args)

def land_on(args):
    fa_instance = FlyAway()
    return fa_instance.land_on(args)
    
if __name__ == "__main__":
    pass
