"""This is the entry point for gunicron with `docker compose up`"""
from flask import Flask, request
import aws
import json

app = Flask(__name__)


@app.route("/")
def index():
    message = f"""Hello from Flask"""
    return message


@app.route("/classify", methods=["POST"])
def classify():
    imageFile = request.form.get("myFile")
    fileName = request.form.get('filename')
    if not aws.upload_file(imageFile, aws.INPUT_BUCKET_NAME, fileName):
        return f'Could not upload file to bucket {aws.INPUT_BUCKET_NAME}', 500

    request_queue = aws.sqs.get_queue_url(
        QueueName=aws.REQUEST_QUEUE_NAME)['QueueUrl']
    request_queue_url = request_queue

    response_queue = aws.sqs.get_queue_url(
        QueueName=aws.RESPONSE_QUEUE_NAME)['QueueUrl']
    response_queue_url = response_queue

    queue_request = aws.sqs.send_message(
        QueueUrl=request_queue_url,
        MessageBody=json.dumps({
            'bucket': aws.INPUT_BUCKET_NAME,
            'key': fileName,
            'responseQueueUrl': response_queue_url
        }),
    )

    # receive_message returns empty list after timeout, wait till list is populated
    while True:
        response = aws.sqs.receive_message(
            QueueUrl=response_queue_url, MaxNumberOfMessages=1)
        messages = response['Messages']
        if len(messages) > 0:
            break

    body = json.loads(messages[0]['Body'])
    result = body['classification']
    return result
