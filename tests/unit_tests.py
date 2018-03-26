# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:18:34 2016

@author: okada

"""


import unittest
import os
import sys
import subprocess

class TestSet(unittest.TestCase):

    CURRENT = os.path.abspath(os.path.dirname(__file__))
    
    # init class
    @classmethod
    def setUpClass(cls):
        pass
        
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
        subprocess.check_call('python ecsub --version'.split(" "))

    def test2_01_submit(self):
        options = [
            "--wdir", "/tmp/ecsub/",
            "--image", "genomon/bwa_alignment:0.1.0",
            "--script", "s3://awsbatch-aokad-ohaio/scripts/bwa-alignment.sh",
            "--tasks", "./example/bwa-alignment-tasks-aokad-20180207-small-1.tsv",
            "--aws-ec2-instance-type", "t2.2xlarge",
            "--disk-size", "128",
            "--aws-s3-bucket", "s3://awsbatch-aokad-ohaio",
        ]
        subprocess.check_call('python ecsub submit'.split(" ") + options)

    def test3_01_report(self):
        subprocess.check_call('python ecsub report /tmp/ecsub/'.split(" "))

def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestSet))
    return suite

