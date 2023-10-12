// we use express and multer libraries to send images
import express from 'express'
import multer from 'multer';
import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import {
  S3Client,
  PutObjectCommand,
} from "@aws-sdk/client-s3";
import { SQSClient, SendMessageCommand, GetQueueUrlCommand, ReceiveMessageCommand, DeleteMessageCommand, DeleteMessageBatchCommand } from "@aws-sdk/client-sqs";
import 'dotenv/config';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const server = express();
const PORT = 3000;

// uploaded images are saved in the folder "/upload_images"
const upload = multer({dest: __dirname + '/upload_images'});

server.use(express.static('public'));

server.get('/', (request, response) => {
  console.log(process.env);
  response.end('hello from aws');
})

// "myfile" is the key of the http payload
server.post('/', upload.single('myfile'), async function(request, respond) {
  if(request.file) console.log(request.file);
  
  // save the image
  // fs.rename(__dirname + '/upload_images/' + request.file.filename, __dirname + '/upload_images/' + request.file.originalname, function(err) {
  //   if ( err ) console.log('ERROR: ' + err);
  // });

  // A region and credentials can be declared explicitly. For example
  // `new S3Client({ region: 'us-east-1', credentials: {...} })` would
  //initialize the client with those settings. However, the SDK will
  // use your local configuration and credentials if those properties
  // are not defined here.
  const clientConfig = { 
    region: process.env.REGION_NAME,
    credentials: {
      "accessKeyId": process.env.AWS_ACCESS_KEY,
      "secretAccessKey": process.env.AWS_SECRET_KEY,
    },
  }
  const s3Client = new S3Client(clientConfig);
  const sqsClient = new SQSClient(clientConfig);


  // Put an object into an Amazon S3 bucket.
  console.log(request.file.path)
  await s3Client.send(
    new PutObjectCommand({
      Bucket: process.env.INPUT_BUCKET_NAME,
      Key: request.file.originalname,
      Body: fs.readFileSync(request.file.path)
    })
  );

  const requestQueueUrlOutput = await sqsClient.send(
    new GetQueueUrlCommand({
      QueueName: process.env.REQUEST_QUEUE_NAME
    })
  )
  const requestQueueUrl = requestQueueUrlOutput.QueueUrl;

  const responseQueueUrlOutput = await sqsClient.send(
    new GetQueueUrlCommand({
      QueueName: process.env.RESPONSE_QUEUE_NAME
    })
  )
  const responseQueueUrl = responseQueueUrlOutput.QueueUrl;
  
  // Send messafe to request queue
  await sqsClient.send(
    new SendMessageCommand({
      QueueUrl: requestQueueUrl,
      MessageBody: JSON.stringify({
          'bucket': process.env.INPUT_BUCKET_NAME,
          'key': request.file.originalname,
          'responseQueueUrl': responseQueueUrl,
      }),
    })
  )

  const getResponseMessage = async (QueueUrl) => {
    while(true){
      const response = await sqsClient.send(
        new ReceiveMessageCommand({ QueueUrl, MaxNumberOfMessages: 1})
      );
      if(!response){
        continue;
      }
      const messages = response.Messages;
      if(messages && messages.length > 0){
        return messages[0];
      }
    }
  }

  console.log('awaiting reponse message');
  const message = await getResponseMessage(responseQueueUrl);
  const {ReceiptHandle, MessageId} = message;
  const body = JSON.parse(message.Body);
  const result = body.classification;

  await sqsClient.send(
    new DeleteMessageBatchCommand({
      QueueUrl: queueUrl,
      Entries: [{
        Id: MessageId,
        ReceiptHandle: ReceiptHandle,
      }],
    }),
  ) 
  
  respond.setHeader('Content-Type', 'text/html');
  respond.end(result);
});

// You need to configure node.js to listen on 0.0.0.0 so it will be able to accept connections on all the IPs of your machine
const hostname = '0.0.0.0';
server.listen(PORT, hostname, () => {
    console.log(`Server running at http://${hostname}:${PORT}/`);
    // console.log(process.env);
  });
