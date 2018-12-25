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

    def __init__(self, params, task_num):
        
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
        
        self.aws_ami_id = ecsub.aws_config.get_ami_id()
        #self.aws_ec2_instance_type = params["aws_ec2_instance_type"]
        self.aws_ec2_instance_type_list = params["aws_ec2_instance_type_list"]
        if self.aws_ec2_instance_type_list == ['']:
            self.aws_ec2_instance_type_list = [params["aws_ec2_instance_type"]]
        
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
        
        self.spot = params["spot"]
        #self.spot_az = ""
        self.retry_od = params["retry_od"]
        #self.spot_price = 0
        #self.od_price = 0
        
        self.task_param = []
        for i in range(task_num):
            self.task_param.append({
                "spot": params["spot"],
                "aws_ec2_instance_type": params["aws_ec2_instance_type"],
                "od_price": 0,
                "spot_az": "",
                "spot_price": 0,
            })
    
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
                #line = "[%s]" % (self.cluster_name) + line
                
            if len(line.rstrip()) > 0:
                sys.stdout.write(line)

    def check_awsconfigure(self):
        if ecsub.aws_config.region_to_location(self.aws_region) == None:
            print(ecsub.tools.error_message (self.cluster_name, None, "region '%s' can not be used in ecsub." % (self.aws_region)))
            return False
        
        return True
    
    def check_inputfiles(self, tasks):

        for task in tasks["tasks"]:
            for i in range(len(task)):
                if tasks["header"][i]["type"] != "input":
                    continue
                
                cmd_template = "aws s3 ls {path}"
                cmd = cmd_template.format(set_cmd = self.set_cmd, path = task[i].rstrip("/"))
                response = self._subprocess_communicate(cmd)

                if response == "":
                    print(ecsub.tools.error_message (self.cluster_name, None, "s3-path '%s' is invalid." % (task[i])))
                    return False

                find = False
                for r in response.split("\n"):
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
        return json.loads(response)["Account"]

    def _get_region(self):
        response = self._subprocess_communicate("aws configure get region")
        return response.rstrip("\n")

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

        print(ecsub.tools.info_message (self.cluster_name, None, "EcsTaskRole: %s" % (ECSTASKROLE)))
        print(ecsub.tools.info_message (self.cluster_name, None, "DockerImage: %s" % (IMAGE_ARN)))
        
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
                      },
                      "mountPoints": [
                          {
                              "containerPath": "/scratch",
                              "sourceVolume": "scratch"
                          }
                      ],
                      "workingDirectory": "/scratch",
                }
            ],
            "taskRoleArn": ECSTASKROLE,
            "family": self.cluster_name,
            "volumes": [
                {
                    "name": "scratch",
                    "host": {
                        "sourcePath": "/external"
                    }
                }
            ]
        }

        json_file = self._conf_path("task_definition.json")
        json.dump(containerDefinitions, open(json_file, "w"), indent=4, separators=(',', ': '))
        
        # check exists ECS cluster
        cmd_template = "aws logs describe-log-groups --log-group-name-prefix {log_group_name} | grep logGroupName | grep \"{log_group_name}\" | wc -l"
        cmd = cmd_template.format(set_cmd = self.set_cmd, log_group_name = self.log_group_name)
        response = self._subprocess_communicate(cmd)
        
        if int(response) == 0:
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

mem_used=\$(vmstat -s | grep "used memory" | sed s/^" "*/""/ | cut -f 1 -d " ")
mem_free=\$(vmstat -s | grep "free memory" | sed s/^" "*/""/ | cut -f 1 -d " ")
mem_util=\$(awk 'BEGIN{{ printf "%.0f\\n", '\$mem_used'*100/('\$mem_used'+'\$mem_free') }}')
aws cloudwatch put-metric-data --value \$mem_util --namespace ECSUB --unit Percent --metric-name MemoryUtilization_BK --region \$AWSREGION --dimensions InstanceId=\$AWSINSTANCEID,ClusterName=\$ECS_CLUSTER_NAME

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
--==BOUNDARY==--
""".format(cluster_arn = self.cluster_arn, disk_size = self.aws_ec2_instance_disk_size, region = self.aws_region)

    def _getblock_device_mappings(self):
        return [
            {
                "DeviceName":"/dev/xvdcz",
                "Ebs": {
                    "VolumeSize": 22,
                    "VolumeType": "gp2",
                    "DeleteOnTermination":True
                }
            },
            {
                "DeviceName":"/dev/sdb",
                "Ebs": {
                    "VolumeSize": self.aws_ec2_instance_disk_size,
                    "VolumeType": "gp2",
                    "DeleteOnTermination":True
                }
            }
        ]
    def _wait_run_instance(self, instance_id, no):
        
        if instance_id != "":
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
            instance_type = self.task_param[no]["aws_ec2_instance_type"],
            json = bd_mappings_file,
            INDEX = no,
            userdata = userdata_file,
            log = log_file
        )
        self._subprocess_call(cmd, no)
        log = self._json_load(log_file)
        instance_id = log["Instances"][0]["InstanceId"]
        
        return self._wait_run_instance(instance_id, no)
    
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
                        values.append(obj["terms"]["OnDemand"][key1]["priceDimensions"][key2]["pricePerUnit"]["USD"])
        except Exception as e:
            print (e)
            print(ecsub.tools.error_message (self.cluster_name, no, "instance-type %s can not be used in region '%s'." % (self.task_param[no]["aws_ec2_instance_type"], self.aws_region)))
            return 0
        
        values.sort()
        if len(values) > 0:
            print(ecsub.tools.info_message (self.cluster_name, no, "Instance Type: %s, Ondemand Price: %s USD" % (self.task_param[no]["aws_ec2_instance_type"], values[-1])))
            self.task_param[no]["od_price"] = float(values[-1])
            return True
        
        print(ecsub.tools.error_message (self.cluster_name, no, "instance-type %s can not be used in region '%s'." % (self.task_param[no]["aws_ec2_instance_type"], self.aws_region)))
        return 0
    
    def set_spot_price (self, no):
        
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
            print(ecsub.tools.error_message (self.cluster_name, no, "spot price %f is close to ondemand price %f." % (price["price"], self.task_param[no]["od_price"])))
            return False
        
        self.task_param[no]["spot_price"] = price["price"]
        self.task_param[no]["spot_az"] = price["az"]
        print(ecsub.tools.info_message (self.cluster_name, no, "Spot Price: %s USD, Availality Zone: %s" % (price["price"], price["az"])))
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
        
        #import pprint
        #pprint.pprint(response)
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
                "Name": "ecsInstanceRole"
            },
            "ImageId": self.aws_ami_id,
            "InstanceType": self.task_param[no]["aws_ec2_instance_type"],
            "KeyName": self.aws_key_name,
            "Placement": {
                "AvailabilityZone": self.task_param[no]["spot_az"],
            },
            "UserData": userdata_text.decode()
        }
                        
        if self.aws_subnet_id != "":
            specification["subnet_id"] = self.aws_subnet_id
        
        specification_file = self._conf_path("specification_file.%03d.json" % (no))
        json.dump(specification, open(specification_file, "w"), indent=4, separators=(',', ': '))
        
        log_file = self._log_path("request-spot-instances.%03d" % (no))
        
        cmd_template = "{set_cmd};" \
            + "aws ec2 request-spot-instances" \
            + " --instance-count 1" \
            + " --type 'one-time'" \
            + " --launch-specification file://{specification_file}" \
            + " > {log}; sleep 10"
        
        cmd = cmd_template.format(
            set_cmd = self.set_cmd,
            specification_file = specification_file,
            log = log_file
        )

        self._subprocess_call(cmd, no)
        log = self._json_load(log_file)
        request_id = ""
        try:
            request_id = log["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
        except Exception:
            print(ecsub.tools.error_message (self.cluster_name, no, "Failure request-spot-instances."))
            return False
        
        for i in range(3):
            response = self._describe_spot_instances(no, request_id = request_id)
            
            try:
                state = response['State']
                status_code = response['Status']['Code']
                
                if state == "active" and status_code == 'fulfilled':
                    instance_id = response['InstanceId']
                    return self._wait_run_instance(instance_id, no)
                
                elif state == "open" and status_code == 'pending-evaluation':
                    cmd_template = "{set_cmd}; aws ec2 wait spot-instance-request-fulfilled --spot-instance-request-ids {REQUEST_ID}"
                    cmd = cmd_template.format(
                        set_cmd = self.set_cmd,
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
        return False
        
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
                return [None, None, False]

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

        response = boto3.client('ecs').describe_tasks(
            cluster=self.cluster_arn,
            tasks=[task_arn]
        )
        while True:
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
        response["tasks"][0]["disk_size"] = self.aws_ec2_instance_disk_size
        response["tasks"][0]["no"] = no
        response["tasks"][0]["log_local"] = log_file

        def support_datetime_default(o):
            if isinstance(o, datetime.datetime):
                return '%04d/%02d/%02d %02d:%02d:%02d %s' % (o.year, o.month, o.day, o.hour, o.minute, o.second, o.tzname())
            raise TypeError(repr(o) + " is not JSON serializable")

        json.dump(response, open(log_file, "w"), default=support_datetime_default, indent=4, separators=(',', ': '))
        
        exit_code = 1
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
        interrupt = True
        if self.task_param[no]["spot"] == False:
            interrupt = False
        else:
            if exit_code == 0:
                interrupt = False
            else:
                response = self._describe_spot_instances(no, request_id = ec2InstanceId)
                if response == None:
                    interrupt = False
                else:
                    state = response['State']
                    status_code = response['Status']['Code']
                    
                    until_t = ecsub.tools.isoformat_to_datetime(response['ValidUntil'])
                    now_t = datetime.datetime.utcnow()
                    cancel_message = "Spot instance was cancelled. [Status] %s [Code] %s [Message] %s" % (
                            response['State'],
                            response['Status']['Code'],
                            response['Status']['Message'])
                    
                    # spot-instance is running -> task mistake
                    if state == "active" and status_code == 'fulfilled':
                        interrupt = False
                    else:
                        print(ecsub.tools.error_message (self.cluster_name, no, cancel_message))
                    
                        # cancelled by user
                        if state == "cancelled" and status_code == 'instance-terminated-by-user':
                            interrupt = False
                        # spot instance time-out -> long long task
                        elif now_t > until_t:
                            interrupt = False
                        else:
                            interrupt = True
                        
        return [ec2InstanceId, exit_code, interrupt]

    def terminate_instances (self, instance_id, no = None):

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
    
    def cancel_spot_instance_requests (self, no = None, instance_id = None, spot_req_id = None):
        
        log_file = self._log_path("cancel-spot-instance-requests")
        if no != None:
            log_file = self._log_path("cancel-spot-instance-requests.%03d" % (no))
    
        if spot_req_id == None:
            response = self._describe_spot_instances (instance_id = instance_id)
            if response != None:
                state = response['State']
                if state == "active" or state == "open":
                    spot_req_id = response['SpotInstanceRequestId']

        if spot_req_id != None:
            cmd_template = "{set_cmd};" \
                + "aws ec2 cancel-spot-instance-requests --spot-instance-request-ids {spot_req_id} > {log}"

            cmd = cmd_template.format(
                set_cmd = self.set_cmd,
                log = log_file,
                spot_req_id = spot_req_id
            )
            self._subprocess_call(cmd, no)
        
    def clean_up (self):
        
        # terminate instances
        instance_ids = []
        for log_file in glob.glob("%s/log/run-instances.*.log" % (self.wdir)):
            log = self._json_load(log_file)
            instance_ids.append(log["Instances"][0]["InstanceId"])
        
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
                response = boto3.client('ecs').describe_task_definition(taskDefinition=self.task_definition_arn)

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
