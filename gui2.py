import shutil
import webbrowser

import boto3
import time
import hashlib
import threading
import logging
import os
import uuid
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

from flask import Flask, render_template, request, redirect, url_for, current_app


# Configure logging
logging.basicConfig(filename='system_logs.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sqs = boto3.client('sqs', region_name='eu-north-1')
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2', region_name='eu-north-1')

app = Flask(__name__)


def check_object_exists(bucket_name, object_key):
    # Create a session using your credentials or rely on default session

    try:
        # Try to get the object metadata
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        print(f"Object '{object_key}' exists in bucket '{bucket_name}'.")
        return True
    except ClientError as e:
        # If a client error is raised, the object does not exist
        if e.response['Error']['Code'] == '404':
            # print(f"Object '{object_key}' does not exist in bucket '{bucket_name}'.")
            return False
        else:
            print('other errors')
            # For other errors, raise the exception
            return False
    except (NoCredentialsError, PartialCredentialsError):
        print("Credentials not available or incomplete.")
        return False


def generate_key():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
    print('MAC is ' + mac)
    current_time = str(time.time()).encode('utf-8')
    hash_object = hashlib.md5()
    hash_object.update(mac.encode('utf-8'))
    hash_object.update(current_time)
    key = hash_object.hexdigest()
    return key


# def check_result(key, event):
#     queue_url = 'https://sqs.eu-north-1.amazonaws.com/992382542532/results-queue'
#     while True:
#         response = sqs.receive_message(
#             QueueUrl=queue_url,
#             MaxNumberOfMessages=1,  # Max number of messages to receive
#             WaitTimeSeconds=5  # Long polling
#         )
#         logging.info('waiting for the image')
#         if 'Messages' in response:
#             message = response['Messages'][0]
#             receipt_handle = message['ReceiptHandle']
#             logging.info('message body is ' + message['Body'] + 'and key is ' + key)
#             if message['Body'] != key:
#                 # it's not the message you are waiting for so sleep to allow others to get the message
#                 # time.sleep(2)
#                 continue
#             s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
#             image_name = str(key) + '.jpg'
#             current_directory = os.getcwd()
#             source_path = os.path.join(current_directory, image_name)
#             destination_path = "C:\\Users\moisi\Desktop\Semester 8\CSE354 Distributed Computing\Project\CODE\Phase_3\static\\"
#             shutil.move(source_path, destination_path)
#             event.set()  # Set the event indicating thread has finished
#             sqs.delete_message(
#                 QueueUrl=queue_url,
#                 ReceiptHandle=receipt_handle
#             )
#
#             s3_client.delete_object(
#                 Bucket='test-n-final-bucket',
#                 Key=key,
#             )
#             print('we got your image')
#             # Get the current working directory
#
#         else:
#             logging.info('waiting for the image')

def check_result(key, event):
    start_time = time.time()
    while True:
        if check_object_exists('test-n-final-bucket', key):
            s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
            image_name = str(key) + '.jpg'
            current_directory = os.getcwd()
            source_path = os.path.join(current_directory, image_name)
            destination_path = "C:\\Users\moisi\Desktop\Semester 8\CSE354 Distributed Computing\Project\CODE\Phase_3\static\\"
            shutil.move(source_path, destination_path)
            event.set()  # Set the event indicating thread has finished
            end_time = time.time()
            # Record the end time
            s3_client.delete_object(
                Bucket='test-n-final-bucket',
                Key=key,
            )
            print('got the object from the bucket directly in ', end_time - start_time)
            break


# Define your photo processing function
def process_photo(file, op):
    # Your photo processing logic here
    # For example, you can just print the filename for now
    print(op)
    image_key = generate_key()
    s3_client.put_object(
        Bucket='kmna-juju-bucket',
        Key=image_key,
        Body=file,
        ContentType='image/jpg',  # Adjust content type if needed
        Metadata={
            'operation': op
        }
    )

    # Create an event to signal when the thread finishes
    event = threading.Event()

    thread = threading.Thread(target=check_result, args=(image_key, event))
    thread.start()

    # Wait for the event (thread) to finish
    event.wait()

    return image_key + '.jpg'
    # Return image key to check_result thread


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the POST request has the file part
        if 'file' not in request.files:
            return render_template('index3.html', message='No file part')

        files = request.files.getlist('file')
        for file in files:
            # If the user does not select a file, the browser submits an empty file without a filename
            if file.filename == '':
                return render_template('index3.html', message='No selected file')

            # If the file exists and is allowed, process it
            if file:
                destination_path = r"C:\Users\moisi\Desktop\Semester 8\CSE354 Distributed Computing\Project\CODE\Phase_3\static"
                filename = file.filename
                file_path = os.path.join(destination_path, filename)
                file.save(file_path)
                with open(destination_path + '\\' + filename, 'rb') as f:
                    image_data = f.read()
                file_size = len(image_data)
                print(file_size)
                option = request.form['options']  # Get selected option from dropdown

                processed_path = process_photo(image_data, option)
                print(processed_path)

                #print("Absolute File Path:", absolute_file_path)
                ##return webbrowser.open_new_tab('http://127.0.0.1:3000/result/' + filename + '/' + processed_path)
                ##return redirect(url_for('success', filename=filename, processed_path=processed_path))

    return render_template('index3.html')


@app.route('/result/<filename>/<processed_path>')
def success(filename, processed_path):
    return render_template('result.html', filename=filename, processed_path=processed_path)


def get_ec2_info(ec2_client):
    response = ec2_client.describe_instances()
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_info = {
                'Instance ID': instance['InstanceId'],
                'Type': instance['InstanceType'],
                'State': instance['State']['Name'],
                'Public IP': instance.get('PublicIpAddress', 'N/A')
                # Add more fields as needed
            }
            instances.append(instance_info)
    print(instances)
    return instances


@app.route('/backend')
def backend():
    data = get_ec2_info(ec2_client)
    return render_template('backend.html', data=data)


if __name__ == '__main__':
    app.run(debug=True, port=3000)
