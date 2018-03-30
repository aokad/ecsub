[![Build Status](https://travis-ci.org/aokad/ecsub.svg?branch=master)](https://travis-ci.org/aokad/ecsub)
![Python](https://img.shields.io/badge/python-2.7-blue.svg)
![Python](https://img.shields.io/badge/python-3.x-blue.svg)

# ecsub

## 1. Dependency

 - python >= 2.7
 - [awscli](https://docs.aws.amazon.com/streams/latest/dev/kinesis-tutorial-cli-installation.html)
 - [boto3](https://github.com/boto/boto3)

## 2. Install

```
git clone https://github.com/aokad/ecsub.git
cd ecsub
python setup.py build install
```

## 3. Setup

```
aws configure
    AWS Access Key ID [None]: <YOUR ACCESS KEY>
    AWS Secret Access Key [None]: <YOUR SECRET ACCESS KEY>
    Default region name [None]: us-west-2
    Default output format [None]: json
```

Push your docker image to dockerhub or Amazon ECR.

-------------------------------------------------------------------------

## 4. Run

Job submit

```
ecsub submit
    --script SCRIPT \
    --tasks  TASKS \
    --aws-s3-bucket AWS_S3_BUCKET \
    [--aws-ec2-instance-type AWS_EC2_INSTANCE_TYPE (default: "t2.micro")] \
    [--disk-size DISK_SIZE (default: 22)] \
    [--aws-security-group-id AWS_SECURITY_GROUP_ID (default: (your "default" security group id))] \
    [--aws-key-name AWS_KEY_NAME (default: (automatic create))] \
    [--wdir WDIR (default: "./")] \
    [--image IMAGE (default: "ubuntu:latest")] \
    [--use_amazon_ecr USE_AMAZON_ECR (default: False)] \
    [--shell SHELL (default: "/bin/bash")]
```

View job report

```
ecsub submit ${WDIR}
```

## 5. License 

See document LICENSE.
