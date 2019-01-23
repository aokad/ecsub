# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:18:34 2016

@author: okada

"""

import unittest
import os
import glob
import subprocess

class TestSet(unittest.TestCase):

    WDIR = "/tmp/ecsub"
    before = []
    
    # init class
    @classmethod
    def setUpClass(cls):
        cls.before = glob.glob(cls.WDIR + "/*")
        
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
            "--wdir", self.WDIR
        ]
        subprocess.check_call(['python', 'ecsub', 'report'] + options)

    def test4_01_logs(self):
        
        after = glob.glob(self.WDIR + "/*")
        
        for b in self.before:
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
        
        for b in self.before:
            if b in after:
                after.remove(b)
        
        for dir_name in after:
            cluster_name = os.path.basename(dir_name)
            
            options = [
                "--wdir", self.WDIR
            ]
            subprocess.check_call(['python', 'ecsub', 'delete', cluster_name] + options)
            
def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestSet))
    return suite

