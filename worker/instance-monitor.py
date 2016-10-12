# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 17:39:49 2016

@author: bcimini
"""

import subprocess
import time

while True:
    cmd='vmstat -SM'
    process=subprocess.Popen(cmd.split(),stdout=subprocess.PIPE)
    out,err=process.communicate()
    time.sleep(30)