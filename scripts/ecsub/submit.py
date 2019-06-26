# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 13:06:19 2018

@author: Okada
"""

import os
import shutil
import multiprocessing
import string
import random
import datetime
import time
import ecsub.aws
import ecsub.aws_config
import ecsub.tools
import ecsub.metrics
import ecsub.pre_submit
import ecsub.params

class Submit:

    def __init__(self):
        self.aws_instance = None
        self.log_fp = None
        
        self.fly_away = False
        
    def _run_task(self, no, instance_id):
        
        system_error = False
        exit_code = 1
        task_log = None
        
        try:
            (exit_code, task_log) = self.aws_instance.run_task(no, instance_id)
            if exit_code == 127:
                system_error = True
        
        except Exception as e:
            ecsub.tools.error_message (self.aws_instance.cluster_name, no, e, self.log_fp)
        
        if not self.fly_away:
            self.aws_instance.terminate_instances(instance_id, no)
        
        return (exit_code, task_log, system_error)
    
    def submit_task_ondemand(self, no):
        
        exit_code = 1
        task_log = None
        
        if not self.aws_instance.set_ondemand_price(no):
            return (exit_code, task_log)
        
        for i in range(3):
            instance_id = self.aws_instance.run_instances_ondemand (no)
            if instance_id == None:
                break
            
            (exit_code, task_log, system_error) = self._run_task(no, instance_id)
                
            if system_error:
                continue
            else:
                return (exit_code, task_log)
            
        return (exit_code, task_log)
    
    def submit_task_spot(self, no):
    
        exit_code = 1
        task_log = None
        
        for itype in self.aws_instance.aws_ec2_instance_type_list:
            
            self.aws_instance.task_param[no]["aws_ec2_instance_type"] = itype
            
            if not self.aws_instance.set_ondemand_price(no):
                continue
            if not self.aws_instance.set_spot_price(no):
                continue
            
            for i in range(3):
                instance_id = self.aws_instance.run_instances_spot (no)
                if instance_id == None:
                    break
    
                (exit_code, task_log, system_error) = self._run_task( no, instance_id)
                
                if not self.fly_away:
                    self.aws_instance.cancel_spot_instance_requests (no = no, instance_id = instance_id)
                    
                if system_error:
                    continue
                elif exit_code == -1:
                    break
                else:
                    return (exit_code, task_log, False)
        
        return (exit_code, task_log, True)
    
    def submit_task(self, no, task_params, spot):
        
        job_summary = {
            "AccountId": self.aws_instance.aws_accountid,
            "AmiId": self.aws_instance.aws_ami_id,
            "AutoKey": self.aws_instance.aws_key_auto,
            "ClusterName": self.aws_instance.cluster_name,
            "ClusterArn": self.aws_instance.cluster_arn,
            "Ec2InstanceDiskSize": self.aws_instance.aws_ec2_instance_disk_size,
            "End": None,
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
            "TaskDefinitionAn": self.aws_instance.task_definition_arn,
            "UseAmazonEcr": self.aws_instance.use_amazon_ecr,
            "Wdir": self.aws_instance.wdir,
            "Jobs":[]
        }
        ecsub.params.save_summary_file(job_summary)
    
        if spot:
            start_t = datetime.datetime.now()
            (exit_code, task_log, retry) = self.submit_task_spot(no)
            job_summary["Jobs"].append(ecsub.params.set_job_info(
                self.aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
            ))
            
            if self.aws_instance.retry_od and retry:
                start_t = datetime.datetime.now()
                self.aws_instance.task_param[no]["aws_ec2_instance_type"] = self.aws_instance.aws_ec2_instance_type_list[0]
                (exit_code, task_log) = self.submit_task_ondemand(no)
                job_summary["Jobs"].append(ecsub.params.set_job_info(
                    self.aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
                ))
        else:
            start_t = datetime.datetime.now()
            (exit_code, task_log) = self.submit_task_ondemand(no)
            job_summary["Jobs"].append(ecsub.params.set_job_info(
                self.aws_instance.task_param[no], start_t, datetime.datetime.now(), task_log, exit_code
            ))
        
        job_summary["SubnetId"] = self.aws_instance.aws_subnet_id
        job_summary["End"] = ecsub.tools.datetime_to_standardformat(datetime.datetime.now())
        
        files = ecsub.metrics.entry_point(self.aws_instance.wdir, no)
        for metrics_file in files:
            s3_file = "" % (task_params. os.basename(metrics_file))
            self.aws_instance.s3_copy(metrics_file, s3_file, False, no)
            
        ecsub.params.save_summary_file(job_summary, print_cost = True, log_fp = self.log_fp)
        exit (exit_code)

    def preparation(self, params):
        
        # set cluster_name
        params["cluster_name"] = params["task_name"]
        if params["cluster_name"] == "":
            params["cluster_name"] = os.path.splitext(os.path.basename(params["tasks"]))[0] \
                + '-' \
                + ''.join([random.choice(string.ascii_letters + string.digits) for i in range(5)])
                
        # check param
        instance_type_list = params["aws_ec2_instance_type_list"].replace(" ", "")
        if len(instance_type_list) == 0:
            params["aws_ec2_instance_type_list"] = [params["aws_ec2_instance_type"]]
        else:
            params["aws_ec2_instance_type_list"] = instance_type_list.split(",")
            
        if params["aws_ec2_instance_type"] != "":
            pass
                
        elif len(params["aws_ec2_instance_type_list"]) > 0:
            if not params["spot"]:
                ecsub.tools.error_message (params["cluster_name"], None, "--aws-ec2-instance-type-list option is not support with ondemand-instance mode.", self.log_fp)
                return None
            
        else:
            ecsub.tools.error_message (params["cluster_name"], None, "One of --aws-ec2-instance-type option and --aws-ec2-instance-type-list option is required.", self.log_fp)
            return None
        
        # "request_payer": 
        request_payer = params["request_payer"].replace(" ", "")
        if len(request_payer) == 0:
            params["request_payer"] = []
        else:
            params["request_payer"] = request_payer.split(",")
            
        # read tasks file
        task_params = ecsub.pre_submit.read_tasksfile(params["tasks"], params["cluster_name"])
        if task_params == None:
            return None
        
        if task_params["tasks"] == []:
            ecsub.tools.info_message (params["cluster_name"], None, "task file is empty.", self.log_fp)
            return task_params
        
        subdir = params["cluster_name"]
        
        params["wdir"] = params["wdir"].rstrip("/") + "/" + subdir
        params["aws_s3_bucket"] = params["aws_s3_bucket"].rstrip("/") + "/" + subdir
        
        if os.path.exists (params["wdir"]):
            shutil.rmtree(params["wdir"])
            ecsub.tools.info_message (params["cluster_name"], None, "'%s' existing directory was deleted." % (params["wdir"]), self.log_fp)
            
        os.makedirs(params["wdir"])
        os.makedirs(params["wdir"] + "/log")
        os.makedirs(params["wdir"] + "/conf")
        os.makedirs(params["wdir"] + "/script")
    
        params["fly_away"] = self.fly_away
        self.aws_instance = ecsub.aws.Aws_ecsub_control(params, len(task_params["tasks"]), self.log_fp)
        
        # check task-param
        if not self.aws_instance.check_awsconfigure():
            return None
    
        # check s3-files path
        (regions, invalid_pathes) = ecsub.pre_submit.check_inputfiles(self.aws_instance, task_params, params["cluster_name"], params["request_payer"], params["aws_s3_bucket"])
        if len(regions) > 1:
            if params["ignore_location"]:
                ecsub.tools.warning_message (params["cluster_name"], None, "your task uses multipule regions '%s'." % (",".join(regions)), self.log_fp)
            else:
                ecsub.tools.error_message (params["cluster_name"], None, "your task uses multipule regions '%s'." % (",".join(regions)), self.log_fp)
                return None
            
        for r in invalid_pathes:
            ecsub.tools.error_message (params["cluster_name"], None, "input '%s' is not access." % (r), self.log_fp)
        if len(invalid_pathes)> 0:
            return None
        
        # write task-scripts, and upload to S3
        local_script_dir = params["wdir"] + "/script"
        s3_script_dir = params["aws_s3_bucket"].rstrip("/") + "/script"
        if not ecsub.pre_submit.upload_scripts(task_params, 
                       self.aws_instance, 
                       local_script_dir, 
                       s3_script_dir,
                       params["script"],
                       params["cluster_name"],
                       params["shell"],
                       params["request_payer"]):
            ecsub.tools.error_message (params["cluster_name"], None, "failure upload files to s3 bucket: %s." % (params["aws_s3_bucket"]), self.log_fp)
            return None
        
        return task_params
    
    def run_procs(self, params, task_params):
        
        # run purocesses
        process_list = []
        
        try:
            # create-cluster
            # and register-task-definition
            if not self.aws_instance.create_cluster():
                self.aws_instance.clean_up()
                return 1
            if not self.aws_instance.register_task_definition():
                self.aws_instance.clean_up()
                return 1
            
            while len(process_list) < len(task_params["tasks"]):
                alives = 0
                for process in process_list:
                    if process.exitcode == None:
                       alives += 1
                        
                jobs = params["processes"] - alives
                submitted = len(process_list)
                
                for i in range(jobs):
                    no = i + submitted
                    if no >= len(task_params["tasks"]):
                        break
                        
                    process = multiprocessing.Process(
                            target = self.submit_task, 
                            name = "%s_%03d" % (params["cluster_name"], no), 
                            args = ((no, task_params, params["spot"]))
                    )
                    process.daemon == True
                    process.start()
                    
                    process_list.append(process)
                    
                    time.sleep(5)
                
                time.sleep(5)
            
            exitcodes = []
            for process in process_list:
                process.join()
                if process.exitcode != None:
                    exitcodes.append(process.exitcode)
            
            if not self.fly_away:
                self.aws_instance.clean_up()
                
            # SUCCESS?
            if [0] == list(set(exitcodes)):
                return 0
            
        except Exception as e:
            ecsub.tools.error_message (params["cluster_name"], None, e, self.log_fp)
            for process in process_list:
                process.terminate()
                    
            self.aws_instance.clean_up()
            
        except KeyboardInterrupt:
            print ("KeyboardInterrupt")
            for process in process_list:
                process.terminate()
                
            self.aws_instance.clean_up()
        
        return 1
    
    def main(self, params):
        task_params =  self.preparation(params)
        if task_params == None:
            return 1
        
        if task_params["tasks"] == []:
            return 0
        
        return self.run_procs(params, task_params)
        
    
def entry_point(args, unknown_args):
    
    submit_instance = Submit()
    return submit_instance.main(ecsub.params.args_to_obj(args))
    
if __name__ == "__main__":
    pass
