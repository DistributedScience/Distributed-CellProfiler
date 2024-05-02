# config.py configuration examples

We have a handful of standard workflows we follow in a stereotyped fashion when running the Cell Painting Assay.
We have listed below the standard way that we configure `config.py` for each workflow.
You can read more information about the pipelines in the context of the Cell Painting Assay [here](https://www.biorxiv.org/content/10.1101/2022.07.13.499171v1.full).

- **Z-projection** creates a new image with each pixel containing the maximum value from any of the z-planes, effectively condensing the contents of multiple focal planes into one.
Generally, we perform projection on all images with multiple z-planes and downstream processing and analysis is performed on the projected images.

- **Illumination Correction** is batched by plate and generates a function that corrects for light path irregularities as described [here](https://onlinelibrary.wiley.com/doi/abs/10.1111/jmi.12178).
Note that this pipeline depends upon having a large number of images.
A standard pipeline can be found [here](https://github.com/broadinstitute/imaging-platform-pipelines/blob/master/JUMP_production/JUMP_illum_LoadData_v1.cppipe).

- **Quality Control** provides metrics on the quality of the input images.
It is not a necessary step but can provide helpful information, particularly for improving wetlab workflows and for comparing across datasets.
A standard pipeline can be found [here](https://github.com/broadinstitute/imaging-platform-pipelines/blob/master/JUMP_production/JUMP_QC_Drag-and-Drop_v1.cppipe).

- **Assay Dev/Segmentation** is a quick pipeline that outputs segmentation outlines overlaid on a multichannel image rescaled for visual inspection.
We often stitch the output into a pseudo-plate view as described [here](https://currentprotocols.onlinelibrary.wiley.com/doi/10.1002/cpz1.89) to confirm we have chosen segmentation parameters that work across our dataset.
A standard pipeline can be found [here](https://github.com/broadinstitute/imaging-platform-pipelines/blob/master/JUMP_production/JUMP_segment_LoadData_v1.cppipe).

- **Analysis** is where illumination correction is applied, actual segmentation occurs, and all of the measurements used for generating image-based profiles are taken.
Note that large images may require more memory than our default parameters listed below.
If you don't have enough memory, reduce the number of copies of CellProfiler running at one time by decreasing DOCKER_CORES.
A standard pipeline can be found [here](https://github.com/broadinstitute/imaging-platform-pipelines/blob/master/JUMP_production/JUMP_analysis_v3.cppipe).

Our internal configurations for each pipeline are as follows:

|   | Z-Projection | Illumination Correction | Quality Control | Assay Dev | Analysis | Notes |
|---|---|---|---|---|---|---|
| APP_NAME | 'PROJECT_NAME_Zproj' |'PROJECT_NAME_Illum' | 'PROJECT_NAME_QC' |' PROJECT_NAME_AssayDev' | 'PROJECT_NAME_Analysis' | If the PROJECT_NAME is excessively long you can enter a truncated version of it here but you will need to be careful to use the correct version in subsequent steps in the protocol. (e.g. 2021_06_08_WCPC_Zproj) |
| LOG_GROUP_NAME | APP_NAME | APP_NAME | APP_NAME | APP_NAME |APP_NAME | We never change this. |
| DOCKERHUB_TAG | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | 'cellprofiler/distributed-cellprofiler:2.0.0_4.2.4' | Ensure the CP tag number matches the version of CellProfiler for your pipeline (can easily see by opening the pipeline in a text editor and looking for the 3rd line “DateRevision: 413”). |
| AWS_REGION | 'us-east-1' | 'us-east-1' | 'us-east-1' | 'us-east-1' | 'us-east-1' |  |
| AWS_PROFILE | 'default' | 'default' | 'default' | 'default' | 'default' |  |
| SSH_KEY_NAME | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' | 'YOURPEM.pem' |   |
| AWS_BUCKET | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | Usually a bucket in the account that is running DCP.  |
| SOURCE_BUCKET | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | Can be a public bucket like cellpainting-gallery.  |
| DESTINATION_BUCKET | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | 'BUCKET' | Usually a bucket in the account that is running DCP.  |
| UPLOAD_FLAGS | '' | '' | '' | '' | '' |   |
| ECS_CLUSTER | 'default' | 'default' | 'default' | 'default' | 'default' | Most of the time we all just use the default cluster but if there are multiple jobs being run at once you can create your own cluster by changing default to YOURNAME so that the correct dockers go on the correct machines. |
| CLUSTER_MACHINES | 100-200 | number of plates / CPUs and rounded up | 25-100 | 25-100 | 100-200 | AWS has limits on the number of machines you can request at a time. 200 is generally the largest we request for a single job to ensure there is some capacity for other users in the team. |
| TASKS_PER_MACHINE | 1 | 1 | 1 | 1 | 1 |  |
| MACHINE_TYPE | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | ['c5.xlarge'] | Historically we have used m4.xlarge and then m5.xlarge however very recently we have been having a hard time getting m class machines so we have switched to c class. Note that they have different memory sizes so you need to make sure MEMORY is set correctly if changing between classes. |
| MACHINE_PRICE | .20 | .20 | .20 | .20 | .20 | Will be different for different size/classes of machines. |
| EBS_VOL_SIZE <br>(if using mounted volume)<br><br>(if downloading from external bucket) | 22<br><br>22 | 22<br><br>200 | 22<br><br>22 | 22<br><br>22 | 22<br><br>40 | Suggested size increases when downloading files from another bucket (DOWNLOAD_FILES = True) depending on the files. |
| DOWNLOAD_FILES | 'False' | 'False' | 'False' | 'False' | 'False' |   |
| DOCKER_CORES | 4 | 4 | 4 | 4  | 3 | If using c class machines and large images (2k + pixels) then you might need to reduce this number. |
| CPU_SHARES | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | DOCKER_CORES * 1024 | We never change this. |
| MEMORY | 7500 | 7500 | 7500 | 7500 | 7500 | This must match your machine type. m class use 15000, c class use 7500. |
| SECONDS_TO_START | 60  | 3*60 | 60 | 3*60 | 3*60 |  |
| SQS_QUEUE_NAME | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | APP_NAME + 'Queue' | We never change this. |
| SQS_MESSAGE_VISIBILITY | 3*60 | 240*60 | 15*60 | 10*60 | 120*60 | About how long you expect a job to take * 1.5 in seconds |
| SQS_DEAD_LETTER_QUEUE | 'YOURNAME_DEADMESSAGES' | 'YOURNAME_DEADMESSAGES' | 'YOURNAME_DEADMESSAGES' | 'YOURNAME_DEADMESSAGES' |'YOURNAME_DEADMESSAGES' |   |
| AUTO_MONITOR | 'True' | 'True' | 'True' | 'True' | 'True' | Can be turned off if manually running Monitor. |
| CREATE_DASHBOARD | 'True' | 'True' | 'True' | 'True' | 'True' | |
| CLEAN_DASHBOARD | 'True' | 'True' | 'True' | 'True' | 'True' | |
| CHECK_IF_DONE_BOOL | 'True' | 'True' | 'True' | 'True' | 'True' | Can be turned off if wanting to overwrite old data. |
| EXPECTED_NUMBER_FILES | 1 (an image) | number channels + 1 (an .npy for each channel and isdone) | 3 (Experiment.csv, Image.csv, and isdone) | 1 (an image) | 5 (Experiment, Image, Cells, Nuclei, and Cytoplasm .csvs) | Better to underestimate than overestimate. |
| MIN_FILE_SIZE_BYTES | 1 | 1 | 1 | 1 | 1 | Count files of any size. |
| NECESSARY_STRING | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
| USE_PLUGINS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| UPDATE_PLUGINS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| PLUGINS_COMMIT | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
| INSTALL_REQUIREMENTS | 'False' | 'False' | 'False' | 'False' | 'False' |  Not necessary for standard workflows. |
| REQUIREMENTS_FILE | '' | '' | '' | '' | '' |  Not necessary for standard workflows. |
