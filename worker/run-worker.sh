#!/bin/bash

echo "Region $AWS_REGION"
echo "Queue $SQS_QUEUE_URL"
echo "Bucket $AWS_BUCKET"

# 1. CONFIGURE AWS CLI
aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure set default.region $AWS_REGION
INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
OWNER_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --output text --query 'Reservations[0].[OwnerId]')
aws ec2 create-tags --resources $INSTANCE_ID --tags Key=Name,Value= ${APP_NAME}_Worker

# 2. MOUNT S3 
echo $AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY > /credentials.txt
chmod 600 /credentials.txt
mkdir -p /home/ubuntu/bucket
mkdir -p /home/ubuntu/local_output
stdbuf -o0 s3fs imaging-platform /home/ubuntu/bucket -o passwd_file=/credentials.txt 

# 3. SET UP ALARMS
aws cloudwatch put-metric-alarm --alarm-name ${APP_NAME}_${INSTANCE_ID} --alarm-actions arn:aws:swf:us-east-1:${OWNER_ID}:action/actions/AWS_EC2.InstanceId.Terminate/1.0 --statistic Maximum --period 60 --threshold 1 --comparison-operator LessThanThreshold --metric-name CPUUtilization --namespace AWS/EC2 --evaluation-periods 15 --dimensions "Name=InstanceId,Value=${INSTANCE_ID}" 

# 4. RUN CP WORKERS
for((k=0; k<$DOCKER_CORES; k++)); do
    stdbuf -o0 python cp-worker.py > $k.out 2> $k.err &
    sleep $SECONDS_TO_START
done
wait

