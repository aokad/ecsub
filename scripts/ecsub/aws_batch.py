# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 15:06:50 2018

@author: Okada
"""

import json
import os
import datetime
import time
import boto3
import ecsub.ansi
import ecsub.aws_config
import ecsub.tools
import base64
import ecsub.cf_template

def json_dump(obj, file_path):
    def support_datetime_default(o):
        if isinstance(o, datetime.datetime):
            return '%04d/%02d/%02d %02d:%02d:%02d %s' % (o.year, o.month, o.day, o.hour, o.minute, o.second, o.tzname())
        raise TypeError(repr(o) + " is not JSON serializable")

    json.dump(obj, open(file_path, "w"), default=support_datetime_default, indent=4, separators=(',', ': '))
    
class Aws_ecsub_control:

    def __init__(self, params, task_num):
        
        self.wdir = params["wdir"].rstrip("/")
        self.job_name = params["job_name"]
        self.job_queue_id = ""
        self.job_definition_id = ""
        self.stack_id = ""
        self.cluster_arn = ""
        
        # Flags
        self.wait = params["wait"]
        self.spot = params["spot"]
        self.gpu = params["gpu"]
        self.dind = params["dind"]
        
        # aws account
        self.account_id = params["account_id"]
        if self.account_id == "":
            self.account_id = self._get_aws_account_id()
        
        # default region
        self.region = params["region"]
        if self.region == "":
            self.region = self._get_region()
    
        # compute env
        self.key_auto = ""
        self.key_name = params["key_name"]
        
        self.security_groups = params["security_groups"].split(",")
        if "" in self.security_groups:
            self.security_groups.remove("")
        self.subnet_ids = params["subnet_ids"].split(",")
        if "" in self.subnet_ids:
            self.subnet_ids.remove("")
            
        self.ami_id = ecsub.aws_config.get_ami_id(self.gpu)
        
        self.vcpu = params["vcpu"]
        self.memory = params["memory"] * 1000
        self.disk_size = params["disk_size"]
        self.root_disk_size = params["root_disk_size"]
        self.disk_type = params["disk_type"]
        self.root_disk_type = params["root_disk_type"]
        self.instance_types = params["instance_types"]
        
        # container image        
        self.image = params["image"]
        self.use_amazon_ecr = params["use_amazon_ecr"]
        self.setx = params["setx"]
        self.shell = params["shell"]
        self.setup_container_cmd = params["setup_container_cmd"]
        if self.setup_container_cmd == "":
            self.setup_container_cmd = "apt update; apt install -y python-pip; pip install awscli --upgrade; aws configure list"
        
        # log group
        self.log_group_name = params["log_group_name"]
        if self.log_group_name == "":
            self.log_group_name = "ecsub-" + self.job_name
        
        # S3 env
        self.s3_runsh = ""
        self.s3_script = ""
        self.s3_setenv = []
        self.s3_downloader = []
        self.s3_uploader = []
        self.request_payer_bucket = []
        self.request_payer_bucket.extend(params["request_payer_bucket"])
        
        # tasks
        self.task_num = task_num
        self.env_options = []
        if "env_options" in params:
            self.env_options.extend(params["env_options"])
        
        self.prices = {"ebs": {}, "ec2": {}, "spot": {}}
    
    def check_awsconfigure(self):
        if ecsub.aws_config.region_to_location(self.region) == None:
            print(ecsub.tools.error_message (self.job_name, None, "region '%s' can not be used in ecsub." % (self.region)))
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
        if not _check_role("AmazonECSTaskS3FullAccess", "ecs-tasks.amazonaws.com", self.job_name):
        
            result = False
            
        if not _check_role("ecsInstanceRole", "ec2.amazonaws.com", self.job_name):
            result = False

        return result

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
        response = boto3.client('sts').get_caller_identity()
        return response['Account']
        
    def _get_region(self):
        return boto3.session.Session().region_name
        
    def _check_keypair (self, key_name):
        try:
            response = boto3.client('ec2').describe_key_pairs(KeyNames=[key_name])
            if len(response["KeyPairs"]) > 0:
                return True
        except Exception as e:
            print(ecsub.tools.error_message (self.job_name, None, e))
            
        return False  
        
    def set_keypair(self):
        if self.key_name != "":
            return self._check_keypair(self.key_name)
            
        try:
            key_pair = boto3.resource('ec2').create_key_pair(KeyName=self.job_name)
        except Exception as e:
            print(e)
            print(ecsub.tools.error_message (self.job_name, None, "Failure to create key pair."))
            return False
        
        self.key_auto = key_pair.key_name
        self.key_name = key_pair.key_name
        return True
    
    def set_vpc_resources(self):
        
        client = boto3.client('ec2')
        vpc_sg = ""
        vpc_subnet = ""
        
        # check entered security groups
        if len(self.security_groups) > 0:
            response = client.describe_security_groups(GroupIds=self.security_groups)

            groups = []
            vpcs = []
            for s in response['SecurityGroups']:
                groups.append(s['GroupId'])
                vpcs.append(s['VpcId'])
            
            vpc = list(set(vpcs))
            if len(vpc) > 1:
                print(ecsub.tools.warning_message (self.job_name, None, "Security group ids are associated with a different VPC."))
                return False
            
            for s in self.security_groups:
                if not s in groups:
                    print(ecsub.tools.warning_message (self.job_name, None, "Security group id '%s' is invalid." % (s)))
                    return False
            vpc_sg = vpc[0]
        
        # check entered subnet id
        if len(self.subnet_ids) > 0:
            response = client.describe_subnets(
                Filters=[{'Name': 'subnet-id', 'Values': [self.subnet_ids]}]
            )
            subnets = []
            vpcs = []
            for s in response['Subnets']:
                subnets.append(s['SubnetId'])
                vpcs.append(s['VpcId'])
            
            vpc = list(set(vpcs))
            if len(vpc) > 1:
                print(ecsub.tools.warning_message (self.job_name, None, "Subnet id are associated with a different VPC."))
                return False
            
            for s in self.subnet_ids:
                if not s in subnets:
                    print(ecsub.tools.warning_message (self.job_name, None, "Subnet id '%s' is invalid." % (s)))
                    return False
            vpc_subnet = vpc[0]

        # same VPC?
        if vpc_sg != "" and vpc_subnet != "":
            if vpc_sg == vpc_subnet:
                return True
            else:
                print(ecsub.tools.warning_message (self.job_name, None, "Subnet id and Security group are associated with a different VPC."))
                return False
        elif vpc_sg != "":
            vpc_id = vpc_sg
        elif vpc_subnet != "":
            vpc_id = vpc_subnet
        else:
            # use default VPC
            response = client.describe_vpcs(
                Filters=[{'Name': 'isDefault', 'Values': ["true"]}]
            )
            if len(response['Vpcs']) == 0:
                print(ecsub.tools.error_message (self.job_name, None, "Default VPC is not exist."))
                return False
            vpc_id = response['Vpcs'][0]['VpcId']            
            
        # use default security group
        if vpc_sg == "":
            response = client.describe_security_groups(GroupNames=["default"])
            for s in response['SecurityGroups']:
                if vpc_id == s['VpcId']:
                    self.security_groups.append(s['GroupId'])
                
            if len(response['SecurityGroups']) == 0:
                print(ecsub.tools.error_message (self.job_name, None, "Default SecurityGroupId is not exist in vpc %s." % (vpc_id)))
                return False

        # set subnet
        if vpc_subnet == "":
            response = client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            for s in response['Subnets']:
                self.subnet_ids.append(s['SubnetId'])
            
            if len(self.subnet_ids) == 0:
                print(ecsub.tools.error_message (self.job_name, None, "Subnet of default VPC is not exist."))
                return False

        return True
        
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
    
    def _userdata(self):
        return """Content-Type: multipart/mixed; boundary="==BOUNDARY=="
MIME-Version: 1.0

--==BOUNDARY==
Content-Type: text/cloud-boothook; charset="us-ascii"

# Install nfs-utils
cloud-init-per once yum_update yum update -y
cloud-init-per once install_tr yum install -y tr
cloud-init-per once install_td yum install -y td
cloud-init-per once install_python37_pip yum install -y python37-pip
cloud-init-per once install_awscli pip install awscli

cat << EOF > /root/metricscript.sh
AWSREGION={region}
AWSINSTANCEID=\$(curl -ss http://169.254.169.254/latest/meta-data/instance-id)

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
""".format(region = self.region)
    
    def set_ondemand_price (self, instance_type):

        def get_ondemand_price (region, instance_type):
            response = boto3.client('pricing', region_name = "ap-south-1").get_products(
                ServiceCode='AmazonEC2',
                Filters = [
                    {'Type' :'TERM_MATCH', 'Field':'instanceType',    'Value': instance_type},
                    {'Type' :'TERM_MATCH', 'Field':'location',        'Value': ecsub.aws_config.region_to_location(region)},
                    {'Type' :'TERM_MATCH', 'Field':'operatingSystem', 'Value': 'Linux'},
                    {'Type' :'TERM_MATCH', 'Field':'tenancy',         'Value': 'Shared'},
                    {'Type' :'TERM_MATCH', 'Field':'preInstalledSw',  'Value': 'NA'},
                    {'Type' :'TERM_MATCH', 'Field':'capacitystatus',  'Value': 'Used'},
                ],
                MaxResults=100
            )
            
            values = []
            for i in range(len(response["PriceList"])):
                obj = json.loads(response["PriceList"][i])
                for key1 in obj["terms"]["OnDemand"].keys():
                    for key2 in obj["terms"]["OnDemand"][key1]["priceDimensions"].keys():
                        values.append(float(obj["terms"]["OnDemand"][key1]["priceDimensions"][key2]["pricePerUnit"]["USD"]))
            
            values.sort()
            if len(values) > 0:
                return values[-1]
            return 0
    
        if instance_type in self.prices["ec2"]:
            return True
        
        od_price = get_ondemand_price(self.region, instance_type)
        self.prices["ec2"][instance_type] = od_price
        
        if od_price == 0:
            print(ecsub.tools.error_message (self.job_name, None, "Failure get on-demand instance price, instance-type %s." % (instance_type)))
            return False
        print(ecsub.tools.info_message (self.job_name, None, "Instance Type: %s, Ondemand Price: $%.3f" % (instance_type, od_price)))
        return True
    
    def set_spot_price (self, instance_type, az):
        
        def get_spot_price (instance_type, az):
            now = datetime.datetime.utcnow()
            start_dt = now - datetime.timedelta(days = 1)
            response = boto3.client('ec2').describe_spot_price_history(
                Filters = [
                    {"Name": 'product-description', "Values": ['Linux/UNIX']},
                    {"Name": 'availability-zone', "Values": [az]}
                ],
                InstanceTypes = [instance_type],
                MaxResults = 100,
                StartTime = start_dt,
                EndTime = now,
            )
            log_file = self._log_path("describe_spot_price_history")
            json_dump(response, log_file)
            
            spot_price = 0
            last_date = None
            for his in response["SpotPriceHistory"]:
                if last_date == None or last_date < his['Timestamp']:
                    spot_price = float(his['SpotPrice'])
                    last_date = his['Timestamp']
            return spot_price 
            
        if instance_type in self.prices["spot"] and az in self.prices["spot"]:
            return True
        
        spot_price = get_spot_price(instance_type, az)
        if not instance_type in self.prices["spot"]:
            self.prices["spot"][instance_type] = {}
        self.prices["spot"][instance_type][az] = spot_price
        
        if spot_price == 0:
            print(ecsub.tools.error_message (self.job_name, None, "Failure get spot instance price, instance-type %s, availability-zone: %s" % (instance_type, az)))
            return False
        print(ecsub.tools.info_message (self.job_name, None, "Spot Price: $%.3f, Availality Zone: %s" % (spot_price, az)))
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
        
        default_type = "gp2"
        price = _get_ebs_price (self.region, default_type)
        self.prices["ebs"][default_type] = price
        print(ecsub.tools.info_message (self.job_name, None, "Disk Price: $%.3f per GB-month of %s" % (price, default_type)))
        
        if self.root_disk_type != default_type:
            price = _get_ebs_price (self.region, self.root_disk_type)
            self.prices["ebs"][self.root_disk_type] = price
            print(ecsub.tools.info_message (self.job_name, None, "Disk Price: $%.3f per GB-month of %s" % (price, self.root_disk_type)))
            
        if self.disk_type != default_type and self.disk_type != self.root_disk_type:
            price = _get_ebs_price (self.region, self.disk_type)
            self.prices["ebs"][self.disk_type] = price
            print(ecsub.tools.info_message (self.job_name, None, "Disk Price: $%.3f per GB-month of %s" % (price, self.disk_type)))
            
        return True
 
    def save_summary(self, no, job):
        def _hour_delta(start_t, end_t):
            if type(start_t) == int:
                return (end_t - start_t)/3600.0
            return (end_t - start_t).total_seconds()/3600.0

        def _describe_instance (instance_id):
            response = boto3.client('ec2').describe_instances(
                InstanceIds = [instance_id]
            )
            log_file = self._log_path("describe_instances.%03d" % (no))
            json_dump(response, log_file)
            return response["Reservations"][0]["Instances"][0]
    
        def _describe_container_instance (container_instance_id):
            def _list_clusters(cluster_prefix, next_token = None):
                if next_token == None:
                    response = boto3.client('ecs').list_clusters()
                else:
                    response = boto3.client('ecs').list_clusters(nextToken=next_token)
                for cluster in response['clusterArns']:
                    if cluster.split("/")[1].startswith(cluster_prefix):
                        return (cluster, None)
                if 'nextToken' in response:
                    return (None, response['nextToken'])
                return (None, None)
            
            if self.cluster_arn == "":
                next_token = None
                while True:
                    (cluster, next_token) = _list_clusters(self.job_name, next_token)
                    if cluster != None:
                        self.cluster_arn = cluster
                        break
                    if next_token == None:
                        return None
                    
            response = boto3.client('ecs').describe_container_instances(
                cluster = self.cluster_arn,
                containerInstances = [container_instance_id]
            )
            log_file = self._log_path("describe_container_instances.%03d" % (no))
            json_dump(response, log_file)
            return response["containerInstances"][0]

        def _describe_volumes(volume_ids):
            response = boto3.client("ec2").describe_volumes(
                VolumeIds=volume_ids,
            )
            log_file = self._log_path("describe_volumes.%03d" % (no))
            json_dump(response, log_file)
            return response["Volumes"]
        
        wtime = _hour_delta(job["startedAt"], job["stoppedAt"])
        messages = []
        
        # instance prices
        cont_info = _describe_container_instance(job["container"]["containerInstanceArn"])
        if cont_info == None:
            print(ecsub.tools.error_message (self.job_name, no, "failure create summary"))
            return
        
        inst_info = _describe_instance(cont_info["ec2InstanceId"])
        itype = inst_info['InstanceType']
        az = inst_info['Placement']['AvailabilityZone']
        
        self.set_ondemand_price (itype)
        
        if self.spot:
            self.set_spot_price (itype, az)
            instance_price = self.prices["spot"][itype][az] * wtime
            template_ec2 = " + instance: $%.3f, instance-type %s (spot) $%.3f (if ondemand: $%.3f) per Hour, running-time %.3f Hour"
            messages.append(template_ec2 % (instance_price, itype, self.prices["spot"][itype][az], self.prices["ec2"][itype], wtime))
        else:
            instance_price = self.prices["ec2"][itype] * wtime
            template_ec2 = " + instance: $%.3f, instance-type %s (ondemand) $%.3f per Hour, running-time %.3f Hour"
            messages.append(template_ec2 % (instance_price, itype, self.prices["ec2"][itype], wtime))
        
        # disk prices
        volume_ids = []
        for mapping in inst_info["BlockDeviceMappings"]:
            volume_ids.append(mapping["Ebs"]["VolumeId"])
            
        disk_price = 0.0
        template_ebs = " + volume %s (%s): $%.3f, attached %d (GiB), $%.3f per GB-month, running-time %.3f Hour"
        if len(volume_ids) > 0:
            vol_info = _describe_volumes(volume_ids)
            for v in vol_info:
                vprice = v["Size"] * self.prices["ebs"][v['VolumeType']] * wtime / 24 / 30
                disk_price += vprice
                messages.append(template_ebs % (v["Attachments"][0]["Device"], v['VolumeType'], vprice, v["Size"], self.prices["ebs"][v['VolumeType']], wtime))
        
        # total price        
        total_price = disk_price + instance_price
        
        # print messages
        message = "The cost of this task is $%.3f." % (total_price)
        print(ecsub.tools.info_message (self.job_name, no, message))
        for message in messages:
            print(ecsub.tools.info_message (self.job_name, no, message))
        
        # output summary
        summary = {}
        for key in self.__dict__.keys():
            summary[key] = self.__dict__[key]
        
        summary["no"] = no
        summary["job_id"] = job["jobId"]
        summary["crated_at"] = job["createdAt"]
        summary["started_at"] = job["startedAt"]
        summary["stopped_at"] = job["stoppedAt"]
        summary["work_hours"] = float("%.5f" % (wtime))
        
        summary["status"] = job["status"]
        summary["exit_code"] = job["container"]["exitCode"]
        summary["log_stream_name"] = job["container"]["logStreamName"]
        
        summary["instance_type"] = itype
        summary["availability_zone"] = az
        summary["instance_price"] = float("%.5f" % (instance_price))
        summary["disk_price"] = float("%.5f" % (disk_price))
        summary["total_price"] = float("%.5f" % (total_price))
               
        log_file = self._log_path("summary.%03d" % (no))
        json_dump(summary, log_file)
    
    def create_batch_env(self):
        
        # set key-pair
        if self.set_keypair() == False:
            return False
        
        # set security-group and subnet id
        if self.set_vpc_resources() == False:
            return False
        
        if self.set_ebs_price() == False:
            return False
        
        IMAGE_ARN = self.image
        if self.use_amazon_ecr:
            IMAGE_ARN = "{account_id}.dkr.ecr.{region}.amazonaws.com/{image}".format(
                account_id = self.account_id,
                region = self.region,
                image = self.image)
        
        option = ""
        if ecsub.tools.is_request_payer_bucket(self.s3_runsh, self.request_payer_bucket):
            option = "--request-payer requester "
        
        cr_type = "EC2"
        if self.spot:
            cr_type = "SPOT"
            
        template = ecsub.cf_template.template
        
        tmp_params = template["Parameters"]
        tmp_params["JobName"]["Default"] = self.job_name
        tmp_params["InstanceTypes"]["Default"]  = self.instance_types
        tmp_params["vCPUs"]["Default"]  = self.vcpu
        tmp_params["Memory"]["Default"] = self.memory
        tmp_params["VolumeSize"]["Default"] = self.disk_size
        tmp_params["ContainerImage"]["Default"] = IMAGE_ARN
        tmp_params["AutoKey"]["Default"] = self.key_auto
        
        tmp_launch = template["Resources"]["LaunchTemplate"]["Properties"]["LaunchTemplateData"]
        tmp_launch["BlockDeviceMappings"][0]["Ebs"]["VolumeSize"] = self.root_disk_size
        tmp_launch["BlockDeviceMappings"][0]["Ebs"]["VolumeType"] = self.root_disk_type
        tmp_launch["BlockDeviceMappings"][1]["Ebs"]["VolumeType"] = self.disk_type
        tmp_launch["UserData"] = base64.b64encode(self._userdata().encode()).decode()
        
        tmp_env = template["Resources"]["ComputeEnvironment"]["Properties"]
        tmp_env["ComputeResources"]["Ec2KeyPair"] = self.key_name
        tmp_env["ComputeResources"]["ImageId"] = self.ami_id
        tmp_env["ComputeResources"]["InstanceRole"] = "ecsInstanceRole"
        tmp_env["ComputeResources"]["MaxvCpus"] = self.vcpu * self.task_num
        tmp_env["ComputeResources"]["SecurityGroupIds"] = self.security_groups
        tmp_env["ComputeResources"]["Subnets"] = self.subnet_ids
        tmp_env["ComputeResources"]["SpotIamFleetRole"] = "arn:aws:iam::%s:role/AmazonEC2SpotFleetRole" % (self.account_id)
        tmp_env["ComputeResources"]["Type"] = cr_type
        tmp_env["ServiceRole"] = "arn:aws:iam::%s:role/service-role/AWSBatchServiceRole" % (self.account_id)
        
        tmp_def = template["Resources"]["JobDefinition"]["Properties"]["ContainerProperties"]
        tmp_def["JobRoleArn"] = "arn:aws:iam::%s:role/ecsInstanceRole" % (self.account_id)
        tmp_def["Command"] = [self.shell, "-c", self.setup_container_cmd + "; aws s3 cp " + option + self.s3_runsh + " /run.sh; " + self.shell + " /run.sh"]
        
        if self.dind:
            tmp_def["MountPoints"].append(
                {
                    "SourceVolume": "dockersock",
                    "ContainerPath": "/var/run/docker.sock"
                }
            )
            tmp_def["Volumes"].append(
                {
                    "Name": "dockersock",
                    "Host": {"SourcePath": "/var/run/docker.sock"}
                }
            )
        
        for env in tmp_def["Environment"]:
            if env["Name"] == "SCRIPT_RUN_PATH":
                env["Value"] = self.s3_script
            elif env["Name"] == "AWS_DEFAULT_REGION":
                env["Value"] = self.region
        
        #create
        client = boto3.client('cloudformation')
        log_file = self._log_path("create_stack")
        json_dump(template, log_file)
            
        try:
            print(ecsub.tools.info_message (self.job_name, None, "boto3.client('cloudformation').create_stack()"))
            response = client.create_stack(
                StackName=self.job_name,
                TemplateBody=json.dumps(template)
            )
            self.stack_id = response['StackId']
            print(ecsub.tools.info_message (self.job_name, None, "boto3.client('cloudformation').get_waiter('stack_create_complete').wait()"))
            client.get_waiter('stack_create_complete').wait(
                StackName = self.stack_id,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 5}
            )
            log_file = self._log_path("describe_stacks")
            json_dump(client.describe_stacks(StackName=self.job_name), log_file)
            
        except Exception as e:
            print(ecsub.tools.error_message (self.job_name, None, "failure to create AWS Batch environment."))
            print(ecsub.tools.error_message (self.job_name, None, e))
            if self.stack_id != "":
                stack_events = client.describe_stack_events(
                    StackName=self.stack_id
                )
                for event in stack_events["StackEvents"]:
                    if event['ResourceStatus'] == 'CREATE_FAILED':
                        print(ecsub.tools.error_message (self.job_name, None, 
                            "ResourceType: %s, ResourceStatusReason: %s" % (event['ResourceType'], event['ResourceStatusReason'])
                        ))
                log_file = self._log_path("describe_stack_events")
                json_dump(stack_events, log_file)
            return False
        
        self.job_queue_id = client.describe_stack_resource(
            StackName=self.job_name, LogicalResourceId="JobQueue"
        )['StackResourceDetail']['PhysicalResourceId']
        
        self.job_definition_id = client.describe_stack_resource(
            StackName=self.job_name, LogicalResourceId="JobDefinition"
        )['StackResourceDetail']['PhysicalResourceId']
        
        return True
        
    def submit_job (self, no):
        """
        exit_code: 0    Success
        exit_code: 1    Error
        """
        
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
        
        print(ecsub.tools.info_message (self.job_name, no, "boto3.client('batch').submit_job()"))
        response = boto3.client('batch').submit_job(
            jobName = "%s_%d" % (self.job_name, no),
            jobQueue = self.job_queue_id,
            jobDefinition = self.job_definition_id,
            containerOverrides={
                "environment": environment,
            },
        )
        log_file = self._log_path("submit_job.%03d" % (no))
        json_dump(response, log_file)
        
        job_id = response['jobId']
        response = boto3.client('batch').describe_jobs(jobs=[job_id])
        log_file = self._log_path("describe_jobs.%03d" % (no))
        json_dump(response, log_file)
        
        print_log = True
        while True:
            if len(response["jobs"]) == 0:
                return 1
            
            if print_log:
                try:
                    stream = response["jobs"][0]["container"]["logStreamName"]
                
                    log_html = "https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logEventViewer:group={group};stream={stream}".format(
                        region = self.region,
                        group = "/aws/batch/job",
                        stream = stream
                    )
                    print(ecsub.tools.info_message (self.job_name, None, "job status is %s" % (response["jobs"][0]['status'])))
                    print(ecsub.tools.message (self.job_name, no, [{"text": " For detail, see log-file: "}, {"text": log_html, "color": ecsub.tools.get_title_color(no)}]))
                    print_log = False
                    if self.wait == False:
                        return 0
                
                except Exception:
                    pass
            if response["jobs"][0]['status'] in ['SUCCEEDED', 'FAILED']:
                break
            
            #print(ecsub.tools.info_message (self.job_name, no, "waiting for job to finish"))
            time.sleep(10)
            response = boto3.client('batch').describe_jobs(jobs=[job_id])
            json_dump(response, log_file)
            
        print (ecsub.tools.info_message (self.job_name, no, "job-stopped with [%s]" % (response["jobs"][0]["status"])))
        #log_file = self._log_path("describe_jobs.%03d" % (no))
        
        # calc_cost
        self.save_summary(no, response["jobs"][0])

        if response["jobs"][0]["status"] == "SUCCEEDED":
            return 0
        else:
            print (ecsub.tools.info_message (self.job_name, no, "statusReason1: %s" % (response["jobs"][0]["statusReason"])))
            print (ecsub.tools.info_message (self.job_name, no, "statusReason2: %s" % (response["jobs"][0]["attempts"][0]["container"]["statusReason"])))
        
        return 1
        
    def clean_up (self):
        if self.stack_id != "":
            client = boto3.client('cloudformation')
            print(ecsub.tools.info_message (self.job_name, None, "boto3.client('cloudformation').delete_stack()"))
            client.delete_stack(StackName = self.stack_id)
            print(ecsub.tools.info_message (self.job_name, None, "boto3.client('cloudformation').get_waiter('stack_delete_complete').wait()"))
            client.get_waiter('stack_delete_complete').wait(
                StackName = self.stack_id,
                WaiterConfig = {
                    'Delay': 30,
                    'MaxAttempts': 120
                }
            )
        # delete ssh key pair
        if self.key_auto != "":
            print(ecsub.tools.info_message (self.job_name, None, "boto3.client('ec2').delete_key_pair()"))
            boto3.client('ec2').delete_key_pair(KeyName=self.key_auto)
    
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
