#!/bin/bash

echo "Region $AWS_REGION"
echo "Queue $SQS_QUEUE_URL"
echo "Bucket $AWS_BUCKET"

# 1. CONFIGURE AWS CLI
aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure set default.region $AWS_REGION

# 2. MOUNT S3 
echo $AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY > /credentials.txt
chmod 600 /credentials.txt
mkdir -p /home/ubuntu/bucket
mkdir -p /home/ubuntu/local_output
stdbuf -o0 s3fs imaging-platform /home/ubuntu/bucket -o passwd_file=/credentials.txt 

# 3. RUN CP WORKERS
for((k=0; k<$DOCKER_CORES; k++)); do
    stdbuf -o0 python cp-worker.py > $k.out 2> $k.err &
    sleep $SECONDS_TO_START
done
wait

