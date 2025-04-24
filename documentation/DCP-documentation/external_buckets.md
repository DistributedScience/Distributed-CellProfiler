# Using External Buckets

Distributed-CellProfiler can read and/or write to/from an external S3 bucket (i.e. a bucket not in the same account as you are running DCP).
To do so, you will need to appropriately set your configuration in run.py.
You may need additional configuration in AWS Identity and Access Management (IAM).

## Config setup

* **AWS_PROFILE:** The profile you use must have appropriate permissions for running DCP as well as read/write permissions for the external bucket.
See below for more information.

* **AWS_BUCKET:** The bucket to which you would like to write log files.
This is generally the bucket in the account in which you are running compute.
* **SOURCE_BUCKET:** The bucket where the files you will be reading are.
Often, this is the same as AWS_BUCKET.
* **DESTINATION_BUCKET:** The bucket where you want to write your output files.
Often, this is the same as AWS_BUCKET.
* **UPLOAD_FLAGS:** If you need to add flags to an AWS CLI command to upload flags to your DESTINATION_BUCKET, this is where you enter them.
This is typically only used if you are writing to a bucket that is not yours.
If you don't need to add UPLOAD_FLAGS, keep it as the default ''.

## Example configs

### Reading from the Cell Painting Gallery

```python
AWS_REGION = 'your-region'              # e.g. 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'bucket-name'              # Your bucket
SOURCE_BUCKET = 'cellpainting-gallery'  
WORKSPACE_BUCKET = 'bucket-name'        # Likely your bucket
DESTINATION_BUCKET = 'bucket-name'      # Your bucket
UPLOAD_FLAGS = ''                      
```

### Read/Write to a collaborator's bucket

```python
AWS_REGION = 'your-region'              # e.g. 'us-east-1'
AWS_PROFILE = 'role-permissions'        # A profile with the permissions setup described above
SSH_KEY_NAME = 'your-key-file.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'bucket-name'              # Your bucket
SOURCE_BUCKET = 'collaborator-bucket'  
WORKSPACE_BUCKET = 'collaborator-bucket'
DESTINATION_BUCKET = 'collaborator-bucket'    
UPLOAD_FLAGS = '--acl bucket-owner-full-control --metadata-directive REPLACE' # Examples of flags that may be necessary
```

## Permissions setup

If you are reading from a public bucket, no additional setup is necessary.
Note that, depending on the configuration of that bucket, you may not be able to mount the public bucket so you will need to set `DOWNLOAD_FILES='True'`.

If you are reading from a non-public bucket or writing to a bucket that is not yours, you wil need further permissions setup.
Often, access to someone else's AWS account is handled through a role that can be assumed.
Learn more about AWS IAM roles [here](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html).
Your collaborator will define the access limits of the role within their AWS IAM.
You will also need to define role limits within your AWS IAM so that when you assume the role (giving you access to your collaborator's resource), that role also has the appropriate permissions to run DCP.

### In your AWS account

In AWS IAM, for the role that has external bucket access, you will need to add all of the DCP permissions described in [Step 0](step_0_prep.md).

You will also need to edit the trust relationship for the role so that ECS and EC2 can assume the role.
A template is as follows:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::123456789123:user/image_analyst",
                    "arn:aws:iam::123456789123:user/image_expert"
                ],
                "Service": [
                    "ecs-tasks.amazonaws.com",
                    "ec2.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

```

### In your DCP instance

DCP reads your AWS_PROFILE from your [control node](step_0_prep.md#the-control-node).
Edit your AWS CLI configuration files for assuming that role in your control node as follows:

In `~/.aws/config`, copy in the following text block at the bottom of the file, editing to your specifications, and save.

[profile access-collaborator]
role_arn = arn:aws:iam::123456789123:role/access-to-other-bucket
source_profile = my-account-profile
region = us-east-1
output = json

In `~/.aws/credentials`, copy in the following text block at the bottom of the file (filling in your access key info) and save.

[my-account-profile]
aws_access_key_id = ACCESS_KEY
aws_secret_access_key = SECRET_ACCESS_KEY
