# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 17:39:49 2016

@author: bcimini
"""

import subprocess
import time

def monitor():
    while True:
        cmdlist=['df -h', 'df -i -h','vmstat -a -SM 1 1', 'iostat']
        for cmd in cmdlist:
            process=subprocess.Popen(cmd.split(),stdout=subprocess.PIPE)
            out,err=process.communicate()
        time.sleep(30)
        
if __name__=='__main__':
    monitor()
