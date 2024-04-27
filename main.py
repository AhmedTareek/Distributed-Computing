import boto3
import uuid
import time
import hashlib

import threading

sqs = boto3.client('sqs', region_name='eu-north-1')
s3_client = boto3.client('s3')


def generate_key():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
    print('MAC is ' + mac)
    current_time = str(time.time()).encode('utf-8')
    hash_object = hashlib.md5()
    hash_object.update(mac.encode('utf-8'))
    hash_object.update(current_time)
    key = hash_object.hexdigest()
    return key


def check_result(key):
    queue_url = 'https://sqs.eu-north-1.amazonaws.com/992382542532/results-queue'
    while True:
        print('waiting for the image')
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,  # Max number of messages to receive
            WaitTimeSeconds=20  # Long polling
        )
        if 'Messages' in response:
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']
            print('message body is ' + message['Body'] + 'and key is ' + key)
            if message['Body'] != key:
                # it's not the message you are waiting for so sleep to allow others to get the message
                time.sleep(2)
                continue
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
            s3_client.delete_object(
                Bucket='test-n-final-bucket',
                Key=key,
            )
            print('we got your image')
            break
        else:
            print('waiting for the image')


# main thread
while True:
    image_path = input('Enter the image path or :q if you wish to exit')
    if image_path == ':q':
        break
    operation = input('Choose a number Operation to do 1-Blur \n2-Convert to Grayscale \n3-Dilate \n4-Erode')

    if operation == '1':
        op = 'blur'
    elif operation == '2':
        op = 'cvtgrayscale'
    elif operation == '3':
        op = 'dilate'
    elif operation == '4':
        op = 'erode'
    else:
        op = ''

    with open(image_path, 'rb') as f:
        image_data = f.read()

    image_key = generate_key()
    response = s3_client.put_object(
        Bucket='kmna-juju-bucket',
        Key=image_key,
        Body=image_data,
        ContentType='image/jpg',  # Adjust content type if needed
        Metadata={
            'operation': op
        }
    )

    thread = threading.Thread(target=check_result, args=(image_key,))
    thread.start()
