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
    "m5.large"   :{"vcpu":  2, "memory":   7800},
    "m5.xlarge"  :{"vcpu":  4, "memory":  15800},
    "m5.2xlarge" :{"vcpu":  8, "memory":  31800},
    "m5.4xlarge" :{"vcpu": 16, "memory":  63800},
    "m5.12xlarge":{"vcpu": 48, "memory": 191800},
    "m5.24xlarge":{"vcpu": 96, "memory": 383800},
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

AMI_ID = {
    "us-east-2"     : "ami-ef64528a",
    "us-east-1"     : "ami-cad827b7",
    "us-west-2"     : "ami-baa236c2",
    "us-west-1"     : "ami-29b8b249",
    "eu-west-3"     : "ami-0356e07e",
    "eu-west-2"     : "ami-25f51242",
    "eu-west-1"     : "ami-64c4871d",
    "eu-central-1"  : "ami-3b7d1354",
    "ap-northeast-2": "ami-3b19b455",
    "ap-northeast-1": "ami-bb5f13dd",
    "ap-southeast-2": "ami-a677b6c4",
    "ap-southeast-1": "ami-f88ade84",
    "ca-central-1"  : "ami-db48cfbf",
    "ap-south-1"    : "ami-9e91cff1",
    "sa-east-1"     : "ami-da2c66b6"
}

def main():
    pass
#    print (INSTANCE_TYPE["t2.2xlarge"])
    
if __name__ == "__main__":
    main()

