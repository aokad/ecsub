[![Build Status](https://travis-ci.org/aokad/ecsub.svg?branch=master)](https://travis-ci.org/aokad/ecsub)
![Python](https://img.shields.io/badge/python-2.7-blue.svg)
![Python](https://img.shields.io/badge/python-3.x-blue.svg)

# ecsub

## 1. Dependency

 - python >= 2.7
 - [awscli](https://docs.aws.amazon.com/streams/latest/dev/kinesis-tutorial-cli-installation.html)
 - [boto3](https://github.com/boto/boto3)
 - six

## 2. Install

Dependent packages are installed automatically.

```Bash
git clone https://github.com/aokad/ecsub.git
cd ecsub
python setup.py build install
```

## 3. Setup

### 3.1 local machine

First, set up `aws configure`.

```Bash
aws configure
    AWS Access Key ID [None]: <YOUR ACCESS KEY>
    AWS Secret Access Key [None]: <YOUR SECRET ACCESS KEY>
    Default region name [None]: <REGION>
    Default output format [None]: json
```

Next, create your S3_bucket, as follows.

```Bash
aws s3 mb s3://yourbucket
```

Optionally, push your docker image (requires python) to dockerhub or Amazon ECR.

### 3.2 AWS IAM

UserGroup:

1. Create "ecsub-user" group, then attach the following policies.

 - AmazonEC2FullAccess
 - S3_S3FullAccess (It is better to limit "Resource:")
 - AmazonECS_FullAccess
 - AWSPriceListServiceFullAccess 
 - CloudWatchLogsFullAccess
 - CloudWatchReadOnlyAccess

Role:

1. Create "ecsInstanceRole" role with AWS EC2, then attach the following policies.

 - AmazonEC2ContainerServiceforEC2Role
 - S3_S3FullAccess
 - CloudWatchMetricFullAccess（create yourself. Choose "CloudWatch:\*Metric\*"）

2. Edit trust, add "allow ecs-tasks"

```Json
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": ["ecs-tasks.amazonaws.com", "ec2.amazonaws.com"]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 4. Run

### 1) Job submit.

```
ecsub submit \
    --script SCRIPT \
    --tasks TASKS \
    --aws-s3-bucket AWS_S3_BUCKET
    [--image IMAGE] \
    [--aws-ec2-instance-type INSTANCE_TYPE] \
    [--disk-size DISK_SIZE]

optional arguments:
  --aws-ec2-instance-type INSTANCE_TYPE
                                  AWS instance type
  --aws-ec2-instance-type-list INSTANCE_TYPE_LIST 
                                  [spot] AWS instance types, split with ','
  --aws-key-name KEY_NAME         Your AWS key pair name
  --aws-s3-bucket S3_BUCKET       Your AWS S3 bucket
  --aws-security-group-id SECURITY_GROUP_ID
                                  Your AWS security_group_id
  --aws-subnet-id SUBNET_ID       AWS subnet_id
  --disk-size DISK_SIZE           AWS disk size (GiB)
  --image IMAGE                   docker image
  --memory MEMORY                 Memory used by AWS ECS task (MB)
  --retry-od                      [spot] In case of failure, retry on demand instance
  --script SCRIPT                 run script
  --shell SHELL                   path to bash or ash in docker-container
  --spot                          [spot] use spot instance
  --task-name TASK_NAME           submit name as AWS ECS cluster name
  --tasks TASKS                   parameters
  --use_amazon_ecr                use_amazon_ecr
  --vcpu VCPU                     vCpu used by AWS ECS task
  --wdir WDIR                     output temporary data
  -h, --help                      show this help message and exit
```

For example,

```Bash
bucket=s3://{yourbucket_name}
ecsub_root={ecsub_download_path}
ecsub submit \
    --script ${ecsub_root}/examples/run-wordcount.sh \
    --tasks ${ecsub_root}/examples/tasks-wordcount.tsv \
    --aws-s3-bucket ${bucket}/output/ \
    --wdir /tmp/ecsub/ \
    --image python:2.7.14 \
    --aws-ec2-instance-type t2.micro \
    --disk-size 22
```

### 2) View job report.

```Bash
ecsub report \
    [--wdir WDIR]

optional arguments:
  --wdir WDIR      {PATH} when 'ecsub submit --wdir {PATH}' (default: "./")
```

For example,

```Bash
ecsub report --wdir /tmp/ecsub/
```

<pre>
|exitCode|                  taskname|no|cpu|memory|instance_type|disk_size|              createdAt|              stoppedAt|                                                  log_local|
|       0|tasks-wordcount-7gqRu_task| 0|  1|   800|     t2.micro|       22|2018/04/02 02:43:26 UTC|2018/04/02 02:44:08 UTC|/tmp/ecsub/tasks-wordcount-7gqRu/log/describe-tasks.000.log|
|     127|tasks-wordcount-Kn8UW_task| 0|  1|   800|     t2.micro|       22|2018/04/02 02:38:28 UTC|2018/04/02 02:38:37 UTC|/tmp/ecsub/tasks-wordcount-Kn8UW/log/describe-tasks.000.log|
</pre>

### 3) Download log files

ecsub creates logs on AWS CloudWatch.
If you need, you can download log-files to local directory, and remove log-streams from AWS.

```
ecsub logs \
    [--wdir WDIR] \
    [--prefix PREFIX] \
    [--remove]

optional arguments:
  --wdir WDIR      {PATH} when 'ecsub submit --wdir {PATH}' (default: "./")
  --prefix PREFIX  prefix of LogGroupName in AWS CloudWatch (default: "ecsub")
  --dw         flag for download from AWS (default: False)
  --rm         flag for remove from AWS (default: False)
```

For example,

```Bash
ecsub logs --wdir /tmp/ecsub --prefix tasks-wordcount --dw
```

## 5. Documentation

 - [document](./docs/AWS-ECS.pdf)
 - [ecsub flow](./docs/ecsub-flow.png)

## 6. License 

See document [LICENSE](./LICENSE).
