# Combined script for AWS resource setup and app tier execution

# Required imports
import boto3
import subprocess
import json
from decouple import config

# Constants for AWS setup

# Extracting constants from .env file
AWS_ACCESS_KEY = config('AWS_ACCESS_KEY')
AWS_SECRET_KEY = config('AWS_SECRET_KEY')
REGION_NAME = config('REGION_NAME')
INPUT_BUCKET_NAME = config('INPUT_BUCKET_NAME')
OUTPUT_BUCKET_NAME = config('OUTPUT_BUCKET_NAME')
QUEUE_NAME = config('QUEUE_NAME')
INSTANCE_TYPE = config('INSTANCE_TYPE')
AMI_ID = config('AMI_ID')
IMAGE_CLASSIFICATION_PATH = config('IMAGE_CLASSIFICATION_PATH')
LABELS_PATH = config('LABELS_PATH')

# Initialize boto3 clients
boto3.setup_default_session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=REGION_NAME)
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
ec2_client = boto3.client('ec2')
cloudwatch_client = boto3.client('cloudwatch')

# Load ImageNet labels
with open(LABELS_PATH, 'r') as f:
    labels = json.load(f)

# Function to process an image
def process_image(file_name):
    output = subprocess.run(["python3", IMAGE_CLASSIFICATION_PATH, file_name], capture_output=True)
    prediction_index = int(output.stdout.decode().strip())
    return labels[prediction_index]

# App Tier function
def app_tier_handler():
    while True:
        messages = sqs_client.receive_message(QueueUrl=QUEUE_NAME, MaxNumberOfMessages=10)
        if 'Messages' in messages:
            for message in messages['Messages']:
                image_key = message['Body']
                s3_client.download_file(INPUT_BUCKET_NAME, image_key, image_key)
                result = process_image(image_key)
                output_key = image_key.split('.')[0]
                s3_client.put_object(Bucket=OUTPUT_BUCKET_NAME, Key=output_key, Body=f"{output_key}, {result}")
                sqs_client.delete_message(QueueUrl=QUEUE_NAME, ReceiptHandle=message['ReceiptHandle'])

# CloudWatch setup function
def setup_cloudwatch_for_sqs(sqs_queue_arn, threshold):
    alarm_name = f"Alarm_{QUEUE_NAME}_Depth"
    metric_name = 'ApproximateNumberOfMessagesVisible'
    namespace = 'AWS/SQS'
    statistic = 'Average'  
    period = 300  
    evaluation_periods = 1  
    response = cloudwatch_client.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=f'Alarm when {QUEUE_NAME} depth exceeds {threshold}',
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:autoscaling:<region>:<account-id>:scalingPolicy:<policy-id>:autoScalingGroupName/<group-name>:policyName/<policy-name>'
        ],
        MetricName=metric_name,
        Namespace=namespace,
        Statistic=statistic,
        Dimensions=[{'Name': 'QueueName', 'Value': QUEUE_NAME}],
        Period=period,
        EvaluationPeriods=evaluation_periods,
        Threshold=threshold,
        ComparisonOperator='GreaterThanThreshold',
        TreatMissingData='breaching'
    )
    return response

# AWS resource setup and initiation
def setup_aws_resources():
    # Create S3 buckets
    s3_client.create_bucket(Bucket=INPUT_BUCKET_NAME)
    s3_client.create_bucket(Bucket=OUTPUT_BUCKET_NAME)
    
    # Create SQS queue
    queue_response = sqs_client.create_queue(QueueName=QUEUE_NAME)
    
    # Launch EC2 instance
    ec2_response = ec2_client.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        KeyName="your-key-pair-name"
    )
    
    # Return created resources' details
    input_bucket_location = s3_client.get_bucket_location(Bucket=INPUT_BUCKET_NAME)['LocationConstraint']
    output_bucket_location = s3_client.get_bucket_location(Bucket=OUTPUT_BUCKET_NAME)['LocationConstraint']
    queue_url = queue_response['QueueUrl']
    instance_id = ec2_response['Instances'][0]['InstanceId']
    return input_bucket_location, output_bucket_location, queue_url, instance_id

# Main execution
if __name__ == "__main__":
    input_loc, output_loc, sqs_url, ec2_id = setup_aws_resources()
    # If you want to print or log these values, you can do so here
    # print(input_loc, output_loc, sqs_url, ec2_id)
    
    # Set up CloudWatch monitoring
    sqs_queue_arn = sqs_client.get_queue_attributes(QueueUrl=sqs_url, AttributeNames=['QueueArn'])['Attributes']['QueueArn']
    setup_cloudwatch_for_sqs(sqs_queue_arn, threshold=20)
    
    # Start the app tier handler
    app_tier_handler()
