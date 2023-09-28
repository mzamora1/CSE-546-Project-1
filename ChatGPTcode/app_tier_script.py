# Consolidated Python script for the app tier based on the provided files

import boto3
import subprocess
import json

# Constants (fill these in with your specific details)
AWS_ACCESS_KEY = 'YOUR_ACCESS_KEY'
AWS_SECRET_KEY = 'YOUR_SECRET_KEY'
REGION_NAME = 'us-east-1'
QUEUE_NAME = "Your_SQS_Queue_Name"
INPUT_BUCKET = "Your_Input_S3_Bucket"
OUTPUT_BUCKET = "Your_Output_S3_Bucket"
IMAGE_CLASSIFICATION_PATH = "/path/to/image_classification.py"  # Adjust this path
LABELS_PATH = "/mnt/data/imagenet-labels.json"  # Path to the JSON file with labels

# Initialize boto3 clients with provided credentials
boto3.setup_default_session(aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=REGION_NAME)
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')
cloudwatch_client = boto3.client('cloudwatch')

# Load ImageNet labels
with open(LABELS_PATH, 'r') as f:
    labels = json.load(f)


def process_image(file_name):
    """Process an image using the deep learning model and return the top prediction."""
    output = subprocess.run(["python3", IMAGE_CLASSIFICATION_PATH, file_name], capture_output=True)
    prediction_index = int(output.stdout.decode().strip())
    return labels[prediction_index]


def app_tier_handler():
    """App Tier function to process messages from SQS, run the model, and store results in S3."""
    while True:
        # Poll the SQS queue for messages
        messages = sqs_client.receive_message(QueueUrl=QUEUE_NAME, MaxNumberOfMessages=10)

        if 'Messages' in messages:
            for message in messages['Messages']:
                image_key = message['Body']

                # Download the image from the S3 input bucket
                s3_client.download_file(INPUT_BUCKET, image_key, image_key)

                # Process the image using the deep learning model
                result = process_image(image_key)

                # Upload the result to the S3 output bucket
                output_key = image_key.split('.')[0]
                s3_client.put_object(Bucket=OUTPUT_BUCKET, Key=output_key, Body=f"{output_key}, {result}")

                # Delete the processed message from the SQS queue
                sqs_client.delete_message(QueueUrl=QUEUE_NAME, ReceiptHandle=message['ReceiptHandle'])


def setup_cloudwatch_for_sqs(sqs_queue_arn, threshold):
    """Setup CloudWatch to monitor the depth of the SQS queue and create an alarm."""
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
            # ARN of the Auto Scaling Policy (fill this in)
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


if __name__ == "__main__":
    # Retrieve the ARN of the SQS queue
    sqs_queue_arn = sqs_client.get_queue_attributes(QueueUrl=QUEUE_NAME, AttributeNames=['QueueArn'])['Attributes']['QueueArn']
    
    # Set up CloudWatch monitoring for the SQS queue
    setup_cloudwatch_for_sqs(sqs_queue_arn, threshold=20)
    
    # Start the app tier handler
    app_tier_handler()

