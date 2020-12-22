[![Build Status](https://travis-ci.org/aokad/ecsub.svg?branch=master)](https://travis-ci.org/aokad/ecsub)
![Python](https://img.shields.io/badge/python-2.7%20%7C%203.5%20%7C%203.6%20%7C%203.7-blue.svg)

# ecsub

## 1. Dependency

 - [awscli](https://docs.aws.amazon.com/streams/latest/dev/kinesis-tutorial-cli-installation.html)
 - [boto3](https://github.com/boto/boto3)
 - pytz
 - six

## 2. Install

Dependent packages are installed automatically.

```Bash
pip install awscli boto3 pyyaml --upgrade
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
$ ecsub submit --help
usage: ecsub submit [-h] [--wdir path/to/dir] [--image docker/image:tag]
                    [--use-amazon-ecr] [--shell path/to/bash]
                    [--setup-container-cmd "pip install awscli"] [--dind]
                    --script path/to/script.sh --tasks path/to/tasks.tsv
                    [--task-name task-name] --aws-s3-bucket s3://output/bucket
                    [--aws-ec2-instance-type t3.micro,t2.micro]
                    [--aws-ec2-instance-type-list t3.micro,t2.micro]
                    [--aws-ecs-instance-role-name ecsInstanceRole]
                    [--disk-size 22] [--processes 20]
                    [--processes-file-check 10]
                    [--aws-security-group-id sg-ab123456,sg-ab456789]
                    [--aws-key-name key-123ab] [--aws-log-group-name lg-name]
                    [--aws-subnet-id subnet-123456ab] [--spot] [--retry-od]
                    [--request-payer-bucket bucket-name] [--ignore-location]
                    [--not-verify-bucket] [--skip-price] [--waiter-delay 15]

optional arguments:
  -h, --help            show this help message and exit
  --wdir path/to/dir    output temporary data
  --image docker/image:tag
                        docker image
  --use-amazon-ecr      use_amazon_ecr
  --shell path/to/bash  path to bash or ash in docker-container
  --setup-container-cmd "pip install awscli"
                        awscli install command
  --dind                Docker in Docker?
  --script path/to/script.sh
                        run script
  --tasks path/to/tasks.tsv
                        parameters
  --task-name task-name
                        submit name as AWS ECS cluster name
  --aws-s3-bucket s3://output/bucket
                        AWS your S3 bucket
  --aws-ec2-instance-type t3.micro,t2.micro
                        AWS instance types, split with ','
  --aws-ec2-instance-type-list t3.micro,t2.micro
                        (Deprecated as it is to be decommissioned.) AWS
                        instance types, split with ','
  --aws-ecs-instance-role-name ecsInstanceRole
                        AWS ECS instance role name
  --disk-size 22        Size of extra disk space in GiB for container layers
                        and mounted volumes, excluding 30GiB for OS and docker
                        runtime
  --processes 20        maximum multi processes
  --processes-file-check 10
                        maximum multi processes for exists of iput files
  --aws-security-group-id sg-ab123456,sg-ab456789
                        AWS your security_group_ids, split with ','
  --aws-key-name key-123ab
                        AWS your key pair name
  --aws-log-group-name lg-name
                        AWS Cloudwatch Logs Log-group-name
  --aws-subnet-id subnet-123456ab
                        AWS subnet_id
  --spot                [spot] use spot instance
  --retry-od            [spot] In case of failure, retry on demand instance
  --request-payer-bucket bucket-name
                        Aware that you will be charged for downloading objects
                        in requester pays buckets. Split with ','
  --ignore-location     Ignore differences in location
  --not-verify-bucket   Do not verify input pathes
  --skip-price          Skip get pricing from aws
  --waiter-delay 15     The amount of time(sec) to boto3 waiter
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

```
$ ecsub report --help
usage: ecsub report [-h] [--wdir path/to/dir] [--past] [-f]
                    [-b [YYYYMMDDhhmm]] [-e [YYYYMMDDhhmm]] [--max 20]
                    [--sortby sort_key]

optional arguments:
  -h, --help            show this help message and exit
  --wdir path/to/dir    {PATH} when 'ecsub submit --wdir {PATH}'
  --past                display summary in previous version.
  -f, --failed          display failed or abnoraml exit status job only.
  -b [YYYYMMDDhhmm], --begin [YYYYMMDDhhmm]
                        The earliest createdAt time for jobs to be summarized,
                        in the format [YYYYMMDDhhmm]
  -e [YYYYMMDDhhmm], --end [YYYYMMDDhhmm]
                        The latest createdAt time for jobs to be summarized,
                        in the format [YYYYMMDDhhmm]
  --max 20              Maximum display count
  --sortby sort_key     Sort summary key
```

For example,

```Bash
ecsub report --wdir /tmp/ecsub -b 201901250000 --max 5
```

<pre>
| exitCode| taskname|  no| Spot|          job_startAt|            job_endAt| instance_type| cpu| memory| disk_size|    instance_createAt|      instance_stopAt|                                       log_local|
|        0|  sample1| 000|    F| 2019/01/25 18:07:40 | 2019/01/25 18:13:46 |      t2.micro|   1|    900|         1| 2019/01/25 18:07:40 | 2019/01/25 18:13:46 | /tmp/ecsub/sample1/log/describe-tasks.000.0.log|
|      255|  sample2| 000|    F| 2019/01/25 16:42:00 | 2019/01/25 16:46:33 |      t2.micro|   1|    800|         1| 2019/01/25 16:42:00 | 2019/01/25 16:46:33 | /tmp/ecsub/sample2/log/describe-tasks.000.0.log|
|       NA|  sample3| 000|    F| 2019/01/25 17:14:58 |                     |              |    |       |         1| 2019/01/25 17:14:58 |                     |                                                |
|        0|  sample4| 000|    F| 2019/01/25 22:06:30 | 2019/01/25 22:20:24 |    i2.8xlarge|  32| 245900|         1| 2019/01/25 22:06:30 | 2019/01/25 22:20:24 | /tmp/ecsub/sample4/log/describe-tasks.000.0.log|
|        1|  sample5| 000|    F| 2019/01/26 07:20:48 | 2019/01/26 07:20:48 |    x1e.xlarge|   0|      0|         1| 2019/01/26 07:20:48 | 2019/01/26 07:20:48 |                                                |
</pre>

### 3) Download log files

ecsub creates logs on AWS CloudWatch.
If you need, you can download log-files to local directory, and remove log-streams from AWS.

```
$ ecsub logs
usage: ecsub logs [-h] [--wdir path/to/dir]
                  [--log-group-prefix ecsub-task-wordcount]
                  [--log-group-name ecsub-task-wordcount-aBc012]
                  [--log-stream-prefix ecsub/log-stream-name-prefix] [--tail]
                  {download,remove-log-group,remove-log-stream}
```

For example,

1) download log

```Bash
# all streams
ecsub logs download --wdir /tmp/ecsub --log-group-prefix ecsub-task-wordcount

# specify streams
ecsub logs download --wdir /tmp/ecsub --log-group-name ecsub-task-wordcount-aBc012 --log-stream-prefix ecsub/task-wordcount-aBc012_tasks/xxx

# last event
ecsub logs download --wdir /tmp/ecsub --log-group-name ecsub-task-wordcount --tail
ecsub logs download --wdir /tmp/ecsub --log-group-name ecsub-task-wordcount-aBc012 --log-stream-prefix ecsub/task-wordcount-aBc012_tasks/xxx --tail
```

2) remove log-groups

```Bash
ecsub logs remove-log-group --log-group-prefix ecsub-task-wordcount
```

3) remove log-streams

```Bash
ecsub logs remove-log-stream --log-group-name ecsub-task-wordcount-aBc012 --log-stream-prefix ecsub/task-wordcount-aBc012_tasks/xxx
```

### 4) Delete jobs.

**Attention!** If task ends normally (exit with 0, 1, 255...), it does not need to be executed.  
`delete` subcommand is used for jobs that have a creation date ("instance_createAt") but no end date ("instance_stopAt") as shown below.

<pre>
| exitCode| taskname|  no| ... |    instance_createAt| instance_stopAt| log_local|
|       NA|  sample3| 000| ... | 2019/01/25 17:14:58 |                |          |
</pre>

```
$ ecsub delete --help
usage: ecsub delete [-h] [--wdir path/to/dir] task-name

positional arguments:
  task-name           task name

optional arguments:
  -h, --help          show this help message and exit
  --wdir path/to/dir  {PATH} when 'ecsub submit --wdir {PATH}'
```

For example,

```Bash
ecsub delete --wdir /tmp/ecsub sample2-bRnfG
```

## 5. Documentation

 - [document](https://aokad.github.io/ecsub-doc-ja/)

## 6. License 

See document [LICENSE](./LICENSE).
