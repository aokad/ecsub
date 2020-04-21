[![Build Status](https://travis-ci.org/aokad/ecsub.svg?branch=master)](https://travis-ci.org/aokad/ecsub)
![Python](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue.svg)

# ecsub

## 1. Dependency

 - [awscli](https://docs.aws.amazon.com/streams/latest/dev/kinesis-tutorial-cli-installation.html)
 - [boto3](https://github.com/boto/boto3)

## 2. Install

Dependent packages are installed automatically.

```Bash
git clone https://github.com/aokad/ecsub.git -b batch
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
 - AmazonECS_FullAccess
 - S3_S3FullAccess (It is better to limit "Resource:")
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
$ ecsub batch --help
usage: ecsub batch [-h] --script path/to/script.sh --tasks path/to/tasks.tsv
                   [--task_name task-name] [--wdir path/to/dir]
                   [--image docker/image:tag] [--shell path/to/bash]
                   [--setup_container_cmd "pip install awscli"] --s3_bucket
                   s3://output/bucket [--instance_types c4.large,m5large]
                   [--vcpu 2] [--memory 8] [--disk_size 22] [--processes 20]
                   [--security_groups sg-ab123456] [--key_name key-123ab]
                   [--subnet_ids subnet-123456ab] [--use_amazon_ecr] [--dind]
                   [--spot] [--gpu] [--request_payer_bucket bucket-name]
                   [--ignore_location] [--not_verify_bucket] [--wait]

optional arguments:
  -h, --help            show this help message and exit
  --script path/to/script.sh
                        run script
  --tasks path/to/tasks.tsv
                        parameters
  --task_name task-name
                        AWS resources name
  --wdir path/to/dir    output temporary data
  --image docker/image:tag
                        docker image
  --shell path/to/bash  path to bash or ash in docker-container
  --setup_container_cmd "pip install awscli"
                        awscli install command
  --s3_bucket s3://output/bucket
                        AWS your S3 bucket
  --instance_types c4.large,m5large
                        AWS instance types, split with ','. [Attention] Do not
                        use 't' family
  --vcpu 2              The number of vCPUs reserved for the container.
  --memory 8            The number of memory reserved for the container.
  --disk_size 22        AWS disk size (GiB)
  --processes 20        maximum multi processes
  --security_groups sg-ab123456
                        AWS your security_group_id, split with ','
  --key_name key-123ab  AWS your key pair name
  --subnet_ids subnet-123456ab
                        AWS subnet_id, split with ','
  --use_amazon_ecr      Use Amazon ECR
  --dind                Docker in Docker?
  --spot                Use SPOT instance
  --gpu                 Use GPU instance
  --request_payer_bucket bucket-name
                        Aware that you will be charged for downloading objects
                        in requester pays buckets. Split with ','
  --ignore_location     Ignore differences in location
  --not_verify_bucket   Do not verify input pathes
  --wait                Wait for completion
```

For example,

```Bash
bucket=s3://{yourbucket_name}
ecsub_root={ecsub_download_path}
ecsub_work=/tmp/ecsub

ecsub batch \
    --script ${ecsub_root}/examples/run-wordcount.sh \
    --tasks ${ecsub_root}/examples/tasks-wordcount.tsv \
    --s3_bucket ${bucket}/output/ \
    --wdir ${ecsub_work} \
    --image python:2.7.14 \
    --disk_size 8
```

## 5. Documentation

 - [document](https://aokad.github.io/ecsub-doc-ja/)

## 6. License 

See document [LICENSE](./LICENSE).
