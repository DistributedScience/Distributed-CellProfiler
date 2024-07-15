#!/bin/bash
echo "${BASH_VERSION}"
echo "Region $AWS_REGION"
echo "Queue $SQS_QUEUE_URL"
if [[ -z "$AWS_BUCKET" ]]
then
  SOURCE_BUCKET=$AWS_BUCKET
fi
echo "Source Bucket $SOURCE_BUCKET"

# 1. CONFIGURE AWS CLI
aws configure set default.region $AWS_REGION
MY_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID $MY_INSTANCE_ID"
OWNER_ID=$(aws ec2 describe-instances --instance-ids $MY_INSTANCE_ID --output text --query 'Reservations[0].[OwnerId]')
aws ec2 create-tags --resources $MY_INSTANCE_ID --tags Key=Name,Value=${APP_NAME}Worker
VOL_0_ID=$(aws ec2 describe-instance-attribute --instance-id $MY_INSTANCE_ID --attribute blockDeviceMapping --output text --query BlockDeviceMappings[0].Ebs.[VolumeId])
aws ec2 create-tags --resources $VOL_0_ID --tags Key=Name,Value=${APP_NAME}Worker
VOL_1_ID=$(aws ec2 describe-instance-attribute --instance-id $MY_INSTANCE_ID --attribute blockDeviceMapping --output text --query BlockDeviceMappings[1].Ebs.[VolumeId])
aws ec2 create-tags --resources $VOL_1_ID --tags Key=Name,Value=${APP_NAME}Worker


# 2. MOUNT S3 
echo $AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY > /credentials.txt
chmod 600 /credentials.txt
mkdir -p /home/ubuntu/bucket
mkdir -p /home/ubuntu/local_output
stdbuf -o0 s3fs $AWS_BUCKET /home/ubuntu/bucket -o passwd_file=/credentials.txt 


# 3. SET UP ALARMS
aws cloudwatch put-metric-alarm --alarm-name ${APP_NAME}_${MY_INSTANCE_ID} --alarm-actions arn:aws:swf:${AWS_REGION}:${OWNER_ID}:action/actions/AWS_EC2.InstanceId.Terminate/1.0 --statistic Maximum --period 60 --threshold 1 --comparison-operator LessThanThreshold --metric-name CPUUtilization --namespace AWS/EC2 --evaluation-periods 15 --dimensions "Name=InstanceId,Value=${MY_INSTANCE_ID}"

# 4. RUN VM STAT MONITOR

python3.8 instance-monitor.py &

# 5. UPDATE AND/OR INSTALL PLUGINS
if [[ ${USE_PLUGINS} == 'True' ]]; then
  if [[ ${UPDATE_PLUGINS} == 'True' ]]; then
    echo "Updating CellProfiler-plugins."
    cd CellProfiler-plugins
    git fetch --all
    cd ..
  fi
  if [[ ${PLUGINS_COMMIT} != 'False' ]]; then
    echo "Checking out specific CellProfiler-plugins commit."
    cd CellProfiler-plugins
    git checkout ${PLUGINS_COMMIT} || echo "No such commit, branch, or version; failing here." & exit 1
    cd ..
  fi 
  if [[ ${INSTALL_REQUIREMENTS} == 'True' ]]; then
    cd CellProfiler-plugins
    if [[ -z "$REQUIREMENTS" ]]; then
      REQUIREMENTS = $REQUIREMENTS_FILE
    fi
    if [[ -d "active_plugins" ]]; then
      echo "Installing CellProfiler-plugins requirements."
      pip install -e . ${REQUIREMENTS} || echo "Requirements install failed." & exit 1
      cd ..
    else 
      echo "Detected deprecated CellProfiler-plugins repo organization. Installing requirements."
      pip install -r ${REQUIREMENTS} || echo "Requirements file not present or install failed; failing here." & exit 1
      cd ..
    fi
  fi
fi

# 6. RUN CP WORKERS
for((k=0; k<$DOCKER_CORES; k++)); do
    python3.8 cp-worker.py |& tee $k.out &
    sleep $SECONDS_TO_START
done
wait
