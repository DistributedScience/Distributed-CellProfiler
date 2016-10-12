# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 17:39:49 2016

@author: bcimini
"""

import subprocess
import time
import logging
import watchtower
import os
import sys

LOG_GROUP_NAME= os.environ['LOG_GROUP_NAME']
MY_INSTANCE_ID= sys.argv[1]
MY_TASK_NAME= sys.argv[2]

def monitor():
    logger = logging.getLogger(__name__)
    watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME+'_perInstance', stream_name=MY_INSTANCE_ID+'_'+MY_TASK_NAME,create_log_group=False)
    logger.addHandler(watchtowerlogger)
    while True:
        cmd='vmstat -SM'
        process=subprocess.Popen(cmd.split(),stdout=subprocess.PIPE)
        out,err=process.communicate()
        logger.info(out)
        time.sleep(30)
        
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    monitor()
