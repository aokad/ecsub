# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 12:54:32 2018

@author: Okada
"""

INSTANCE_TYPE = {
    "c4.2xlarge"  : {"vcpu":   8, "t.memory":   15, "d.memory":  200},
    "c4.4xlarge"  : {"vcpu":  16, "t.memory":   30, "d.memory":  200},
    "c4.8xlarge"  : {"vcpu":  36, "t.memory":   60, "d.memory":  200},
    "c4.large"    : {"vcpu":   2, "t.memory": 3.75, "d.memory":  200},
    "c4.xlarge"   : {"vcpu":   4, "t.memory":  7.5, "d.memory":  200},
    "c5.18xlarge" : {"vcpu":  72, "t.memory":  144, "d.memory":  200},
    "c5.2xlarge"  : {"vcpu":   8, "t.memory":   16, "d.memory":  200},
    "c5.4xlarge"  : {"vcpu":  16, "t.memory":   32, "d.memory":  200},
    "c5.9xlarge"  : {"vcpu":  36, "t.memory":   72, "d.memory":  200},
    "c5.large"    : {"vcpu":   2, "t.memory":    4, "d.memory":  200},
    "c5.xlarge"   : {"vcpu":   4, "t.memory":    8, "d.memory":  200},
    "d2.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  200},
    "d2.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  200},
    "d2.8xlarge"  : {"vcpu":  36, "t.memory":  244, "d.memory":  200},
    "d2.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  200},
    "g3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  200},
    "g3.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  200},
    "g3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  200},
    "i2.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  200},
    "i2.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  200},
    "i2.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  200},
    "i2.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  200},
    "i3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  200},
    "i3.2xlarge"  : {"vcpu":   8, "t.memory":  601, "d.memory":  200},
    "i3.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  200},
    "i3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  200},
    "i3.large"    : {"vcpu":   2, "t.memory":15.25, "d.memory":  200},
    "i3.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  200},
    "m4.10xlarge" : {"vcpu":  40, "t.memory":  160, "d.memory":  200},
    "m4.16xlarge" : {"vcpu":  64, "t.memory":  256, "d.memory":  200},
    "m4.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  200},
    "m4.4xlarge"  : {"vcpu":  16, "t.memory":   64, "d.memory":  200},
    "m4.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  200},
    "m4.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  200},
    "m5.12xlarge" : {"vcpu":  48, "t.memory":  192, "d.memory": 7000},
    "m5.24xlarge" : {"vcpu":  96, "t.memory":  384, "d.memory": 6000},
    "m5.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory": 2000},
    "m5.4xlarge"  : {"vcpu":  16, "t.memory":   64, "d.memory": 2000},
    "m5.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  500},
    "m5.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory": 1000},
    "p2.16xlarge" : {"vcpu":  64, "t.memory":  732, "d.memory":  200},
    "p2.8xlarge"  : {"vcpu":  32, "t.memory":  488, "d.memory":  200},
    "p2.xlarge"   : {"vcpu":   4, "t.memory":   61, "d.memory":  200},
    "p3.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  200},
    "p3.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  200},
    "p3.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  200},
    "r4.16xlarge" : {"vcpu":  64, "t.memory":  488, "d.memory":  200},
    "r4.2xlarge"  : {"vcpu":   8, "t.memory":   61, "d.memory":  200},
    "r4.4xlarge"  : {"vcpu":  16, "t.memory":  122, "d.memory":  200},
    "r4.8xlarge"  : {"vcpu":  32, "t.memory":  244, "d.memory":  200},
    "r4.large"    : {"vcpu":   2, "t.memory":15.25, "d.memory":  200},
    "r4.xlarge"   : {"vcpu":   4, "t.memory": 30.5, "d.memory":  200},
    "t2.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  200},
    "t2.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  200},
    "t2.medium"   : {"vcpu":   2, "t.memory":    4, "d.memory":  200},
    "t2.micro"    : {"vcpu":   1, "t.memory":    1, "d.memory":  200},
    "t2.nano"     : {"vcpu":   1, "t.memory":  0.5, "d.memory":  200},
    "t2.small"    : {"vcpu":   1, "t.memory":    2, "d.memory":  200},
    "t2.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  200},
    "t3.2xlarge"  : {"vcpu":   8, "t.memory":   32, "d.memory":  200},
    "t3.large"    : {"vcpu":   2, "t.memory":    8, "d.memory":  200},
    "t3.medium"   : {"vcpu":   2, "t.memory":    4, "d.memory":  200},
    "t3.micro"    : {"vcpu":   2, "t.memory":    1, "d.memory":  200},
    "t3.nano"     : {"vcpu":   2, "t.memory":  0.5, "d.memory":  200},
    "t3.small"    : {"vcpu":   2, "t.memory":    2, "d.memory":  200},
    "t3.xlarge"   : {"vcpu":   4, "t.memory":   16, "d.memory":  200},
    "x1.16xlarge" : {"vcpu":  64, "t.memory":  976, "d.memory":  200},
    "x1.32xlarge" : {"vcpu": 128, "t.memory": 1952, "d.memory":  200},
    "c5d.18xlarge": {"vcpu":  72, "t.memory":  144, "d.memory":  200},
    "c5d.2xlarge" : {"vcpu":   8, "t.memory":   16, "d.memory":  200},
    "c5d.4xlarge" : {"vcpu":  16, "t.memory":   32, "d.memory":  200},
    "c5d.9xlarge" : {"vcpu":  36, "t.memory":   72, "d.memory":  200},
    "c5d.large"   : {"vcpu":   2, "t.memory":    4, "d.memory":  200},
    "c5d.xlarge"  : {"vcpu":   4, "t.memory":    8, "d.memory":  200},
    "g3s.xlarge"  : {"vcpu":   4, "t.memory": 30.5, "d.memory":  200},
    "i3.metal"    : {"vcpu":  72, "t.memory":  512, "d.memory":  200},
    # add. 2018/12/14
    #"m5d.12xlarge": {"vcpu":  48, "t.memory":  192, "d.memory":  200},
    #"m5d.24xlarge": {"vcpu":  96, "t.memory":  384, "d.memory":  200},
    #"m5d.2xlarge" : {"vcpu":   8, "t.memory":   32, "d.memory":  200},
    #"m5d.4xlarge" : {"vcpu":  16, "t.memory":   64, "d.memory":  200},
    #"m5d.large"   : {"vcpu":   2, "t.memory":    8, "d.memory":  200},
    #"m5d.xlarge"  : {"vcpu":   4, "t.memory":   16, "d.memory":  200},
    "r5.12xlarge" : {"vcpu":  48, "t.memory":  384, "d.memory":  200},
    "r5.24xlarge" : {"vcpu":  96, "t.memory":  768, "d.memory":  200},
    "r5.2xlarge"  : {"vcpu":   8, "t.memory":   64, "d.memory":  200},
    "r5.4xlarge"  : {"vcpu":  16, "t.memory":  128, "d.memory":  200},
    "r5.large"    : {"vcpu":   2, "t.memory":   16, "d.memory":  200},
    "r5.xlarge"   : {"vcpu":   4, "t.memory":   32, "d.memory":  200},
    "r5d.12xlarge": {"vcpu":  48, "t.memory":  384, "d.memory":  200},
    "r5d.24xlarge": {"vcpu":  96, "t.memory":  768, "d.memory":  200},
    "r5d.2xlarge" : {"vcpu":   8, "t.memory":   64, "d.memory":  200},
    "r5d.4xlarge" : {"vcpu":  16, "t.memory":  128, "d.memory":  200},
    "r5d.large"   : {"vcpu":   2, "t.memory":   16, "d.memory":  200},
    "r5d.xlarge"  : {"vcpu":   4, "t.memory":   32, "d.memory":  200},
    "x1e.16xlarge": {"vcpu":  64, "t.memory": 1952, "d.memory":  200},
    "x1e.2xlarge" : {"vcpu":   8, "t.memory":  244, "d.memory":  200},
    "x1e.32xlarge": {"vcpu": 128, "t.memory": 3904, "d.memory":  200},
    "x1e.4xlarge" : {"vcpu":  16, "t.memory":  488, "d.memory":  200},
    "x1e.8xlarge" : {"vcpu":  32, "t.memory":  976, "d.memory":  200},
    "x1e.xlarge"  : {"vcpu":   4, "t.memory":  122, "d.memory":  200},
    "z1d.12xlarge": {"vcpu":  48, "t.memory":  384, "d.memory":  200},
    "z1d.2xlarge" : {"vcpu":   8, "t.memory":   64, "d.memory":  200},
    "z1d.3xlarge" : {"vcpu":  12, "t.memory":   96, "d.memory":  200},
    "z1d.6xlarge" : {"vcpu":  24, "t.memory":  192, "d.memory":  200},
    "z1d.large"   : {"vcpu":   2, "t.memory":   16, "d.memory":  200},
    "z1d.xlarge"  : {"vcpu":   4, "t.memory":   32, "d.memory":  200},
}

def get_ami_id():
    import boto3
    data=boto3.client("ssm").get_parameters(Names=["/aws/service/ecs/optimized-ami/amazon-linux/recommended/image_id"])
    return data['Parameters'][0]['Value']

def region_to_location(region):
    location = {
        "us-east-1": "US East (N. Virginia)",           # 米国東部（バージニア北部）
        "us-east-2": "US East (Ohio)",                  # 米国東部 (オハイオ)
        "us-west-1": "US West (N. California)",         # 米国西部 (北カリフォルニア)
        "us-west-2": "US West (Oregon)",                # 米国西部 (オレゴン)
        "ca-central-1": "Canada (Central)",             # カナダ (中部)
        "eu-central-1": "EU (Frankfurt)",               # 欧州 (フランクフルト)
        "eu-west-1": "EU (Ireland)",                    # 欧州 (アイルランド)
        "eu-west-2": "EU (London)",                     # 欧州 (ロンドン)
        "eu-west-3": "EU (Paris)",                      # EU (パリ)
        "ap-northeast-1": "Asia Pacific (Tokyo)",       # アジアパシフィック (東京)
        "ap-northeast-2": "Asia Pacific (Seoul)",       # アジアパシフィック (ソウル)
        "ap-northeast-3": "Asia Pacific (Osaka-Local)", # アジアパシフィック (大阪: ローカル)
        "ap-southeast-1": "Asia Pacific (Singapore)",   # アジアパシフィック (シンガポール)
        "ap-southeast-2": "Asia Pacific (Sydney)",      # アジアパシフィック (シドニー)
        "ap-south-1": "Asia Pacific (Mumbai)",          # アジアパシフィック (ムンバイ)
        "sa-east-1": "South America (Sao Paulo)",       # 南米 (サンパウロ)
    }
    if region in location:
        return location[region]
    return None
    
def main():
    pass
    
if __name__ == "__main__":
    main()
