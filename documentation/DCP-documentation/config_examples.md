# Config.py configuration examples

We have a handful of standard workflows we follow when running the Cell painting Assay. {Brief description of pipelines.}

Our internal configurations for each pipeline are as follows:

|   | Z-Projection | Illumination Correction | Quality Control | Assay Dev | Analysis | Notes |
|---|---|---|---|---|---|---|
| APP_NAME | 'PROJECT_NAME_Zproj' |'PROJECT_NAME_Illum' | 'PROJECT_NAME_Illum_QC' |' PROJECT_NAME_Illum_AssayDev' | 'PROJECT_NAME_Illum_Analysis' | If the PROJECT_NAME is excessively long you can enter a truncated version of it here but you will need to be careful to use the correct version in subsequent steps in the protocol. (e.g. 2021_06_08_WCPC_Zproj) |
| DOCKERHUB_TAG | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | Ensure the CP tag number matches the version of CellProfiler for your pipeline (can easily see by opening the pipeline in a text editor and looking for the 3rd line “DateRevision: 413”). |
| AWS_REGION | 'us-east-1' | 'us-east-1' | 'us-east-1' | 'us-east-1' | 'us-east-1' |  |
| AWS_PROFILE | 'default' | 'default' | 'default' | 'default' | 'default' |  |
| SSH_KEY_NAME | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' |   |
| AWS_BUCKET | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' |   |
| ECS_CLUSTER | 'default' | 'default' | 'default' | 'default' | 'default' | Most of the time we all just use the default cluster but if there are multiple jobs being run at once you can create your own cluster by changing default to YOURNAME so that the correct dockers go on the correct machines. |
| CLUSTER_MACHINES | 100-200 | number of plates / CPUs and rounded up | 25-100 |   | AWS has limits on the number of machines you can request at a time. 200 is generally the largest we request for a single job to ensure there is some capacity for other users in the team. |
| TASKS_PER_MACHINE | 1 | 1 | 1 | 1 | 1 |  |
| MACHINE_TYPE | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | Historically we have used m4.xlarge and then m5.xlarge however very recently we have been having a hard time getting m class machines so we have switched to c class. Note that they have different memory sizes so you need to make sure MEMORY is set correctly if changing between classes. |
| MACHINE_PRICE | .10 | .10 | .10 | .10 | .10 | Will be different for different size/classes of machines. |
| TASKS_PER_MACHINE | 1 | 1 | 1 | 1 | 1 |  |
| EBS_VOL_SIZE | 22 | 22 | 22 | 22 | 22 | You might need to make this larger if you set DOWNLOAD_FILES = True  |
| DOWNLOAD_FILES | 'False' | 'False' | 'False' | 'False' | 'False' |   |
| DOCKER_CORES | 4 | 4 | 4 | 4  | 4 | If using c class machines and large images (2k + pixels) then you might need to reduce this number. |
| CPU_SHARES | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | We never change this. |
| MEMORY | 7500 | 7500 | 7500 | 7500 | 7500 | This must match your machine type. m class use 15000, c class use 7500. |
| SECONDS_TO_START | 60  | 3*60 | 60 | 3*60 | 3*60 |  |
| SQS_QUEUE_NAME | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | We never change this. |
| SQS_MESSAGE_VISIBILITY | 3*60 | 720*60 | 15*60 |   |   | About how long you expect a job to take * 1.5 in seconds |
| SQS_DEAD_LETTER_QUEUE | 'YOUR_DEADMESSAGES_ARN' | 'YOUR_DEADMESSAGES_ARN' | 'YOUR_DEADMESSAGES_ARN' | 'YOUR_DEADMESSAGES_ARN' |   |
| LOG_GROUP_NAME | APP_NAME | APP_NAME | APP_NAME | APP_NAME | We never change this. |
| CHECK_IF_DONE_BOOL | 'True' | 'True' | 'True' | 'True' | 'True' | Can be turned off if wanting to overwrite old data. |
| EXPECTED_NUMBER_FILES | 1 (an image) | number channels + 1 (an .npy for each channel and isdone) | 3 (Experiment.csv, Image.csv, and isdone) |   |   | Better to underestimate than overestimate. |
| MIN_FILE_SIZE_BYTES | 1 | 1 | 1 | 1 | 1 | Count files of any size. |
| NECESSARY_STRING | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
| USE_PLUGINS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| UPDATE_PLUGINS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| PLUGINS_COMMIT | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
| INSTALL_REQUIREMENTS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| REQUIREMENTS_FILE | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
