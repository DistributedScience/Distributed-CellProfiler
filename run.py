import os, sys
import boto, boto3
import datetime
import json
import subprocess
import time
from base64 import b64encode
from ConfigParser import ConfigParser
from pprint import pprint

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

def killdeadAlarms(fleetId,monitorapp):
	checkdates=[datetime.datetime.now().strftime('%Y-%m-%d'),(datetime.datetime.now()-datetime.timedelta(days=1)).strftime('%Y-%m-%d')]
	todel=[]
	for eachdate in checkdates:
         cmd="aws ec2 describe-spot-fleet-request-history --spot-fleet-request-id "+fleetId+" --start-time "+eachdate+" --output json" 
         datedead=getAWSJsonOutput(cmd)
         for eachevent in datedead['HistoryRecords']:
             if eachevent['EventType']=='instanceChange':
                 if eachevent['EventInformation']['EventSubType']=='terminated':
                     todel.append(eachevent['EventInformation']['InstanceId'])
	for eachmachine in todel:
	 	cmd='aws cloudwatch delete-alarms --alarm-name '+monitorapp+'_'+eachmachine
		subprocess.Popen(cmd.split())
		time.sleep(3) #Avoid Rate exceeded error
		print 'Deleted', monitorapp+'_'+eachmachine, 'if it existed'
	print 'Old alarms deleted'

def seeIfLogExportIsDone(logExportId):
	while True:
		cmd='aws logs describe-export-tasks --task-id '+logExportId
		result =getAWSJsonOutput(cmd) 
		if result['exportTasks'][0]['status']['code']!='PENDING':
			if result['exportTasks'][0]['status']['code']!='RUNNING':
				print result['exportTasks'][0]['status']['code']
				break
		time.sleep(30)
	
def generateECSconfig(ECS_CLUSTER,APP_NAME,AWS_BUCKET,s3client):
	configfile=open('configtemp.config','w')
	configfile.write('ECS_CLUSTER='+ECS_CLUSTER+'\n')
	configfile.write('ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs"]')
	configfile.close()
	s3client.upload_file('configtemp.config',AWS_BUCKET,'ecsconfigs/'+APP_NAME+'_ecs.config')
	os.remove('configtemp.config')
	return 's3://'+AWS_BUCKET+'/ecsconfigs/'+APP_NAME+'_ecs.config'

def generateUserData(ecsConfigFile):
	userData= '#!/bin/bash \n'
	userData+='sudo yum install -y aws-cli \n'
	userData+='sudo yum install -y awslogs \n'
	userData+='aws s3 cp '+ecsConfigFile+' /etc/ecs/ecs.config'
	return b64encode(userData)
	
def removequeue(queueName):
    cmd='aws sqs list-queues --queue-name-prefix ' + queueName
    queueoutput=getAWSJsonOutput(cmd)
    if len(queueoutput["QueueUrls"])==1:
	queueUrl=queueoutput["QueueUrls"][0]
    else: #In case we have "AnalysisQueue" and "AnalysisQueue1" and only want to delete the first of those
	for eachUrl in queueoutput["QueueUrls"]:
		if eachUrl.split('/')[-1] == queueName:
			queueUrl=eachUrl
    cmd='aws sqs delete-queue --queue-url ' + queueUrl
    subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
	
def deregistertask(taskName):
    cmd='aws ecs list-task-definitions --family-prefix '+taskName+' --status ACTIVE'
    taskArns=getAWSJsonOutput(cmd)
    for eachtask in taskArns['taskDefinitionArns']:
	fulltaskname=eachtask.split('/')[-1]
	cmd='aws ecs deregister-task-definition --task-definition '+fulltaskname
	result=getAWSJsonOutput(cmd) 

def removeClusterIfUnused(clusterName):
    if clusterName != 'default':
	cmd = 'aws ecs describe-clusters --cluster '+clusterName
	result=getAWSJsonOutput(cmd) 
	if sum([result['clusters'][0]['pendingTasksCount'],result['clusters'][0]['runningTasksCount'],result['clusters'][0]['activeServicesCount']])==0:
	    cmd = 'aws ecs delete-cluster --cluster '+clusterName
	    result=getAWSJsonOutput(cmd)
	
#################################
# CLASS TO HANDLE SQS QUEUE
#################################

class JobQueue():

    def __init__(self,name=None):
        self.sqs = boto3.resource('sqs')
        if name==None:
            self.queue = self.sqs.get_queue_by_name(QueueName=SQS_QUEUE_NAME)
        else:
            self.queue = self.sqs.get_queue_by_name(QueueName=name)
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
        if [visible, nonVis] != [self.pending,self.inProcess]:
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
	if 'output_structure' not in jobInfo.keys(): #backwards compatibility for 1.0.0
		jobInfo["output_structure"]=''
	templateMessage = {'Metadata': '',
		'pipeline': jobInfo["pipeline"],
		'output': jobInfo["output"],
            	'input': jobInfo["input"],
		'data_file': jobInfo["data_file"],
		'output_structure':jobInfo["output_structure"]
	}

	# Step 2: Reach the queue and schedule tasks
	print 'Contacting queue'
	queue = JobQueue()
	print 'Scheduling tasks'
	for batch in jobInfo["groups"]:
		#support Metadata passed as either a single string or as a list
		try: #single string ('canonical' DCP)
			templateMessage["Metadata"] = batch["Metadata"]
		except KeyError: #list of parameters (cellprofiler --print-groups)
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

	#Step 1: set up the configuration files
    s3client=boto3.client('s3')
    ecsConfigFile=generateECSconfig(ECS_CLUSTER,APP_NAME,AWS_BUCKET,s3client)
    spotfleetConfig=loadConfig(sys.argv[2])
    userData=generateUserData(ecsConfigFile)
    spotfleetConfig['LaunchSpecifications'][0]["UserData"]=userData
    spotfleetConfig['LaunchSpecifications'][0]['BlockDeviceMappings'][1]['Ebs']["VolumeSize"]= EBS_VOL_SIZE


	# Step 2: make the spot fleet request
    ec2client=boto3.client('ec2')
    requestInfo = ec2client.request_spot_fleet(SpotFleetRequestConfig=spotfleetConfig)
    print 'Request in process. Wait until your machines are available in the cluster.'
    print 'SpotFleetRequestId',requestInfo['SpotFleetRequestId']
    createMonitor=open('files/' + APP_NAME + 'SpotFleetRequestId.json','w')
    createMonitor.write('{"MONITOR_FLEET_ID" : "'+requestInfo['SpotFleetRequestId']+'",\n')
    createMonitor.write('"MONITOR_APP_NAME" : "'+APP_NAME+'",\n')
    createMonitor.write('"MONITOR_ECS_CLUSTER" : "'+ECS_CLUSTER+'",\n')
    createMonitor.write('"MONITOR_QUEUE_NAME" : "'+SQS_QUEUE_NAME+'",\n')
    createMonitor.write('"MONITOR_BUCKET_NAME" : "'+AWS_BUCKET+'",\n')
    createMonitor.write('"MONITOR_LOG_GROUP_NAME" : "'+LOG_GROUP_NAME+'",\n')
    createMonitor.write('"MONITOR_START_TIME" : "'+str(int(time.time()*1000))+'"}\n')
    createMonitor.close()
    
    
  
	
	# Step 2: wait until instances in the cluster are available
    cmd = 'aws ec2 describe-spot-fleet-instances --spot-fleet-request-id ' + requestInfo['SpotFleetRequestId']
    status = getAWSJsonOutput(cmd)
    while len(status['ActiveInstances']) < CLUSTER_MACHINES:
         time.sleep(20)
         print '.',
         status = getAWSJsonOutput(cmd)
    print '\nCluster ready'

	# Step 3: Create a log group for this app and date if one does not already exist
    logclient=boto3.client('logs')
    loggroupinfo=logclient.describe_log_groups(logGroupNamePrefix=LOG_GROUP_NAME)
    groupnames=[d['logGroupName'] for d in loggroupinfo['logGroups']]
    if LOG_GROUP_NAME not in groupnames:
         logclient.create_log_group(logGroupName=LOG_GROUP_NAME)
	 logclient.put_retention_policy(logGroupName=LOG_GROUP_NAME, retentionInDays=60)
    if LOG_GROUP_NAME+'_perInstance' not in groupnames:
         logclient.create_log_group(logGroupName=LOG_GROUP_NAME+'_perInstance')
	 logclient.put_retention_policy(logGroupName=LOG_GROUP_NAME+'_perInstance', retentionInDays=60)
		
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
    
    monitorInfo = loadConfig(sys.argv[2])
    monitorcluster=monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp=monitorInfo["MONITOR_APP_NAME"]
    fleetId=monitorInfo["MONITOR_FLEET_ID"]
    queueId=monitorInfo["MONITOR_QUEUE_NAME"]
    bucketId=monitorInfo["MONITOR_BUCKET_NAME"]
    loggroupId=monitorInfo["MONITOR_LOG_GROUP_NAME"]
    starttime=monitorInfo["MONITOR_START_TIME"]

    	# Step 1: Create job and count messages periodically
    queue = JobQueue(name=queueId)
    while queue.pendingLoad():
	#Once a day check for terminated machines and delete their alarms.  
	#These records are only kept for 48 hours, which is why we don't just do it at the end
        curtime=datetime.datetime.now().strftime('%H%M')
        if curtime=='1200':
            killdeadAlarms(fleetId,monitorapp)
        time.sleep(MONITOR_TIME)
	
	# Step 2: When no messages are pending, stop service
    cmd = 'aws ecs update-service --cluster ' + monitorcluster + \
	      ' --service ' + monitorapp + 'Service' + \
	      ' --desired-count 0'
    update = getAWSJsonOutput(cmd)
    print 'Service has been downscaled'

	# Step3: Delete the alarms from active machines and machines that have died since the last sweep 
    cmd= 'aws ec2 describe-spot-fleet-instances --spot-fleet-request-id '+fleetId+" --output json"
    result= getAWSJsonOutput(cmd)
    for eachinstance in result['ActiveInstances']:
        delalarm='aws cloudwatch delete-alarms --alarm-name '+monitorapp+'_'+eachinstance["InstanceId"]
        subprocess.Popen(delalarm.split())
    killdeadAlarms(fleetId,monitorapp)
	
	# Step 4: Read spot fleet id and terminate all EC2 instances
    print 'Shutting down spot fleet',fleetId
    cmd = 'aws ec2 cancel-spot-fleet-requests --spot-fleet-request-ids '+ fleetId +' --terminate-instances'
    result = getAWSJsonOutput(cmd)
    print 'Job done.'

	# Step 5. Release other resources
	# Remove SQS queue, ECS Task Definition, ECS Service
    ECS_TASK_NAME = monitorapp + 'Task'
    ECS_SERVICE_NAME = monitorapp + 'Service'
    print 'Deleting existing queue.'
    removequeue(queueId)
    print 'Deleting service'
    cmd='aws ecs delete-service --cluster '+monitorcluster+' --service '+ECS_SERVICE_NAME
    result=getAWSJsonOutput(cmd)
    print 'De-registering task'
    deregistertask(ECS_TASK_NAME)
    print "Removing cluster if it's not the default and not otherwise in use"
    removeClusterIfUnused(monitorcluster)
	
	#Step 6: Export the logs to S3
    cmd = 'aws logs create-export-task --task-name "'+loggroupId+'" --log-group-name '+loggroupId+ \
	' --from '+starttime+' --to '+'%d' %(time.time()*1000)+' --destination '+bucketId+' --destination-prefix exportedlogs/'+loggroupId
    result =getAWSJsonOutput(cmd)
    print 'Log transfer 1 to S3 initiated'
    seeIfLogExportIsDone(result['taskId'])
    cmd = 'aws logs create-export-task --task-name "'+loggroupId+'_perInstance" --log-group-name '+loggroupId+'_perInstance '+ \
	'--from '+starttime+' --to '+'%d' %(time.time()*1000)+' --destination '+bucketId+' --destination-prefix exportedlogs/'+loggroupId
    result =getAWSJsonOutput(cmd)
    print 'Log transfer 2 to S3 initiated'
    seeIfLogExportIsDone(result['taskId'])
    print 'All export tasks done'

	
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

