# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 15:06:50 2018

@author: Okada
"""

import subprocess
import json
import sys
import os
import datetime
import boto3
import ecsub.ansi
import ecsub.aws_config

class Aws_ecsub_control:

    def __init__(self, params):
        
        self.aws_accountid = self._get_aws_account_id()
        self.aws_region = self._get_region()

        self.aws_key_auto = None
        self.aws_key_name = params["aws_key_name"]
        self.aws_security_group_id = params["aws_security_group_id"]
        
        self.wdir = params["wdir"].rstrip("/")
        self.cluster_name = params["cluster_name"]
        self.set_cmd = params["set_cmd"]

        self.aws_ami_id = ecsub.aws_config.AMI_ID[self.aws_region]
        self.aws_ec2_instance_type = params["aws_ec2_instance_type"]
        self.aws_ec2_instance_cpu = ecsub.aws_config.INSTANCE_TYPE[params["aws_ec2_instance_type"]]["vcpu"]
        self.aws_ec2_instance_memory = ecsub.aws_config.INSTANCE_TYPE[params["aws_ec2_instance_type"]]["memory"]
        self.aws_ec2_instance_disk_size = params["aws_ec2_instance_disk_size"]
        self.image = params["image"]

        self.task_definition_arn = ""
        self.cluster_arn = ""

        self.s3_runsh = ""
        self.s3_script = ""
        self.s3_setenv = []

    def _subprocess_communicate (self, cmd):
        responce = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
        if type(responce) == type(b''):
            return responce.decode('ascii')
        return responce
        
    def _subprocess_call (self, cmd, no = None):
        def __subprocess_call (cmd):

            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            while True:
                line = proc.stdout.readline()
                if line:
                    if type(line) == type(b''):
                        line = line.decode('ascii')
                    yield line

                if not line and proc.poll() is not None:
                    break

        for line in __subprocess_call(cmd):
            if no != None:
                line = ecsub.ansi.colors.paint("[%s:%03d]" % (self.cluster_name, no), ecsub.ansi.colors.roll_list[no % len(ecsub.ansi.colors.roll_list)]) + line
            else:
                line = "[%s]" % (self.cluster_name) + line
                
            if len(line.rstrip()) > 0:
                sys.stdout.write(line)

    def _message (self, no, messages):
        
        text = "[%s]" % (self.cluster_name)
        if no != None:     
            text = ecsub.ansi.colors.paint("[%s:%03d]" % (self.cluster_name, no), ecsub.ansi.colors.roll_list[no % len(ecsub.ansi.colors.roll_list)])

        for m in messages:
            if "color" in m.keys():
                text += ecsub.ansi.colors.paint(m["text"], m["color"])
            else:
                text += m["text"]

        return text

    def _warning_message (self, no, text):
        return self._message (no, [{"text": " [WARNING] %s" % (text), "color": ecsub.ansi.colors.WARNING}])

    def _error_message (self, no, text):
        return self._message (no, [{"text": " [ERROR] %s" % (text), "color": ecsub.ansi.colors.FAIL}])

    def _info_message (self, no, text):
        return self._message (no, [{"text": " %s" % (text)}])
        
    def check_inputfiles(self, tasks):

        for task in tasks["tasks"]:
            for i in range(len(task)):
                if tasks["header"][i]["type"] != "input":
                    continue
                #cmd_template = "{set_cmd}; aws s3 ls {path}"
                cmd_template = "aws s3 ls {path}"
                cmd = cmd_template.format(set_cmd = self.set_cmd, path = task[i].rstrip("/"))
                responce = self._subprocess_communicate(cmd)

                if responce == "":
                    print(self._error_message (None, "s3-path '%s' is invalid." % (task[i])))
                    return False

                find = False
                for r in responce.split("\n"):
                    if r.split(" ")[-1].rstrip("/") == os.path.basename(task[i].rstrip("/")):
                        find = True
                        break
                if find == False:
                    print(self._error_message (None, "s3-path '%s' is invalid." % (task[i])))
                    return False
        return True

    def s3_copy(self, src, dst, recursive):

        cmd_template = "{set_cmd}; aws s3 cp --only-show-errors {r_option} {file1} {file2}"

        r_option = ""
        if recursive:
            r_option = "--recursive"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            file1 = src,
            file2 = dst,
            r_option = r_option
        )
        self._subprocess_call(cmd)
        return True

    def set_s3files(self, s3_runsh, s3_script, s3_setenv):
        self.s3_runsh = s3_runsh
        self.s3_script = s3_script
        self.s3_setenv.extend(s3_setenv)

    def _log_path (self, name):
        return "%s/log/%s.log" % (self.wdir, name)

    def _conf_path (self, name):
        return "%s/conf/%s" % (self.wdir, name)

    def _get_aws_account_id(self):
        responce = self._subprocess_communicate("aws sts get-caller-identity")
        return json.loads(responce)["Account"]

    def _get_region(self):
        responce = self._subprocess_communicate("aws configure get region")
        return responce.rstrip("\n")

    def _json_load(self, json_file):
        try:
            obj = json.load(open(json_file))
        except Exception as e:
            print(self._error_message (None, e))
            return None
        return obj
        
    def _check_keypair (self, aws_key_name):
        try:
            responce = boto3.client('ec2').describe_key_pairs(KeyNames=[aws_key_name])
            if len(responce["KeyPairs"]) > 0:
                return True
        except Exception as e:
            print(self._error_message (None, e))
            
        return False  
        
    def set_keypair(self):
        if self.aws_key_name != "":
            if self._check_keypair(self.aws_key_name):
                self.aws_key_auto = False
                return True

        log_file = self._log_path("create-key-pair")
        cmd_template = "{set_cmd}; aws ec2 create-key-pair --key-name {key_name} > {log}"
        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            key_name = self.cluster_name,
            log = log_file
        )
        self._subprocess_call(cmd)
        if self._check_keypair(self.cluster_name):
            self.aws_key_name = self.cluster_name
            self.aws_key_auto = True
            return True
        
        print(self._error_message (None, "Failure to create key pair."))
        return False
        
    def set_security_group(self):
        
        if self.aws_security_group_id != "":
            try:
                responce = boto3.client('ec2').describe_security_groups(GroupIds=[self.aws_security_group_id])
                if len(responce['SecurityGroups']) > 0:
                    return True
            except Exception:
                pass
            print(self._error_warning (None, "SecurityGroupId '%s' is invalid." % (self.aws_security_group_id)))
            
        try:
            responce = boto3.client('ec2').describe_security_groups(GroupNames=["default"])
            if len(responce['SecurityGroups']) > 0:
                self.aws_security_group_id =responce['SecurityGroups'][0]['GroupId']
                return True
        except Exception:
            pass

        print(self._error_message (None, "Default SecurityGroupId is not exist."))
        return False
        
    def create_cluster(self):

        # set key-pair
        if self.set_keypair() == False:
            return False
        
        # set security-group
        if self.set_security_group() == False:
            return False

        log_file = self._log_path("create-cluster")

        cmd_template = "{set_cmd}; aws ecs create-cluster --cluster-name {cluster_name} > {log}"
        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            cluster_name = self.cluster_name,
            log = log_file
        )
        self._subprocess_call(cmd)
        log = self._json_load(log_file)

        self.cluster_arn = log["cluster"]["clusterArn"]
        return True

    def register_task_definition(self):

        ECSTASKROLE = "arn:aws:iam::{AWS_ACCOUNTID}:role/AmazonECSTaskS3FullAccess".format(
            AWS_ACCOUNTID = self.aws_accountid)
        IMAGE_ARN = "{AWS_ACCOUNTID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{IMAGE_NAME}".format(
            AWS_ACCOUNTID = self.aws_accountid,
            AWS_REGION = self.aws_region,
            IMAGE_NAME = self.image)

        print(self._info_message (None, "ECSTASKROLE: %s" % (ECSTASKROLE)))
        print(self._info_message (None, "IMAGE_ARN: %s" % (IMAGE_ARN)))
        
        containerDefinitions = {
            "containerDefinitions": [
                {
                    "name": self.cluster_name + "_task",
                    "image": IMAGE_ARN,
                    "cpu": self.aws_ec2_instance_cpu,
                    "memory": self.aws_ec2_instance_memory,
                    "essential": True,
                      "entryPoint": [
                          "/bin/bash",
                          "-c"
                      ],
                      "command": [
                          "apt install -y python-pip; pip install awscli --upgrade; aws configure list; aws s3 cp " + self.s3_runsh + " /exec.sh; /bin/bash /exec.sh"
                      ],
                      "environment": [
                          {
                              "name": "SCRIPT_EXEC_PATH",
                              "value": self.s3_script
                          },
                          {
                              "name": "SCRIPT_ENVM_PATH",
                              "value": ""
                          }
                      ],
                      "logConfiguration": {
                          "logDriver": "awslogs",
                          "options": {
                              "awslogs-group": self.cluster_name,
                              "awslogs-region": self.aws_region,
                              "awslogs-stream-prefix": "ecsub"
                          }
                      }
                }
            ],
            "taskRoleArn": ECSTASKROLE,
            "family": self.cluster_name
        }

        json_file = self._conf_path("task_definition.json")
        json.dump(containerDefinitions, open(json_file, "w"), indent=4, separators=(',', ': '))

        # check exists ECS cluster
        cmd_template = "aws logs describe-log-groups --log-group-name-prefix {cluster_name} | grep logGroupName | grep \"{cluster_name}\" | wc -l"
        cmd = cmd_template.format(set_cmd = self.set_cmd, cluster_name = self.cluster_name)
        responce = self._subprocess_communicate(cmd)
        
        if int(responce) == 0:
            cmd_template = "{set_cmd}; aws logs create-log-group --log-group-name {cluster_name}"
            cmd = cmd_template.format(set_cmd = self.set_cmd, cluster_name = self.cluster_name)
            self._subprocess_call(cmd)

        #  register-task-definition
        log_file = self._log_path("register-task-definition")
        cmd_template = "{set_cmd}; aws ecs register-task-definition --cli-input-json file://{json} > {log}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            json = json_file,
            log = log_file
        )
        self._subprocess_call(cmd)
        log = self._json_load(log_file)
        self.task_definition_arn = log["taskDefinition"]["taskDefinitionArn"]

        return True

    def run_instances (self, no):

        sh_file = self._conf_path("userdata.sh")
        open(sh_file, "w").write("""Content-Type: multipart/mixed; boundary="==BOUNDARY=="
MIME-Version: 1.0

--==BOUNDARY==
Content-Type: text/cloud-boothook; charset="us-ascii"

# Install nfs-utils
cloud-init-per once yum_update yum update -y
cloud-init-per once install_nfs_utils yum install -y nfs-utils

cloud-init-per once docker_options echo 'OPTIONS="${{OPTIONS}} --storage-opt dm.basesize={disk_size}G"' >> /etc/sysconfig/docker

#!/bin/bash
# Set any ECS agent configuration options
echo "ECS_CLUSTER={cluster_arn}" >> /etc/ecs/ecs.config

--==BOUNDARY==--
""".format(cluster_arn = self.cluster_arn, disk_size = self.aws_ec2_instance_disk_size))

        log_file = self._log_path("run-instances.%03d" % (no))

        block_device_mappings = [{
            "DeviceName":"/dev/xvdcz",
            "Ebs": {
                "VolumeSize":self.aws_ec2_instance_disk_size,
                "DeleteOnTermination":True
            }
        }]
        json_file = self._conf_path("block_device_mappings.json")
        json.dump(block_device_mappings, open(json_file, "w"), indent=4, separators=(',', ': '))

        cmd_template = "{set_cmd};" \
            + "aws ec2 run-instances" \
            + " --image-id {AMI_ID}" \
            + " --security-group-ids {SECURITYGROUPID}" \
            + " --key-name {KEY_NAME}" \
            + " --user-data file://{userdata}" \
            + " --iam-instance-profile Name=ecsInstanceRole" \
            + " --instance-type {instance_type}" \
            + " --block-device-mappings file://{json}" \
            + " --count 1" \
            + " > {log}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            AMI_ID = self.aws_ami_id,
            SECURITYGROUPID = self.aws_security_group_id,
            KEY_NAME = self.aws_key_name,
            instance_type = self.aws_ec2_instance_type,
            json = json_file,
            INDEX = no,
            userdata = sh_file,
            log = log_file
        )
        self._subprocess_call(cmd, no)
        log = self._json_load(log_file)
        instance_id = log["Instances"][0]["InstanceId"]
        
        cmd_template = "{set_cmd}; aws ec2 wait instance-running --instance-ids {INSTANCE_ID}"
        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            INSTANCE_ID = instance_id
        )
        self._subprocess_call(cmd, no)

        cmd_template = "{set_cmd}; aws ec2 wait instance-status-ok --include-all-instances --instance-ids {INSTANCE_ID}"
        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            INSTANCE_ID = instance_id
        )
        self._subprocess_call(cmd, no)

        for i in range(3):
            responce = boto3.client("ec2").describe_instance_status(InstanceIds=[instance_id])
            if responce['InstanceStatuses'][0]['InstanceStatus']['Status'] == "ok":
                return True
            self._subprocess_call(cmd, no)

        print(self._error_message (None, "Failure run instance."))
        return False

    def run_task (self, no):

        # run-task
        containerOverrides = {
            "containerOverrides": [
                {
                    "name": self.cluster_name + "_task",
                    "environment": [
                        {
                            "name": "SCRIPT_ENVM_PATH",
                            "value": self.s3_setenv[no]
                        }
                    ]
            }]
        }

        overrides = self._conf_path("containerOverrides.%03d.json" % (no))
        json.dump(containerOverrides, open(overrides, "w"), indent=4, separators=(',', ': '))

        log_file = self._log_path("run-task.%03d" % (no))

        cmd_template = "{set_cmd}; " \
            + "aws ecs run-task --cluster {CLUSTER_ARN}" \
            + " --task-definition {TASK_DEFINITION_ARN}" \
            + " --overrides file://{OVERRIDES} > {log}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            CLUSTER_ARN = self.cluster_arn,
            TASK_DEFINITION_ARN = self.task_definition_arn,
            OVERRIDES = overrides,
            log = log_file
        )
        self._subprocess_call(cmd, no)

        # run-task error print
        log = self._json_load(log_file)
        if log["tasks"] == []:
            print (self._error_message (no, "failures: %s" % (json.dumps(log["failures"]))))
            if log["failures"][0]["reason"] == "RESOURCE:MEMORY":
                responce2 = boto3.client('ecs').describe_container_instances(cluster=self.cluster_arn, containerInstances=[log["failures"][0]["arn"]])
                for resouce in responce2['containerInstances'][0]['remainingResources']:
                    if resouce["name"] == "MEMORY":
                        print (self._error_message (no, "remainingResources(MEMORY): %d" % (resouce["integerValue"])))
                        break
            return None

        # get instance-ID from task-ID
        task_arn = log["tasks"][0]["taskArn"]
        containerInstanceArn = log["tasks"][0]["containerInstanceArn"]

        log_file = self._log_path("describe-container-instances.%03d" % (no))

        cmd_template = "aws ecs describe-container-instances" \
            + " --container-instances {containerInstanceArn}" \
            + " --cluster {CLUSTER_ARN} > {log}"

        cmd = cmd_template.format(
            CLUSTER_ARN = self.cluster_arn,
            containerInstanceArn = containerInstanceArn,
            log = log_file
        )
        self._subprocess_call(cmd, no)
        log = self._json_load(log_file)
        ec2InstanceId = log["containerInstances"][0]["ec2InstanceId"]

        # get log-path
        log_html_template = "https://{region}.console.aws.amazon.com/cloudwatch/home" \
            + "?region={region}#logEventViewer:group={cluster_name};stream=ecsub/{cluster_name}_task/{task_id}"

        log_html = log_html_template.format(
            region = self.aws_region,
            cluster_name = self.cluster_name,
            task_id = task_arn.split("/")[1]
        )
        print (self._message (no, [{"text": " For detail, see log-file: "}, {"text": log_html, "color": ecsub.ansi.colors.CYAN}]))

        # set Name to instance
        cmd_template = "{set_cmd};aws ec2 create-tags --resources {INSTANCE_ID} --tags Key=Name,Value={cluster_name}.{I}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            INSTANCE_ID = ec2InstanceId,
            cluster_name = self.cluster_name,
            I = no,
        )
        self._subprocess_call(cmd, no)

        # wait to task-stop
        cmd_template = "{set_cmd};aws ecs wait tasks-stopped --tasks {TASK_ARN} --cluster {CLUSTER_ARN}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            CLUSTER_ARN = self.cluster_arn,
            TASK_ARN = task_arn,
        )
        self._subprocess_call(cmd, no)

        responce = boto3.client('ecs').describe_tasks(
            cluster=self.cluster_arn,
            tasks=[task_arn]
        )
        while True:
            if responce["tasks"][0]['lastStatus'] != "RUNNING":
                break

            self._subprocess_call(cmd, no)
            responce = boto3.client('ecs').describe_tasks(
                cluster=self.cluster_arn,
                tasks=[task_arn]
            )

        # check exit code
        log_file = self._log_path("describe-tasks.%03d" % (no))

        responce["tasks"][0]["log"] = log_html
        responce["tasks"][0]["instance_type"] = self.aws_ec2_instance_type
        responce["tasks"][0]["disk_size"] = self.aws_ec2_instance_disk_size
        responce["tasks"][0]["no"] = no
        responce["tasks"][0]["log_local"] = log_file

        def support_datetime_default(o):
            if isinstance(o, datetime.datetime):
                return '%04d/%02d/%02d %02d:%02d:%02d %s' % (o.year, o.month, o.day, o.hour, o.minute, o.second, o.tzname())
            raise TypeError(repr(o) + " is not JSON serializable")

        json.dump(responce, open(log_file, "w"), default=support_datetime_default, indent=4, separators=(',', ': '))

        exit_code = responce["tasks"][0]["containers"][0][u'exitCode']
        if exit_code == 0:
            print (self._info_message (no, "tasks-stopped with [0]"))
        else:
            print (self._error_message (no, "tasks-stopped with [%d], %s" % (exit_code, responce["tasks"][0]["stoppedReason"])))

        return ec2InstanceId

    def terminate_instances (self, no, instance_id):

        log_file = self._log_path("terminate-instances")
        if no != None:
            log_file = self._log_path("terminate-instances.%03d" % (no))

        cmd_template = "{set_cmd};" \
            + "aws ec2 terminate-instances --instance-ids {ec2InstanceId} > {log};" \
            + "aws ec2 wait instance-terminated --instance-ids {ec2InstanceId}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            log = log_file,
            ec2InstanceId = instance_id
        )
        self._subprocess_call(cmd, no)

    def clean_up (self):

        # delete cluster
        if self.cluster_arn != "":
            responce = boto3.client('ecs').list_container_instances(cluster=self.cluster_arn)
            if len(responce['containerInstanceArns']):
                responce2 = boto3.client('ecs').describe_container_instances(cluster=self.cluster_arn, containerInstances=responce['containerInstanceArns'])
                instance_ids = ""
                for instance in responce2['containerInstances']:
                    instance_ids += instance['ec2InstanceId'] + " "
                self.terminate_instances (None, instance_ids)
        
            responce = boto3.client('ecs').describe_clusters(clusters=[self.cluster_arn])
            if len(responce["clusters"]) > 0:
                cmd_template = "{set_cmd}; aws ecs delete-cluster --cluster {cluster} > {log}"
                cmd = cmd_template.format(
                    set_cmd = self.set_cmd,
                    cluster = self.cluster_arn,
                    log = self._log_path("delete-cluster")
                )
                self._subprocess_call(cmd)

        # delete task definition
        if self.task_definition_arn != "":
            try:
                responce = boto3.client('ecs').describe_task_definition(taskDefinition=self.task_definition_arn)

                cmd_template = "{set_cmd}; aws ecs deregister-task-definition --task-definition {task} > {log}"
                cmd = cmd_template.format(
                    set_cmd = self.set_cmd,
                    task = self.task_definition_arn,
                    log = self._log_path("deregister-task-definition")
                )
                self._subprocess_call(cmd)
            except Exception:
                pass

        # delete ssh key pair
        if self.aws_key_auto:
            cmd_template = "{set_cmd}; aws ec2 delete-key-pair --key-name {key_name} > {log}"
            cmd = cmd_template.format(
                set_cmd = self.set_cmd,
                key_name = self.aws_key_name,
                log = self._log_path("delete-key-pair")
            )
            self._subprocess_call(cmd)
