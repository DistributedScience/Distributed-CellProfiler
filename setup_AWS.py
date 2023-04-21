import sys
import boto3
import json

iam = boto3.client("iam")
sns = boto3.client("sns")
lmbda = boto3.client("lambda")

ecsInstanceRole_policy_list = [
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/CloudWatchFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchActionsEC2Access",
    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole",
]
LambdaFullAccess_policy_list = [
    "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
    "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
    "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole",
    "arn:aws:iam::aws:policy/AWSLambdaExecute",
    "arn:aws:iam::aws:policy/AmazonECS_FullAccess",
    "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/AmazonSQSFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchFullAccess"
]


def setup():
    # Create ECS Instance Role
    assume_role_policy_document = json.dumps(
        {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )
    try:
        iam.create_role(
            RoleName="ecsInstanceRole",
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
        for arn in ecsInstanceRole_policy_list:
            iam.attach_role_policy(
                PolicyArn=arn,
                RoleName="ecsInstanceRole",
            )
        print ('Created ecsInstanceRole.')
    except iam.exceptions.EntityAlreadyExistsException:
        print ('Skipping creation of ecsInstanceRole. Already exists.')


    # Create EC2 Spot Fleet Tagging Role
    assume_role_policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"Service": "spotfleet.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )
    try:
        iam.create_role(
            RoleName="aws-ec2-spot-fleet-tagging-role",
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
        iam.attach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
            RoleName="aws-ec2-spot-fleet-tagging-role",
        )
        print ('Created aws-ec2-spot-fleet-tagging-role.')
    except iam.exceptions.EntityAlreadyExistsException:
        print ('Skipping creation of aws-ec2-spot-fleet-tagging-role. Already exists.')

    # Create Lambda Full Access Role
    assume_role_policy_document = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )
    try:
        iam.create_role(
            RoleName="LambdaFullAccess",
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
        for arn in LambdaFullAccess_policy_list:
            iam.attach_role_policy(
                PolicyArn=arn,
                RoleName="LambdaFullAccess",
            )
        print ('Created LambdaFullAccess role.')
    except iam.exceptions.EntityAlreadyExistsException:
        print ('Skipping creation of LambdaFullAccess role. Already exists.')
 
    # Create SNS Monitor topic
    MonitorTopic = sns.create_topic(Name="Monitor")
    print ('(Re-)Created Monitor SNS Topic.')

    # Create Monitor Lambda function
    LambdaFullAccess = iam.get_role(RoleName="LambdaFullAccess")

    fxn = open("lambda_function.zip", "rb").read()
    try:
        MonitorFunction = lmbda.create_function(
            FunctionName="Monitor",
            Runtime="python3.9",
            Role=LambdaFullAccess["Role"]["Arn"],
            Handler="lambda_function.lambda_handler",
            Code={
                "ZipFile": fxn,
            },
            Description="Auto-monitor DS runs",
            Timeout=900,
            MemorySize=3008,
            Publish=True,
            PackageType="Zip",
            TracingConfig={"Mode": "PassThrough"},
            Architectures=["x86_64"],
            EphemeralStorage={"Size": 512}
        )
        # Subscribe Monitor Lambda to Monitor Topic
        sns.subscribe(
            TopicArn=MonitorTopic["TopicArn"],
            Protocol="lambda",
            Endpoint=MonitorFunction["FunctionArn"],
        )
        print ('Created Monitor Lambda Function.')
    except lmbda.exceptions.ResourceConflictException:
        print ('Skipping creation of Monitor Lambda Function. Already exists.')
    try:
        lmbda.add_permission(
            FunctionName='Monitor',
            StatementId='InvokeBySNS',
            Action='lambda:InvokeFunction',
            Principal='sns.amazonaws.com')
    except lmbda.exceptions.ResourceConflictException:
        print ('Monitor Lambda Function already has SNS invoke permission.')

def destroy():
    # Delete roles
    for arn in ecsInstanceRole_policy_list:
        iam.detach_role_policy(RoleName="ecsInstanceRole", PolicyArn=arn)
    iam.delete_role(RoleName="ecsInstanceRole")

    iam.detach_role_policy(
        RoleName="aws-ec2-spot-fleet-tagging-role",
        PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole",
    )
    iam.delete_role(RoleName="aws-ec2-spot-fleet-tagging-role")

    for arn in LambdaFullAccess_policy_list:
        iam.detach_role_policy(RoleName="LambdaFullAccess", PolicyArn=arn)
    iam.delete_role(RoleName="LambdaFullAccess")

    # Delete Monitor Lambda function
    lmbda.delete_function(FunctionName="Monitor")

    # Delete Monitor SNS topic
    # create_topic is idempotent so we use it to return ARN since topic already exists
    MonitorTopic = sns.create_topic(Name="Monitor")
    sns.delete_topic(TopicArn=MonitorTopic["TopicArn"])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        setup()
    else:
        if sys.argv[1] == "destroy":
            destroy()
        else:
            print("Use: setup_AWS.py or setup_AWS.py destroy")
            sys.exit()
