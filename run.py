import os, sys
import boto3
import botocore
import datetime
import json
import time
from base64 import b64encode
import configparser

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Back compatability with old config versions
SOURCE_BUCKET = 'False'
WORKSPACE_BUCKET = 'False'
UPLOAD_FLAGS = 'False'
UPDATE_PLUGINS = 'False'
CREATE_DASHBOARD = 'False'
CLEAN_DASHBOARD = 'False'
AUTO_MONITOR = 'False'
REQUIREMENTS_FILE = False
ALWAYS_CONTINUE = 'False'
JOB_RETRIES = 10
ASSIGN_IP = 'True'

from config import *

# Back compatability with old config requirements
if ':' in SQS_DEAD_LETTER_QUEUE:
    SQS_DEAD_LETTER_QUEUE = SQS_DEAD_LETTER_QUEUE.rsplit(':',1)[1]
if REQUIREMENTS_FILE:
    REQUIREMENTS = REQUIREMENTS_FILE

WAIT_TIME = 60
MONITOR_TIME = 60


#################################
# SETUP TEMPLATES
#################################

TASK_DEFINITION = {
    "family": APP_NAME,
    "containerDefinitions": [
        {
            "environment": [
                {
                    "name": "AWS_REGION",
                    "value": AWS_REGION
                }
                ],
            "name": APP_NAME,
            "image": DOCKERHUB_TAG,
            "cpu": CPU_SHARES,
            "memory": MEMORY,
            "essential": True,
            "privileged": True,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": LOG_GROUP_NAME+"_perInstance",
                    "awslogs-region": AWS_REGION,
                    "awslogs-stream-prefix": APP_NAME
                    }
                }
        }
    ]
}


#################################
# AUXILIARY FUNCTIONS
#################################

def generate_task_definition(AWS_PROFILE):
    task_definition = TASK_DEFINITION.copy()

    config = configparser.ConfigParser()
    config.read(f"{os.environ['HOME']}/.aws/config")

    if config.has_section(AWS_PROFILE):
        profile_name = AWS_PROFILE
    elif config.has_section(f'profile {AWS_PROFILE}'):
        profile_name = f'profile {AWS_PROFILE}'
    else:
        print ('Problem handling profile')

    if config.has_option(profile_name, 'role_arn'):
        print ("Using role for credentials", config[profile_name]['role_arn'])
        taskRoleArn = config[profile_name]['role_arn']
    else:
        taskRoleArn = False
        if config.has_option(profile_name, 'source_profile'):
            creds = configparser.ConfigParser()
            creds.read(f"{os.environ['HOME']}/.aws/credentials")
            source_profile = config[profile_name]['source_profile']
            aws_access_key = creds[source_profile]['aws_access_key_id']
            aws_secret_key = creds[source_profile]['aws_secret_access_key']
        elif config.has_option(profile_name, 'aws_access_key_id'):
            aws_access_key = config[profile_name]['aws_access_key_id']
            aws_secret_key = config[profile_name]['aws_secret_access_key']
        elif profile_name == 'default':
            creds = configparser.ConfigParser()
            creds.read(f"{os.environ['HOME']}/.aws/credentials")
            aws_access_key = creds['default']['aws_access_key_id']
            aws_secret_key = creds['default']['aws_secret_access_key']    
        else:
            print (f"Problem getting credentials.")
        task_definition['containerDefinitions'][0]['environment'] += [
            {
                "name": "AWS_ACCESS_KEY_ID",
                "value": aws_access_key
            },
            {
                "name": "AWS_SECRET_ACCESS_KEY",
                "value": aws_secret_key
            }]
    sqs = boto3.client("sqs")
    queue_url = get_queue_url(sqs, SQS_QUEUE_NAME)
    task_definition["containerDefinitions"][0]["environment"] += [
        {"name": "APP_NAME", "value": APP_NAME},
        {"name": "SQS_QUEUE_URL", "value": queue_url},
        {"name": "AWS_BUCKET", "value": AWS_BUCKET},
        {"name": "DOCKER_CORES", "value": str(DOCKER_CORES)},
        {"name": "LOG_GROUP_NAME", "value": LOG_GROUP_NAME},
        {"name": "CHECK_IF_DONE_BOOL", "value": CHECK_IF_DONE_BOOL},
        {"name": "EXPECTED_NUMBER_FILES", "value": str(EXPECTED_NUMBER_FILES)},
        {"name": "ECS_CLUSTER", "value": ECS_CLUSTER},
        {"name": "SECONDS_TO_START", "value": str(SECONDS_TO_START)},
        {"name": "MIN_FILE_SIZE_BYTES", "value": str(MIN_FILE_SIZE_BYTES)},
        {"name": "USE_PLUGINS", "value": str(USE_PLUGINS)},
        {"name": "NECESSARY_STRING", "value": NECESSARY_STRING},
        {"name": "DOWNLOAD_FILES", "value": DOWNLOAD_FILES},
        {"name": "ALWAYS_CONTINUE", "value": ALWAYS_CONTINUE},
    ]
    if SOURCE_BUCKET.lower()!='false':
        task_definition['containerDefinitions'][0]['environment'] += [
            {
                'name': 'SOURCE_BUCKET',
                'value': SOURCE_BUCKET
            },
            {
                'name': 'DESTINATION_BUCKET',
                'value': DESTINATION_BUCKET
            }]
    if WORKSPACE_BUCKET.lower()!='false':
        task_definition['containerDefinitions'][0]['environment'] += [
            {
                'name': 'WORKSPACE_BUCKET',
                'value': WORKSPACE_BUCKET
            }]
    if UPLOAD_FLAGS.lower()!='false':
        task_definition['containerDefinitions'][0]['environment'] += [
            {
                'name': 'UPLOAD_FLAGS',
                'value': UPLOAD_FLAGS
            }]
    if USE_PLUGINS.lower()=='true':
        task_definition["containerDefinitions"][0]["environment"] += [
            {"name": "UPDATE_PLUGINS", "value": str(UPDATE_PLUGINS)},
            {"name": "PLUGINS_COMMIT", "value": str(PLUGINS_COMMIT)},
            {"name": "INSTALL_REQUIREMENTS", "value": str(INSTALL_REQUIREMENTS)},
            {"name": "REQUIREMENTS", "value": str(REQUIREMENTS)},
        ]
    return task_definition, taskRoleArn

def update_ecs_task_definition(ecs, ECS_TASK_NAME, AWS_PROFILE):
    task_definition, taskRoleArn = generate_task_definition(AWS_PROFILE)
    if not taskRoleArn:
        ecs.register_task_definition(family=ECS_TASK_NAME,containerDefinitions=task_definition['containerDefinitions'])
    elif taskRoleArn:
        ecs.register_task_definition(family=ECS_TASK_NAME,containerDefinitions=task_definition['containerDefinitions'],taskRoleArn=taskRoleArn)
    else:
        print('Mistake in handling role for Task Definition.')
    print('Task definition registered')

def get_or_create_cluster(ecs):
    data = ecs.list_clusters()
    cluster = [clu for clu in data['clusterArns'] if clu.endswith(ECS_CLUSTER)]
    if len(cluster) == 0:
        ecs.create_cluster(clusterName=ECS_CLUSTER)
        time.sleep(WAIT_TIME)
        print('Cluster '+ECS_CLUSTER+' created')
    else:
        print('Cluster '+ECS_CLUSTER+' exists')

def create_or_update_ecs_service(ecs, ECS_SERVICE_NAME, ECS_TASK_NAME):
    # Create the service with no workers (0 desired count)
    data = ecs.list_services(cluster=ECS_CLUSTER)
    service = [srv for srv in data['serviceArns'] if srv.endswith(ECS_SERVICE_NAME)]
    if len(service) > 0:
        print('Service exists. Removing')
        ecs.delete_service(cluster=ECS_CLUSTER, service=ECS_SERVICE_NAME)
        print('Removed service '+ECS_SERVICE_NAME)
        time.sleep(WAIT_TIME)

    print('Creating new service')
    ecs.create_service(cluster=ECS_CLUSTER, serviceName=ECS_SERVICE_NAME, taskDefinition=ECS_TASK_NAME, desiredCount=0)
    print('Service created')

def get_queue_url(sqs, queue_name):
    result = sqs.list_queues()
    queue_url = None
    if 'QueueUrls' in result.keys():
        for u in result['QueueUrls']:
            if u.split('/')[-1] == queue_name:
                queue_url = u
    return queue_url

def get_or_create_queue(sqs):
    queue_url = get_queue_url(sqs, SQS_QUEUE_NAME)
    dead_url = get_queue_url(sqs, SQS_DEAD_LETTER_QUEUE)
    if dead_url is None:
        print("Creating DeadLetter queue")
        sqs.create_queue(QueueName=SQS_DEAD_LETTER_QUEUE)
        time.sleep(WAIT_TIME)
        dead_url = get_queue_url(sqs, SQS_DEAD_LETTER_QUEUE)
    else:
        print (f'DeadLetter queue {SQS_DEAD_LETTER_QUEUE} already exists.')
    if queue_url is None:
        print('Creating queue')
        response = sqs.get_queue_attributes(QueueUrl=dead_url, AttributeNames=["QueueArn"])
        dead_arn = response["Attributes"]["QueueArn"]
        SQS_DEFINITION = {
        "DelaySeconds": "0",
        "MaximumMessageSize": "262144",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "0",
        "RedrivePolicy": f'{{"deadLetterTargetArn":"{dead_arn}","maxReceiveCount":"{str(JOB_RETRIES)}"}}',
        "VisibilityTimeout": str(SQS_MESSAGE_VISIBILITY),
    }
        sqs.create_queue(QueueName=SQS_QUEUE_NAME, Attributes=SQS_DEFINITION)
        time.sleep(WAIT_TIME)
    else:
        print('Queue exists')

def loadConfig(configFile):
    data = None
    with open(configFile, 'r') as conf:
        data = json.load(conf)
    return data

def killdeadAlarms(fleetId,monitorapp,ec2,cloud):
    todel=[]
    changes = ec2.describe_spot_fleet_request_history(SpotFleetRequestId=fleetId,StartTime=(datetime.datetime.now()-datetime.timedelta(hours=2)).replace(microsecond=0))
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

    try: #Python2
        return b64encode(pre_user_data.as_string())
    except TypeError: #Python3
        pre_user_data_string = pre_user_data.as_string()
        return b64encode(pre_user_data_string.encode('utf-8')).decode('utf-8')

def removequeue(queueName):
    sqs = boto3.client('sqs')
    queueoutput= sqs.list_queues(QueueNamePrefix=queueName)
    if len(queueoutput["QueueUrls"])==1:
        queueUrl=queueoutput["QueueUrls"][0]
    else: #In case we have "AnalysisQueue" and "AnalysisQueue1" and only want to delete the first of those
        for eachUrl in queueoutput["QueueUrls"]:
            if eachUrl.split('/')[-1] == queueName:
                queueUrl=eachUrl

    sqs.delete_queue(QueueUrl=queueUrl)

def deregistertask(taskName, ecs):
    taskArns = ecs.list_task_definitions(familyPrefix=taskName, status='ACTIVE')
    for eachtask in taskArns['taskDefinitionArns']:
        fulltaskname=eachtask.split('/')[-1]
        ecs.deregister_task_definition(taskDefinition=fulltaskname)

def removeClusterIfUnused(clusterName, ecs):
    if clusterName != 'default':
        #never delete the default cluster
        result = ecs.describe_clusters(clusters=[clusterName])
        if sum([result['clusters'][0]['pendingTasksCount'],result['clusters'][0]['runningTasksCount'],result['clusters'][0]['activeServicesCount'],result['clusters'][0]['registeredContainerInstancesCount']])==0:
            ecs.delete_cluster(cluster=clusterName)

def downscaleSpotFleet(queue, spotFleetID, ec2, manual=False):
    visible, nonvisible = queue.returnLoad()
    if manual:
        ec2.modify_spot_fleet_request(ExcessCapacityTerminationPolicy='noTermination', SpotFleetRequestId=spotFleetID, TargetCapacity = int(manual))
        return
    elif visible > 0:
        return
    else:
        status = ec2.describe_spot_fleet_instances(SpotFleetRequestId=spotFleetID)
        if nonvisible < len(status['ActiveInstances']):
            ec2.modify_spot_fleet_request(ExcessCapacityTerminationPolicy='noTermination', SpotFleetRequestId=spotFleetID, TargetCapacity = nonvisible)

def export_logs(logs, loggroupId, starttime, bucketId):
    try:
        result = logs.create_export_task(taskName = loggroupId, logGroupName = loggroupId, fromTime = int(starttime), to = int(time.time()*1000), destination = bucketId, destinationPrefix = 'exportedlogs/'+loggroupId)
    except botocore.errorfactory.InvalidParameterException:
        print("Failed to export DCP logs to S3. Check your bucket permissions.")
        return
    logExportId = result['taskId']

    while True:
        result = logs.describe_export_tasks(taskId = logExportId)
        if result['exportTasks'][0]['status']['code']!='PENDING':
            if result['exportTasks'][0]['status']['code']!='RUNNING':
                print(result['exportTasks'][0]['status']['code'])
                break
        time.sleep(30)

def create_dashboard(requestInfo):
    cloudwatch = boto3.client("cloudwatch")
    DashboardMessage = {
        "widgets": [
            {
                "height": 6,
                "width": 6,
                "y": 0,
                "x": 18,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [ "AWS/SQS", "NumberOfMessagesReceived", "QueueName", f'{APP_NAME}Queue' ],
                        [ ".", "NumberOfMessagesDeleted", ".", "." ],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": AWS_REGION,
                    "period": 300,
                    "stat": "Average"
                }
            },
            {
                "height": 6,
                "width": 6,
                "y": 0,
                "x": 6,
                "type": "metric",
                "properties": {
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        [ "AWS/ECS", "MemoryUtilization", "ClusterName", ECS_CLUSTER ]
                    ],
                    "region": AWS_REGION,
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "min": 0
                        }
                    }
                }
            },
            {
                "height": 6,
                "width": 6,
                "y": 0,
                "x": 12,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [ "AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", f'{APP_NAME}Queue' ],
                        [ ".", "ApproximateNumberOfMessagesNotVisible", ".", "."],
                        [ ".", "ApproximateNumberOfMessagesVisible", ".", f'{SQS_DEAD_LETTER_QUEUE}' ],
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": AWS_REGION,
                    "period": 300,
                    "stat": "Average"
                }
            },
            {
                "height": 6,
                "width": 12,
                "y": 6,
                "x": 12,
                "type": "log",
                "properties": {
                    "query": f"SOURCE '{APP_NAME}' | fields @message| filter @message like 'cellprofiler -c'| stats count_distinct(@message)\n",
                    "region": AWS_REGION,
                    "stacked": False,
                    "title": "Distinct Logs with \"cellprofiler -c\"",
                    "view": "table"
                }
            },
            {
                "height": 6,
                "width": 12,
                "y": 6,
                "x": 0,
                "type": "log",
                "properties": {
                    "query": f"SOURCE '{APP_NAME}' | fields @message| filter @message like 'cellprofiler -c'| stats count(@message)",
                    "region": AWS_REGION,
                    "stacked": False,
                    "title": "All Logs \"cellprofiler -c\"",
                    "view": "table"
                }
            },
            {
                "height": 6,
                "width": 24,
                "y": 12,
                "x": 0,
                "type": "log",
                "properties": {
                    "query": f"SOURCE '{APP_NAME}' | fields @message   | filter @message like \"Error\"   | display @message",
                    "region": AWS_REGION,
                    "stacked": False,
                    "title": "Errors",
                    "view": "table"
                }
            },
            {
                "height": 6,
                "width": 6,
                "y": 0,
                "x": 0,
                "type": "metric",
                "properties": {
                    "metrics": [
                        [ "AWS/EC2Spot", "FulfilledCapacity", "FleetRequestId", requestInfo["SpotFleetRequestId"]],
                        [ ".", "TargetCapacity", ".", "."],
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": AWS_REGION,
                    "period": 300,
                    "stat": "Average"
                }
            }
        ]
    }
    DashboardMessage_json = json.dumps(DashboardMessage, indent = 4) 
    response = cloudwatch.put_dashboard(DashboardName=APP_NAME, DashboardBody=DashboardMessage_json)
    if response['DashboardValidationMessages']:
        print ('Likely error in Dashboard creation')
        print (response['DashboardValidationMessages'])


def clean_dashboard(monitorapp):
    cloudwatch = boto3.client("cloudwatch")
    dashboard_list = cloudwatch.list_dashboards()
    for entry in dashboard_list["DashboardEntries"]:
        if monitorapp in entry["DashboardName"]:
            cloudwatch.delete_dashboards(DashboardNames=[entry["DashboardName"]])

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
# SERVICE 1: SETUP (formerly fab)
#################################

def setup():
    ECS_TASK_NAME = APP_NAME + 'Task'
    ECS_SERVICE_NAME = APP_NAME + 'Service'
    sqs = boto3.client('sqs')
    get_or_create_queue(sqs)
    ecs = boto3.client('ecs')
    get_or_create_cluster(ecs)
    update_ecs_task_definition(ecs, ECS_TASK_NAME, AWS_PROFILE)
    create_or_update_ecs_service(ecs, ECS_SERVICE_NAME, ECS_TASK_NAME)

#################################
# SERVICE 2: SUBMIT JOB
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
# SERVICE 3: START CLUSTER
#################################

def startCluster():
    if len(sys.argv) < 3:
        print('Use: run.py startCluster configFile')
        sys.exit()

    thistime = datetime.datetime.now().replace(microsecond=0)
    #Step 1: set up the configuration files
    s3client = boto3.client('s3')
    ecsConfigFile=generateECSconfig(ECS_CLUSTER,APP_NAME,AWS_BUCKET,s3client)
    spotfleetConfig=loadConfig(sys.argv[2])
    spotfleetConfig['ValidFrom']=thistime
    spotfleetConfig['ValidUntil']=(thistime+datetime.timedelta(days=365)).replace(microsecond=0)
    spotfleetConfig['TargetCapacity']= CLUSTER_MACHINES
    spotfleetConfig['SpotPrice'] = '%.2f' %MACHINE_PRICE
    DOCKER_BASE_SIZE = int(round(float(EBS_VOL_SIZE)/int(TASKS_PER_MACHINE))) - 2
    userData=generateUserData(ecsConfigFile,DOCKER_BASE_SIZE)
    for LaunchSpecification in range(0,len(spotfleetConfig['LaunchSpecifications'])):
        spotfleetConfig['LaunchSpecifications'][LaunchSpecification]["UserData"]=userData
        spotfleetConfig['LaunchSpecifications'][LaunchSpecification]['BlockDeviceMappings'][1]['Ebs']["VolumeSize"]= EBS_VOL_SIZE
        spotfleetConfig['LaunchSpecifications'][LaunchSpecification]['InstanceType'] = MACHINE_TYPE[LaunchSpecification]
    if ASSIGN_IP.lower() == 'false':
        print("Setting 'AssociatePublicIPAddress' to False, overwriting setting in Fleet file")
        try:
            spotfleetConfig['LaunchSpecifications'][0]['NetworkInterfaces'][0]['AssociatePublicIpAddress'] = False
        except:
            print("Couldn't add or overwrite 'AssociatePublicIpAddress' to False in spot fleet config.")

    # Step 2: make the spot fleet request
    ec2client=boto3.client('ec2')
    requestInfo = ec2client.request_spot_fleet(SpotFleetRequestConfig=spotfleetConfig)
    print('Request in process. Wait until your machines are available in the cluster.')
    print('SpotFleetRequestId',requestInfo['SpotFleetRequestId'])

    # Step 3: Make the monitor
    starttime=str(int(time.time()*1000))
    monitor_file_name=f'files/{APP_NAME}SpotFleetRequestId.json'
    createMonitor=open(monitor_file_name,'w')
    createMonitor.write('{"MONITOR_FLEET_ID" : "'+requestInfo['SpotFleetRequestId']+'",\n')
    createMonitor.write('"MONITOR_APP_NAME" : "'+APP_NAME+'",\n')
    createMonitor.write('"MONITOR_ECS_CLUSTER" : "'+ECS_CLUSTER+'",\n')
    createMonitor.write('"MONITOR_QUEUE_NAME" : "'+SQS_QUEUE_NAME+'",\n')
    createMonitor.write('"MONITOR_BUCKET_NAME" : "'+AWS_BUCKET+'",\n')
    createMonitor.write('"MONITOR_LOG_GROUP_NAME" : "'+LOG_GROUP_NAME+'",\n')
    createMonitor.write('"MONITOR_START_TIME" : "'+ starttime+'",\n')
    createMonitor.write('"CLEAN_DASHBOARD" : "'+ CLEAN_DASHBOARD+'"}\n')
    createMonitor.close()

    # Upload monitor file to S3 so it can be read by Auto-Monitor lambda function
    if AUTO_MONITOR.lower()=='true':
        s3 = boto3.client("s3")
        json_on_bucket_name = f'monitors/{APP_NAME}SpotFleetRequestId.json' # match path set in lambda function
        with open(monitor_file_name, "rb") as a:
            s3.put_object(Body=a, Bucket=AWS_BUCKET, Key=json_on_bucket_name)

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
    #time.sleep(15) # This is now too fast, so sometimes the spot fleet request history throws an error!
    while len(status['ActiveInstances']) < CLUSTER_MACHINES:
        # First check to make sure there's not a problem
        errorcheck = ec2client.describe_spot_fleet_request_history(SpotFleetRequestId=requestInfo['SpotFleetRequestId'], EventType='error', StartTime=thistime - datetime.timedelta(minutes=1))
        if len(errorcheck['HistoryRecords']) != 0:
            print('Your spot fleet request is causing an error and is now being cancelled.  Please check your configuration and try again')
            for eacherror in errorcheck['HistoryRecords']:
                print(eacherror['EventInformation']['EventSubType'] + ' : ' + eacherror['EventInformation']['EventDescription'])
            #If there's only one error, and it's the type we see for insufficient capacity (but also other types)
            #AND if there are some machines on, indicating that other than capacity the spec is otherwise good, don't cancel
            if len(errorcheck['HistoryRecords']) == 1:
                if errorcheck['HistoryRecords'][0]['EventInformation']['EventSubType'] == 'allLaunchSpecsTemporarilyBlacklisted':
                    if len(status['ActiveInstances']) >= 1:
                        print("I think, but am not sure, that this is an insufficient capacity error. You should check the console for more information.")
                        return
            ec2client.cancel_spot_fleet_requests(SpotFleetRequestIds=[requestInfo['SpotFleetRequestId']], TerminateInstances=True)
            return

        # If everything seems good, just bide your time until you're ready to go
        print('.')
        time.sleep(20)
        status = ec2client.describe_spot_fleet_instances(
            SpotFleetRequestId=requestInfo["SpotFleetRequestId"]
        )
    print("Spot fleet successfully created. Your job should start in a few minutes.")
    print(f"Your monitor file is available at {monitor_file_name}")
    
    if CREATE_DASHBOARD.lower()=='true':
        print ("Creating CloudWatch dashboard for run metrics")
        create_dashboard(requestInfo)

    if AUTO_MONITOR.lower()=='true':
        # Create alarms that will trigger Monitor based on SQS queue metrics
        cloudwatch = boto3.client("cloudwatch")
        metricnames = [
            "ApproximateNumberOfMessagesNotVisible",
            "ApproximateNumberOfMessagesVisible",
        ]
        sns = boto3.client("sns")
        MonitorARN = sns.create_topic(Name="Monitor")['TopicArn'] # returns ARN since topic already exists
        for metric in metricnames:
            response = cloudwatch.put_metric_alarm(
                AlarmName=f'{metric}isZero_{APP_NAME}',
                ActionsEnabled=True,
                OKActions=[],
                AlarmActions=[MonitorARN],
                InsufficientDataActions=[],
                MetricName=metric,
                Namespace="AWS/SQS",
                Statistic="Average",
                Dimensions=[
                    {"Name": "QueueName", "Value": f'{APP_NAME}Queue'}
                ],
                Period=300,
                EvaluationPeriods=1,
                DatapointsToAlarm=1,
                Threshold=0,
                ComparisonOperator="LessThanOrEqualToThreshold",
                TreatMissingData="missing",
            )

#################################
# SERVICE 4: MONITOR JOB
#################################

def monitor(cheapest=False):
    if len(sys.argv) < 3:
        print('Use: run.py monitor spotFleetIdFile')
        sys.exit()

    if '.json' not in sys.argv[2]:
        print('Use: run.py monitor spotFleetIdFile')
        sys.exit()

    if len(sys.argv) == 4:
        cheapest = sys.argv[3]

    monitorInfo = loadConfig(sys.argv[2])
    monitorcluster=monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp=monitorInfo["MONITOR_APP_NAME"]
    fleetId=monitorInfo["MONITOR_FLEET_ID"]
    queueId=monitorInfo["MONITOR_QUEUE_NAME"]

    ec2 = boto3.client('ec2')
    cloud = boto3.client('cloudwatch')

    # Optional Step 0 - decide if you're going to be cheap rather than fast. This means that you'll get 15 minutes
    # from the start of the monitor to get as many machines as you get, and then it will set the requested number to 1.
    # Benefit: this will always be the cheapest possible way to run, because if machines die they'll die fast,
    # Potential downside- if machines are at low availability when you start to run, you'll only ever get a small number
    # of machines (as opposed to getting more later when they become available), so it might take VERY long to run if that happens.
    if cheapest:
        queue = JobQueue(name=queueId)
        startcountdown = time.time()
        while queue.pendingLoad():
            if time.time() - startcountdown > 900:
                downscaleSpotFleet(queue, fleetId, ec2, manual=1)
                # Print spot fleet metrics.
                spot_fleet_info = ec2.describe_spot_fleet_requests(SpotFleetRequestIds=[fleetId])
                target = spot_fleet_info['SpotFleetRequestConfigs'][0]['SpotFleetRequestConfig']['TargetCapacity']
                fulfilled = spot_fleet_info['SpotFleetRequestConfigs'][0]['SpotFleetRequestConfig']['FulfilledCapacity']
                print(f'Spot fleet has {target} requested instances. {fulfilled} are currently fulfilled.')
                break
            time.sleep(MONITOR_TIME)

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
        pass

    # Step 4: Read spot fleet id and terminate all EC2 instances
    print('Shutting down spot fleet',fleetId)
    ec2.cancel_spot_fleet_requests(SpotFleetRequestIds=[fleetId], TerminateInstances=True)
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
    # Remove Cloudwatch dashboard if created and cleanup desired
    if CREATE_DASHBOARD.lower()=='true' and CLEAN_DASHBOARD.lower()=='true':
        clean_dashboard(monitorapp)

    #Step 6: Export the logs to S3
    logs=boto3.client('logs')

    print('Transfer of CellProfiler logs to S3 initiated')
    export_logs(logs, loggroupId, starttime, bucketId)

    print('Transfer of per-instance to S3 initiated')
    export_logs(logs, loggroupId+'_perInstance', starttime, bucketId)

    print('All export tasks done')

#################################
# MAIN USER INTERACTION
#################################

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Use: run.py setup | submitJob | startCluster | monitor')
        sys.exit()

    if sys.argv[1] == 'setup':
        setup()
    elif sys.argv[1] == 'submitJob':
        submitJob()
    elif sys.argv[1] == 'startCluster':
        startCluster()
    elif sys.argv[1] == 'monitor':
        monitor()
        
