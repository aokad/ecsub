#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 24 15:32:29 2019

@author: aokada
"""

import ecsub.aws

def encrypt(arg):
    return ecsub.aws.encrypt_data(arg.plain_text)

def decrypt(arg):
    return ecsub.aws.decrypt_data(arg.cipher_text)
    
def main():
    pass

if __name__ == "__main__":
    main()

