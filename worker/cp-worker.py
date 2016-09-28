import boto3
import glob
import json
import logging
import os
import re
import subprocess
import sys 
import time

#################################
# CONSTANT PATHS IN THE CONTAINER
#################################

DATA_ROOT = '/home/ubuntu/bucket'
LOCAL_OUTPUT = '/home/ubuntu/local_output'
QUEUE_URL = os.environ['SQS_QUEUE_URL']
AWS_BUCKET = os.environ['AWS_BUCKET']

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

def printAndSave(name, log, values):
	print name.upper(),':',log
	outFile = '%(OUT)s/%(MetadataID)s.std' + name
	outFile = outFile % values
	with open(outFile, 'w') as output:
		output.write(log)

#################################
# RUN CELLPROFILER PROCESS
#################################

def runCellProfiler(message):
    #List the directories in the bucket- this prevents a strange s3fs error
    os.system('ls '+DATA_ROOT+r'/projects')
    # Prepare paths and parameters
    metadataID = '-'.join([x.split('=')[1] for x in message['Metadata'].split(',')]) # Strip equal signs from the metadata
    localOut = LOCAL_OUTPUT + '/%(MetadataID)s' % {'MetadataID': metadataID}
    replaceValues = {'PL':message['pipeline'], 'OUT':localOut, 'FL':message['data_file'],
			'DATA': DATA_ROOT, 'Metadata': message['Metadata'], 'IN': message['input'], 
			'MetadataID':metadataID }
    # Build and run CellProfiler command
    cpDone = LOCAL_OUTPUT + '/cp.is.done'
    if message['pipeline'][-3:]!='.h5':
        cmd = 'cellprofiler -c -r -b -p %(DATA)s/%(PL)s -i %(DATA)s/%(IN)s -o %(OUT)s -d ' + cpDone
        cmd += ' --data-file=%(DATA)s/%(FL)s -g %(Metadata)s'
    else:
        cmd = 'cellprofiler -c -r -b -p %(DATA)s/%(PL)s -o %(OUT)s -d ' + cpDone + ' --data-file=%(DATA)s/%(FL)s -g %(Metadata)s'
    cmd = cmd % replaceValues
    print 'Running', cmd
    subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = subp.communicate()
    printAndSave('err', err, replaceValues)
    # Get the outputs and move them to S3
    if os.path.isfile(cpDone):
        if next(open(cpDone))=='Complete\n':
            time.sleep(30)
            cmd = 'aws s3 mv ' + LOCAL_OUTPUT + ' s3://' + AWS_BUCKET + '/' + message['output'] + ' --recursive' 
            subp = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = subp.communicate()
            print '== OUT',out
            if err == '':
                return 'SUCCESS'
            else:
                print 'OUTPUT PROBLEM. See below'
                print '== ERR',err
                return 'OUTPUT_PROBLEM'
        else:
            print 'CP PROBLEM: Done file reports failure'
            return 'CP_PROBLEM'
    else:
        print 'CP PROBLEM: Done file does not exist.'
        return 'CP_PROBLEM'

#################################
# MAIN WOKRER LOOP
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
	print 'Worker started'
	main()
	print 'Worker finished'

