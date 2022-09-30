# SQS QUEUE Information

This is in-depth information about the configurable components in SQS QUEUE INFORMATION, a section in [Step 1: Configuration](step_1_configuration.md) of running Distributed CellProfiler.

## SQS_QUEUE_NAME

**SQS_QUEUE_NAME** is the name of the queue where all of your jobs are sent.
(A queue is exactly what it sounds like - a list of things waiting their turn. Jobs represent one complete run through a CellProfiler pipeline (though each job may involve any number of images. e.g. analysis may require thousands of jobs, each with a single image making one complete CellProfiler run, while making an illumination correction may be a single job that iterates through thousands of images to produce a single output file.))
You want a name that is descriptive enough to distinguish it from other queues.
We usually name our queues based on the project and the step or pipeline goal.
An example may be something like Hepatocyte_Differentiation_Illum or Lipid_Droplet_Analysis.

## SQS_DEAD_LETTER_QUEUE

**SQS_DEAD_LETTER_QUEUE** is the name of the queue where all the jobs that failed to run are sent.
If everything goes perfectly, this will always remain empty.
If jobs that are in the queue fail multiple times (our default is 10) they are moved to the dead-letter queue, which is not used to initiate jobs.
The dead-letter queue therefore functions effectively as a log so you can see if any of your jobs failed.
It is different from your other queue as machines do not try and pull jobs from it.
Protip: Each member of our team maintains their own dead-letter queue so we don’t have to worry about finding messages if multiple people are running jobs at the same time.
We use names like DeadMessages_Erin.

If all of your jobs end up in your dead-letter queue there are many different places you could have a problem.
Hopefully, you’ll keep an eye on the logs in your CloudWatch (the part of AWS used for monitoring what all your other AWS services are doing) after starting a run and catch the issue before all of your jobs fail multiple times.

If a single job ends up in your dead-letter queue while the rest of your jobs complete successfully, it is likely that that an image is corrupted (a corrupted image is one that has failed to save properly or has been damaged so that it will not open).
This is true whether your pipeline processes a single image at a time (such as in analysis runs where you’re interested in cellular measurements on a per-image basis) or whether your pipeline processes many images at a time (such as when making an illumination correction image on a per-plate basis).
This is the major reason why we have the dead-letter queue: you certainly don’t want to pay for your cluster to indefinitely attempt to process a corrupted image.
Keeping an eye on your CloudWatch logs wouldn’t necessarily help you catch this kind of error because you could have tens or hundreds of successful jobs run before an instance pulls the job for the corrupted image, or the corrupted image could be thousands of images into an illumination correction run, etc.

## SQS_MESSAGE_VISIBILITY

**SQS_MESSAGE_VISIBILITY** controls how long jobs are hidden after being pulled by a machine to run.
Jobs must be visible (i.e. not hidden) in order to be pulled by a Docker and therefore run.
In other words, the time you enter in SQS_MESSAGE_VISIBILITY is how long a job is allowed a chance to complete before it is unhidden and made available to be started by a different copy of CellProfiler.
It’s quite important to set this time correctly - we typically say to estimate 1.5X how long the job typically takes to run (or your best guess of that if you’re not sure).
To understand why, and the consequences of setting an incorrect time, let’s look more carefully at the SQS queue.

The SQS queue has two categories - “Messages Available” and “Messages In Flight”.
Each message is a job and regardless of the category it’s in, the jobs all remain in the same queue.
In effect, “In Flight” means currently hiding and “Available” means not currently hiding.

When you submit your Config file to AWS it creates your queue in SQS but that queue starts out empty.
When you submit your Jobs file to AWS it puts all of your jobs into the queue under “Messages Available”.
When you submit your Fleet file to AWS it 1) creates machines in EC2, 2) ECS puts Docker containers on those instances, and 3) those instances look in “Messages Available” in SQS for jobs to run.

Once a Docker has pulled a job, that job moves from “Available’ to “In Flight”.
It remains hidden (“In Flight”) for the duration of time set in SQS_MESSAGE_VISIBILITY and then it becomes visible again (“Available”).
Jobs are hidden so that multiple machines don’t process the same job at the same time.
If the job completes successfully, the Docker tells the queue to delete that message.

If the job completes but it is not successful (e.g. CellProfiler errors), the Docker tells the queue to move the job from “In Flight” to “Available” so another Docker (with a different copy of CellProfiler) can attempt to complete the job.

If the SQS_MESSAGE_VISIBILITY is too short then a job will become unhidden even though it is still currently being (hopefully successfully) run by the Docker that originally picked it up.
This means that another Docker may come along and start the same job and you end up paying for unnecessary compute time because both Dockers will continue to run the job until they each finish.

If the SQS_MESSAGE_VISIBILITY is too long then you can end up wasting time and money waiting for the job to become available again after a crash even when the rest of your analysis is done.
If anything causes a job to stop mid-run (e.g. CellProfiler crashes, the instance crashes, or the instance is removed by AWS because you are outbid), that job stays hidden until the set time.
If a Docker instance goes to the queue and doesn’t find any visible jobs, then it does not try to run any more jobs in that copy of CellProfiler, limiting the effective computing power of that Docker.
Therefore, some or all of your instances may hang around doing nothing (but costing money) until the job is visible again.
When in doubt, it is better to have your SQS_MESSAGE_VISIBILITY set too long than too short because, while crashes can happen, it is rare that AWS takes small machines from your fleet, though we do notice it happening with larger machines.

There is not an easy way to see if you have selected the appropriate amount of time for your SQS_MESSAGE_VISIBILITY on your first run through a brand new pipeline.
To confirm that multiple Dockers didn’t run the same job, after the jobs are complete, you need to manually go through each log in CloudWatch and figure out how many times you got the word “SUCCESS” in each log.
(This may be reasonable to do on an illumination correction run where you have a single job per plate, but it’s not so reasonable if running an analysis pipeline on thousands of individual images).
To confirm that multiple Dockers are never processing the same job, you can keep an eye on your queue and make sure that you never have more jobs “In Flight” than the number of copies of CellProfiler that you have running; likewise, if your timeout time is too short, it may seem like too few jobs are “In Flight” even though the CPU usage on all your machines is high.

Once you have run a pipeline once, you can check the execution time (either by noticing how long after you started your jobs that your first jobs begin to finish, or by checking the logs of individual jobs and noting the start and end time), you will then have an accurate idea of roughly how long that pipeline needs to execute, and can set your message visibility accordingly.  
You can even do this on the fly while jobs are currently processing; the updated visibility time won’t affect the jobs already out for processing (i.e. if the time was set to 3 hours and you change it to 1 hour, the jobs already processing will remain hidden for 3 hours or until finished), but any job that begins processing AFTER the change will use the new visibility timeout setting.

## Example SQS Queue

[[images/Sample_SQS_Queue.png|alt="Sample_SQS_Queue"]]

This is an example of an SQS Queue.
You can see that there is one active task with 64 jobs in it.
In this example, we are running a fleet of 32 instances, each with a single Docker, so at this moment (right after starting the fleet), there are 32 tasks "In Flight" and 32 tasks that are still "Available."
You can also see that many lab members have their own dead-letter queues which are, fortunately, all currently empty.
