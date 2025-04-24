# What happens in AWS when I run Distributed-CellProfiler?

The steps for actually running the Distributed-CellProfiler code are outlined in the repository [README](https://github.com/DistributedScience/Distributed-CellProfiler/blob/master/README.md), and details of the parameters you set in each step are on their respective Documentation pages ([Step 1: Config](step_1_configuration.md), [Step 2: Jobs](step_2_submit_jobs.md), [Step 3: Fleet](step_3_start_cluster.md), and optional [Step 4: Monitor](step_4_monitor.md)).
We'll give an overview of what happens in AWS at each step here and explain what AWS does automatically once you have it set up.

![Distributed-CellProfiler Chronological Overview](images/DCP_chronological_schematic.png)

**Step 1**:
In the Config file you set quite a number of specifics that are used by EC2, ECS, SQS, and in making Dockers.
When you run `$ python3 run.py setup` to execute the Config, it does three major things:

* Creates task definitions.
These are found in ECS.
They define the configuration of the Dockers and include the settings you gave for **CHECK_IF_DONE_BOOL**, **DOCKER_CORES**, **EXPECTED_NUMBER_FILES**, and **MEMORY**.
* Makes a queue in SQS (it is empty at this point) and sets a dead-letter queue.
* Makes a service in ECS which defines how many Dockers you want.

**Step 2**:
In the Job file you set the location of any inputs (e.g. data and batch-specific scripts) and outputs.
Additionally, you list all of the individual tasks that you want run.
When you submit the Job file it adds that list of tasks to the queue in SQS (which you made in the previous step).
Submit jobs with `$ python3 run.py submitJob`.

**Step 3**:
In the Config file you set the number and size of the EC2 instances you want.
This information, along with account-specific configuration in the Fleet file is used to start the fleet with `$ python3 run.py startCluster`.

**After these steps are complete, a number of things happen automatically**:

* ECS puts Docker containers onto EC2 instances.
If there is a mismatch within your Config file and the Docker is larger than the instance it will not be placed.
ECS will keep placing Dockers onto an instance until it is full, so if you accidentally create instances that are too large you may end up with more Dockers placed on it than intended.
This is also why you may want multiple **ECS_CLUSTER**s so that ECS doesn't blindly place Dockers you intended for one job onto an instance you intended for another job.
* When a Docker container gets placed it gives the instance it's on its own name.
* Once an instance has a name, the Docker gives it an alarm that tells it to reboot if it is sitting idle for 15 minutes.
* The Docker hooks the instance up to the _perinstance logs in CloudWatch.
* The instances look in SQS for a job.
Any time they don't have a job they go back to SQS.
If SQS tells them there are no visible jobs then they shut themselves down.
* When an instance finishes a job it sends a message to SQS and removes that job from the queue.

## What does an instance configuration look like?

![Example Instance Configuration](images/sample_DCP_config_1.png)

This is an example of one possible instance configuration.
This is one m4.16xlarge EC2 instance (64 CPUs, 250GB of RAM) with a 165 EBS volume mounted on it.
A spot fleet could contain many such instances.

It has 16 tasks (individual Docker containers).

Each Docker container uses 10GB of hard disk space and is assigned 4 CPUs and 15 GB of RAM (which it does not share with other Docker containers).

Each container shares its individual resources among 4 copies of CellProfiler.
Each copy of CellProfiler runs a pipeline on one "job", which can be anything from a single image to an entire 384 well plate or timelapse movie.

You can optionally stagger the start time of these 4 copies of CellProfiler, ensuring that the most memory- or disk-intensive steps aren't happening simultaneously, decreasing the likelihood of a crash.

Read more about this and other configurations in [Step 1: Configuration](step_1_configuration.md).

## How do I determine my configuration?

To some degree, you determine the best configuration for your needs through trial and error.  

* Looking at the resources your software uses on your local computer when it runs your jobs can give you a sense of roughly how much hard drive and memory space each job requires, which can help you determine your group size and what machines to use.  
* Prices of different machine sizes fluctuate, so the choice of which type of machines to use in your spot fleet is best determined at the time you run it.
How long a job takes to run and how quickly you need the data may also affect how much you're willing to bid for any given machine.
* Running a few large Docker containers (as opposed to many small ones) increases the amount of memory all the copies of your software are sharing, decreasing the likelihood you'll run out of memory if you stagger your job start times.
However, you're also at a greater risk of running out of hard disk space.  

Keep an eye on all of the logs the first few times you run any workflow and you'll get a sense of whether your resources are being utilized well or if you need to do more tweaking.

## What does this look like on AWS?

 The following five are the primary resources that Distributed-CellProfiler interacts with.
 After you have finished [preparing for Distributed-CellProfiler](step_0_prep), you do not need to directly interact with any of these services outside of Distributed-CellProfiler.
 If you would like a granular view of what Distributed-CellProfiler is doing while it runs, you can open each console in a separate tab in your browser and watch their individual behaviors, though this is not necessary, especially if you run the [monitor command](step_4_monitor.md) and/or have DS automatically create a Dashboard for you (see [Configuration](step_1_configuration.md)).

* [S3 Console](https://console.aws.amazon.com/s3)
* [EC2 Console](https://console.aws.amazon.com/ec2/)
* [ECS Console](https://console.aws.amazon.com/ecs/)
* [SQS Console](https://console.aws.amazon.com/sqs/)
* [CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
