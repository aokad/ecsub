[![Build Status](https://travis-ci.org/aokad/ecsub.svg?branch=master)](https://travis-ci.org/aokad/ecsub)
![Python](https://img.shields.io/badge/python-2.7-blue.svg)
![Python](https://img.shields.io/badge/python-3.x-blue.svg)

# ecsub

## 1. Dependency

 - python >= 2.7
 - [awscli](https://docs.aws.amazon.com/streams/latest/dev/kinesis-tutorial-cli-installation.html)
 - [boto3](https://github.com/boto/boto3)

## 2. Install

Dependent packages are installed automatically.

```Bash
git clone https://github.com/aokad/ecsub.git
cd ecsub
python setup.py build install
```

## 3. Setup

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

## 4. Run

### 1) Job submit.

```Bash
ecsub submit \
    --script SCRIPT \
    --tasks  TASKS \
    --aws-s3-bucket AWS_S3_BUCKET \
    [--aws-ec2-instance-type AWS_EC2_INSTANCE_TYPE] \
    [--disk-size DISK_SIZE] \
    [--aws-security-group-id AWS_SECURITY_GROUP_ID )] \
    [--aws-key-name AWS_KEY_NAME] \
    [--aws-subnet-id AWS_SUBNET_ID] \
    [--wdir WDIR] \
    [--image IMAGE] \
    [--use_amazon_ecr USE_AMAZON_ECR] \
    [--shell SHELL] \
    [--task-name TASK_NAME]

optional arguments:
  --wdir WDIR                     output temporary data (default: "./")
  --image IMAGE                   docker image (default: "python:2.7.14")
  --use_amazon_ecr                use_amazon_ecr (default: False)
  --shell SHELL                   path to "bash" or "ash" (or "dash", ...) in docker-container (default: "/bin/bash")
  --task-name TASK_NAME           submit name as AWS ECS cluster name (default: ${filename of "tasks" option}-${random 5 letters})
  --aws-ec2-instance-type TYPE    AWS instance type (default: "t2.micro")
  --disk-size DISK_SIZE           AWS disk size (Gib) (default: 22)
  --aws-security-group-id SG_ID   AWS your security_group_id (default: (your "default" security group id)
  --aws-key-name KEY_NAME         AWS your key pair name (default: (automatic create))
  --aws-subnet-id SUBNET_ID       AWS your subnet_id (default: (your "default" VPC's "default" subnet id)
```

For example,

```Bash
bucket=s3://yourbucket
ecsub_root={download_path}
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

```Bash
ecsub logs \
    [--wdir WDIR] \
    [--prefix PREFIX] \
    [--remove]

optional arguments:
  --wdir WDIR      {PATH} when 'ecsub submit --wdir {PATH}' (default: "./")
  --prefix PREFIX  prefix of LogGroupName in AWS CloudWatch (default: "ecsub")
  --remove         flag for remove from AWS (default: False)
```

For example,

```Bash
ecsub logs --wdir /tmp/ecsub --remove
```

## 5. Documentation

 - [document](./docs/AWS-ECS.pdf)
 - [ecsub flow](./docs/ecsub-flow.png)

## 6. License 

See document [LICENSE](./LICENSE).
