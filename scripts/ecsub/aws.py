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
import ecsub.tools
import glob

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
        self.shell = params["shell"]
        self.log_group_name = "ecsub-" + self.cluster_name
        
        #self.aws_ami_id = ecsub.aws_config.AMI_ID[self.aws_region]
        self.aws_ami_id = ecsub.aws_config.get_ami_id()
        self.aws_ec2_instance_type = params["aws_ec2_instance_type"]
        self.aws_ecs_task_vcpu = params["aws_ecs_task_vcpu"]
        self.aws_ecs_task_memory = params["aws_ecs_task_memory"]
        
        self.aws_ec2_instance_disk_size = params["aws_ec2_instance_disk_size"]
        self.aws_subnet_id = params["aws_subnet_id"]
        self.image = params["image"]
        self.use_amazon_ecr = params["use_amazon_ecr"]
        
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
                line = ecsub.tools.info_message (self.cluster_name, None, line)
                #line = "[%s]" % (self.cluster_name) + line
                
            if len(line.rstrip()) > 0:
                sys.stdout.write(line)

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
                    print(ecsub.tools.error_message (self.cluster_name, None, "s3-path '%s' is invalid." % (task[i])))
                    return False

                find = False
                for r in responce.split("\n"):
                    if r.split(" ")[-1].rstrip("/") == os.path.basename(task[i].rstrip("/")):
                        find = True
                        break
                if find == False:
                    print(ecsub.tools.error_message (self.cluster_name, None, "s3-path '%s' is invalid." % (task[i])))
                    return False
        return True

    def check_roles(self):
    
        def _check_role(role_name, service, cluster_name):
            result = False
            try:
                responce = boto3.client('iam').get_role(RoleName = role_name)
                if responce["Role"]["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]["Service"] == service:
                    result = True

            except Exception as e:
                print(ecsub.tools.error_message (cluster_name, None, e))
                
            return result
        
        def _check_policy(policy_arn, cluster_name):
            result = False
            try:
                responce = boto3.client('iam').get_policy(PolicyArn = policy_arn)
                if responce["Policy"]["IsAttachable"]:
                    result = True
                    
            except Exception as e:
                print(ecsub.tools.error_message (cluster_name, None, e))
                
            return result
            
        result = True
        if not _check_role("AmazonECSTaskS3FullAccess", "ecs-tasks.amazonaws.com", self.cluster_name):
        
            result = False
            
        if not _check_role("ecsInstanceRole", "ec2.amazonaws.com", self.cluster_name):
            result = False

        return result
    
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
            print(ecsub.tools.error_message (self.cluster_name, None, e))
            return None
        return obj
        
    def _check_keypair (self, aws_key_name):
        try:
            responce = boto3.client('ec2').describe_key_pairs(KeyNames=[aws_key_name])
            if len(responce["KeyPairs"]) > 0:
                return True
        except Exception as e:
            print(ecsub.tools.error_message (self.cluster_name, None, e))
            
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
        
        print(ecsub.tools.error_message (self.cluster_name, None, "Failure to create key pair."))
        return False
        
    def set_security_group(self):
        
        if self.aws_security_group_id != "":
            try:
                responce = boto3.client('ec2').describe_security_groups(GroupIds=[self.aws_security_group_id])
                if len(responce['SecurityGroups']) > 0:
                    return True
            except Exception:
                pass
            print(ecsub.tools.warning_message (self.cluster_name, None, "SecurityGroupId '%s' is invalid." % (self.aws_security_group_id)))
            
        try:
            responce = boto3.client('ec2').describe_security_groups(GroupNames=["default"])
            if len(responce['SecurityGroups']) > 0:
                self.aws_security_group_id =responce['SecurityGroups'][0]['GroupId']
                return True
        except Exception:
            pass

        print(ecsub.tools.error_message (self.cluster_name, None, "Default SecurityGroupId is not exist."))
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

        ECSTASKROLE = "arn:aws:iam::{AWS_ACCOUNTID}:role/ecsInstanceRole".format(
            AWS_ACCOUNTID = self.aws_accountid)

        IMAGE_ARN = self.image
        if self.use_amazon_ecr:
            IMAGE_ARN = "{AWS_ACCOUNTID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{IMAGE_NAME}".format(
                AWS_ACCOUNTID = self.aws_accountid,
                AWS_REGION = self.aws_region,
                IMAGE_NAME = self.image)

        print(ecsub.tools.info_message (self.cluster_name, None, "ECSTASKROLE: %s" % (ECSTASKROLE)))
        print(ecsub.tools.info_message (self.cluster_name, None, "DOCKER_IMAGE: %s" % (IMAGE_ARN)))
        
        containerDefinitions = {
            "containerDefinitions": [
                {
                    "name": self.cluster_name + "_task",
                    "image": IMAGE_ARN,
                    "cpu": self.aws_ecs_task_vcpu,
                    "memory": self.aws_ecs_task_memory,
                    "essential": True,
                      "entryPoint": [
                          self.shell,
                          "-c"
                      ],
                      "command": [
                          "apt update; apt install -y python-pip; pip install awscli --upgrade; aws configure list; aws s3 cp " + self.s3_runsh + " /exec.sh; " + self.shell + " /exec.sh"
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
                              "awslogs-group": self.log_group_name,
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
        cmd_template = "aws logs describe-log-groups --log-group-name-prefix {log_group_name} | grep logGroupName | grep \"{log_group_name}\" | wc -l"
        cmd = cmd_template.format(set_cmd = self.set_cmd, log_group_name = self.log_group_name)
        responce = self._subprocess_communicate(cmd)
        
        if int(responce) == 0:
            cmd_template = "{set_cmd}; aws logs create-log-group --log-group-name {log_group_name}"
            cmd = cmd_template.format(set_cmd = self.set_cmd, log_group_name = self.log_group_name)
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
cloud-init-per once install_tr yum install -y tr
cloud-init-per once install_td yum install -y td
cloud-init-per once install_python27_pip yum install -y python27-pip
cloud-init-per once install_awscli pip install awscli

cloud-init-per once docker_options echo 'OPTIONS="${{OPTIONS}} --storage-opt dm.basesize={disk_size}G"' >> /etc/sysconfig/docker
cloud-init-per once ecs_option echo "ECS_CLUSTER={cluster_arn}" >> /etc/ecs/ecs.config

#!/bin/bash
# Set any ECS agent configuration options
# echo "ECS_CLUSTER={cluster_arn}" >> /etc/ecs/ecs.config

cat << EOF > /root/metricscript.sh
AWSREGION={region}
AWSINSTANCEID=\$(curl -ss http://169.254.169.254/latest/meta-data/instance-id)
ECS_CLUSTER_NAME=\$(cat /etc/ecs/ecs.config | grep ^ECS_CLUSTER | cut -d "/" -f 2)

function convertUnits {{

  unit=\$(echo \$1 | tr -d [0-9.] | tr '[:upper:]' '[:lower:]')
  value=\$(echo \$1 | tr -d [A-Za-z,])
  
  if [ "\$unit" == "b" ] ; then
    echo \$value
  elif [ "\$unit" == "kb" ] ; then
    awk 'BEGIN{{ printf "%.0f\\n", '\$value' * 1000 }}'
  elif [ "\$unit" == "mb" ] ; then
    awk 'BEGIN{{ printf "%.0f\\n", '\$value' * 1000**2 }}'
  elif [ "\$unit" == "gb" ] ; then
    awk 'BEGIN{{ printf "%.0f\\n", '\$value' * 1000**3 }}'
  elif [ "\$unit" == "tb" ] ; then
    awk 'BEGIN{{ printf "%.0f\\n", '\$value' * 1000**4 }}'
  else
    echo "Unknown unit \$unit"
    exit 1
  fi
}}

disk_used=\$(convertUnits \$(docker info | awk '/Data Space Used/ {{print \$4}}'))
disk_total=\$(convertUnits \$(docker info | awk '/Data Space Total/ {{print \$4}}'))
disk_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\$disk_used'*100/('\$disk_total') }}')
aws cloudwatch put-metric-data --value \$disk_util --namespace ECSUB --unit Percent --metric-name DataStorageUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

mem_used=\$(vmstat -s | grep "used memory" | sed s/^" "*/""/ | cut -f 1 -d " ")
mem_free=\$(vmstat -s | grep "free memory" | sed s/^" "*/""/ | cut -f 1 -d " ")
mem_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\$mem_used'*100/('\$mem_used'+'\$mem_free') }}')
aws cloudwatch put-metric-data --value \$mem_util --namespace ECSUB --unit Percent --metric-name MemoryUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

sts=(\$(vmstat | tail -n 1))
cpu_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\${{sts[12]}}'+'\${{sts[13]}}' }}')
aws cloudwatch put-metric-data --value \$cpu_util --namespace ECSUB --unit Percent --metric-name CPUUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME
EOF

chmod +x /root/metricscript.sh

cat << EOF > /etc/crontab
SHELL=/bin/bash
PATH=/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=
HOME=/
*/1 * * * * root /root/metricscript.sh
*/30 * * * * cat /dev/null > /var/spool/mail/root
EOF
--==BOUNDARY==--
""".format(cluster_arn = self.cluster_arn, disk_size = self.aws_ec2_instance_disk_size, region = self.aws_region))

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
        subnet_id = ""
        if self.aws_subnet_id != "":
            subnet_id = "--subnet-id %s" % (self.aws_subnet_id)

        cmd_template = "{set_cmd};" \
            + "aws ec2 run-instances" \
            + " --image-id {AMI_ID}" \
            + " --security-group-ids {SECURITYGROUPID}" \
            + " --key-name {KEY_NAME}" \
            + " --user-data file://{userdata}" \
            + " --iam-instance-profile Name=ecsInstanceRole" \
            + " --instance-type {instance_type}" \
            + " --block-device-mappings file://{json}" \
            + " --count 1 {subnet_id}" \
            + " > {log}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            AMI_ID = self.aws_ami_id,
            SECURITYGROUPID = self.aws_security_group_id,
            KEY_NAME = self.aws_key_name,
            subnet_id = subnet_id,
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

        print(ecsub.tools.error_message (self.cluster_name, None, "Failure run instance."))
        return False

    def _check_memory(self, log_file):
        log = self._json_load(log_file)
        if len(log["tasks"]) > 0:
            return (log, None)
        
        error_message = []
        error_message.append("failures: %s" % (json.dumps(log["failures"])))
        
        if log["failures"][0]["reason"] != "RESOURCE:MEMORY":
            return (None, error_message)
            
        responce2 = boto3.client('ecs').describe_container_instances(cluster=self.cluster_arn, containerInstances=[log["failures"][0]["arn"]])
        for resouce in responce2['containerInstances'][0]['remainingResources']:
            if resouce["name"] == "MEMORY":
                error_message.append("remainingResources(MEMORY): %d" % (resouce["integerValue"]))
        return (None, error_message)
               
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

        # retry run-task and error print
        (log, err_msg) = self._check_memory(log_file)
        if log == None:
            for msg in err_msg:
                print (ecsub.tools.warning_message (self.cluster_name, no, msg))
            
            log_file_retry = self._log_path("run-task-retry.%03d" % (no))
            cmd = cmd_template.format(
                set_cmd = self.set_cmd + "; sleep 10",
                CLUSTER_ARN = self.cluster_arn,
                TASK_DEFINITION_ARN = self.task_definition_arn,
                OVERRIDES = overrides,
                log = log_file_retry
            )
            self._subprocess_call(cmd, no)
            (log, err_msg) = self._check_memory(log_file_retry)
            if log == None:
                for msg in err_msg:
                    print (ecsub.tools.error_message (self.cluster_name, no, msg))
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
            + "?region={region}#logEventViewer:group={log_group_name};stream=ecsub/{cluster_name}_task/{task_id}"

        log_html = log_html_template.format(
            region = self.aws_region,
            cluster_name = self.cluster_name,
            log_group_name = self.log_group_name,
            task_id = task_arn.split("/")[1]
        )
        #print (ecsub.tools.message (self.cluster_name, no, [{"text": " For detail, see log-file: "}, {"text": log_html, "color": ecsub.ansi.colors.CYAN}]))
        print (ecsub.tools.message (self.cluster_name, no, [{"text": " For detail, see log-file: "}, {"text": log_html, "color": ecsub.tools.get_title_color(no)}]))

        # set Name to instance
        instanceName = "{cluster_name}.{I}".format(cluster_name = self.cluster_name, I = no)
        cmd_template = "{set_cmd};aws ec2 create-tags --resources {INSTANCE_ID} --tags Key=Name,Value={instanceName}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            INSTANCE_ID = ec2InstanceId,
            instanceName = instanceName
        )
        self._subprocess_call(cmd, no)
        json.dump(
            {"InstanceId": ec2InstanceId, "InstanceName": instanceName},
            open(self._log_path("create-tags.%03d" % (no)), "w")
        )
        
        # wait to task-stop
        cmd_template = "{set_cmd};aws ecs wait tasks-stopped --tasks {TASK_ARN} --cluster {CLUSTER_ARN}"

        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            CLUSTER_ARN = self.cluster_arn,
            TASK_ARN = task_arn
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
        
        exit_code = -1
        if "containers" in responce["tasks"][0]:
            if "exitCode" in responce["tasks"][0]["containers"][0]:
                exit_code = responce["tasks"][0]["containers"][0]["exitCode"]
                print (ecsub.tools.info_message (self.cluster_name, no, "tasks-stopped with [%d]" % (exit_code)))

            if "reason" in responce["tasks"][0]["containers"][0]:
                if exit_code != 0:
                    print (ecsub.tools.error_message (self.cluster_name, no, "An error occurred: %s" % (responce["tasks"][0]["containers"][0]["reason"])))

        if "stoppedReason" in responce["tasks"][0]:
            if exit_code != 0:
                print (ecsub.tools.error_message (self.cluster_name, no, "An error occurred: %s" % (responce["tasks"][0]["stoppedReason"])))

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
        # terminate instances
        instance_ids = []
        for log_file in glob.glob("%s/log/run-instances.*.log" % (self.wdir)):
            log = self._json_load(log_file)
            instance_ids.append(log["Instances"][0]["InstanceId"])
            
        if len(instance_ids) > 0:
            self.terminate_instances (None, " ".join(instance_ids))
        
        # delete cluster
        if self.cluster_arn != "":
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
