import boto3
import aws


def launch_web_tier():
    """
        web-tier EC2 instance forwards user input to sqs queue
    """
    ec2_instance = aws.ec2.run_instances(
        # ImageId=aws.WEB_TIER_AMI_ID,
        # InstanceType=aws.INSTANCE_TYPE,
        # KeyName=aws.KEY_NAME,
        MinCount=1,
        MaxCount=1,
        LaunchTemplate={
            'LaunchTemplateName': aws.LAUNCH_TEMPLATE_NAME_WEB_TIER
        },
        # TagSpecifications=[{'ResourceType': 'instance',
        #                     'Tags': [
        #                         {
        #                             'Key': 'Name',
        #                             'Value': 'App Tier Worker'
        #                         }
        #                     ]}],
        Monitoring={'Enabled': False}
    )
    return ec2_instance


def launch_sqs():
    """
        Request messages get processed by image processors (AMI: ami-09c6ef0459a2ff40e)
        then result it sent through response queue
    """
    request_queue = aws.sqs.create_queue(QueueName=aws.REQUEST_QUEUE_NAME)
    response_queue = aws.sqs.create_queue(QueueName=aws.RESPONSE_QUEUE_NAME)
    return {
        'request': request_queue,
        'response': response_queue
    }


def create_app_tier_launch_template():
    """
        Creates template for lauching image processor EC2 instances
    """
    try:
        template = aws.ec2.create_launch_template(
            DryRun=aws.DEBUG,
            LaunchTemplateName=aws.LAUNCH_TEMPLATE_NAME_APP_TIER,
            VersionDescription='launch image processor',
            LaunchTemplateData={
                'ImageId': aws.APP_TIER_AMI_ID,
                'InstanceType': aws.INSTANCE_TYPE,
                'KeyName': aws.KEY_NAME,
            }
        )
        return template
    except Exception as e:
        print(repr(e))


def launch_autoscaling():
    """
        Auto scales image processors linearly based on SQS queue size
        Image Processor Instances: 1 1 2 3 4 5...20
        Queue Size               : 0 1 2 3 4 5...20           
        https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-target-tracking-metric-math.html
    """
    try:
        aws.autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=aws.AUTOSCALING_GROUP_NAME,
            LaunchTemplate={
                'LaunchTemplateName': aws.LAUNCH_TEMPLATE_NAME_APP_TIER,
                'Version': '$Latest'
            },
            MinSize=1,
            MaxSize=20,
            AvailabilityZones=[
                aws.REGION_NAME + 'a',
                aws.REGION_NAME + 'b',
                aws.REGION_NAME + 'c',
                aws.REGION_NAME + 'd',
                aws.REGION_NAME + 'e',
            ],
        )
    except Exception as e:
        print(repr(e))
        return
    policy_arn = aws.autoscaling.put_scaling_policy(
        AutoScalingGroupName=aws.AUTOSCALING_GROUP_NAME,
        PolicyName='sqs-size-scaling-policy',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            "CustomizedMetricSpecification": {
                "Metrics": [
                    {
                        "Label": "Get the queue size (the number of messages waiting to be processed)",
                        "Id": "m1",
                        "MetricStat": {
                            "Metric": {
                                "MetricName": "ApproximateNumberOfMessagesVisible",
                                "Namespace": "AWS/SQS",
                                "Dimensions": [
                                    {
                                        "Name": "QueueName",
                                        "Value": aws.REQUEST_QUEUE_NAME
                                    }
                                ]
                            },
                            "Stat": "Sum"
                        },
                        "ReturnData": False
                    },
                    {
                        "Label": "Get the group size (the number of InService instances)",
                        "Id": "m2",
                        "MetricStat": {
                            "Metric": {
                                "MetricName": "GroupInServiceInstances",
                                "Namespace": "AWS/AutoScaling",
                                "Dimensions": [
                                    {
                                        "Name": "AutoScalingGroupName",
                                        "Value": aws.AUTOSCALING_GROUP_NAME
                                    }
                                ]
                            },
                            "Stat": "Average"
                        },
                        "ReturnData": False
                    },
                    {
                        "Label": "Calculate the backlog per instance",
                        "Id": "e1",
                        "Expression": "m1 / m2",
                        "ReturnData": True
                    }
                ]
            },
            "TargetValue": 1
        }
    )
    return policy_arn


def launch_app_tier():
    create_app_tier_launch_template()
    launch_autoscaling()


def launch_s3():
    location = {'LocationConstraint': aws.REGION_NAME}
    print(location)
    myS3 = boto3.resource('s3')
    try:
        myS3.create_bucket(
            Bucket=aws.INPUT_BUCKET_NAME,
            # CreateBucketConfiguration=location
        )
        # aws.s3.create_bucket(Bucket=aws.INPUT_BUCKET_NAME)
    except Exception as e:
        print(repr(e))
    try:
        myS3.create_bucket(
            Bucket=aws.OUTPUT_BUCKET_NAME,
            CreateBucketConfiguration=location
        )
        # aws.s3.create_bucket(Bucket=aws.OUTPUT_BUCKET_NAME,
        #                      CreateBucketConfiguration=location)
    except Exception as e:
        print(repr(e))
    # aws.s3.create_bucket(Bucket=aws.OUTPUT_BUCKET_NAME,
    #                      CreateBucketConfiguration=location)


def launch_data_tier():
    launch_s3()


def launch():
    launch_web_tier()
    launch_sqs()
    launch_app_tier()
    launch_data_tier()


if __name__ == '__main__':
    launch()
