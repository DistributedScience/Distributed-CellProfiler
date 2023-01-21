# What does Distributed-CellProfiler cost?

Distributed-CellProfiler is run by a series of three commands, only one of which incurs costs:

[`setup`](step_1_configuration.md) creates a queue in SQS and a cluster, service, and task definition in ECS. 
ECS is entirely free. 
SQS queues are free to create and use up to 1 million requests/month.

[`submitJobs`](step_2_submit_jobs.md) places messages in the SQS queue which is free (under 1 million requests/month).

[`startCluster`](step_1_start_cluster.md) is the only command that incurs costs. 
It initiates your spot fleet request, the major cost of running Distributed-CellProfiler, exact pricing of which depends on the number of machines, type of machines, and duration of use. 
Your bid is configured in the [config file](step_1_configuration.md).

Spot fleet costs can be minimized/stopped in multiple ways:
1) We encourage the use of [`monitor`](step_4_monitor.md) during your job to help minimize the spot fleet cost as it automatically scales down your spot fleet request as your job queue empties and cancels your spot fleet request when you have no more jobs in the queue.
2) If your job is finished, you can still initiate [`monitor`](step_4_monitor.md) to perform the same cleanup (without the automatic scaling).
3) If you want to abort and clean up a run, you can purge your SQS queue in the [AWS SQS console](https://console.aws.amazon.com/sqs/) (by selecting your queue and pressing Actions => Purge) and then initiate [`monitor`](step_4_monitor.md) to perform the same cleanup.
4) You can stop the spot fleet request directly in the [AWS EC2 console](https://console.aws.amazon.com/ec2/) by going to Instances => Spot Requests, selecting your spot request, and pressing Actions => Cancel Spot Request.

After the spot fleet has started, a Cloudwatch instance alarm is automatically placed on each instance in the fleet.
Cloudwatch instance alarms are currently $0.10/alarm/month.
Cloudwatch instance alarm costs can be minimized/stopped in multiple ways:
1) If you run monitor during your job, it will automatically delete Cloudwatch alarms for any instance that is no longer in use once an hour while running and at the end of a run.
2) If your job is finished, you can still initiate [`monitor`](step_4_monitor.md) to delete Cloudwatch alarms for any instance that is no longer in use.
3) In [AWS Cloudwatch console](https://console.aws.amazon.com/cloudwatch/) you can select unused alarms by going to Alarms => All alarms. Change Any State to Insufficient Data, select all alarms, and then Actions => Delete.
4) We provide a [hygiene script](hygiene.md) that will clean up old alarms for you.
