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
    Default region name [None]: <REGION>
    Default output format [None]: json
```

Optionally, push your docker image (requires python) to dockerhub or Amazon ECR.

## 4. Run

1) Job submit.

```
ecsub submit \
    --script SCRIPT \
    --tasks  TASKS \
    --aws-s3-bucket AWS_S3_BUCKET \
    [--aws-ec2-instance-type AWS_EC2_INSTANCE_TYPE (default: "t2.micro")] \
    [--disk-size DISK_SIZE (default: 22)] \
    [--aws-security-group-id AWS_SECURITY_GROUP_ID (default: (your "default" security group id))] \
    [--aws-key-name AWS_KEY_NAME (default: (automatic create))] \
    [--wdir WDIR (default: "./")] \
    [--image IMAGE (default: "python:2.7.14")] \
    [--use_amazon_ecr USE_AMAZON_ECR (default: False)] \
    [--shell SHELL (default: "/bin/bash")]
```

For example,

```
ecsub submit \
    --script ./examples/run-wordcount.sh \
    --tasks ./examples/tasks-wordcount.tsv \
    --aws-s3-bucket s3://ecsub-ohaio/output/ \
    --wdir /tmp/ecsub/ \
    --image python:2.7.14 \
    --aws-ec2-instance-type t2.micro \
    --disk-size 22
```

2) View job report.

```
ecsub report ${WDIR}
```

For example,

```
ecsub report /tmp/ecsub/
```

<pre>
|exitCode|                  taskname|no|cpu|memory|instance_type|disk_size|              createdAt|              stoppedAt|                                                  log_local|
|       0|tasks-wordcount-7gqRu_task| 0|  1|   800|     t2.micro|       22|2018/04/02 02:43:26 UTC|2018/04/02 02:44:08 UTC|/tmp/ecsub/tasks-wordcount-7gqRu/log/describe-tasks.000.log|
|     127|tasks-wordcount-Kn8UW_task| 0|  1|   800|     t2.micro|       22|2018/04/02 02:38:28 UTC|2018/04/02 02:38:37 UTC|/tmp/ecsub/tasks-wordcount-Kn8UW/log/describe-tasks.000.log|
</pre>

## 5. Documentation

 - [document](./docs/AWS-ECS.pdf)
 - [ecsub flow](./docs/ecsub-flow.png)

## 6. License 

See document [LICENSE](./LICENSE).
