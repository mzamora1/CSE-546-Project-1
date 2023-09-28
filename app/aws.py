import boto3
import boto3
from decouple import config

ec2 = boto3.resource('ec2',
                     region_name='REGION',
                     aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                     aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'))

sqs = boto3.client('sqs',
                   region_name='us-east-1',
                   aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                   aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'))
