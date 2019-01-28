# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:18:34 2016

@author: okada

"""

import unittest
import os
import glob
import subprocess
import datetime

class DailyTest(unittest.TestCase):

    WDIR = None
    BEFORE = None
    START = None
    
    # init class
    @classmethod
    def setUpClass(cls):
        cls.WDIR = "/tmp/ecsub"
        cls.BEFORE = glob.glob(cls.WDIR + "/*")
        cls.START = datetime.datetime.now().strftime("%Y%m%d%H%M")
    
    # terminated class
    @classmethod
    def tearDownClass(cls):
        pass

    # init method
    def setUp(self):
        pass

    # terminated method
    def tearDown(self):
        pass
    
    def test1_01_version(self):
        subprocess.check_call(['python', 'ecsub', '--version'])

    def test2_01_submit(self):
        options = [
            "--wdir", self.WDIR,
            "--image", "python:2-alpine3.6",
            "--shell", "ash",
            "--script", "./examples/run-wordcount.sh",
            "--tasks", "./tests/test-wordcount.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "1",
            "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
        ]
        subprocess.check_call(['python', 'ecsub', 'submit'] + options)
    
    def test2_02_submit(self):
        options = [
            "--wdir", self.WDIR,
            "--image", "python:2-alpine3.6",
            "--shell", "ash",
            "--script", "./examples/run-wordcount.sh",
            "--tasks", "./tests/test-wordcount.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "1",
            "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
            "--spot",
        ]
        subprocess.check_call(['python', 'ecsub', 'submit'] + options)
    
    def test3_01_report(self):
        options = [
            "--wdir", self.WDIR,
            "-b", self.START,
        ]
        subprocess.check_call(['python', 'ecsub', 'report'] + options)

    def test4_01_logs(self):
        
        after = glob.glob(self.WDIR + "/*")
        
        for b in self.BEFORE:
            if b in after:
                after.remove(b)
        
        for dir_name in after:
            cluster_name = os.path.basename(dir_name)
            
            # download and remove
            options = [
                "--wdir", self.WDIR,
                "--prefix", cluster_name,
                "--rm", "--dw"
            ]
            subprocess.check_call(['python', 'ecsub', 'logs'] + options)
    
    def test5_01_delete(self):
    
        after = glob.glob(self.WDIR + "/*")
        for b in self.BEFORE:
            if b in after:
                after.remove(b)
            
        for dir_name in after:
            cluster_name = os.path.basename(dir_name)
            
            options = [
                "--wdir", self.WDIR
            ]
            subprocess.check_call(['python', 'ecsub', 'delete', cluster_name] + options)

class MassiveTest(unittest.TestCase):

    WDIR = None
    BEFORE = None
    START = None
    
    # init class
    @classmethod
    def setUpClass(cls):
        cls.WDIR = "/tmp/ecsub"
        cls.BEFORE = glob.glob(cls.WDIR + "/*")
        cls.START = datetime.datetime.now().strftime("%Y%m%d%H%M")
        
    # terminated class
    @classmethod
    def tearDownClass(cls):
        pass

    # init method
    def setUp(self):
        pass

    # terminated method
    def tearDown(self):
        pass
    
    def test_submit_instance_type(self):
        instance_types = [
#            "c4.2xlarge"  ,
#            "c4.4xlarge"  ,
#            "c4.8xlarge"  ,
#            "c4.large"    ,
#            "c4.xlarge"   ,
#            "c5.18xlarge" ,
#            "c5.2xlarge"  ,
#            "c5.4xlarge"  ,
#            "c5.9xlarge"  ,
#            "c5.large"    ,
#            "c5.xlarge"   ,
#            "d2.2xlarge"  ,
#            "d2.4xlarge"  ,
#            "d2.8xlarge"  ,
#            "d2.xlarge"   ,
#            "g3.16xlarge" ,
#            "g3.4xlarge"  ,
#            "g3.8xlarge"  ,
#            "i2.2xlarge"  ,
#            "i2.4xlarge"  ,
#            "i2.8xlarge"  ,
#            "i2.xlarge"   ,
#            "i3.16xlarge" ,
#            "i3.2xlarge"  ,
#            "i3.4xlarge"  ,
#            "i3.8xlarge"  ,
#            "i3.large"    ,
#            "i3.xlarge"   ,
#            "m4.10xlarge" ,
#            "m4.16xlarge" ,
#            "m4.2xlarge"  ,
#            "m4.4xlarge"  ,
#            "m4.large"    ,
#            "m4.xlarge"   ,
#            "m5.12xlarge" ,
#            "m5.24xlarge" ,
#            "m5.2xlarge"  ,
#            "m5.4xlarge"  ,
#            "m5.large"    ,
#            "m5.xlarge"   ,
#            "p2.16xlarge" ,
#            "p2.8xlarge"  ,
#            "p2.xlarge"   ,
#            "p3.16xlarge" ,
#            "p3.2xlarge"  ,
#            "p3.8xlarge"  ,
#            "r4.16xlarge" ,
#            "r4.2xlarge"  ,
#            "r4.4xlarge"  ,
#            "r4.8xlarge"  ,
#            "r4.large"    ,
#            "r4.xlarge"   ,
#            "t2.2xlarge"  ,
#            "t2.large"    ,
#            "t2.medium"   ,
#            "t2.micro"    ,
#            "t2.nano"     ,
#            "t2.small"    ,
#            "t2.xlarge"   ,
#            "t3.2xlarge"  ,
#            "t3.large"    ,
#            "t3.medium"   ,
#            "t3.micro"    ,
#            "t3.nano"     ,
#            "t3.small"    ,
#            "t3.xlarge"   ,
#            "x1.16xlarge" ,
#            "x1.32xlarge" ,
#            "c5d.18xlarge",
#            "c5d.2xlarge" ,
#            "c5d.4xlarge" ,
#            "c5d.9xlarge" ,
#            "c5d.large"   ,
#            "c5d.xlarge"  ,
#            "g3s.xlarge"  ,
#            "i3.metal"    ,
#            "m5d.12xlarge",
#            "m5d.24xlarge",
#            "m5d.2xlarge" ,
#            "m5d.4xlarge" ,
#            "m5d.large"   ,
#            "m5d.xlarge"  ,
#            "r5.12xlarge" ,
#            "r5.24xlarge" ,
#            "r5.2xlarge"  ,
#            "r5.4xlarge"  ,
#            "r5.large"    ,
#            "r5.xlarge"   ,
#            "r5d.12xlarge",
#            "r5d.24xlarge",
#            "r5d.2xlarge" ,
#            "r5d.4xlarge" ,
#            "r5d.large"   ,
#            "r5d.xlarge"  ,
#            "x1e.16xlarge",
#            "x1e.2xlarge" ,
#            "x1e.32xlarge",
#            "x1e.4xlarge" ,
#            "x1e.8xlarge" ,
#            "x1e.xlarge"  ,
#            "z1d.12xlarge",
#            "z1d.2xlarge" ,
#            "z1d.3xlarge" ,
#            "z1d.6xlarge" ,
#            "z1d.large"   ,
#            "z1d.xlarge"  ,
        ]
        for itype in instance_types:
            options = [
                "--wdir", self.WDIR,
                "--image", "python:2-alpine3.6",
                "--shell", "ash",
                "--script", "./examples/run-wordcount.sh",
                "--tasks", "./tests/test-wordcount.tsv",
                "--aws-ec2-instance-type", itype,
                "--disk-size", "1",
                "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
            ]
            try:
                subprocess.check_call(['python', 'ecsub', 'submit'] + options)
            except Exception as e:
                print(e)
    
    def test_submit_many_input(self):
        options = [
            "--wdir", self.WDIR,
            "--image", "python:2-alpine3.6",
            "--shell", "ash",
            "--script", "./examples/run-wordcount.sh",
            "--tasks", "/home/Okada/gitlab/ecsub-testdata/unit_test/many_inputs.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "1",
            "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
        ]
        subprocess.check_call(['echo', 'python', 'ecsub', 'submit'] + options)
        #subprocess.check_call(['python', 'ecsub', 'submit'] + options)
         
def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(DailyTest))
    #suite.addTests(unittest.makeSuite(MassiveTest))
    return suite

