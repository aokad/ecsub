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
import time
import boto3
import ecsub.ansi
import ecsub.aws_config
import ecsub.tools
import glob
import base64

class Aws_ecsub_control:

    def __init__(self, params, task_num):
        
        self.aws_accountid = params["aws_account_id"]
        if self.aws_accountid == "":
            self.aws_accountid = self._get_aws_account_id()
            
        self.aws_region = params["aws_region"]
        if self.aws_region == "":
            self.aws_region = self._get_region()

        self.aws_key_auto = None
        self.aws_key_name = params["aws_key_name"]
        self.aws_security_group_id = params["aws_security_group_id"]
        self.aws_ecs_instance_role_name = params['aws_ecs_instance_role_name']

        self.wdir = params["wdir"].rstrip("/")
        self.cluster_name = params["cluster_name"]
        self.setx = params["setx"]
        self.shell = params["shell"]
        self.setup_container_cmd = params["setup_container_cmd"]
        if self.setup_container_cmd == "":
            self.setup_container_cmd = "apt update; apt install -y python-pip; pip install awscli --upgrade; aws configure list"
        self.dind = params["dind"]
        self.log_group_name = params["aws_log_group_name"]
        if self.log_group_name == "":
            self.log_group_name = "ecsub-" + self.cluster_name
        
        self.aws_ami_id = ecsub.aws_config.get_ami_id()
        self.aws_ec2_instance_type_list = params["aws_ec2_instance_type_list"]
        
        self.aws_ecs_task_vcpu_default = 1
        self.aws_ecs_task_memory_default = 300
        self.disk_size = params["disk_size"]
        self.root_disk_size = params["root_disk_size"]
        self.aws_subnet_id = params["aws_subnet_id"]
        self.image = params["image"]
        self.use_amazon_ecr = params["use_amazon_ecr"]
        
        self.task_definition_arn = ""
        self.cluster_arn = ""

        self.s3_runsh = ""
        self.s3_script = ""
        self.s3_setenv = []
        self.s3_downloader = []
        self.s3_uploader = []
        self.request_payer_bucket = []
        self.request_payer_bucket.extend(params["request_payer_bucket"])
        
        self.spot = params["spot"]
        self.retry_od = params["retry_od"]
        
        self.task_param = []
        for i in range(task_num):
            self.task_param.append({
                "spot": params["spot"],
                "aws_ec2_instance_type": params["aws_ec2_instance_type_list"][0],
                "aws_subnet_id": "",
                "od_price": 0,
                "spot_az": "",
                "spot_price": 0,
            })
        
        self.flyaway = params["flyaway"]
        self.env_options = []
        if "env_options" in params:
            self.env_options.extend(params["env_options"])
        
        self.ebs_price = 0
        
    def _subprocess_communicate (self, cmd):
        response = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
        if type(response) == type(b''):
            return response.decode('ascii')
        return response
        
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
                line = "%s " % (str(datetime.datetime.now())) + ecsub.ansi.colors.paint("[%s:%03d]" % (self.cluster_name, no), ecsub.ansi.colors.roll_list[no % len(ecsub.ansi.colors.roll_list)]) + line
            else:
                line = ecsub.tools.info_message (self.cluster_name, None, line)
                
            if len(line.rstrip()) > 0:
                sys.stdout.write(line)

    def check_awsconfigure(self):
        if ecsub.aws_config.region_to_location(self.aws_region) == None:
            print(ecsub.tools.error_message (self.cluster_name, None, "region '%s' can not be used in ecsub." % (self.aws_region)))
            return False
        
        return True
    
    def check_file(self, path, no = None):
        
        print(ecsub.tools.info_message (self.cluster_name, no, "check s3-path '%s'..." % (path)))
        
        option = ""
        if ecsub.tools.is_request_payer_bucket(path, self.request_payer_bucket):
            option = "--request-payer requester"
            
        cmd_template = "{setx}; aws s3 ls {option} {path}"
        cmd = cmd_template.format(setx = self.setx, path = path, option = option)
        response = self._subprocess_communicate(cmd)
    
        if response == "":
            print(ecsub.tools.error_message (self.cluster_name, no, "s3-path '%s' is invalid." % (path)))
            return False
    
        find = False
        for r in response.split("\n"):
            if r.split(" ")[-1].rstrip("/") == os.path.basename(path):
                print(ecsub.tools.info_message (self.cluster_name, no, "check s3-path '%s'...ok" % (path)))
                find = True
                break
        if find == False:
            print(ecsub.tools.error_message (self.cluster_name, no, "s3-path '%s' is invalid." % (path)))
            return False
        
        return True

    def check_roles(self):
    
        def _check_role(role_name, service, cluster_name):
            result = False
            try:
                response = boto3.client('iam').get_role(RoleName = role_name)
                if response["Role"]["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]["Service"] == service:
                    result = True

            except Exception as e:
                print(ecsub.tools.error_message (cluster_name, None, e))
                
            return result
        
        def _check_policy(policy_arn, cluster_name):
            result = False
            try:
                response = boto3.client('iam').get_policy(PolicyArn = policy_arn)
                if response["Policy"]["IsAttachable"]:
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
    
    def s3_copy(self, src, dst, recursive, no = None):

        cmd_template = "{setx}; aws s3 cp --only-show-errors {option} {file1} {file2}"

        option = ""
        if recursive:
            option = "--recursive"

        if ecsub.tools.is_request_payer_bucket(src, self.request_payer_bucket) or \
           ecsub.tools.is_request_payer_bucket(dst, self.request_payer_bucket) :
            if option != "":
                option += " "
            option += "--request-payer requester"
            
        cmd = cmd_template.format(
            setx = self.setx,
            file1 = src,
            file2 = dst,
            option = option
        )
        self._subprocess_call(cmd, no)
        return True

    def set_s3files(self, s3_runsh, s3_script, s3_setenv, s3_downloader, s3_uploader):
        self.s3_runsh = s3_runsh
        self.s3_script = s3_script
        self.s3_setenv.extend(s3_setenv)
        self.s3_downloader.extend(s3_downloader)
        self.s3_uploader.extend(s3_uploader)
        
    def _log_path (self, name):
        
        i = 0
        log_path = ""
        while True:
            log_path = "%s/log/%s.%d.log" % (self.wdir, name, i)
            i += 1
            if not os.path.exists(log_path):
                break

        return log_path

    def _conf_path (self, name):
        return "%s/conf/%s" % (self.wdir, name)

    def _get_aws_account_id(self):
        response = self._subprocess_communicate("aws sts get-caller-identity")
        
        info = json.loads(response)
        account = ""
        if "Account" in info:
            account = info["Account"]
        
        return account
        #return json.loads(response)["Account"]
        
    def _get_region(self):
        return boto3.session.Session().region_name

    def _json_load(self, json_file):
        
        if os.path.getsize(json_file) == 0:
            return None
        
        try:
            obj = json.load(open(json_file))
        except Exception:
            #print(ecsub.tools.error_message (self.cluster_name, None, e))
            return None
        return obj
        
    def _check_keypair (self, aws_key_name):
        try:
            response = boto3.client('ec2').describe_key_pairs(KeyNames=[aws_key_name])
            if len(response["KeyPairs"]) > 0:
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
        cmd_template = "{setx}; aws ec2 create-key-pair --key-name {key_name} > {log}"
        cmd = cmd_template.format(
            setx = self.setx,
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
                response = boto3.client('ec2').describe_security_groups(GroupIds=[self.aws_security_group_id])
                if len(response['SecurityGroups']) > 0:
                    return True
            except Exception:
                pass
            print(ecsub.tools.warning_message (self.cluster_name, None, "SecurityGroupId '%s' is invalid." % (self.aws_security_group_id)))
            
        try:
            response = boto3.client('ec2').describe_security_groups(GroupNames=["default"])
            if len(response['SecurityGroups']) > 0:
                self.aws_security_group_id =response['SecurityGroups'][0]['GroupId']
                return True
        except Exception:
            pass

        print(ecsub.tools.error_message (self.cluster_name, None, "Default SecurityGroupId is not exist."))
        return False
    
    def get_secret_value(self):
        if self.duration_seconds < -1:
            return None
        if self.duration_seconds < 900:
            self.duration_seconds = 900
            
        response = boto3.client("sts").client.get_session_token(DurationSeconds=self.duration_seconds)
        if "Credentials" in response:
            return response["Credentials"]
        """
        {
            'AccessKeyId': 'A***',
            'Expiration': datetime.datetime(),
            'SecretAccessKey': '***',
            'SessionToken': '***'
        }
        """
        return None
    
    def create_cluster(self):

        # set key-pair
        if self.set_keypair() == False:
            return False
        
        # set security-group
        if self.set_security_group() == False:
            return False

        log_file = self._log_path("create-cluster")

        cmd_template = "{setx}; aws ecs create-cluster --cluster-name {cluster_name} > {log}"
        cmd = cmd_template.format(
            setx = self.setx,
            cluster_name = self.cluster_name,
            log = log_file
        )
        self._subprocess_call(cmd)
        log = self._json_load(log_file)

        self.cluster_arn = log["cluster"]["clusterArn"]
        return True

    def register_task_definition(self):

        ECSTASKROLE = \
            "arn:aws:iam::{AWS_ACCOUNTID}:role/{AWS_ECS_INSTANCE_ROLE_NAME}"\
            .format(AWS_ACCOUNTID=self.aws_accountid,
                    AWS_ECS_INSTANCE_ROLE_NAME=self.aws_ecs_instance_role_name)

        IMAGE_ARN = self.image
        if self.use_amazon_ecr:
            IMAGE_ARN = "{AWS_ACCOUNTID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{IMAGE_NAME}".format(
                AWS_ACCOUNTID = self.aws_accountid,
                AWS_REGION = self.aws_region,
                IMAGE_NAME = self.image)

        #print(ecsub.tools.info_message (self.cluster_name, None, "EcsTaskRole: %s" % (ECSTASKROLE)))
        #print(ecsub.tools.info_message (self.cluster_name, None, "DockerImage: %s" % (IMAGE_ARN)))
        option = ""
        if ecsub.tools.is_request_payer_bucket(self.s3_runsh, self.request_payer_bucket):
            option = "--request-payer requester "
        
        mountpoints = [
            {
                "sourceVolume": "scratch",
                "containerPath": "/scratch"
            }
        ]
        volumes = [
            {
                "name": "scratch",
                "host": {"sourcePath": "/external"}
            }
        ]
        
        if self.dind:
            mountpoints.append(
                {
                    "sourceVolume": "dockersock",
                    "containerPath": "/var/run/docker.sock"
                }
            )
            volumes.append(
                {
                    "name": "dockersock",
                    "host": {"sourcePath": "/var/run/docker.sock"}
                }
            )
        
        containerDefinitions = {
            "containerDefinitions": [
                {
                    "name": self.cluster_name + "_task",
                    "image": IMAGE_ARN,
                    "cpu": self.aws_ecs_task_vcpu_default,
                    "memory": self.aws_ecs_task_memory_default,
                    "essential": True,
                      "entryPoint": [
                          self.shell,
                          "-c"
                      ],
                      "command": [
                          self.setup_container_cmd + "; aws s3 cp " + option + self.s3_runsh + " /run.sh; " + self.shell + " /run.sh"
                      ],
                      "environment": [
                          {
                              "name": "SCRIPT_RUN_PATH",
                              "value": self.s3_script
                          },
                          {
                              "name": "SCRIPT_SETENV_PATH",
                              "value": ""
                          },
                          {
                              "name": "SCRIPT_DOWNLOADER_PATH",
                              "value": ""
                          },
                          {
                              "name": "SCRIPT_UPLOADER_PATH",
                              "value": ""
                          },
                          {
                              "name": "AWS_DEFAULT_REGION",
                              "value": self.aws_region
                          }
                      ],
                      "logConfiguration": {
                          "logDriver": "awslogs",
                          "options": {
                              "awslogs-group": self.log_group_name,
                              "awslogs-region": self.aws_region,
                              "awslogs-stream-prefix": "ecsub"
                          }
                      },
                      "mountPoints": mountpoints,
                      "workingDirectory": "/scratch",
                }
            ],
            "taskRoleArn": ECSTASKROLE,
            "family": self.cluster_name,
            "volumes": volumes
        }

        json_file = self._conf_path("task_definition.json")
        json.dump(containerDefinitions, open(json_file, "w"), indent=4, separators=(',', ': '))
        
        # check exists ECS cluster
        for i in range(3):
            cmd_template = "aws logs describe-log-groups --log-group-name-prefix {log_group_name} | grep logGroupName | grep \"{log_group_name}\" | wc -l"
            cmd = cmd_template.format(setx = self.setx, log_group_name = self.log_group_name)
            response = self._subprocess_communicate(cmd)
            
            if int(response) == 0:
                cmd_template = "{setx}; aws logs create-log-group --log-group-name {log_group_name}"
                cmd = cmd_template.format(setx = self.setx, log_group_name = self.log_group_name)
                self._subprocess_call(cmd)
                time.sleep(5)
            else:
                print(ecsub.tools.info_message (self.cluster_name, None, "aws logs describe-log-groups --log-group-name-prefix {log_group_name} ... ok".format(log_group_name = self.log_group_name)))
                break

        if int(response) == 0:
            return False
            
        #  register-task-definition
        log_file = self._log_path("register-task-definition")
        cmd_template = "{setx}; aws ecs register-task-definition --cli-input-json file://{json} > {log}"

        cmd = cmd_template.format(
            setx = self.setx,
            json = json_file,
            log = log_file
        )
        self._subprocess_call(cmd)
        log = self._json_load(log_file)
        self.task_definition_arn = log["taskDefinition"]["taskDefinitionArn"]

        return True

    def _userdata(self):
        return """Content-Type: multipart/mixed; boundary="==BOUNDARY=="
MIME-Version: 1.0

--==BOUNDARY==
Content-Type: text/cloud-boothook; charset="us-ascii"

# Install nfs-utils
cloud-init-per once yum_update yum update -y
cloud-init-per once install_tr yum install -y tr
cloud-init-per once install_td yum install -y td
cloud-init-per once install_python27_pip yum install -y python27-pip
cloud-init-per once install_awscli pip install awscli

cloud-init-per once ecs_option echo "ECS_CLUSTER={cluster_arn}" >> /etc/ecs/ecs.config

cat << EOF > /root/metricscript.sh
AWSREGION={region}
AWSINSTANCEID=\$(curl -ss http://169.254.169.254/latest/meta-data/instance-id)
ECS_CLUSTER_NAME=\$(cat /etc/ecs/ecs.config | grep ^ECS_CLUSTER | cut -d "/" -f 2)

disk_util=\$(df /external | awk '/external/ {{print \$5}}' | awk -F% '{{print \$1}}')
aws cloudwatch put-metric-data --value \$disk_util --namespace ECSUB --unit Percent --metric-name DataStorageUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

sts=(\$(vmstat | tail -n 1))
cpu_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\${{sts[12]}}'+'\${{sts[13]}}' }}')
aws cloudwatch put-metric-data --value \$cpu_util --namespace ECSUB --unit Percent --metric-name CPUUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

# new
mem_total=\$(free | awk '/Mem:/ {{print \$2}}')
mem_used=\$(free | awk '/buffers\/cache:/ {{print \$3}}')
mem_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\$mem_used'*100/'\$mem_total' }}')
aws cloudwatch put-metric-data --value \$mem_util --namespace ECSUB --unit Percent --metric-name MemoryUtilization --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

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

cloud-init-per once mkfs_sdb mkfs -t ext4 /dev/sdb
cloud-init-per once mkdir_external mkdir /external
cloud-init-per once mount_sdb mount /dev/sdb /external

echo "aws configure set aws_access_key_id "\$(aws configure get aws_access_key_id) > /external/aws_confgure.sh
echo "aws configure set aws_secret_access_key "\$(aws configure get aws_secret_access_key) >> /external/aws_confgure.sh
echo "aws configure set region "\$AWSREGION >> /external/aws_confgure.sh
--==BOUNDARY==--
""".format(cluster_arn = self.cluster_arn, region = self.aws_region)
    
    def _getblock_device_mappings(self):
        return [
            {
                "DeviceName":"/dev/xvdcz",
                "Ebs": {
                    "VolumeSize": self.root_disk_size,
                    "VolumeType": "gp2",
                    "DeleteOnTermination":True
                }
            },
            {
                "DeviceName":"/dev/sdb",
                "Ebs": {
                    "VolumeSize": self.disk_size,
                    "VolumeType": "gp2",
                    "DeleteOnTermination":True
                }
            }
        ]
    
    def _wait_run_instance(self, instance_id, no):
        
        if instance_id != "":
            cmd_template = "{setx}; aws ec2 wait instance-running --instance-ids {INSTANCE_ID}"
            cmd = cmd_template.format(
                setx = self.setx,
                INSTANCE_ID = instance_id
            )
            self._subprocess_call(cmd, no)
    
            cmd_template = "{setx}; aws ec2 wait instance-status-ok --include-all-instances --instance-ids {INSTANCE_ID}"
            cmd = cmd_template.format(
                setx = self.setx,
                INSTANCE_ID = instance_id
            )
            self._subprocess_call(cmd, no)
    
            for i in range(3):
                response = boto3.client("ec2").describe_instance_status(InstanceIds=[instance_id])
                if response['InstanceStatuses'][0]['InstanceStatus']['Status'] == "ok":
                    return True
                self._subprocess_call(cmd, no)
    
        print(ecsub.tools.error_message (self.cluster_name, no, "Failure run instance."))
        return False
    
    def run_instances_ondemand (self, no):
        userdata_file = self._conf_path("userdata.%03d.sh" % (no))
        userdata_text = self._userdata()
        
        open(userdata_file, "w").write(userdata_text)

        log_file = self._log_path("run-instances.%03d" % (no))

        block_device_mappings = self._getblock_device_mappings()
        
        bd_mappings_file = self._conf_path("block_device_mappings.%03d.json" % (no))
        json.dump(block_device_mappings, open(bd_mappings_file, "w"), indent=4, separators=(',', ': '))
        subnet_id = ""
        if self.task_param[no]["aws_subnet_id"] != "":
            subnet_id = "--subnet-id %s" % (self.task_param[no]["aws_subnet_id"])

        cmd_template = "{setx};" \
            + "aws ec2 run-instances" \
            + " --image-id {AMI_ID}" \
            + " --security-group-ids {SECURITYGROUPID}" \
            + " --key-name {KEY_NAME}" \
            + " --user-data file://{userdata}" \
            + " --iam-instance-profile Name={AWS_ECS_INSTANCE_ROLE_NAME}" \
            + " --instance-type {instance_type}" \
            + " --block-device-mappings file://{json}" \
            + " --count 1 {subnet_id}" \
            + " > {log}"

        cmd = cmd_template.format(
            setx = self.setx,
            AMI_ID = self.aws_ami_id,
            SECURITYGROUPID = self.aws_security_group_id,
            KEY_NAME = self.aws_key_name,
            subnet_id = subnet_id,
            instance_type = self.task_param[no]["aws_ec2_instance_type"],
            AWS_ECS_INSTANCE_ROLE_NAME=self.aws_ecs_instance_role_name,
            json = bd_mappings_file,
            INDEX = no,
            userdata = userdata_file,
            log = log_file
        )
        self._subprocess_call(cmd, no)
        log = self._json_load(log_file)
        try:
            instance_id = log["Instances"][0]["InstanceId"]
            if self._wait_run_instance(instance_id, no):
                return instance_id
        except Exception:
            pass
        return None
        
    def _describe_instance (self, instance_id):
        response = boto3.client('ec2').describe_instances(
            InstanceIds = [instance_id]
        )
        instances = None
        try:
            instances = response["Reservations"][0]["Instances"][0]
        except Exception:
            pass
        return instances

    def _describe_container_instance (self, cluster, instance_id):
        response = boto3.client('ecs').describe_container_instances(
            cluster = cluster,
            containerInstances = [instance_id]
        )
        instances = None
        try:
            instances = response["containerInstances"][0]
        except Exception:
            pass
        return instances
    
    def set_ondemand_price (self, no):
        
        self.task_param[no]["spot"] = False
                       
        response = boto3.client('pricing', region_name = "ap-south-1").get_products(
            ServiceCode='AmazonEC2',
            Filters = [
                {'Type' :'TERM_MATCH', 'Field':'instanceType',    'Value': self.task_param[no]["aws_ec2_instance_type"]},
                {'Type' :'TERM_MATCH', 'Field':'location',        'Value': ecsub.aws_config.region_to_location(self.aws_region)},
                {'Type' :'TERM_MATCH', 'Field':'operatingSystem', 'Value': 'Linux'},
                {'Type' :'TERM_MATCH', 'Field':'tenancy',         'Value': 'Shared'},
                {'Type' :'TERM_MATCH', 'Field':'preInstalledSw',  'Value': 'NA'},
                {'Type' :'TERM_MATCH', 'Field':'capacitystatus',  'Value': 'Used'},
            ],
            MaxResults=100
        )
        
        values = []
        try:
            for i in range(len(response["PriceList"])):
                obj = json.loads(response["PriceList"][i])
                for key1 in obj["terms"]["OnDemand"].keys():
                    for key2 in obj["terms"]["OnDemand"][key1]["priceDimensions"].keys():
                        values.append(float(obj["terms"]["OnDemand"][key1]["priceDimensions"][key2]["pricePerUnit"]["USD"]))
        except Exception as e:
            print (e)
            print(ecsub.tools.error_message (self.cluster_name, no, "instance-type %s can not be used in region '%s'." % (self.task_param[no]["aws_ec2_instance_type"], self.aws_region)))
            return 0
        
        values.sort()
        if len(values) > 0:
            print(ecsub.tools.info_message (self.cluster_name, no, "Instance Type: %s, Ondemand Price: $%.3f" % (self.task_param[no]["aws_ec2_instance_type"], values[-1])))
            self.task_param[no]["od_price"] = values[-1]
            return True
        
        print(ecsub.tools.error_message (self.cluster_name, no, "instance-type %s can not be used in region '%s'." % (self.task_param[no]["aws_ec2_instance_type"], self.aws_region)))
        return 0
    
    def set_spot_price (self, no):
        
        availarity_zone = []
        subnet_az_map = []
        if  len(self.aws_subnet_id) > 0:
            try:
                response = boto3.client('ec2').describe_subnets(SubnetIds=self.aws_subnet_id)
                for subnet in response['Subnets']:
                    availarity_zone.append(subnet['AvailabilityZone'])
                    subnet_az_map.append({'AvailabilityZone': subnet['AvailabilityZone'], 'SubnetId': subnet['SubnetId']})
            except Exception as e:
                print (e)
                return False
            
        now = datetime.datetime.utcnow()
        start_dt = now - datetime.timedelta(days = 6)
        response = boto3.client('ec2').describe_spot_price_history(
            Filters = [{"Name":'product-description', "Values": ['Linux/UNIX']}],
            InstanceTypes = [self.task_param[no]["aws_ec2_instance_type"]],
            MaxResults = 100,
            StartTime = start_dt,
            EndTime = now,
        )
        
        spot_prices = {}
        try:
            for his in response["SpotPriceHistory"]:
                az = his['AvailabilityZone']
                if availarity_zone != [] and not az in availarity_zone:
                    continue
                if not az in spot_prices:
                    spot_prices[az] = []
                spot_prices[az].append(float(his['SpotPrice']))
        except Exception as e:
            print (e)
            return False
    
        price = {"az": "", "price": -1}
        for key in spot_prices.keys():
            new_price = sum(spot_prices[key])/len(spot_prices[key])
            if (price["price"] < 0) or (price["price"] > new_price):
                price["price"] = new_price
                price["az"] = key

        if price["price"] < 0:
            print(ecsub.tools.error_message (self.cluster_name, no, "failure describe_spot_price_history."))
            return False
        
        if price["price"] > self.task_param[no]["od_price"] * 0.98:
            print(ecsub.tools.error_message (self.cluster_name, no, "spot price $%.3f is close to ondemand price $%.3f." % (price["price"], self.task_param[no]["od_price"])))
            return False
        
        self.task_param[no]["spot_price"] = price["price"]
        self.task_param[no]["spot_az"] = price["az"]
        for map in subnet_az_map:
            if map['AvailabilityZone'] == price["az"]:
                self.task_param[no]["aws_subnet_id"] = map['SubnetId']
                break
        print(ecsub.tools.info_message (self.cluster_name, no, "Spot Price: $%.3f, Availality Zone: %s" % (price["price"], price["az"])))
        return True
    
    def set_ebs_price (self):
        def _get_ebs_price (region, vtype):
        
            ebs_name_map = {
                'standard': 'Magnetic',
                'gp2': 'General Purpose',
                'io1': 'Provisioned IOPS',
                'st1': 'Throughput Optimized HDD',
                'sc1': 'Cold HDD'
            }
            
            response = boto3.client('pricing', region_name = "ap-south-1").get_products(
                ServiceCode='AmazonEC2',
                Filters = [
                    {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': ebs_name_map[vtype]}, 
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': ecsub.aws_config.region_to_location(region)}
                ],
                MaxResults=100
            )
            
            values = []
            try:
                for i in range(len(response["PriceList"])):
                    obj = json.loads(response["PriceList"][i])
                    for key1 in obj["terms"]["OnDemand"].keys():
                        for key2 in obj["terms"]["OnDemand"][key1]["priceDimensions"].keys():
                            values.append(obj["terms"]["OnDemand"][key1]["priceDimensions"][key2]["pricePerUnit"]["USD"])
            except Exception:
                return 0
            
            values.sort()
            if len(values) > 0:
                return float(values[-1])
            
            return 0
    
        price = _get_ebs_price (self.aws_region, "gp2")
        
        if price == 0:
            print(ecsub.tools.error_message (self.cluster_name, None, "failure _get_ebs_price."))
            return False
        
        self.ebs_price = price
        print(ecsub.tools.info_message (self.cluster_name, None, "Disk Price: $%.3f per GB-month of General Purpose SSD (gp2)" % (price)))
        return True
    
    def _describe_spot_instances(self, no, request_id = None, instance_id = None):

        response = None
        if request_id != None:
            response = boto3.client("ec2").describe_spot_instance_requests(
                SpotInstanceRequestIds=[
                    request_id,
                ]
            )
        elif instance_id != None:
            response = boto3.client("ec2").describe_spot_instance_requests(
                Filters = [
                    {"Name":"instance-id", "Values": [instance_id]}
                ]
            )
        else:
            return None
        
        if not 'SpotInstanceRequests' in response:
            return None

        import copy
        response_cp = copy.deepcopy(response)
        r0 = response['SpotInstanceRequests'][0]
        r0_cp = response_cp['SpotInstanceRequests'][0]
        r0_cp['CreateTime'] = ecsub.tools.datetime_to_isoformat(r0['CreateTime'])
        r0_cp['Status']['UpdateTime'] = ecsub.tools.datetime_to_isoformat(r0['Status']['UpdateTime']) 
        r0_cp['ValidUntil'] = ecsub.tools.datetime_to_isoformat(r0['ValidUntil']) 
        json.dump(response_cp, open(self._log_path("describe-spot-instance-requests.%03d" % no), "w"), indent=4, separators=(',', ': '))
        
        return response['SpotInstanceRequests'][0]
    
    def run_instances_spot (self, no):
        
        self.task_param[no]["spot"] = True
        
        userdata_text = ecsub.tools.base64_encode(self._userdata())
        block_device_mappings = self._getblock_device_mappings()
        
        specification = {
            "SecurityGroupIds": [ self.aws_security_group_id ],
            "BlockDeviceMappings": block_device_mappings,
            "IamInstanceProfile": {
                "Name": self.aws_ecs_instance_role_name
            },
            "ImageId": self.aws_ami_id,
            "InstanceType": self.task_param[no]["aws_ec2_instance_type"],
            "KeyName": self.aws_key_name,
            "Placement": {
                "AvailabilityZone": self.task_param[no]["spot_az"],
            },
            "UserData": userdata_text.decode()
        }
                        
        if self.task_param[no]["aws_subnet_id"] != "":
            specification["SubnetId"] = self.task_param[no]["aws_subnet_id"]
        
        specification_file = self._conf_path("specification_file.%03d.json" % (no))
        json.dump(specification, open(specification_file, "w"), indent=4, separators=(',', ': '))
        
        log_file = self._log_path("request-spot-instances.%03d" % (no))
        
        cmd_template = "{setx};" \
            + "aws ec2 request-spot-instances" \
            + " --instance-count 1" \
            + " --type 'one-time'" \
            + " --launch-specification file://{specification_file}" \
            + " > {log};"
        
        cmd = cmd_template.format(
            setx = self.setx,
            specification_file = specification_file,
            log = log_file
        )

        self._subprocess_call(cmd, no)
        time.sleep(10)
        log = self._json_load(log_file)
        request_id = ""
        try:
            request_id = log["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
        except Exception:
            print(ecsub.tools.error_message (self.cluster_name, no, "Failure request-spot-instances."))
            return None
        
        for i in range(3):
            response = self._describe_spot_instances(no, request_id = request_id)
            
            try:
                state = response['State']
                status_code = response['Status']['Code']
                
                if state == "active" and status_code == 'fulfilled':
                    instance_id = response['InstanceId']
                    if self._wait_run_instance(instance_id, no):
                        return instance_id
                
                elif state == "open" and status_code == 'pending-evaluation':
                    cmd_template = "{setx}; aws ec2 wait spot-instance-request-fulfilled --spot-instance-request-ids {REQUEST_ID}"
                    cmd = cmd_template.format(
                        setx = self.setx,
                        REQUEST_ID = request_id
                    )
                    self._subprocess_call(cmd, no)
                else:
                    print(ecsub.tools.error_message (self.cluster_name, no, "Failure request-spot-instances. [Status] %s [Code] %s [Message] %s" % 
                        (response['State'],
                         response['Status']['Code'],
                         response['Status']['Message'])
                    ))
                    break
            except Exception:
                break
            
        self.cancel_spot_instance_requests (no = no, spot_req_id = request_id)
        return None
        
    def _check_memory(self, log_file):
        log = self._json_load(log_file)

        # failue
        if log == None:
            return (None, [])
        
        if not "tasks" in log:
            return (None, [])
        
        if not "failures" in log:
            return (None, [])
        
        # success
        if len(log["tasks"]) > 0:
            return (log, None)
        
        # failure with memory
        error_message = []
        error_message.append("failures: %s" % (json.dumps(log["failures"])))
        
        if log["failures"][0]["reason"] != "RESOURCE:MEMORY":
            return (None, error_message)
            
        response = boto3.client('ecs').describe_container_instances(cluster=self.cluster_arn, containerInstances=[log["failures"][0]["arn"]])
        for resouce in response['containerInstances'][0]['remainingResources']:
            if resouce["name"] == "MEMORY":
                error_message.append("remainingResources(MEMORY): %d" % (resouce["integerValue"]))
        return (None, error_message)
        
    def run_task (self, no, instance_id):
        """
        exit_code: 0    Success
        exit_code: 1    Error
        exit_code: 127  SystemError
        exit_code: -1   SpotInstance terminated-capacity-oversubscribed
        """
        
        import math
        
        exit_code = 1
        
        container_instance = None
        for i in range(3):
            response = boto3.client("ecs").list_container_instances(
                cluster = self.cluster_arn,
                filter = "ec2InstanceId == %s" % (instance_id)
            )
            try:
                container_instance = response['containerInstanceArns'][0]
                break
            except Exception:
                time.sleep(10)
        
        if container_instance == None:
            return (exit_code, None)
        
        # get subnet
        inst_info = self._describe_instance(instance_id)
        subnet_id = None
        if inst_info != None:
            subnet_id = inst_info["SubnetId"]
    
        cont_info = self._describe_container_instance (self.cluster_arn, container_instance.split("/")[-1])
        if cont_info == None:
            return (exit_code, None)
        
        task_vcpu = 0
        task_memory = 0
        for resource in cont_info['remainingResources']:
            if resource["name"] == "CPU":
                task_vcpu = int(math.floor(resource['integerValue']/1000))
                if task_vcpu == 0:
                    print(ecsub.tools.error_message(self.cluster_name, no, "remainingResources(CPU): %d" % (resource["integerValue"])))
                    return (exit_code, None)
            elif resource["name"] == "MEMORY":
                task_memory = int(math.floor(resource['integerValue']/100) * 100)
            else:
                continue

        environment = [
            {
                "name": "SCRIPT_SETENV_PATH",
                "value": self.s3_setenv[no]
            },
            {
                "name": "SCRIPT_DOWNLOADER_PATH",
                "value": self.s3_downloader[no]
            },
            {
                "name": "SCRIPT_UPLOADER_PATH",
                "value": self.s3_uploader[no]
            }
        ]
        
        for op in self.env_options:
            environment.append({
                "name": op["name"],
                "value": op["value"],
            })
            
        # run-task
        containerOverrides = {
            "containerOverrides": [
                {
                    "cpu": task_vcpu*1024,
                    "memory": task_memory,
                    "name": self.cluster_name + "_task",
                    "environment": environment
            }]
        }

        overrides = self._conf_path("containerOverrides.%03d.json" % (no))
        json.dump(containerOverrides, open(overrides, "w"), indent=4, separators=(',', ': '))

        log_file = self._log_path("start-task.%03d" % (no))

        cmd_template = "{setx}; " \
            + "aws ecs start-task --cluster {CLUSTER_ARN}" \
            + " --task-definition {TASK_DEFINITION_ARN}" \
            + " --overrides file://{OVERRIDES}" \
            + " --container-instances {INSTANCE_ID} > {log}"

        cmd = cmd_template.format(
            setx = self.setx,
            CLUSTER_ARN = self.cluster_arn,
            TASK_DEFINITION_ARN = self.task_definition_arn,
            OVERRIDES = overrides,
            INSTANCE_ID = container_instance,
            log = log_file
        )
        self._subprocess_call(cmd, no)

        # retry run-task and error print
        (log, err_msg) = self._check_memory(log_file)
        if log == None:
            for msg in err_msg:
                print (ecsub.tools.warning_message (self.cluster_name, no, msg))
            
            log_file_retry = self._log_path("start-task-retry.%03d" % (no))
            cmd = cmd_template.format(
                setx = self.setx,
                CLUSTER_ARN = self.cluster_arn,
                TASK_DEFINITION_ARN = self.task_definition_arn,
                OVERRIDES = overrides,
                INSTANCE_ID = container_instance,
                log = log_file_retry
            )
            self._subprocess_call(cmd, no)
            time.sleep(10)
            (log, err_msg) = self._check_memory(log_file_retry)
            if log == None:
                for msg in err_msg:
                    print (ecsub.tools.error_message (self.cluster_name, no, msg))
                return (exit_code, None)

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
        if instance_id != log["containerInstances"][0]["ec2InstanceId"]:
            print (ecsub.tools.error_message (self.cluster_name, no, "%s != %s" % (instance_id, log["containerInstances"][0]["ec2InstanceId"])))
        
        # get log-path
        log_html_template = "https://{region}.console.aws.amazon.com/cloudwatch/home" \
            + "?region={region}#logEventViewer:group={log_group_name};stream=ecsub/{cluster_name}_task/{task_id}"

        log_html = log_html_template.format(
            region = self.aws_region,
            cluster_name = self.cluster_name,
            log_group_name = self.log_group_name,
            task_id = task_arn.split("/")[1]
        )
        print (ecsub.tools.message (self.cluster_name, no, [{"text": " For detail, see log-file: "}, {"text": log_html, "color": ecsub.tools.get_title_color(no)}]))

        # set Name to instance
        instanceName = "{cluster_name}.{I}".format(cluster_name = self.cluster_name, I = no)
        cmd_template = "{setx};aws ec2 create-tags --resources {INSTANCE_ID} --tags Key=Name,Value={instanceName}"

        cmd = cmd_template.format(
            setx = self.setx,
            INSTANCE_ID = instance_id,
            instanceName = instanceName
        )
        self._subprocess_call(cmd, no)
        json.dump(
            {"InstanceId": instance_id, "InstanceName": instanceName},
            open(self._log_path("create-tags.%03d" % (no)), "w")
        )
        
        if self.flyaway:
            return (0, None)
            
        # wait to task-stop
        cmd_template = "{setx};aws ecs wait tasks-stopped --tasks {TASK_ARN} --cluster {CLUSTER_ARN}"

        cmd = cmd_template.format(
            setx = self.setx,
            CLUSTER_ARN = self.cluster_arn,
            TASK_ARN = task_arn
        )
        self._subprocess_call(cmd, no)

        response = boto3.client('ecs').describe_tasks(
            cluster=self.cluster_arn,
            tasks=[task_arn]
        )
        while True:
            if len(response["tasks"]) == 0:
                return (exit_code, log_file)
            if response["tasks"][0]['lastStatus'] != "RUNNING":
                break

            self._subprocess_call(cmd, no)
            response = boto3.client('ecs').describe_tasks(
                cluster=self.cluster_arn,
                tasks=[task_arn]
            )

        # check exit code
        log_file = self._log_path("describe-tasks.%03d" % (no))

        response["tasks"][0]["log"] = log_html
        response["tasks"][0]["instance_type"] = self.task_param[no]["aws_ec2_instance_type"]
        response["tasks"][0]["disk_size"] = self.disk_size
        response["tasks"][0]["root_disk_size"] = self.root_disk_size
        response["tasks"][0]["no"] = no
        response["tasks"][0]["instance_id"] = instance_id
        response["tasks"][0]["subnet_id"] = subnet_id
        response["tasks"][0]["log_local"] = log_file
                
        def support_datetime_default(o):
            if isinstance(o, datetime.datetime):
                return '%04d/%02d/%02d %02d:%02d:%02d %s' % (o.year, o.month, o.day, o.hour, o.minute, o.second, o.tzname())
            raise TypeError(repr(o) + " is not JSON serializable")

        json.dump(response, open(log_file, "w"), default=support_datetime_default, indent=4, separators=(',', ': '))
        
        #exit_code = 1
        if "containers" in response["tasks"][0]:
            if "exitCode" in response["tasks"][0]["containers"][0]:
                exit_code = response["tasks"][0]["containers"][0]["exitCode"]
                print (ecsub.tools.info_message (self.cluster_name, no, "tasks-stopped with [%d]" % (exit_code)))

            if "reason" in response["tasks"][0]["containers"][0]:
                if exit_code != 0:
                    print (ecsub.tools.error_message (self.cluster_name, no, "An error occurred: %s" % (response["tasks"][0]["containers"][0]["reason"])))

        if "stoppedReason" in response["tasks"][0]:
            if exit_code != 0:
                print (ecsub.tools.error_message (self.cluster_name, no, "An error occurred: %s" % (response["tasks"][0]["stoppedReason"])))

        # check spot insatance was canceled?
        if self.task_param[no]["spot"]:
            response = boto3.client("ec2").describe_spot_instance_requests(
                Filters = [
                    {"Name":"instance-id", "Values": [instance_id]}
                ]
            )
            if len(response['SpotInstanceRequests']) > 0:
                if response['SpotInstanceRequests'][0]["Status"]["Code"] == 'instance-terminated-capacity-oversubscribed':
                    exit_code = -1

        return (exit_code, log_file)

    def terminate_instances (self, instance_id, no = None):

        log_file = self._log_path("terminate-instances")
        if no != None:
            log_file = self._log_path("terminate-instances.%03d" % (no))

        cmd_template = "{setx};" \
            + "aws ec2 terminate-instances --instance-ids {ec2InstanceId} > {log};" \
            + "aws ec2 wait instance-terminated --instance-ids {ec2InstanceId}"

        cmd = cmd_template.format(
            setx = self.setx,
            log = log_file,
            ec2InstanceId = instance_id
        )
        self._subprocess_call(cmd, no)
    
    def cancel_spot_instance_requests (self, no = None, instance_id = None, spot_req_id = None):
        
        log_file = self._log_path("cancel-spot-instance-requests")
        if no != None:
            log_file = self._log_path("cancel-spot-instance-requests.%03d" % (no))
    
        if spot_req_id == None:
            response = self._describe_spot_instances (no, instance_id = instance_id)
            if response != None:
                state = response['State']
                if state == "active" or state == "open":
                    spot_req_id = response['SpotInstanceRequestId']

        if spot_req_id != None:
            cmd_template = "{setx};" \
                + "aws ec2 cancel-spot-instance-requests --spot-instance-request-ids {spot_req_id} > {log}"

            cmd = cmd_template.format(
                setx = self.setx,
                log = log_file,
                spot_req_id = spot_req_id
            )
            self._subprocess_call(cmd, no)
        
    def clean_up (self):
        
        # terminate instances
        instance_ids = []
        for log_file in glob.glob("%s/log/run-instances.*.log" % (self.wdir)):
            log = self._json_load(log_file)
            try:
                instance_id = log["Instances"][0]["InstanceId"]
                instance_ids.append(instance_id)
            except Exception:
                pass
        
        for log_file in glob.glob("%s/log/describe-spot-instance-requests.*.log" % (self.wdir)):
            log = self._json_load(log_file)
            try:
                instance_ids.append(log["SpotInstanceRequests"][0]["InstanceId"])
            except Exception:
                pass
        
        if len(instance_ids) > 0:
            self.terminate_instances (" ".join(instance_ids))
        
        # cancel_spot_instance_requests
        req_ids = []
        for log_file in glob.glob("%s/log/request-spot-instances.*.log" % (self.wdir)):
            log = self._json_load(log_file)
            try:
                req_ids.append(log["SpotInstanceRequests"][0]["SpotInstanceRequestId"])
            except Exception:
                pass
            
        if len(req_ids) > 0:
            self.cancel_spot_instance_requests (spot_req_id = " ".join(req_ids))
            
        # delete cluster
        if self.cluster_arn != "":
            response = boto3.client('ecs').describe_clusters(clusters=[self.cluster_arn])
            if len(response["clusters"]) > 0:
                cmd_template = "{setx}; aws ecs delete-cluster --cluster {cluster} > {log}"
                cmd = cmd_template.format(
                    setx = self.setx,
                    cluster = self.cluster_arn,
                    log = self._log_path("delete-cluster")
                )
                self._subprocess_call(cmd)

        # delete task definition
        if self.task_definition_arn != "":
            try:
                response = boto3.client('ecs').describe_task_definition(taskDefinition=self.task_definition_arn)

                cmd_template = "{setx}; aws ecs deregister-task-definition --task-definition {task} > {log}"
                cmd = cmd_template.format(
                    setx = self.setx,
                    task = self.task_definition_arn,
                    log = self._log_path("deregister-task-definition")
                )
                self._subprocess_call(cmd)
            except Exception:
                pass

        # delete ssh key pair
        if self.aws_key_auto:
            cmd_template = "{setx}; aws ec2 delete-key-pair --key-name {key_name} > {log}"
            cmd = cmd_template.format(
                setx = self.setx,
                key_name = self.aws_key_name,
                log = self._log_path("delete-key-pair")
            )
            self._subprocess_call(cmd)

def __get_ecsub_key():
    
    client = boto3.client("kms")
    response = client.list_aliases()
    
    ecsub_keys = []
    if 'Aliases' in response:
        for alias in response['Aliases']:
            if not alias["AliasName"].startswith("alias/ecsub"):
                continue
            
            response2 = client.describe_key(
                KeyId=alias['TargetKeyId']
            )
            
            ecsub_keys.append({
                'AliasName': alias['AliasName'],
                'TargetKeyId': alias['TargetKeyId'],
                'CreationDate': response2['KeyMetadata']['CreationDate']
            })
   
    if len(ecsub_keys) == 0:
        return None

    return sorted(ecsub_keys, key=lambda x: x['CreationDate'])[-1]['AliasName']
                
def encrypt_data(plain_text):
    key = __get_ecsub_key()
    
    if key == None:
        print(ecsub.tools.error_message (None, None, "ecsub-key is not exist."))
        return ""
    
    response = boto3.client("kms").encrypt(
        KeyId = key,
        Plaintext = plain_text
    )
    
    return base64.b64encode(response['CiphertextBlob']).decode('utf-8')
    
def decrypt_data(encrypt_text):
    
    enc = base64.b64decode(encrypt_text)
    response = boto3.client("kms").decrypt(
        CiphertextBlob= enc
    )
    return response['Plaintext'].decode('utf-8')
