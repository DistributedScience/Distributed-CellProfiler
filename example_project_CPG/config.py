# Constants (User configurable)

APP_NAME = 'ExampleCPG'                # Used to generate derivative names unique to the application.

# DOCKER REGISTRY INFORMATION:
DOCKERHUB_TAG = 'erinweisbart/distributed-cellprofiler:2.2.0rc1_4.2.4'

# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'your-bucket-name'         # Bucket to use for logging
SOURCE_BUCKET = 'cellpainting-gallery'  # Bucket to download image files from 
WORKSPACE_BUCKET = 'your-bucket-name'   # Bucket to download non-image files from
DESTINATION_BUCKET = 'your-bucket-name' # Bucket to upload files to

# EC2 AND ECS INFORMATION:
ECS_CLUSTER = 'default'
CLUSTER_MACHINES = 3
TASKS_PER_MACHINE = 1
MACHINE_TYPE = ['c4.xlarge']
MACHINE_PRICE = 0.13
EBS_VOL_SIZE = 22                       # In GB.  Minimum allowed is 22.
DOWNLOAD_FILES = 'True'
ASSIGN_IP = 'False'                     # If false, will overwrite setting in Fleet file

# DOCKER INSTANCE RUNNING ENVIRONMENT:
DOCKER_CORES = 1                        # Number of CellProfiler processes to run inside a docker container
CPU_SHARES = DOCKER_CORES * 1024        # ECS computing units assigned to each docker container (1024 units = 1 core)
MEMORY = 7000                           # Memory assigned to the docker container in MB
SECONDS_TO_START = 3*60                 # Wait before the next CP process is initiated to avoid memory collisions

# SQS QUEUE INFORMATION:
SQS_QUEUE_NAME = APP_NAME + 'Queue'
SQS_MESSAGE_VISIBILITY = 10*60           # Timeout (secs) for messages in flight (average time to be processed)
SQS_DEAD_LETTER_QUEUE = 'ExampleProject_DeadMessages'

# LOG GROUP INFORMATION:
LOG_GROUP_NAME = APP_NAME 

# CLOUDWATCH DASHBOARD CREATION
CREATE_DASHBOARD = 'True'           # Create a dashboard in Cloudwatch for run
CLEAN_DASHBOARD = 'True'            # Automatically remove dashboard at end of run with Monitor

# REDUNDANCY CHECKS
CHECK_IF_DONE_BOOL = 'False'  #True or False- should it check if there are a certain number of non-empty files and delete the job if yes?
EXPECTED_NUMBER_FILES = 7    #What is the number of files that trigger skipping a job?
MIN_FILE_SIZE_BYTES = 1      #What is the minimal number of bytes an object should be to "count"?
NECESSARY_STRING = ''        #Is there any string that should be in the file name to "count"?

# PLUGINS
USE_PLUGINS = 'False'
UPDATE_PLUGINS = 'False'
PLUGINS_COMMIT = '' # What commit or version tag do you want to check out?
INSTALL_REQUIREMENTS = 'False'
REQUIREMENTS_FILE = '' # Path within the plugins repo to a requirements file
