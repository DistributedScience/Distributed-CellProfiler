from __future__ import print_function
import os, sys
import boto3
import datetime
import json
import time
from base64 import b64encode

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import *
MONITOR_TIME = 60

#################################
# AUXILIARY FUNCTIONS
#################################

def loadConfig(configFile):
    data = None
    with open(configFile, 'r') as conf:
        data = json.load(conf)
    return data

def killdeadAlarms(fleetId,monitorapp,ec2,cloud):
    todel=[]
    changes = ec2.describe_spot_fleet_request_history(SpotFleetRequestId=fleetId,StartTime=datetime.datetime.now()-datetime.timedelta(hours=2))
    for eachevent in changes['HistoryRecords']:
        if eachevent['EventType']=='instanceChange':
            if eachevent['EventInformation']['EventSubType']=='terminated':
                todel.append(eachevent['EventInformation']['InstanceId'])

    existing_alarms = [x['AlarmName'] for x in cloud.describe_alarms(AlarmNamePrefix=monitorapp)['MetricAlarms']]
    
    for eachmachine in todel:
        monitorname = monitorapp+'_'+eachmachine
        if monitorname in existing_alarms:
            cloud.delete_alarms(AlarmNames=[monitorname])
            print('Deleted', monitorname, 'if it existed')
            time.sleep(3)
    
    print('Old alarms deleted')

def generateECSconfig(ECS_CLUSTER,APP_NAME,AWS_BUCKET,s3client):
    configfile=open('configtemp.config','w')
    configfile.write('ECS_CLUSTER='+ECS_CLUSTER+'\n')
    configfile.write('ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs"]')
    configfile.close()
    s3client.upload_file('configtemp.config',AWS_BUCKET,'ecsconfigs/'+APP_NAME+'_ecs.config')
    os.remove('configtemp.config')
    return 's3://'+AWS_BUCKET+'/ecsconfigs/'+APP_NAME+'_ecs.config'

def generateUserData(ecsConfigFile,dockerBaseSize):
    config_str = '#!/bin/bash \n'
    config_str += 'sudo yum install -y aws-cli \n'
    config_str += 'sudo yum install -y awslogs \n'
    config_str += 'aws s3 cp '+ecsConfigFile+' /etc/ecs/ecs.config'

    boothook_str = '#!/bin/bash \n'
    boothook_str += "echo 'OPTIONS="+'"${OPTIONS} --storage-opt dm.basesize='+str(dockerBaseSize)+'G"'+"' >> /etc/sysconfig/docker"

    config = MIMEText(config_str, _subtype='x-shellscript')
    config.add_header('Content-Disposition', 'attachment',filename='config_temp.txt')

    boothook = MIMEText(boothook_str, _subtype='cloud-boothook')
    boothook.add_header('Content-Disposition', 'attachment',filename='boothook_temp.txt')

    pre_user_data = MIMEMultipart()
    pre_user_data.attach(boothook)
    pre_user_data.attach(config)

    return b64encode(pre_user_data.as_string())

def removequeue(queueName):
    sqs = boto3.client('sqs')
    queueoutput= sqs.list_queues(QueueNamePrefix=queueName)
    if len(queueoutput["QueueUrls"])==1:
        queueUrl=queueoutput["QueueUrls"][0]
    else: #In case we have "AnalysisQueue" and "AnalysisQueue1" and only want to delete the first of those
        for eachUrl in queueoutput["QueueUrls"]:
            if eachUrl.split('/')[-1] == queueName:
                queueUrl=eachUrl
    sqs.delete_queue(QueueURL=queueUrl)

def deregistertask(taskName, ecs):
    taskArns = ecs.list_task_definitions(familyPrefix=taskName, status='ACTIVE')
    for eachtask in taskArns['taskDefinitionArns']:
        fulltaskname=eachtask.split('/')[-1]
        ecs.deregister_task_definition(taskDefinition=fulltaskname)

def removeClusterIfUnused(clusterName, ecs):
    if clusterName != 'default':
        #never delete the default cluster
        ecs.describe_clusters(clusters=[clusterName])
        if sum([result['clusters'][0]['pendingTasksCount'],result['clusters'][0]['runningTasksCount'],result['clusters'][0]['activeServicesCount'],result['clusters'][0]['registeredContainerInstancesCount']])==0:
            ecs.delete_cluster(cluster=clusterName)

def downscaleSpotFleet(queue, spotFleetID, ec2):
    visible, nonvisible = queue.returnLoad()
    if visible > 0:
        return
    else:
        status = ec2.describe_spot_fleet_instances(SpotFleetRequestId=spotFleetID)
        if nonvisible < len(status['ActiveInstances']):
            ec2.modify_spot_fleet_request(ExcessCapacityTerminationPolicy='noTermination', SpotFleetRequestId=spotFleetID, TargetCapacity = nonvisible)

def export_logs(logs, loggroupId, starttime, bucketId, loggroupId)
    result = logs.create_export_task(taskName = loggroupId, logGroupName = loggroupId, fromTime = starttime, to = time.time()*1000, destination = bucketId, destinationPrefix = 'exportedlogs/'+loggroupId)
    
    logExportId = result['taskId']

    while True:
        result = describe_export_tasks(taskId = logExportId)
        if result['exportTasks'][0]['status']['code']!='PENDING':
            if result['exportTasks'][0]['status']['code']!='RUNNING':
                print(result['exportTasks'][0]['status']['code'])
                break
        time.sleep(30)

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
        print('Batch sent. Message ID:',response.get('MessageId'))

    def pendingLoad(self):
        self.queue.load()
        visible = int( self.queue.attributes['ApproximateNumberOfMessages'] )
        nonVis = int( self.queue.attributes['ApproximateNumberOfMessagesNotVisible'] )
        if [visible, nonVis] != [self.pending,self.inProcess]:
            self.pending = visible
            self.inProcess = nonVis
            d = datetime.datetime.now()
            print(d,'In process:',nonVis,'Pending',visible)
        if visible + nonVis > 0:
            return True
        else:
            return False

    def returnLoad(self):
        self.queue.load()
        visible = int( self.queue.attributes['ApproximateNumberOfMessages'] )
        nonVis = int( self.queue.attributes['ApproximateNumberOfMessagesNotVisible'] )
	return visible, nonVis


#################################
# SERVICE 1: SUBMIT JOB
#################################

def submitJob():
    if len(sys.argv) < 3:
        print('Use: run.py submitJob jobfile')
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
    print('Contacting queue')
    queue = JobQueue()
    print('Scheduling tasks')
    for batch in jobInfo["groups"]:
        #support Metadata passed as either a single string or as a list
        try: #single string ('canonical' DCP)
            templateMessage["Metadata"] = batch["Metadata"]
        except KeyError: #list of parameters (cellprofiler --print-groups)
            templateMessage["Metadata"] = batch
        queue.scheduleBatch(templateMessage)
    print('Job submitted. Check your queue')

#################################
# SERVICE 2: START CLUSTER 
#################################

def startCluster():
    if len(sys.argv) < 3:
        print('Use: run.py startCluster configFile')
        sys.exit()

    #Step 1: set up the configuration files
    s3client = boto3.client('s3')
    ecsConfigFile=generateECSconfig(ECS_CLUSTER,APP_NAME,AWS_BUCKET,s3client)
    spotfleetConfig=loadConfig(sys.argv[2])
    userData=generateUserData(ecsConfigFile,DOCKER_BASE_SIZE)
    for LaunchSpecification in range(0,len(spotfleetConfig['LaunchSpecifications'])): 
        spotfleetConfig['LaunchSpecifications'][LaunchSpecification]["UserData"]=userData
        spotfleetConfig['LaunchSpecifications'][LaunchSpecification]['BlockDeviceMappings'][1]['Ebs']["VolumeSize"]= EBS_VOL_SIZE


    # Step 2: make the spot fleet request
    ec2client=boto3.client('ec2')
    requestInfo = ec2client.request_spot_fleet(SpotFleetRequestConfig=spotfleetConfig)
    print('Request in process. Wait until your machines are available in the cluster.')
    print('SpotFleetRequestId',requestInfo['SpotFleetRequestId'])

    # Step 3: Make the monitor
    starttime=str(int(time.time()*1000))
    createMonitor=open('files/' + APP_NAME + 'SpotFleetRequestId.json','w')
    createMonitor.write('{"MONITOR_FLEET_ID" : "'+requestInfo['SpotFleetRequestId']+'",\n')
    createMonitor.write('"MONITOR_APP_NAME" : "'+APP_NAME+'",\n')
    createMonitor.write('"MONITOR_ECS_CLUSTER" : "'+ECS_CLUSTER+'",\n')
    createMonitor.write('"MONITOR_QUEUE_NAME" : "'+SQS_QUEUE_NAME+'",\n')
    createMonitor.write('"MONITOR_BUCKET_NAME" : "'+AWS_BUCKET+'",\n')
    createMonitor.write('"MONITOR_LOG_GROUP_NAME" : "'+LOG_GROUP_NAME+'",\n')
    createMonitor.write('"MONITOR_START_TIME" : "'+ starttime+'"}\n')
    createMonitor.close()
    
    # Step 4: Create a log group for this app and date if one does not already exist
    logclient=boto3.client('logs')
    loggroupinfo=logclient.describe_log_groups(logGroupNamePrefix=LOG_GROUP_NAME)
    groupnames=[d['logGroupName'] for d in loggroupinfo['logGroups']]
    if LOG_GROUP_NAME not in groupnames:
        logclient.create_log_group(logGroupName=LOG_GROUP_NAME)
        logclient.put_retention_policy(logGroupName=LOG_GROUP_NAME, retentionInDays=60)
    if LOG_GROUP_NAME+'_perInstance' not in groupnames:
        logclient.create_log_group(logGroupName=LOG_GROUP_NAME+'_perInstance')
        logclient.put_retention_policy(logGroupName=LOG_GROUP_NAME+'_perInstance', retentionInDays=60)
    
    # Step 5: update the ECS service to be ready to inject docker containers in EC2 instances
    print('Updating service')
    ecs = boto3.client('ecs')
    ecs.update_service(cluster=ECS_CLUSTER, service=APP_NAME+'Service', desiredCount=CLUSTER_MACHINES*TASKS_PER_MACHINE)
    print('Service updated.') 
    
    # Step 6: Monitor the creation of the instances until all are present
    status = ec2client.describe_spot_fleet_instances(SpotFleetRequestId=requestInfo['SpotFleetRequestId'])
    while len(status['ActiveInstances']) < CLUSTER_MACHINES:
        # First check to make sure there's not a problem
        errorcheck = ec2client.describe_spot_fleet_request_history(SpotFleetRequestId=requestInfo['SpotFleetRequestId'], EventType='error', StartTime=datetime.datetime.today)
        if len(errorcheck['HistoryRecords']) != 0:
            print('Your spot fleet request is causing an error and is now being cancelled.  Please check your configuration and try again')
            for eacherror in errorcheck['HistoryRecords']:
                print(eacherror['EventInformation']['EventSubType'] + ' : ' + eacherror['EventInformation']['EventDescription'])
            ec2client.cancel_spot_fleet_requests(SpotFleetRequestIds=requestInfo['SpotFleetRequestId'], TerminateInstances=True)
            return
        
        # If everything seems good, just bide your time until you're ready to go
        print('.')
        time.sleep(20)
        status = ec2client.describe_spot_fleet_instances(SpotFleetRequestId=requestInfo['SpotFleetRequestId'])

    print('Spot fleet successfully created. Your job should start in a few minutes.')

#################################
# SERVICE 3: MONITOR JOB 
#################################

def monitor():
    if len(sys.argv) < 3:
        print('Use: run.py monitor spotFleetIdFile')
        sys.exit()
    
    monitorInfo = loadConfig(sys.argv[2])
    monitorcluster=monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp=monitorInfo["MONITOR_APP_NAME"]
    fleetId=monitorInfo["MONITOR_FLEET_ID"]
    queueId=monitorInfo["MONITOR_QUEUE_NAME"]

    ec2 = boto3.client('ec2')
    cloud = boto3.client('cloudwatch') 
    # Step 1: Create job and count messages periodically
    queue = JobQueue(name=queueId)
    while queue.pendingLoad():
        #Once an hour (except at midnight) check for terminated machines and delete their alarms.  
        #This is slooooooow, which is why we don't just do it at the end
        curtime=datetime.datetime.now().strftime('%H%M')
        if curtime[-2:]=='00':
            if curtime[:2]!='00':
                killdeadAlarms(fleetId,monitorapp,ec2,cloud)
        #Once every 10 minutes, check if all jobs are in process, and if so scale the spot fleet size to match
        #the number of jobs still in process WITHOUT force terminating them.
        #This can help keep costs down if, for example, you start up 100+ machines to run a large job, and
        #1-10 jobs with errors are keeping it rattling around for hours.
        if curtime[-1:]=='9':
            downscaleSpotFleet(queue, fleetId, ec2)
        time.sleep(MONITOR_TIME)
    
    # Step 2: When no messages are pending, stop service
    # Reload the monitor info, because for long jobs new fleets may have been started, etc
    monitorInfo = loadConfig(sys.argv[2])
    monitorcluster=monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp=monitorInfo["MONITOR_APP_NAME"]
    fleetId=monitorInfo["MONITOR_FLEET_ID"]
    queueId=monitorInfo["MONITOR_QUEUE_NAME"]
    bucketId=monitorInfo["MONITOR_BUCKET_NAME"]
    loggroupId=monitorInfo["MONITOR_LOG_GROUP_NAME"]
    starttime=monitorInfo["MONITOR_START_TIME"]    

    ecs = boto3.client('ecs')
    ecs.update_service(cluster=monitorcluster, service=monitorapp+'Service', desiredCount=0)
    print('Service has been downscaled')

    # Step3: Delete the alarms from active machines and machines that have died since the last sweep
    # This is in a try loop, because while it is important, we don't want to not stop the spot fleet
    try:
        result = ec2.describe_spot_fleet_instances(SpotFleetRequestId=fleetId)
        instancelist = result['ActiveInstances']
        while len(instancelist) > 0:
            to_del = instancelist[:100]
            del_alarms = [monitorapp+'_'+x['InstanceId'] for x in to_del]
            cloud.delete_alarms(AlarmNames=del_alarms)
            time.sleep(10)
            instancelist = instancelist[100:]
        killdeadAlarms(fleetId,monitorapp)
	except:
        continue

    # Step 4: Read spot fleet id and terminate all EC2 instances
    print('Shutting down spot fleet',fleetId)
    ec2.cancel_spot_fleet_requests(SpotFleetRequestIds=fleetId, TerminateInstances=True)
    print('Job done.')

    # Step 5. Release other resources
    # Remove SQS queue, ECS Task Definition, ECS Service
    ECS_TASK_NAME = monitorapp + 'Task'
    ECS_SERVICE_NAME = monitorapp + 'Service'
    print('Deleting existing queue.')
    removequeue(queueId)
    print('Deleting service')
    ecs.delete_service(cluster=monitorcluster, service = ECS_SERVICE_NAME)
    print('De-registering task')
    deregistertask(ECS_TASK_NAME,ecs)
    print("Removing cluster if it's not the default and not otherwise in use")
    removeClusterIfUnused(monitorcluster, ecs)

    #Step 6: Export the logs to S3
    logs=boto3.client('logs')

    print('Transfer of CellProfiler logs to S3 initiated')
    export_logs(logs, loggroupId, starttime, bucketId, loggroupId)

    print('Transfer of per-instance to S3 initiated')
    export_logs(logs, loggroupId+'_perInstance', starttime, bucketId, loggroupId)

    print('All export tasks done')

#################################
# MAIN USER INTERACTION 
#################################

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Use: run.py submitJob | startCluster | monitor')
        sys.exit()
    if sys.argv[1] == 'submitJob':
        submitJob()
    elif sys.argv[1] == 'startCluster':
        startCluster()
    elif sys.argv[1] == 'monitor':
        monitor()
