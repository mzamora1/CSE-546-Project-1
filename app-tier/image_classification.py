# import torch
# import torchvision
# import torchvision.transforms as transforms
# import torch.nn as nn
# import torch.nn.functional as F
# import torchvision.models as models
# from urllib.request import urlopen
# from PIL import Image
# import numpy as np
# import json
# import sys
# import time

# url = str(sys.argv[1])
# #img = Image.open(urlopen(url))
# img = Image.open(url)

# model = models.resnet18(pretrained=True)

# model.eval()
# img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
# outputs = model(img_tensor)
# _, predicted = torch.max(outputs.data, 1)

# with open('./imagenet-labels.json') as f:
#     labels = json.load(f)
# result = labels[np.array(predicted)[0]]
# img_name = url.split("/")[-1]
# #save_name = f"({img_name}, {result})"
# save_name = f"{img_name},{result}"
# print(f"{save_name}")


import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
from urllib.request import urlopen
from PIL import Image
import numpy as np
import json
import aws
from io import BytesIO
import tempfile

request_queue_url = aws.sqs.get_queue_url(
    QueueName=aws.REQUEST_QUEUE_NAME)['QueueUrl']


def process_message():
    """
        Takes message from request queue, processes it, and inserts into response queue
    """
    while True:
        request = aws.sqs.receive_message(
            QueueUrl=request_queue_url, MaxNumberOfMessages=1)
        if 'Messages' not in request:
            continue
        messages = request['Messages']
        if len(messages) > 0:
            break
    body = json.loads(messages[0]['Body'])
    image_name = body['key']
    receiptHandle = messages[0]['ReceiptHandle']

    print(messages)
    # print(aws.s3.list_objects(Bucket=body['bucket']))
    # with BytesIO() as image_file:
    with tempfile.TemporaryFile(suffix='jpeg') as image_file:
        aws.s3.download_fileobj(body['bucket'], image_name, image_file)
        # obj = aws.s3.get_object(Bucket=body['bucket'], Key=body['key'])
        # print(obj['Body'].read())
        img = Image.open(image_file)

        model = models.resnet18(pretrained=True)

        model.eval()
        img_tensor = transforms.ToTensor()(img).unsqueeze_(0)
    outputs = model(img_tensor)
    _, predicted = torch.max(outputs.data, 1)

    with open('./imagenet-labels.json') as f:
        labels = json.load(f)
    result = labels[np.array(predicted)[0]]

    save_name = f"{image_name},{result}".encode()
    print(f"{save_name}")

    print(aws.OUTPUT_BUCKET_NAME)

    from pathlib import Path

    filename = Path(image_name).stem
    print(filename)

    with BytesIO(bytes(save_name)) as f:
        aws.upload_file(f, aws.OUTPUT_BUCKET_NAME, filename)

    aws.sqs.delete_message(
        QueueUrl=request_queue_url,
        ReceiptHandle=receiptHandle
    )

    aws.sqs.send_message(
        QueueUrl=body['responseQueueUrl'],
        MessageBody=json.dumps({
            'classification': result
        }),
    )

    return result


def main():
    while True:
        process_message()


if __name__ == '__main__':
    main()
