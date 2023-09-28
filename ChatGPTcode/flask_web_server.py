from flask_web_server import Flask, request, jsonify
import boto3

app = Flask(__name__)

# Initialize SQS client
sqs_client = boto3.client('sqs')
QUEUE_URL = 'YOUR_SQS_QUEUE_URL'

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "Image not provided"}), 400

    image = request.files['image']
    
    # Here, you might want to save the image to an S3 bucket or another storage medium
    # For the sake of simplicity, we'll assume you get an image_key (e.g., filename) that you'll place in SQS

    image_key = image.filename
    image.save(image_key)  # Save locally for the time being
    
    # Send a message to SQS with the image key
    sqs_client.send_message(QueueUrl=QUEUE_URL, MessageBody=image_key)

    return jsonify({"success": True}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
