# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 12:54:32 2018

@author: Okada
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
