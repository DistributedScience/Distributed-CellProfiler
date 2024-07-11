# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 17:39:49 2016

@author: bcimini
"""

import subprocess
import time
import logging

def runcmd(cmd):
    logger = logging.getLogger(__name__)
    process=subprocess.Popen(cmd.split(),stdout=subprocess.PIPE)
    out,err=process.communicate()
    logger.info(out)
    return out

def monitor():
    logger = logging.getLogger(__name__)
    while True:
        out = runcmd('df -h')
        metrics = str(out).split('\\n')[1]
        metrics = [x for x in metrics.split(' ') if x]
        logger.info(f'Root disk usage {metrics[4]}.')
        if int((metrics[4].split('%')[0]))> 90:
            logger.warning('WARNING: High disk usage.')

        runcmd('df -i -h')

        out = runcmd('vmstat -a -SM 1 1')
        metrics = str(out).split('\\n')[2]
        metrics = [x for x in metrics.split(' ') if x]
        logger.info(f'Free memory {metrics[3]}. Inactive memory {metrics[4]}. Active memory {metrics[5]}')
        if float(metrics[4])/float(metrics[5]) < .1:
            logger.warning('WARNING: High memory usage.')
        
        out = runcmd('iostat')
        metrics = str(out).split('\\n')[3]
        metrics = [x for x in metrics.split(' ') if x]
        logger.info(f'Idle CPU {metrics[-1]}')
        if float(metrics[-1]) < 10:
            logger.warning('WARNING: Low CPU')
            
        time.sleep(30)
        
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    monitor()
