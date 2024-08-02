# Troubleshooting startCluster

If you are having problems at [Step 3 (Start Cluster)](step_3_start_cluster.md) in your Distributed-CellProfiler runs, you may find the following troubleshooting information helpful.

## IamFleetRole

If there is a problem with the `IamFleetRole` in your Fleet File, you may get the following error:

```bash
botocore.exceptions.ClientError: An error occurred (InvalidSpotFleetRequestConfig) when calling the RequestSpotFleet operation: Parameter: SpotFleetRequestConfig.IamFleetRole is invalid.
```

## IamInstanceProfile

If there is a problem with the `IamInstanceProfile` in your Fleet File, you may get the following error:

```bash
Your spot fleet request is causing an error and is now being cancelled.  Please check your configuration and try again
spotFleetRequestConfigurationInvalid : c5.xlarge, ami-0f161e6034a6262d8, Linux/UNIX: Value
```

- Check your FleetFile.json.
Confirm that in the `IamInstanceProfile` the `Arn` is an **instance-profile** NOT a **role** (e.g. `"arn:aws:iam::012345678901:instance-profile/ecsInstanceRole"`).
This is different from the `IamFleetRole` at the top of the FleetFile.json that is a **role**.
- Confirm that your ecsInstanceRole was created correctly.
If you created resources manually, using either the CLI or the console, you may have missed part of the `IamInstanceProfile` creation.
In your command line, run `aws iam list-instance-profiles-for-role --role-name ecsInstanceRole`.
If it returns `{"InstanceProfiles": []}`, then run the following commands:

```bash
aws iam create-instance-profile --instance-profile-name ecsInstanceRole

aws iam add-role-to-instance-profile --role-name ecsInstanceRole --instance-profile-name ecsInstanceRole
```

## SubnetId

If there is a problem with the `SubnetId` in your Fleet File, you may get the following error:

```bash
botocore.exceptions.ClientError: An error occurred (InvalidSpotFleetRequestConfig) when calling the RequestSpotFleet operation: One of the provided subnets was not valid.
```

## Groups

If there is a problem with the `Groups` in your Fleet File, you may get the following error:

```bash
Your spot fleet request is causing an error and is now being cancelled.  Please check your configuration and try again
spotFleetRequestConfigurationInvalid : c5.xlarge, ami-0f161e6034a6262d8, Linux/UNIX: The security group 'sg-01234567890123451atest' does not exist in VPC 'vpc-0123456789012345'
```
