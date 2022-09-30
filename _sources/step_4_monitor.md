# Step 4: Monitor

Your workflow is now submitted.
Distributed-CellProfiler will keep an eye on a few things for you at this point without you having to do anything else.

* Each instance is labeled with your APP_NAME, so that you can easily find your instances if you want to look at the instance metrics on the Running Instances section of the [EC2 web interface](https://console.aws.amazon.com/ec2/v2/home) to monitor performance.

* You can also look at the whole-cluster CPU and memory usage statistics related to your APP_NAME in the [ECS web interface](https://console.aws.amazon.com/ecs/home).

* Each instance will have an alarm placed on it so that if CPU usage dips below 1% for 15 consecutive minutes (almost always the result of a crashed machine), the instance will be automatically terminated and a new one will take its place.

* Each individual job processed will create a log of the CellProfiler output, and each Docker container will create a log showing CPU, memory, and disk usage.

If you choose to run the monitor script, Distributed-CellProfiler can be even more helpful.
The monitor can be run by entering `python run.py monitor files/APP_NAMESpotFleetRequestId.json`; the JSON file containing all the information Distributed-CellProfiler needs will have been automatically created when you sent the instructions to start your cluster in the previous step.

(**Note:** You should run the monitor inside [Screen](https://www.gnu.org/software/screen/), [tmux](https://tmux.github.io/), or another comparable service to keep a network disconnection from killing your monitor; this is particularly critical the longer your run takes.)

***

## Monitor functions

### While your analysis is running

* Checks your queue once per minute to see how many jobs are currently processing and how many remain to be processed.

* Once per hour, it deletes the alarms for any instances that have been terminated in the last 24 hours (because of spot prices rising above your maximum bid, machine crashes, etc).

### When the number of jobs in your queue goes to 0

* Downscales the ECS service associated with your APP_NAME.

* Deletes all the alarms associated with your spot fleet (both the currently running and the previously terminated instances).

* Shuts down your spot fleet to keep you from incurring charges after your analysis is over.

* Gets rid of the queue, service, and task definition created for this analysis.

* Exports all the logs from your analysis onto your S3 bucket.

***

## Cheapest mode

You can run the monitor in an optional "cheapest" mode, which will downscale the number of requested machines (but not RUNNING machines) to one 15 minutes after the monitor is engaged.
You can engage cheapest mode by adding `True` as a final configurable parameter when starting the monitor, aka `python run.py monitor files/APP_NAMESpotFleetRequestId.json True`

Cheapest mode is cheapest because it will remove all but 1 machine as soon as that machine crashes and/or runs out of jobs to do; this can save you money, particularly in multi-CPU Dockers running long jobs.

This mode is optional because running this way involves some inherent risks.
If machines stall out due to processing errors, they will not be replaced, meaning your job will take overall longer.
Additionally, if there is limited capacity for your requested configuration when you first start (e.g. you want 200 machines but AWS says it can currently only allocate you 50), more machines will not be added if and when they become available in cheapest mode as they would in normal mode.
