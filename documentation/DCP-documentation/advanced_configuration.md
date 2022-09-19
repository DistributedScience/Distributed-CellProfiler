# Advanced Configuration of DCP

We've tried very hard to make Distributed-CellProfiler light and adaptable, but keeping the configuration settings to a manageable number requires making some default assumptions.
Below is a non-comprehensive list of places where you can adapt the code to your own purposes.

***
## Changes you can make to Distributed-CellProfiler outside of the Docker container

* **Location of ECS configuration files:** By default these are placed into your bucket with a prefix of 'ecsconfigs/'.
Alternate locations can be designated in the run script.
* **Log configuration and location of exported logs:** Distributed-CellProfiler creates log groups with a default retention of 60 days (to avoid hitting the AWS limit of 250) and after finishing the run exports them into your bucket with a prefix of 'exportedlogs/LOG_GROUP_NAME/'.
These may be modified in the run script.
* **Advanced EC2 configuration:** Any additional configuration of your EC2 spot fleet (such as installing additional packages or running scripts on startup) can be done by modifying the userData parameter in the run script.
* **SQS queue detailed configuration:**  Distributed-CellProfiler creates a queue where messages will be tried 10 times before being consigned to a DeadLetterQueue, and unprocessed messages will expire after 14 days (the AWS maximum).
These values can be modified in run.py .

***

## Changes that will require you to make your own Docker container

* **CellProfiler version:** We try to keep Distributed-CellProfiler up to date with the latest stable release of CellProfiler, but in case you want to use your own Dockerized version of a different CellProfiler build you can edit the Dockerfile to call that CellProfiler Docker instead.
* **Alarm names or thresholds:** These can be modified in the run-worker script.  
* **Frequency or types of information included in the per-instance logs:** These can be adjusted in the instance-monitor script.
* **[CellProfiler command line flags](https://github.com/CellProfiler/CellProfiler/wiki/Adapting-CellProfiler-to-a-LIMS-environment#cmd):** These can be modified in the cp-worker script.
* **Log stream names or logging level:** These can be modified in the cp-worker script.
