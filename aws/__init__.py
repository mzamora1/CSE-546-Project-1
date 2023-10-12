from decouple import config
import logging
import boto3
from botocore.exceptions import ClientError
import os

DEBUG = os.getenv('DEBUG') is not None
AWS_ACCESS_KEY = config('AWS_ACCESS_KEY')
AWS_ACCOUNT_ID = config('AWS_ACCOUNT_ID')
AWS_SECRET_KEY = config('AWS_SECRET_KEY')
REGION_NAME = config('REGION_NAME')
INPUT_BUCKET_NAME = config('INPUT_BUCKET_NAME')
OUTPUT_BUCKET_NAME = config('OUTPUT_BUCKET_NAME')
REQUEST_QUEUE_NAME = config('REQUEST_QUEUE_NAME')
RESPONSE_QUEUE_NAME = config('RESPONSE_QUEUE_NAME')
INSTANCE_TYPE = config('INSTANCE_TYPE')
APP_TIER_AMI_ID = config('APP_TIER_AMI_ID')
WEB_TIER_AMI_ID = config('WEB_TIER_AMI_ID')
IMAGE_CLASSIFICATION_PATH = config('IMAGE_CLASSIFICATION_PATH')
LABELS_PATH = config('LABELS_PATH')
KEY_NAME = config('KEY_NAME')
AUTOSCALING_GROUP_NAME = 'autoscale-app-tier'
LAUNCH_TEMPLATE_NAME_APP_TIER = 'launch-image-processor'
LAUNCH_TEMPLATE_NAME_WEB_TIER = 'Launch-Web-Tier'


boto3.setup_default_session(aws_access_key_id=AWS_ACCESS_KEY,
                            aws_secret_access_key=AWS_SECRET_KEY,
                            region_name=REGION_NAME)

ec2 = boto3.client('ec2')
sqs = boto3.client('sqs')
s3 = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')
autoscaling = boto3.client('autoscaling')


def upload_file(file, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file: File to upload (path or file like object with read() -> bytes)
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then `file` filename is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(
            file if isinstance(file, str) else file.name)

    # Upload the file
    try:
        if isinstance(file, str):
            s3.upload_file(file, bucket, object_name)
        else:
            s3.upload_fileobj(file, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True
