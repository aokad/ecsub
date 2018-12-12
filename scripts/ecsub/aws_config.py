# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 12:54:32 2018

@author: Okada
"""

INSTANCE_TYPE = {
    "t2.nano"    :{"vcpu":  1, "memory":    300},
    "t2.micro"   :{"vcpu":  1, "memory":    800},
    "t2.small"   :{"vcpu":  1, "memory":   1800},
    "t2.medium"  :{"vcpu":  2, "memory":   3800},
    "t2.large"   :{"vcpu":  2, "memory":   7800},
    "t2.xlarge"  :{"vcpu":  4, "memory":  15800},
    "t2.2xlarge" :{"vcpu":  8, "memory":  31800},
    "t3.nano"    :{"vcpu":  2, "memory":    300},
    "t3.micro"   :{"vcpu":  2, "memory":    800},
    "t3.small"   :{"vcpu":  2, "memory":   1800},
    "t3.medium"  :{"vcpu":  2, "memory":   3800},
    "t3.large"   :{"vcpu":  2, "memory":   7800},
    "t3.xlarge"  :{"vcpu":  4, "memory":  15800},
    "t3.2xlarge" :{"vcpu":  8, "memory":  31800},
    "m5.large"   :{"vcpu":  2, "memory":   7500},
    "m5.xlarge"  :{"vcpu":  4, "memory":  15000},
    "m5.2xlarge" :{"vcpu":  8, "memory":  30700},
    "m5.4xlarge" :{"vcpu": 16, "memory":  62000},
    "m5.12xlarge":{"vcpu": 48, "memory": 185000},
    "m5.24xlarge":{"vcpu": 96, "memory": 378000},
    "m4.large"   :{"vcpu":  2, "memory":   7800},
    "m4.xlarge"  :{"vcpu":  4, "memory":  15800},
    "m4.2xlarge" :{"vcpu":  8, "memory":  31800},
    "m4.4xlarge" :{"vcpu": 16, "memory":  63800},
    "m4.10xlarge":{"vcpu": 40, "memory": 159800},
    "m4.16xlarge":{"vcpu": 64, "memory": 255800},
    "c5.large"   :{"vcpu":  2, "memory":   3800},
    "c5.xlarge"  :{"vcpu":  4, "memory":   7800},
    "c5.2xlarge" :{"vcpu":  8, "memory":  15800},
    "c5.4xlarge" :{"vcpu": 16, "memory":  31800},
    "c5.9xlarge" :{"vcpu": 36, "memory":  71800},
    "c5.18xlarge":{"vcpu": 72, "memory": 143800},
    "c4.large"   :{"vcpu":  2, "memory":   3550},
    "c4.xlarge"  :{"vcpu":  4, "memory":   7300},
    "c4.2xlarge" :{"vcpu":  8, "memory":  14800},
    "c4.4xlarge" :{"vcpu": 16, "memory":  29800},
    "c4.8xlarge" :{"vcpu": 36, "memory":  59800},
    "g3.4xlarge" :{"vcpu": 16, "memory": 121800},
    "g3.8xlarge" :{"vcpu": 32, "memory": 243800},
    "g3.16xlarge":{"vcpu": 64, "memory": 487800},
    "p2.xlarge"  :{"vcpu":  4, "memory":  60800},
    "p2.8xlarge" :{"vcpu": 32, "memory": 487800},
    "p2.16xlarge":{"vcpu": 64, "memory": 731800},
    "p3.2xlarge" :{"vcpu":  8, "memory":  60800},
    "p3.8xlarge" :{"vcpu": 32, "memory": 243800},
    "p3.16xlarge":{"vcpu": 64, "memory": 487800},
    "r4.large"   :{"vcpu":  2, "memory":  15050},
    "r4.xlarge"  :{"vcpu":  4, "memory":  30300},
    "r4.2xlarge" :{"vcpu":  8, "memory":  60800},
    "r4.4xlarge" :{"vcpu": 16, "memory": 121800},
    "r4.8xlarge" :{"vcpu": 32, "memory": 243800},
    "r4.16xlarge":{"vcpu": 64, "memory": 487800},
    "x1.16xlarge":{"vcpu": 64, "memory": 975800},
    "x1.32xlarge":{"vcpu":128, "memory":1951800},
    "d2.xlarge"  :{"vcpu":  4, "memory":  30300},
    "d2.2xlarge" :{"vcpu":  8, "memory":  60800},
    "d2.4xlarge" :{"vcpu": 16, "memory": 121800},
    "d2.8xlarge" :{"vcpu": 36, "memory": 243800},
    "i2.xlarge"  :{"vcpu":  4, "memory":  30300},
    "i2.2xlarge" :{"vcpu":  8, "memory":  60800},
    "i2.4xlarge" :{"vcpu": 16, "memory": 121800},
    "i2.8xlarge" :{"vcpu": 32, "memory": 243800},
    "h1.2xlarge" :{"vcpu":  8, "memory":  31800},
    "h1.4xlarge" :{"vcpu": 16, "memory":  63800},
    "h1.8xlarge" :{"vcpu": 32, "memory": 127800},
    "h1.16xlarge":{"vcpu": 64, "memory": 255800},
    "i3.large"   :{"vcpu":  2, "memory":  15050},
    "i3.xlarge"  :{"vcpu":  4, "memory":  30300},
    "i3.2xlarge" :{"vcpu":  8, "memory":  60800},
    "i3.4xlarge" :{"vcpu": 16, "memory": 121800},
    "i3.8xlarge" :{"vcpu": 32, "memory": 243800},
    "i3.16xlarge":{"vcpu": 64, "memory": 487800},
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
