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
            "--image", "python:2-alpine3.6",
            "--shell", "ash",
            "--script", "./examples/run-wordcount.sh",
            "--tasks", "./examples/tasks-wordcount.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "22",
            "--aws-s3-bucket", "s3://ecsub-ohaio/output/",
        ]
        subprocess.check_call('python ecsub submit'.split(" ") + options)

    def test3_01_report(self):
        subprocess.check_call('python ecsub report /tmp/ecsub/'.split(" "))

def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestSet))
    return suite

