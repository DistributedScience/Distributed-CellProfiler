import os, sys
import boto, boto3
import datetime
import json
import subprocess
import time

from config import *
MONITOR_TIME = 60

#################################
# AUXILIARY FUNCTIONS
#################################

def getAWSJsonOutput(cmd):
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
	out, err = process.communicate()
	requestInfo = json.loads(out)
	return requestInfo

def loadConfig(configFile):
	data = None
	with open(configFile, 'r') as conf:
		data = json.load(conf)
	return data

#################################
# CLASS TO HANDLE SQS QUEUE
#################################

class JobQueue():

	def __init__(self):
		self.sqs = boto3.resource('sqs')
		self.queue = self.sqs.get_queue_by_name(QueueName=SQS_QUEUE_NAME)
		self.inProcess = -1 
		self.pending = -1

	def scheduleBatch(self, data):
		msg = json.dumps(data)
		response = self.queue.send_message(MessageBody=msg)
		print 'Batch sent. Message ID:',response.get('MessageId')

	def pendingLoad(self):
		self.queue.load()
		visible = int( self.queue.attributes['ApproximateNumberOfMessages'] )
		nonVis = int( self.queue.attributes['ApproximateNumberOfMessagesNotVisible'] )
		if visible != self.pending:
			self.pending = visible
			self.inProcess = nonVis
			d = datetime.datetime.now()
			print d,'In process:',nonVis,'Pending',visible
		if visible + nonVis > 0:
			return True
		else:
			return False

#################################
# SERVICE 1: SUBMIT JOB
#################################

def submitJob():
	if len(sys.argv) < 3:
		print 'Use: run.py submitJob jobfile'
		sys.exit()

	# Step 1: Read the job configuration file
	jobInfo = loadConfig(sys.argv[2])
	templateMessage = {'pipeline': jobInfo["pipeline"],
		'output': jobInfo["output"],
            'input': jobInfo["input"],
		'data_file': jobInfo["data_file"],
		'Metadata': ''
	}

	# Step 2: Reach the queue and schedule tasks
	print 'Contacting queue'
	queue = JobQueue()
	print 'Scheduling tasks'
	for batch in jobInfo["groups"]:
		templateMessage["Metadata"] = batch
		queue.scheduleBatch(templateMessage)
	print 'Job submitted. Check your queue'

#################################
# SERVICE 2: START CLUSTER 
#################################

def startCluster():
	if len(sys.argv) < 3:
		print 'Use: run.py startCluster configFile'
		sys.exit()

	# Step 1: make a spot fleet request
	cmd = 'aws ec2 request-spot-fleet --spot-fleet-request-config file://' + sys.argv[2]
	requestInfo = getAWSJsonOutput(cmd)
	print 'Request in process. Wait until your machines are available in the cluster.'
	print 'SpotFleetRequestId',requestInfo['SpotFleetRequestId']
	with open('files/' + APP_NAME + '.SpotFleetRequestId','w') as fleetId:
		fleetId.write(requestInfo['SpotFleetRequestId'])
	
	# Step 2: wait until instances in the cluster are available
	cmd = 'aws ec2 describe-spot-fleet-instances --spot-fleet-request-id ' + requestInfo['SpotFleetRequestId']
	status = getAWSJsonOutput(cmd)
	while len(status['ActiveInstances']) < CLUSTER_MACHINES:
		time.sleep(20)
		print '.',
		status = getAWSJsonOutput(cmd)
	print '\nCluster ready'

	# Step 3: tag all instances in the cluster
	print 'Tagging EC2 instances'
	resources = ' '.join( [k['InstanceId'] for k in status['ActiveInstances']] )
	cmd = 'aws ec2 create-tags --resources ' + resources + ' --tags Key=Name,Value=' + APP_NAME + 'Worker'
	subprocess.Popen(cmd.split())

	# Step 4: update the ECS service to inject docker containers in EC2 instances
	print 'Updating service'
	cmd = 'aws ecs update-service --cluster ' + ECS_CLUSTER + \
	      ' --service ' + APP_NAME + 'Service' + \
	      ' --desired-count ' + str(CLUSTER_MACHINES*TASKS_PER_MACHINE)
	update = getAWSJsonOutput(cmd)
	print 'Service updated. Your job should start in a few minutes.'

#################################
# SERVICE 3: MONITOR JOB 
#################################

def monitor():
	if len(sys.argv) < 3:
		print 'Use: run.py monitor spotFleetIdFile'
		sys.exit()
	
	# Step 1: Create job and count messages periodically
	queue = JobQueue()
	while queue.pendingLoad():
		time.sleep(MONITOR_TIME)
	
	# Step 2: When no messages are pending, stop service
	cmd = 'aws ecs update-service --cluster ' + ECS_CLUSTER + \
	      ' --service ' + APP_NAME + 'Service' + \
	      ' --desired-count 0'
	update = getAWSJsonOutput(cmd)
	print 'Service has been downscaled'

	# Step 3: Read spot fleet id and terminate all EC2 instances
	with open(sys.argv[2],'r') as idFile:
		fleetId = idFile.readline()
		print 'Shutting down spot fleet',fleetId
		cmd = 'aws ec2 cancel-spot-fleet-requests --spot-fleet-request-ids '+ fleetId +' --terminate-instances'
		result = getAWSJsonOutput(cmd)
	print 'Job done.'

	# Step 4. Release other resources
	# Remove SQS queue, ECS Task Definition, ECS Service


#################################
# MAIN USER INTERACTION 
#################################

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print 'Use: run.py submitJob | startCluster | monitor'
		sys.exit()
	if sys.argv[1] == 'submitJob':
		submitJob()
	elif sys.argv[1] == 'startCluster':
		startCluster()
	elif sys.argv[1] == 'monitor':
		monitor()

