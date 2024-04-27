import boto3
import cv2
import numpy as np

# Create SQS client
sqs = boto3.client('sqs', region_name='eu-north-1')
s3 = boto3.client('s3', region_name='eu-north-1')
queue_url = 'https://sqs.eu-north-1.amazonaws.com/992382542532/image-processing-s3-to-ec2-queue'


def process_image(image, op):
    nparr = np.frombuffer(image, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if op == 'blur':
        return cv2.blur(img_np, (10, 10))
    elif op == 'cvtgrayscale':
        return cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    elif op == 'dilate':
        gray_image = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((5, 5), np.uint8)  # You can adjust the kernel size as needed
        return cv2.dilate(gray_image, kernel, iterations=1)
    elif op == 'erode':
        gray_image = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((5, 5), np.uint8)  # You can adjust the kernel size as needed
        return cv2.erode(gray_image, kernel, iterations=1)
    else:
        return img_np


# Receive message from SQS queue
while True:
    print('waiting for messages ...')
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,  # Max number of messages to receive
        WaitTimeSeconds=20  # Long polling
    )
    # print(response)
    if 'Messages' in response:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']

        # Delete received message from queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        print('Received and deleted message from SQS: %s' % message)
        # get the bucket name and key from the message
        l = message['Body'].split(' ')
        print(l)
        bucket = l[0]
        key = l[2]
        # get the object from the s3 bucket
        s3_response = s3.get_object(Bucket=bucket, Key=key)
        image_data = s3_response['Body'].read()
        operation = s3_response['Metadata']['operation']
        print('operation is ' + operation)
        processed_image = process_image(image_data, operation)
        _, processed_img_bytes = cv2.imencode('.jpg', processed_image)
        processed_img_bytes = processed_img_bytes.tobytes()
        print('storing the result to test-n-final-bucket')
        response = s3.put_object(
            Bucket='test-n-final-bucket',
            Key=key,
            Body=processed_img_bytes,
            ContentType='image/jpg',  # Adjust content type if needed
            Metadata={
                'operation': operation
            }
        )
    else:
        print("No messages received.")
