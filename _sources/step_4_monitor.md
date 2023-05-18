# Step 4: Monitor

Your workflow is now submitted.
Distributed-CellProfiler will keep an eye on a few things for you at this point without you having to do anything else.
* Each instance is labeled with your APP_NAME, so that you can easily find your instances if you want to look at the instance metrics on the Running Instances section of the [EC2 web interface](https://console.aws.amazon.com/ec2/v2/home) to monitor performance.
* You can also look at the whole-cluster CPU and memory usage statistics related to your APP_NAME in the [ECS web interface](https://console.aws.amazon.com/ecs/home).
* Each instance will have an alarm placed on it so that if CPU usage dips below 1% for 15 consecutive minutes (almost always the result of a crashed machine), the instance will be automatically terminated and a new one will take its place.
* Each individual job processed will create a log of the CellProfiler output, and each Docker container will create a log showing CPU, memory, and disk usage.

If you choose to run the Monitor script, Distributed-CellProfiler can be even more helpful.

## Running Monitor 

### Manually running Monitor
Monitor can be run by entering `python run.py monitor files/APP_NAMESpotFleetRequestId.json`.
While the optimal time to initiate Monitor is as soon as you have triggered a run as it downscales infrastructure as necessary, you can run Monitor at any point in time and it will clean up whatever infrastructure remains.

**Note:** You should run the monitor inside [Screen](https://www.gnu.org/software/screen/), [tmux](https://tmux.github.io/), or another comparable service to keep a network disconnection from killing your monitor; this is particularly critical the longer your run takes.

### Using Auto-Monitor
Instead of manually triggering Monitor, you can have a version of Monitor automatically initiate after you [start your cluster](step_3_start_cluster.md) by setting `AUTO_MONITOR = 'True'` in your [config file](step_1_configuration.md). 
Auto-Monitor is an AWS Lambda function that is triggered by alarms placed on the SQS queue. 
Read more about the [SQS Queue](SQS_QUEUE_information.md) to better understand the alarm metrics.

## Monitor functions

### While your analysis is running
* Scales down the spot fleet request to match the number of remaining jobs WITHOUT force terminating them.
This happens every 10 minutes with manual Monitor or when the are no Visible Messages in your queue for Auto-Monitor.
* Deletes the alarms for any instances that have been terminated in the last 24 hours (because of spot prices rising above your maximum bid, machine crashes, etc).
This happens every hour with manual Monitor or when the are no Visible Messages in your queue for Auto-Monitor.

### When your queue is totally empty (there are no Visible or Not Visible messages)
* Downscales the ECS service associated with your APP_NAME.
* Deletes all the alarms associated with your spot fleet (both the currently running and the previously terminated instances).
* Shuts down your spot fleet to keep you from incurring charges after your analysis is over.
* Gets rid of the queue, service, and task definition created for this analysis.
* Exports all the logs from your analysis onto your S3 bucket.
* Deletes your Cloudwatch Dashboard if you created it and set `CLEAN_DASHBOARD = 'True'` in your [config file](step_1_configuration.md).

## Cheapest mode

If you are manually triggering Monitor, you can run the monitor in an optional "cheapest" mode, which will downscale the number of requested machines (but not RUNNING machines) to one machine 15 minutes after the monitor is engaged.
You can engage cheapest mode by adding `True` as a final configurable parameter when starting the monitor, aka `python run.py monitor files/APP_NAMESpotFleetRequestId.json True`

Cheapest mode is cheapest because it will remove all but 1 machine as soon as that machine crashes and/or runs out of jobs to do; this can save you money, particularly in multi-CPU Dockers running long jobs. 
This mode is optional because running this way involves some inherent risks. 
If machines stall out due to processing errors, they will not be replaced, meaning your job will take overall longer.
Additionally, if there is limited capacity for your requested configuration when you first start (e.g. you want 200 machines but AWS says it can currently only allocate you 50), more machines will not be added if and when they become available in cheapest mode as they would in normal mode.

***

## Monitor file

The JSON monitor file containing all the information Distributed-CellProfiler needs will have been automatically created when you sent the instructions to start your cluster in the [previous step](step_3_start_cluster).
The file itself is quite simple and contains the following information:

```
{"MONITOR_FLEET_ID" : "sfr-9999ef99-99fc-9d9d-9999-9999999e99ab",
"MONITOR_APP_NAME" : "2021_12_13_Project_Analysis",
"MONITOR_ECS_CLUSTER" : "default",
"MONITOR_QUEUE_NAME" : "2021_12_13_Project_AnalysisQueue",
"MONITOR_BUCKET_NAME" : "bucket-name",
"MONITOR_LOG_GROUP_NAME" : "2021_12_13_Project_Analysis",
"MONITOR_START_TIME" : "1649187798951"}
```

For any Distributed-CellProfiler run where you have run [`startCluster`](step_3_start_cluster) more than once, the most recent values will overwrite the older values in the monitor file.
Therefore, if you have started multiple spot fleets (which you might do in different subnets if you are having trouble getting enough capacity in your spot fleet, for example), Monitor will only clean up the latest request unless you manually edit the `MONITOR_FLEET_ID` to match the spot fleet you have kept.