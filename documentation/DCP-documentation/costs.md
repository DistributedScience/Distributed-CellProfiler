# What does Distributed-CellProfiler cost?

Distributed-CellProfiler is run by a series of three commands, only one of which incurs costs at typical scale of usage:

[`setup`](step_1_configuration.md) creates a queue in SQS and a cluster, service, and task definition in ECS.
ECS is entirely free.
SQS queues are free to create and use up to 1 million requests/month.

[`submitJobs`](step_2_submit_jobs.md) places messages in the SQS queue which is free (under 1 million requests/month).

[`startCluster`](step_3_start_cluster.md) is the only command that incurs costs with initiation of your spot fleet request, creating machine alarms, and optionally creating a run dashboard.

The spot fleet is the major cost of running Distributed-CellProfiler, exact pricing of which depends on the number of machines, type of machines, and duration of use.
Your bid is configured in the [config file](step_1_configuration.md).
Simple spot fleet configurations can be minimized by:

1) Optimize `MACHINE_TYPE` and `EBS_VOL_SIZE` based on the actual memory and harddrive needs of your run.
2) When possible, mount your S3 bucket using S3FS so that you can set `DOWNLOAD_FILES = 'False'` to not incur file egress costs.
See [Step 1 Configuration](step_1_configuration.md) for more information.
Data egress charges range for various reasons including traversing AWS regions and/or AWS availability zones but are [often $0.08–$0.12 per GB](https://aws.amazon.com/blogs/apn/aws-data-transfer-charges-for-server-and-serverless-architectures/).
3) Set `ASSIGN_IP = 'False'` so that you don't pay for IPv4 addresses per EC2 instance in your spot fleet.
Public IPv4 costs are minimal ([$0.005/IP/hour as of February 1, 2024](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/)) but there is no need to incur even this minimal cost unless you have a specific need for it.
See [Step 1 Configuration](step_1_configuration.md) for more information.

Spot fleet costs can be minimized/stopped in multiple ways:

1) We encourage the use of [`monitor`](step_4_monitor.md) during your job to help minimize the spot fleet cost as it automatically scales down your spot fleet request as your job queue empties and cancels your spot fleet request when you have no more jobs in the queue.
Note that you can also perform a more aggressive downscaling of your fleet by monitor by engaging Cheapest mode (see [`more information here`](step_4_monitor.md)).
2) If your job is finished, you can still initiate [`monitor`](step_4_monitor.md) to perform the same cleanup (without the automatic scaling).
3) If you want to abort and clean up a run, you can purge your SQS queue in the [AWS SQS console](https://console.aws.amazon.com/sqs/) (by selecting your queue and pressing Actions => Purge) and then initiate [`monitor`](step_4_monitor.md) to perform the same cleanup.
4) You can stop the spot fleet request directly in the [AWS EC2 console](https://console.aws.amazon.com/ec2/) by going to Instances => Spot Requests, selecting your spot request, and pressing Actions => Cancel Spot Request.

After the spot fleet has started, a Cloudwatch instance alarm is automatically placed on each instance in the fleet.
Cloudwatch instance alarms [are currently $0.10/alarm/month](https://aws.amazon.com/cloudwatch/pricing/).
Cloudwatch instance alarm costs can be minimized/stopped in multiple ways:

1) If you run monitor during your job, it will automatically delete Cloudwatch alarms for any instance that is no longer in use once an hour while running and at the end of a run.
2) If your job is finished, you can still initiate [`monitor`](step_4_monitor.md) to delete Cloudwatch alarms for any instance that is no longer in use.
3) In [AWS Cloudwatch console](https://console.aws.amazon.com/cloudwatch/) you can select unused alarms by going to Alarms => All alarms. Change Any State to Insufficient Data, select all alarms, and then Actions => Delete.
4) We provide a [hygiene script](hygiene.md) that will clean up old alarms for you.

Cloudwatch Dashboards [are currently free](https://aws.amazon.com/cloudwatch/pricing/) for 3 Dashboards with up to 50 metrics per month and are $3 per dashboard per month after that.
Cloudwatch Dashboard costs can be minimized/prevented in multiple ways:

1) You can choose not to have Distributed-CellProfiler create a Dashboard by setting `CREATE_DASHBOARD = 'False'` in your [config file](step_1_configuration.md).
2) We encourage the use of [`monitor`](step_4_monitor.md) during your job as if you have set `CLEAN_DASHBOARD = 'True'` in your [config file](step_1_configuration.md) it will automatically delete your Dashboard when your job is done.
3) If your job is finished, you can still initiate [`monitor`](step_4_monitor.md) to perform the same cleanup (without the automatic scaling).
4) You can manually delete Dashboards in the [Cloudwatch Console]((https://console.aws.amazon.com/cloudwatch/)) by going to Dashboards, selecting your Dashboard, and selecting Delete.
