# CPG Example Project

Included in this folder is all of the resources for running a complete mini-example of Distributed-CellProfiler.
This example differs from the other example project in that it reads data hosted in the public data repository the [Cell Painting Gallery](https://github.com/broadinstitute/cellpainting-gallery) instead of reading images from your own bucket.
Workspace files are hosted in your own S3 bucket, and data is output to your bucket, and compute is performed in your account.
It includes the Distributed-CellProfiler files pre-configured to create a queue of 3 jobs and spin up a spot fleet of 3 instances, each of which will process a single image set.

## Running example project

### Step 0

Before running this mini-example, you will need to set up your AWS infrastructure as described in our [online documentation](https://distributedscience.github.io/Distributed-CellProfiler/step_0_prep.html).
This includes creating the fleet file that you will use in Step 3.

Upload the 'sample_project' folder to the top level of your bucket.
While in the `Distributed-CellProfiler` folder, use the following command, replacing `yourbucket` with your bucket name:

```bash
# Copy example files to S3
BUCKET=yourbucket
aws s3 sync example_project_CPG/demo_project_folder s3://${BUCKET}/demo_project_folder

# Replace the default config with the example config
cp example_project_CPG/config.py config.py
```

### Step 1

In config.py you will need to update the following fields specific to your AWS configuration:

```python
# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'your-bucket-name'
WORKSPACE_BUCKET = 'your-bucket-name'   # Only differs from AWS_BUCKET with advanced configuration
DESTINATION_BUCKET = 'your-bucket-name' # Only differs from AWS_BUCKET with advanced configuration
```

Then run `python run.py setup`

### Step 2

This command points to the job file created for this demonstration and should be run as-is.
`python run.py submitJob example_project_CPG/files/exampleCPGJob.json`

### Step 3

This command should point to whatever fleet file you created in Step 0 so you may need to update the `exampleFleet.json` file name.
`python run.py startCluster files/exampleFleet.json`

### Step 4

This command points to the monitor file that is automatically created with your run and should be run as-is.
`python run.py monitor files/ExampleCPGSpotFleetRequestId.json`

## Results

While a run is happening, you can watch real-time metrics in your Cloudwatch Dashboard by navigating in the [Cloudwatch console](https://console.aws.amazon.com/cloudwatch).
Note that the metrics update at intervals that may not be helpful with this fast, minimal example.

After the run is done, you should see your CellProfiler output files in your S3 bucket at s3://${BUCKET}/project_folder/output in per-well-and-site folders.

## Cleanup

The spot fleet, queue, and task definition will be automatically cleaned up after your demo is complete because you are running `monitor`.

To remove everything else:

```bash
# Remove files added to S3 bucket
BUCKET=yourbucket
aws s3 rm --recursive s3://${BUCKET}/demo_project_folder

# Remove Cloudwatch logs
aws logs delete-log-group --log-group-name ExampleCPG
aws logs delete-log-group --log-group-name ExampleCPG_perInstance

# Delete DeadMessages queue
aws sqs delete-queue --queue-url ExampleProject_DeadMessages
```
