# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 13:18:34 2016

@author: okada

"""

import unittest
import subprocess

class ShortTest(unittest.TestCase):

    def test1_01_version(self):
        subprocess.check_call(['ecsub', '--version'])
    
    def test2_01_report(self):
        subprocess.check_call(['ecsub', 'report'])


# do not add to suite
#def suite():
#    suite = unittest.TestSuite()
#    suite.addTests(unittest.makeSuite(ShortTest))
#    return suite

