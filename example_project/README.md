Included in this folder is all of the resources for running a complete mini-example of Distributed-Cellprofiler.
It includes 3 sample image sets and a CellProfiler pipeline that identifies cells within the images and makes measuremements.
It also includes the Distributed-CellProfiler files pre-configured to create a queue of all 3 jobs and spin up a spot fleet of 3 instances, each of which will process a single image set.

## Running example project

### Step 0

Before running this mini-example, you will need to set up your AWS infrastructure as described in our [online documentation](https://distributedscience.github.io/Distributed-CellProfiler/step_0_prep.html).
This includes creating the fleet file that you will use in Step 3.

Upload the 'sample_project' folder to the top level of your bucket. 
While in the `Distributed-CellProfiler` folder, use the following command, replacing `yourbucket` with your bucket name:

```bash
# Copy example files to S3
BUCKET=yourbucket
aws s3 sync example_project/project_folder s3://${BUCKET}/project_folder

# Replace the default config with the example config
cp example_project/config.py config.py
```

### Step 1
In config.py you will need to update the following fields specific to your AWS configuration:
```
# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'your-bucket-name'
SOURCE_BUCKET = 'your-bucket-name'      # Only differs from AWS_BUCKET with advanced configuration
DESTINATION_BUCKET = 'your-bucket-name' # Only differs from AWS_BUCKET with advanced configuration
```
Then run `python3 run.py setup`

### Step 2
This command points to the job file created for this demonstartion and should be run as-is.
`python3 run.py submitJob example_project/files/exampleJob.json`

### Step 3
This command should point to whatever fleet file you created in Step 0 so you may need to update the `exampleFleet.json` file name.
`python3 run.py startCluster files/exampleFleet.json`

### Step 4
This command points to the monitor file that is automatically created with your run and should be run as-is.
`python3 run.py monitor files/FlyExampleSpotFleetRequestId.json`

## Results

While the run is happening, you can watch real-time metrics in your Cloudwatch Dashboard by navigating in the [Cloudwatch console](https://console.aws.amazon.com/cloudwatch).
Note that the metrics update at intervals that may not be helpful with this fast, minimal example.

After the run is done, you should see your CellProfiler output files in S3 at s3://${BUCKET}/project_folder/output in per-image folders.