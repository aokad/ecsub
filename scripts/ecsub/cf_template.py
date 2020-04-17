template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS Batch envrionment for ECSUB",
    "Parameters": {
        "JobName": {
            "Type": "String",
            "Default": "ecsub_default",
            "Description": "Job Name"
        },
        "InstanceTypes": {
            "Type": "CommaDelimitedList",
            "Default": "optimal",
            "Description": "Instance Type"
        },
        "vCPUs": {
            "Type": "Number",
            "Default": 2,
            "Description": "vCPUs"
        },
        "Memory": {
            "Type": "Number",
            "Default": 8,
            "Description": "Memory, Minimum 4"
        },
        "VolumeSize": {
            "Type": "Number",
            "Default": 8,
            "Description": "Disk size, GiB, Minimum 8"
        },
        "ContainerImage": {
            "Type": "String",
            "Default": "",
            "Description": "Container Image"
        },
        "AutoKey": {
            "Type": "String",
            "Default": "",
            "Description": "Auto create key name"
        },
    },
    "Metadata": {
        "AWS::CloudFormation::Interface": {
            "ParameterGroups": [
                {
                    "Label": {
                        "default": "ECSUB Configuration"
                    },
                    "Parameters": [
                        "JobName",
                        "InstanceTypes",
                        "vCPUs",
                        "Memory",
                        "VolumeSize",
                        "ContainerImage",
                        "AutoKey"
                    ]
                }
            ]
        }
    },
    "Resources": {
        "LaunchTemplate": {
            "Type": "AWS::EC2::LaunchTemplate",
            "Properties": {
                "LaunchTemplateData": {
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/xvdcz",
                            "Ebs": {
                                "DeleteOnTermination": True,
                                "Encrypted": False,
                                "VolumeSize": 22,
                                "VolumeType": "gp2"
                            }
                        },
                        {
                            "DeviceName": "/dev/sdb",
                            "Ebs": {
                                "DeleteOnTermination": True,
                                "Encrypted": False,
                                "VolumeSize": {
                                    "Ref": "VolumeSize"
                                },
                                "VolumeType": "gp2"
                            }
                        }
                    ],
                    "UserData": ""
                },
                "LaunchTemplateName": {
                    "Ref": "JobName"
                }
            }
        },
        "ComputeEnvironment": {
            "Type": "AWS::Batch::ComputeEnvironment",
            "Properties": {
                "ComputeEnvironmentName": {
                    "Ref": "JobName"
                },
                "ComputeResources": {
                    "BidPercentage": 100,
                    "Ec2KeyPair": "",
                    "ImageId": "ami-032b1a02e6610214e",
                    "InstanceRole": "ecsInstanceRole",
                    "InstanceTypes": {
                        "Ref": "InstanceTypes"
                    },
                    "LaunchTemplate": {
                        "LaunchTemplateId": {
                            "Ref": "LaunchTemplate"
                        }
                    },
                    "MaxvCpus": 0,
                    "MinvCpus": 0,
                    "DesiredvCpus": {
                        "Ref": "vCPUs"
                    },
                    "SecurityGroupIds": [],
                    "Subnets": [],
                    "Tags": {
                        "Name": {
                            "Ref": "JobName"
                        }
                    },
                    "SpotIamFleetRole": "arn:aws:iam::047717877309:role/AmazonEC2SpotFleetRole",
                    "Type": "SPOT"
                },
                "ServiceRole": "arn:aws:iam::047717877309:role/service-role/AWSBatchServiceRole",
                "State": "ENABLED",
                "Type": "MANAGED"
            }
        },
        "JobQueue": {
            "Type": "AWS::Batch::JobQueue",
            "Properties": {
                "ComputeEnvironmentOrder": [
                    {
                        "ComputeEnvironment": {
                            "Ref": "ComputeEnvironment"
                        },
                        "Order": 10
                    }
                ],
                "JobQueueName": {
                    "Ref": "JobName"
                },
                "Priority": 10
            }
        },
        "JobDefinition": {
            "Type": "AWS::Batch::JobDefinition",
            "Properties": {
                "ContainerProperties": {
                    "Command": [],
                    "Environment": [
                        {
                            "Name": "SCRIPT_RUN_PATH",
                            "Value": ""
                        },
                        {
                            "Name": "SCRIPT_SETENV_PATH",
                            "Value": ""
                        },
                        {
                            "Name": "SCRIPT_DOWNLOADER_PATH",
                            "Value": ""
                        },
                        {
                            "Name": "SCRIPT_UPLOADER_PATH",
                            "Value": ""
                        },
                        {
                            "Name": "AWS_DEFAULT_REGION",
                            "Value": ""
                        }
                    ],
                    "Image": {
                        "Ref": "ContainerImage"
                    },
                    "JobRoleArn": "arn:aws:iam::047717877309:role/ecsInstanceRole",
                    "Memory": {
                        "Ref": "Memory"
                    },
                    "MountPoints": [
                        {
                            "ContainerPath": "/scratch",
                            "SourceVolume": "scratch"
                        }
                    ],
                    "Vcpus": {
                        "Ref": "vCPUs"
                    },
                    "Volumes": [
                        {
                            "Host": {
                                "SourcePath": "/external"
                            },
                            "Name": "scratch"
                        }
                    ]
                },
                "JobDefinitionName": {
                    "Ref": "JobName"
                },
                "Type": "container"
            }
        }
    },
    "Outputs": {
        "LaunchTemplateId": {
            "Description": "Launch Template",
            "Value": {
                "Ref": "LaunchTemplate"
            }
        },
        "ComputeEnvironmentId": {
            "Description": "Compute Environment",
            "Value": {
                "Ref": "ComputeEnvironment"
            }
        },
        "JobQueueId": {
            "Description": "Job Queue",
            "Value": {
                "Ref": "JobQueue"
            }
        },
        "JobDefinitionId": {
            "Description": "Job Definition",
            "Value": {
                "Ref": "JobDefinition"
            }
        }
    }
}
