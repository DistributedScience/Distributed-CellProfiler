import boto3
import glob
import json
import logging
import os
import re
import subprocess
import sys 
import time
import watchtower

#################################
# CONSTANT PATHS IN THE CONTAINER
#################################

DATA_ROOT = '/home/ubuntu/bucket'
LOCAL_OUTPUT = '/home/ubuntu/local_output'
QUEUE_URL = os.environ['SQS_QUEUE_URL']
AWS_BUCKET = os.environ['AWS_BUCKET']
LOG_GROUP_NAME= os.environ['LOG_GROUP_NAME']
CHECK_IF_DONE_BOOL= os.environ['CHECK_IF_DONE_BOOL']
EXPECTED_NUMBER_FILES= os.environ['EXPECTED_NUMBER_FILES']

#################################
# CLASS TO HANDLE THE SQS QUEUE
#################################

class JobQueue():

	def __init__(self, queueURL):
		self.client = boto3.client('sqs')
		self.queueURL = queueURL
	
	def readMessage(self):
		response = self.client.receive_message(QueueUrl=self.queueURL, WaitTimeSeconds=20)
		if 'Messages' in response.keys():
			data = json.loads(response['Messages'][0]['Body'])
			handle = response['Messages'][0]['ReceiptHandle']
			return data, handle
		else:
			return None, None

	def deleteMessage(self, handle):
		self.client.delete_message(QueueUrl=self.queueURL, ReceiptHandle=handle)
		return

	def returnMessage(self, handle):
		self.client.change_message_visibility(QueueUrl=self.queueURL, ReceiptHandle=handle, VisibilityTimeout=60)
		return

#################################
# AUXILIARY FUNCTIONS
#################################


def monitorAndLog(process,logger):
    while True:
        output= process.stdout.readline()
        if output== '' and process.poll() is not None:
            break
        if output:
            print output.strip()
            logger.info(output)  

def printandlog(text,logger):
    print text
    logger.info(text)

#################################
# RUN CELLPROFILER PROCESS
#################################

def runCellProfiler(message):
    #List the directories in the bucket- this prevents a strange s3fs error
    os.system('ls '+DATA_ROOT+r'/projects')
    # Prepare paths and parameters
    metadataID = '-'.join([x.split('=')[1] for x in message['Metadata'].split(',')]) # Strip equal signs from the metadata
    localOut = LOCAL_OUTPUT + '/%(MetadataID)s' % {'MetadataID': metadataID}
    remoteOut= os.path.join(message['output'],metadataID)
    replaceValues = {'PL':message['pipeline'], 'OUT':localOut, 'FL':message['data_file'],
			'DATA': DATA_ROOT, 'Metadata': message['Metadata'], 'IN': message['input'], 
			'MetadataID':metadataID }
    # See if this is a message you've already handled, if you've so chosen
    if CHECK_IF_DONE_BOOL == 'True':
        try:
		s3client=boto3.client('s3')
		bucketlist=s3client.list_objects(Bucket=AWS_BUCKET,Prefix=remoteOut)
		objectsizelist=[k['Size'] for k in bucketlist['Contents']]
		if len(objectsizelist)>=int(EXPECTED_NUMBER_FILES):
		    if 0 not in objectsizelist:
			return 'SUCCESS'
	except KeyError: #Returned if that folder does not exist
		pass
    # Configure the logs
    logger = logging.getLogger(__name__)
    watchtowerlogger=watchtower.CloudWatchLogHandler(log_group=LOG_GROUP_NAME, stream_name=metadataID,create_log_group=False)
    logger.addHandler(watchtowerlogger)
    # Build and run CellProfiler command
    cpDone = LOCAL_OUTPUT + '/cp.is.done'
    if message['pipeline'][-3:]!='.h5':
        cmd = 'cellprofiler -c -r -b -p %(DATA)s/%(PL)s -i %(DATA)s/%(IN)s -o %(OUT)s -d ' + cpDone
        cmd += ' --data-file=%(DATA)s/%(FL)s -g %(Metadata)s'
    else:
        cmd = 'cellprofiler -c -r -b -p %(DATA)s/%(PL)s -o %(OUT)s -d ' + cpDone + ' --data-file=%(DATA)s/%(FL)s -g %(Metadata)s'
    cmd = cmd % replaceValues
    print 'Running', cmd
    logger.info(cmd)
    
    subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    monitorAndLog(subp,logger)
   
    # Get the outputs and move them to S3
    if os.path.isfile(cpDone):
        if next(open(cpDone))=='Complete\n':
            time.sleep(30)
	    mvtries=0
	    while mvtries <3:
	    	try:
            		printandlog('Move attempt #'+(mvtries)+1,logger)
			cmd = 'aws s3 mv ' + localOut + ' s3://' + AWS_BUCKET + '/' + remoteOut + ' --recursive' 
            		subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
           		out,err = subp.communicate()
            		printandlog('== OUT /n'+out, logger)
            		if err == '':
				break
		except
			printandlog('Move failed',logger)
			printandlog('== ERR /n'+err,logger)
			time.sleep(30)
			mvtries+=1
	    if mvtries<3:
		printandlog('SUCCESS',logger)
		logger.removeHandler(watchtowerlogger)
               	return 'SUCCESS'
            else:
                printandlog('OUTPUT PROBLEM. Giving up on '+metadataID,logger)
		logger.removeHandler(watchtowerlogger)
		return 'OUTPUT_PROBLEM'
        else:
            printandlog('CP PROBLEM: Done file reports failure',logger)
	    logger.removeHandler(watchtowerlogger)
            return 'CP_PROBLEM'
    else:
        printandlog('CP PROBLEM: Done file does not exist.',logger)
	logger.removeHandler(watchtowerlogger)
        return 'CP_PROBLEM'
    

#################################
# MAIN WORKER LOOP
#################################

def main():
	queue = JobQueue(QUEUE_URL)
	# Main loop. Keep reading messages while they are available in SQS
	while True:
		msg, handle = queue.readMessage()
		if msg is not None:
			result = runCellProfiler(msg)
			if result == 'SUCCESS':
				print 'Batch completed successfully.'
				queue.deleteMessage(handle)
			else:
				print 'Returning message to the queue.'
				queue.returnMessage(handle)
		else:
			print 'No messages in the queue'
			break

#################################
# MODULE ENTRY POINT
#################################

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	print 'Worker started'
	main()
	print 'Worker finished'

