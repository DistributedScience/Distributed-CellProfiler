#!/bin/bash

echo "Region $AWS_REGION"
echo "Queue $SQS_QUEUE_URL"
echo "Bucket $AWS_BUCKET"

# 1. CONFIGURE AWS CLI
aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
aws configure set default.region $AWS_REGION
MY_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID $MY_INSTANCE_ID"
OWNER_ID=$(aws ec2 describe-instances --instance-ids $MY_INSTANCE_ID --output text --query 'Reservations[0].[OwnerId]')
aws ec2 create-tags --resources $MY_INSTANCE_ID --tags Key=Name,Value=${APP_NAME}Worker

# 2. MAP TASK NAME TO INSTANCE ID 

CONTAINER_INSTANCES=$(aws ecs list-container-instances --query "containerInstanceArns[*]" --output text)
INSTANCE_STRINGS=$(for ci in $CONTAINER_INSTANCES; do echo $ci| cut -d'/' -f 2|cut -d '"' -f 1; done)

for i in $INSTANCE_STRINGS; do 
    INSTANCE_ID=$(aws ecs describe-container-instances --cluster Cluster2 --container-instances $i --query "containerInstances[*].ec2InstanceId" --output text); 
    if [ "$INSTANCE_ID" == "$MY_INSTANCE_ID" ]; 
    then 
        MY_CONTAINER_ARN=$(aws ecs describe-container-instances --cluster Cluster2 --container-instances $i --query "containerInstances[*].containerInstanceArn" --output text); 
    fi;
done   

TASK_LIST=$( aws ecs list-tasks --query "taskArns[*]" --output text)
TASK_STRINGS=$(for tl in $TASK_LIST; do echo $tl| cut -d'/' -f 2|cut -d '"' -f 1; done)

for k in $TASK_STRINGS; do 
    CONTAINER_ARN=$(aws ecs describe-tasks --cluster Cluster2 --tasks $k  --query "tasks[*].[containerInstanceArn]" --output text); 
    if [ "$CONTAINER_ARN" == "$MY_CONTAINER_ARN" ]; 
    then 
        MY_TASK_NAME=$(aws ecs describe-tasks --cluster Cluster2 --tasks $k  --query "tasks[*].overrides.[containerOverrides]" --output text); 
    fi; 
done   

MY_TASK_NAME=$(echo $MY_TASK_NAME| cut -d'/' -f 2|cut -d '"' -f 1)

# 3. MOUNT S3 
echo $AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY > /credentials.txt
chmod 600 /credentials.txt
mkdir -p /home/ubuntu/bucket
mkdir -p /home/ubuntu/local_output
stdbuf -o0 s3fs imaging-platform /home/ubuntu/bucket -o passwd_file=/credentials.txt 

# 4. SET UP ALARMS
aws cloudwatch put-metric-alarm --alarm-name ${APP_NAME}_${MY_INSTANCE_ID} --alarm-actions arn:aws:swf:us-east-1:${OWNER_ID}:action/actions/AWS_EC2.InstanceId.Terminate/1.0 --statistic Maximum --period 60 --threshold 1 --comparison-operator LessThanThreshold --metric-name CPUUtilization --namespace AWS/EC2 --evaluation-periods 15 --dimensions "Name=InstanceId,Value=${MY_INSTANCE_ID}" 

# 5. RUN VM STAT MONITOR

python -v instance-monitor.py &

# 6. RUN CP WORKERS
for((k=0; k<$DOCKER_CORES; k++)); do
    python -v cp-worker.py |& tee $k.out &
    sleep $SECONDS_TO_START
done
wait

