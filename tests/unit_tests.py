# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:18:34 2016

@author: okada

"""

import unittest
import glob
import subprocess
import datetime
import ecsub.encrypt

class SubmitTest(unittest.TestCase):

    WDIR = None
    START = None
    
    # init class
    @classmethod
    def setUpClass(self):
        self.WDIR = "/tmp/ecsub"
        self.START = datetime.datetime.now().strftime("%Y%m%d%H%M")
    
    # terminated class
    @classmethod
    def tearDownClass(self):
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
            "--script", "./tests/run-wordcount.sh",
            "--tasks", "./tests/test-wordcount.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "1",
            "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
            "--aws-log-group-name", "ecsub-travis1",
        ]
        subprocess.check_call(['python', 'ecsub', 'submit'] + options)
    
    def test2_02_submit(self):
        options = [
            "--wdir", self.WDIR,
            "--image", "python:2-alpine3.6",
            "--shell", "ash",
            "--script", "./tests/run-wordcount.sh",
            "--tasks", "./tests/test-wordcount.tsv",
            "--aws-ec2-instance-type", "t2.micro",
            "--disk-size", "1",
            "--aws-s3-bucket", "s3://travisci-work/wordcount/output/",
            "--spot",
            "--aws-log-group-name", "ecsub-travis2",
        ]
        subprocess.check_call(['python', 'ecsub', 'submit'] + options)
    
    def test3_01_report(self):
        options = [
            "--wdir", self.WDIR,
            "-b", self.START,
        ]
        subprocess.check_call(['python', 'ecsub', 'report'] + options)

    def test4_01_logs(self):

        options = [
            "download",
            "--wdir", self.WDIR,
            "--log-group-prefix", "ecsub-travis"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)
            
    def test4_02_logs(self):
        
        options = [
            "download",
            "--wdir", self.WDIR,
            "--log-group-prefix", "ecsub-travis",
            "--tail"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)
            
    def test4_03_logs(self):

        options = [
            "download",
            "--wdir", self.WDIR,
            "--log-group-name", "ecsub-travis1",
            "--log-stream-prefix", "ecsub/"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)
            
    def test4_04_logs(self):

        options = [
            "download",
            "--wdir", self.WDIR,
            "--log-group-name", "ecsub-travis1",
            "--log-stream-prefix", "ecsub/",
            "--tail"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)

    def test4_05_logs(self):
        
        options = [
            "remove-log-stream",
            "--log-group-name", "ecsub-travis1",
            "--log-stream-prefix", "ecsub/"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)
            
    def test4_06_logs(self):
        
        options = [
            "remove-log-group",
            "--log-group-name", "ecsub-travis2"
        ]
        subprocess.check_call(['python', 'ecsub', 'logs'] + options)
    
    #def test5_01_delete(self):
    #
    #    cluster_name = glob.glob(self.WDIR + "/*")[0].split("/")[-1].rstrip("/")
    #
    #    options = [
    #        cluster_name,
    #        "--wdir", self.WDIR
    #    ]
    #    subprocess.check_call(['python', 'ecsub', 'delete'] + options)

    def test6_01_encrypt(self):
    
        class Argments:
            def __init__(self):
                self.plain_text = "abcdef"
                self.cipher_text = ""
                
        args = Argments()
        args.cipher_text = ecsub.encrypt.encrypt(args)
        dec = ecsub.encrypt.decrypt(args)
        self.assertEqual (args.plain_text, dec)

def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(SubmitTest))
    return suite

