import boto3
import datetime
import botocore
import json

s3 = boto3.client("s3")
ecs = boto3.client("ecs")
ec2 = boto3.client("ec2")
cloudwatch = boto3.client("cloudwatch")
sqs = boto3.client("sqs")

bucket = "BUCKET_NAME"


def killdeadAlarms(fleetId, project):
    checkdates = [
        datetime.datetime.now().strftime("%Y-%m-%d"),
        (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    ]
    todel = []
    for eachdate in checkdates:
        datedead = ec2.describe_spot_fleet_request_history(
            SpotFleetRequestId=fleetId, StartTime=eachdate
        )
        for eachevent in datedead["HistoryRecords"]:
            if eachevent["EventType"] == "instanceChange":
                if eachevent["EventInformation"]["EventSubType"] == "terminated":
                    todel.append(eachevent["EventInformation"]["InstanceId"])
    todel = [f"{project}_{x}" for x in todel]
    while len(todel) > 100:
        dellist = todel[:100]
        cloudwatch.delete_alarms(AlarmNames=dellist)
        todel = todel[100:]
    if len(todel) <= 100:
        cloudwatch.delete_alarms(AlarmNames=todel)
    print("Old alarms deleted")


def seeIfLogExportIsDone(logExportId):
    while True:
        result = cloudwatch.describe_export_tasks(taskId=logExportId)
        if result["exportTasks"][0]["status"]["code"] != "PENDING":
            if result["exportTasks"][0]["status"]["code"] != "RUNNING":
                print(result["exportTasks"][0]["status"]["code"])
                break
                time.sleep(30)


def downscaleSpotFleet(nonvisible, spotFleetID):
    status = ec2.describe_spot_fleet_instances(SpotFleetRequestId=spotFleetID)
    if nonvisible < len(status["ActiveInstances"]):
        ec2.modify_spot_fleet_request(
            ExcessCapacityTerminationPolicy="noTermination",
            TargetCapacity=str(nonvisible),
            SpotFleetRequestId=spotFleetID,
        )


def check_sqs_queue(queueName):
    response = sqs.get_queue_url(QueueName=queueName)
    queueUrl = response["QueueUrl"]
    response = sqs.get_queue_attributes(
        QueueUrl=queueUrl,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "ApproximateNumberOfMessagesNotVisible",
        ],
    )
    visible = int(response["Attributes"]["ApproximateNumberOfMessages"])
    nonvisible = int(response["Attributes"]["ApproximateNumberOfMessagesNotVisible"])
    print(
        f"Found {visible} visible messages and {nonvisible} nonvisible messages in queue."
    )
    return visible, nonvisible


def lambda_handler(event, lambda_context):
    # Triggered any time SQS queue ApproximateNumberOfMessagesVisible = 0
    # OR ApproximateNumberOfMessagesNotVisible = 0
    messagestring = event["Records"][0]["Sns"]["Message"]
    messagedict = json.loads(messagestring)
    queueName = messagedict["Trigger"]["Dimensions"][0]["value"]
    project = queueName.rsplit("_", 1)[0]

    # Download monitor file
    monitor_file_name = f"{queueName.split('Queue')[0]}SpotFleetRequestId.json"
    monitor_local_name = f"/tmp/{monitor_file_name}"
    monitor_on_bucket_name = f"monitors/{monitor_file_name}"

    with open(monitor_local_name, "wb") as f:
        try:
            s3.download_fileobj(bucket, monitor_on_bucket_name, f)
        except botocore.exceptions.ClientError as error:
            print("Error retrieving monitor file.")
            return
    with open(monitor_local_name, "r") as input:
        monitorInfo = json.load(input)

    monitorcluster = monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp = monitorInfo["MONITOR_APP_NAME"]
    fleetId = monitorInfo["MONITOR_FLEET_ID"]
    loggroupId = monitorInfo["MONITOR_LOG_GROUP_NAME"]
    CLEAN_DASHBOARD = monitorInfo["CLEAN_DASHBOARD"]
    print(f"Monitor triggered for {monitorcluster} {monitorapp} {fleetId} {loggroupId}")

    visible, nonvisible = check_sqs_queue(queueName)

    # If no visible messages, downscale machines
    if visible == 0 and nonvisible > 0:
        print("No visible messages. Tidying as we go.")
        killdeadAlarms(fleetId, project)
        downscaleSpotFleet(nonvisible, fleetId)

    # If no messages in progress, cleanup
    if visible == 0 and nonvisible == 0:
        print("No messages in progress. Cleaning up.")
        ecs.update_service(
            cluster=monitorcluster,
            service=f"{monitorapp}Service",
            desiredCount=0,
        )
        print("Service has been downscaled")

        # Delete the alarms from active machines and machines that have died.
        active_dictionary = ec2.describe_spot_fleet_instances(
            SpotFleetRequestId=fleetId
        )
        active_instances = []
        for instance in active_dictionary["ActiveInstances"]:
            active_instances.append(instance["InstanceId"])
        while len(active_instances) > 100:
            dellist = active_instances[:100]
            cloudwatch.delete_alarms(AlarmNames=dellist)
            active_instances = active_instances[100:]
        if len(active_instances) <= 100:
            cloudwatch.delete_alarms(AlarmNames=active_instances)
        killdeadAlarms(fleetId, monitorapp, project)

        # Read spot fleet id and terminate all EC2 instances
        ec2.cancel_spot_fleet_requests(
            SpotFleetRequestIds=[fleetId], TerminateInstances=True
        )
        print("Fleet shut down.")

        # Remove SQS queue, ECS Task Definition, ECS Service
        ECS_TASK_NAME = monitorapp + "Task"
        ECS_SERVICE_NAME = monitorapp + "Service"

        print("Deleting existing queue.")
        queueoutput = sqs.list_queues(QueueNamePrefix=queueName)
        try:
            if len(queueoutput["QueueUrls"]) == 1:
                queueUrl = queueoutput["QueueUrls"][0]
            else:  # In case we have "AnalysisQueue" and "AnalysisQueue1" and only want to delete the first of those
                for eachUrl in queueoutput["QueueUrls"]:
                    if eachUrl.split("/")[-1] == queueName:
                        queueUrl = eachUrl
            sqs.delete_queue(QueueUrl=queueUrl)
        except KeyError:
            print("Can't find queue to delete.")

        print("Deleting service")
        try:
            ecs.delete_service(cluster=monitorcluster, service=ECS_SERVICE_NAME)
        except:
            print("Couldn't delete service.")

        print("De-registering task")
        taskArns = ecs.list_task_definitions(familyPrefix=ECS_TASK_NAME)
        for eachtask in taskArns["taskDefinitionArns"]:
            fulltaskname = eachtask.split("/")[-1]
            ecs.deregister_task_definition(taskDefinition=fulltaskname)

        print("Removing cluster if it's not the default and not otherwise in use")
        if monitorcluster != "default":
            result = ecs.describe_clusters(clusters=[monitorcluster])
        if (
            sum(
                [
                    result["clusters"][0]["pendingTasksCount"],
                    result["clusters"][0]["runningTasksCount"],
                    result["clusters"][0]["activeServicesCount"],
                ]
            )
            == 0
        ):
            ecs.delete_cluster(cluster=monitorcluster)

        # Remove alarms that triggered monitor
        print("Removing alarms that triggered Monitor")
        cloudwatch.delete_alarms(
            AlarmNames=[
                f"ApproximateNumberOfMessagesVisibleisZero_{monitorapp}",
                f"ApproximateNumberOfMessagesNotVisibleisZero_{monitorapp}",
            ]
        )

        # Remove Cloudwatch dashboard if created and cleanup desired
        if CLEAN_DASHBOARD.lower() == "true":
            dashboard_list = cloudwatch.list_dashboards()
            for entry in dashboard_list["DashboardEntries"]:
                if monitorapp in entry["DashboardName"]:
                    cloudwatch.delete_dashboards(
                        DashboardNames=[entry["DashboardName"]]
                    )

        # Delete monitor file
        s3.delete_object(Bucket=bucket, Key=monitor_on_bucket_name)
