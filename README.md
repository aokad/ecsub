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

docker image push to your ECS 

-------------------------------------------------------------------------

## 4. Run

Job submit

```
ecsub submit
    --script SCRIPT \
    --tasks  TASKS \
    --aws-s3-bucket AWS_S3_BUCKET \
    [--aws-ec2-instance-type AWS_EC2_INSTANCE_TYPE] \
    [--disk-size DISK_SIZE] \
    [--aws-security-group-id AWS_SECURITY_GROUP_ID] \
    [--aws-key-name AWS_KEY_NAME] \
    [--wdir WDIR] \
    [--image IMAGE]
```

View job report

```
ecsub submit ${WDIR}
```

## 8. License 

See document LICENSE.
