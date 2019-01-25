# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 12:54:32 2018

@author: Okada
"""

SUPPORT_FAMILY = [
 "c4", "c5", "c5d",
 "d2",
 "g3", "g3s",
 "i2", "i3",
 "m4", "m5",
 "p2", "p3",
 "r4", "r5", "r5d",
 "t2", "t3",
 "x1", "x1e",
 "z1d",
]

"""
INSTANCE_TYPE = {
    "c4.2xlarge"  : {"vcpu":   8, "t.memory":   15, "d.memory":  0.2},
    "c4.4xlarge"  : {"vcpu":  16, "t.memory":   30, "d.memory":  0.2},
    "c4.8xlarge"  : {"vcpu":  36, "t.memory":   60, "d.memory":  0.2},
    "c4.large"    : {"vcpu":   2, "t.memory": 3.75, "d.memory":  0.2},
    "c4.xlarge"   : {"vcpu":   4, "t.memory":  7.5, "d.memory":  0.2},
    "c5.18xlarge" : {"vcpu":  72, "t.memory":  144, "d.memory":  4.0},
    "c5.2xlarge"  : {"vcpu":   8, "t.memory":   16, "d.memory":  0.2},
    "c5.4xlarge"  : {"vcpu":  16, "t.memory":   32, "d.memory":  0.2},
    "c5.9xlarge"  : {"vcpu":  36, "t.memory":   72, "d.memory":  0.2},
    "c5.large"    : {"vcpu":   2, "t.memory":    4, "d.memory":  0.2},
    "c5.xlarge"   : {"vcpu":   4, "t.memory":    8, "d.memory":  0.2},
    "d2.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  0.2},
    "d2.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  0.2},
    "d2.8xlarge"  : {"vcpu":  36, "t.memory":  244, "d.memory":  0.2},
    "d2.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  0.2},
    "g3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  0.2},
    "g3.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  0.2},
    "g3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  0.2},
    "i2.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  0.2},
    "i2.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  0.2},
    "i2.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  0.2},
    "i2.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  0.2},
    "i3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  0.2},
    "i3.2xlarge"  : {"vcpu":   8, "t.memory":  601, "d.memory":  0.2},
    "i3.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  0.2},
    "i3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  0.2},
    "i3.large"    : {"vcpu":   2, "t.memory":15.25, "d.memory":  0.2},
    "i3.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  0.2},
    "m4.10xlarge" : {"vcpu":  40, "t.memory":  160, "d.memory":  0.2},
    "m4.16xlarge" : {"vcpu":  64, "t.memory":  256, "d.memory":  0.2},
    "m4.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  0.2},
    "m4.4xlarge"  : {"vcpu":  16, "t.memory":   64, "d.memory":  0.2},
    "m4.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  0.2},
    "m4.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  0.2},
    "m5.12xlarge" : {"vcpu":  48, "t.memory":  192, "d.memory":  7.0},
    "m5.24xlarge" : {"vcpu":  96, "t.memory":  384, "d.memory":  6.0},
    "m5.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  2.0},
    "m5.4xlarge"  : {"vcpu":  16, "t.memory":   64, "d.memory":  2.0},
    "m5.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  0.5},
    "m5.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  1.0},
    "p2.16xlarge" : {"vcpu":  64, "t.memory":  732, "d.memory":  0.2},
    "p2.8xlarge"  : {"vcpu":  32, "t.memory":  488, "d.memory":  0.2},
    "p2.xlarge"   : {"vcpu":   4, "t.memory":   61, "d.memory":  0.2},
    "p3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  0.2},
    "p3.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  0.2},
    "p3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  0.2},
    "r4.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  0.2},
    "r4.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  0.2},
    "r4.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  0.2},
    "r4.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  0.2},
    "r4.large"    : {"vcpu":   2, "t.memory":15.25, "d.memory":  0.2},
    "r4.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  0.2},
    "t2.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  0.2},
    "t2.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  0.2},
    "t2.medium"   : {"vcpu":   2, "t.memory":    4, "d.memory":  0.2},
    "t2.micro"    : {"vcpu":   1, "t.memory":    1, "d.memory":  0.2},
    "t2.nano"     : {"vcpu":   1, "t.memory":  0.5, "d.memory":  0.2},
    "t2.small"    : {"vcpu":   1, "t.memory":    2, "d.memory":  0.2},
    "t2.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  0.2},
    "t3.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  0.2},
    "t3.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  0.2},
    "t3.medium"   : {"vcpu":   2, "t.memory":    4, "d.memory":  0.2},
    "t3.micro"    : {"vcpu":   2, "t.memory":    1, "d.memory":  0.2},
    "t3.nano"     : {"vcpu":   2, "t.memory":  0.5, "d.memory":  0.2},
    "t3.small"    : {"vcpu":   2, "t.memory":    2, "d.memory":  0.2},
    "t3.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  0.2},
    "x1.16xlarge" : {"vcpu":  64, "t.memory":  976, "d.memory":  0.2},
    "x1.32xlarge" : {"vcpu": 128, "t.memory": 1952, "d.memory":  0.2},
    "c5d.18xlarge": {"vcpu":  72, "t.memory":  144, "d.memory":  0.2},
    "c5d.2xlarge" : {"vcpu":   8, "t.memory":   16, "d.memory":  0.2},
    "c5d.4xlarge" : {"vcpu":  16, "t.memory":   32, "d.memory":  0.2},
    "c5d.9xlarge" : {"vcpu":  36, "t.memory":   72, "d.memory":  0.2},
    "c5d.large"   : {"vcpu":   2, "t.memory":    4, "d.memory":  0.2},
    "c5d.xlarge"  : {"vcpu":   4, "t.memory":    8, "d.memory":  0.2},
    "g3s.xlarge"  : {"vcpu":   4, "t.memory": 30.5, "d.memory":  0.2},
    "i3.metal"    : {"vcpu":  72, "t.memory":  512, "d.memory":  0.2},
    # add. 2018/12/14
    "m5d.12xlarge": {"vcpu":  48, "t.memory":  192, "d.memory":  0.2},
    "m5d.24xlarge": {"vcpu":  96, "t.memory":  384, "d.memory":  0.2},
    "m5d.2xlarge" : {"vcpu":   8, "t.memory":   32, "d.memory":  0.2},
    "m5d.4xlarge" : {"vcpu":  16, "t.memory":   64, "d.memory":  0.2},
    "m5d.large"   : {"vcpu":   2, "t.memory":    8, "d.memory":  0.2},
    "m5d.xlarge"  : {"vcpu":   4, "t.memory":   16, "d.memory":  0.2},
    "r5.12xlarge" : {"vcpu":  48, "t.memory":  384, "d.memory":  0.2},
    "r5.24xlarge" : {"vcpu":  96, "t.memory":  768, "d.memory":  0.2},
    "r5.2xlarge"  : {"vcpu":   8, "t.memory":   64, "d.memory":  0.2},
    "r5.4xlarge"  : {"vcpu":  16, "t.memory":  128, "d.memory":  0.2},
    "r5.large"    : {"vcpu":   2, "t.memory":   16, "d.memory":  0.2},
    "r5.xlarge"   : {"vcpu":   4, "t.memory":   32, "d.memory":  0.2},
    "r5d.12xlarge": {"vcpu":  48, "t.memory":  384, "d.memory":  0.2},
    "r5d.24xlarge": {"vcpu":  96, "t.memory":  768, "d.memory":  0.2},
    "r5d.2xlarge" : {"vcpu":   8, "t.memory":   64, "d.memory":  0.2},
    "r5d.4xlarge" : {"vcpu":  16, "t.memory":  128, "d.memory":  0.2},
    "r5d.large"   : {"vcpu":   2, "t.memory":   16, "d.memory":  0.2},
    "r5d.xlarge"  : {"vcpu":   4, "t.memory":   32, "d.memory":  0.2},
    "x1e.16xlarge": {"vcpu":  64, "t.memory": 1952, "d.memory":  0.2},
    "x1e.2xlarge" : {"vcpu":   8, "t.memory":  244, "d.memory":  0.2},
    "x1e.32xlarge": {"vcpu": 128, "t.memory": 3904, "d.memory":  0.2},
    "x1e.4xlarge" : {"vcpu":  16, "t.memory":  488, "d.memory":  0.2},
    "x1e.8xlarge" : {"vcpu":  32, "t.memory":  976, "d.memory":  0.2},
    "x1e.xlarge"  : {"vcpu":   4, "t.memory":  122, "d.memory":  0.2},
    "z1d.12xlarge": {"vcpu":  48, "t.memory":  384, "d.memory":  0.2},
    "z1d.2xlarge" : {"vcpu":   8, "t.memory":   64, "d.memory":  0.2},
    "z1d.3xlarge" : {"vcpu":  12, "t.memory":   96, "d.memory":  0.2},
    "z1d.6xlarge" : {"vcpu":  24, "t.memory":  192, "d.memory":  0.2},
    "z1d.large"   : {"vcpu":   2, "t.memory":   16, "d.memory":  0.2},
    "z1d.xlarge"  : {"vcpu":   4, "t.memory":   32, "d.memory":  0.2},
}
"""
def get_ami_id():
    import boto3
    data=boto3.client("ssm").get_parameters(Names=["/aws/service/ecs/optimized-ami/amazon-linux/recommended/image_id"])
    return data['Parameters'][0]['Value']

def region_to_location(region):
    location = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "ca-central-1": "Canada (Central)",
        "eu-central-1": "EU (Frankfurt)",
        "eu-west-1": "EU (Ireland)",
        "eu-west-2": "EU (London)",
        "eu-west-3": "EU (Paris)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "ap-northeast-2": "Asia Pacific (Seoul)",
        "ap-northeast-3": "Asia Pacific (Osaka-Local)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-south-1": "Asia Pacific (Mumbai)",
        "sa-east-1": "South America (Sao Paulo)",
    }
    if region in location:
        return location[region]
    return None
    
def main():
    pass
    
if __name__ == "__main__":
    main()
