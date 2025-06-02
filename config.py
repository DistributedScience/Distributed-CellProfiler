# Constants (User configurable)

APP_NAME = 'DistributedCP'                # Used to generate derivative names unique to the application.
LOG_GROUP_NAME = APP_NAME

# DOCKER REGISTRY INFORMATION:
DOCKERHUB_TAG = 'cellprofiler/distributed-cellprofiler:2.2.0_4.2.8'

# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'your-bucket-name'         # Bucket to use for logging
SOURCE_BUCKET = 'bucket-name'           # Bucket to download image files from
WORKSPACE_BUCKET = 'bucket-name'        # Bucket to download non-image files from
DESTINATION_BUCKET = 'bucket-name'      # Bucket to upload files to
UPLOAD_FLAGS = ''                       # Any flags needed for upload to destination bucket

# EC2 AND ECS INFORMATION:
ECS_CLUSTER = 'default'
CLUSTER_MACHINES = 3
TASKS_PER_MACHINE = 1
MACHINE_TYPE = ['m5.xlarge']
MACHINE_PRICE = 0.20
EBS_VOL_SIZE = 30                       # In GB.  Minimum allowed is 22.
DOWNLOAD_FILES = 'False'
ASSIGN_IP = 'True'                     # If false, will overwrite setting in Fleet file

# DOCKER INSTANCE RUNNING ENVIRONMENT:
DOCKER_CORES = 4                        # Number of CellProfiler processes to run inside a docker container
CPU_SHARES = DOCKER_CORES * 1024        # ECS computing units assigned to each docker container (1024 units = 1 core)
MEMORY = 15000                           # Memory assigned to the docker container in MB
SECONDS_TO_START = 3*60                 # Wait before the next CP process is initiated to avoid memory collisions

# SQS QUEUE INFORMATION:
SQS_QUEUE_NAME = APP_NAME + 'Queue'
SQS_MESSAGE_VISIBILITY = 1*60           # Timeout (secs) for messages in flight (average time to be processed)
SQS_DEAD_LETTER_QUEUE = 'user_DeadMessages'
JOB_RETRIES = 3            # Number of times to retry a job before sending it to DEAD_LETTER_QUEUE

# MONITORING
AUTO_MONITOR = 'True'

# CLOUDWATCH DASHBOARD CREATION
CREATE_DASHBOARD = 'True'           # Create a dashboard in Cloudwatch for run
CLEAN_DASHBOARD = 'True'            # Automatically remove dashboard at end of run with Monitor

# REDUNDANCY CHECKS
CHECK_IF_DONE_BOOL = 'False'  #True or False- should it check if there are a certain number of non-empty files and delete the job if yes?
EXPECTED_NUMBER_FILES = 7    #What is the number of files that trigger skipping a job?
MIN_FILE_SIZE_BYTES = 1      #What is the minimal number of bytes an object should be to "count"?
NECESSARY_STRING = ''        #Is there any string that should be in the file name to "count"?

# CELLPROFILER SETTINGS
ALWAYS_CONTINUE = 'False'     # Whether or not to run CellProfiler with the --always-continue flag, which will keep CellProfiler from crashing if it errors

# PLUGINS
USE_PLUGINS = 'False'          # True to use any plugin from CellProfiler-plugins repo
UPDATE_PLUGINS = 'False'       # True to download updates from CellProfiler-plugins repo
PLUGINS_COMMIT = 'False'       # What commit or version tag do you want to check out? If not, set to False.
INSTALL_REQUIREMENTS = 'False' # True to install REQUIREMENTS defined below. Requirements should have all plugin dependencies.
REQUIREMENTS = ''       # Flag to use with install (current) or path within the CellProfiler-plugins repo to a requirements file (deprecated).
