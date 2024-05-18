import random
import threading

from flask import Flask, request, render_template, redirect, url_for
import os
from concurrent.futures import ThreadPoolExecutor
import boto3
import hashlib
import time
import shutil
import uuid
import asyncio
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

app = Flask(__name__)

# AWS S3 Client setup
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')

# Ensure the upload folder exists
UPLOAD_FOLDER = r"D:\UNI\sems\2024 spring\Distributed Computing\Project\static"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

paths_list = []


# Function to check if an object exists in S3
def check_object_exists(bucket_name, object_key):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        print(f"Object '{object_key}' exists in bucket '{bucket_name}'.")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print('Other errors')
            return False
    except (NoCredentialsError, PartialCredentialsError):
        print("Credentials not available or incomplete.")
        return False


# Function to generate a unique key
def generate_key():
    # Generate the MAC address
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
    print('MAC is ' + mac)

    # Get the current time
    current_time = str(time.time()).encode('utf-8')

    # Generate a random value
    random_value = str(random.randint(0, 1000000)).encode('utf-8')

    # Create a hash object
    hash_object = hashlib.md5()

    # Update the hash object with MAC address, current time, and random value
    hash_object.update(mac.encode('utf-8'))
    hash_object.update(current_time)
    hash_object.update(random_value)

    # Generate the key
    key = hash_object.hexdigest()

    return key


# Function to check the result in S3
def check_result(key):
    print('thread started')
    start_time = time.time()
    while True:
        if check_object_exists('test-n-final-bucket', key):
            s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
            image_name = str(key) + '.jpg'
            current_directory = os.getcwd()
            source_path = os.path.join(current_directory, image_name)
            destination_path = "D:\\UNI\sems\\2024 spring\\Distributed Computing\\Project\\static"
            shutil.move(source_path, destination_path)
            end_time = time.time()
            s3_client.delete_object(Bucket='test-n-final-bucket', Key=key)
            print('Got the object from the bucket directly in', end_time - start_time)
            break


# Photo processing function
def process_photo(file, op):
    print(op + ' entered')
    key = generate_key()
    s3_client.put_object(
        Bucket='kmna-juju-bucket',
        Key=key,
        Body=file,
        ContentType='image/jpg',  # Adjust content type if needed
        Metadata={'operation': op}
    )

    # Create an event to signal when the thread finishes
    # check_result(image_key)
    print('thread started')
    start_time = time.time()
    while True:
        if check_object_exists('test-n-final-bucket', key):
            s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
            image_name = str(key) + '.jpg'
            current_directory = os.getcwd()
            source_path = os.path.join(current_directory, image_name)
            destination_path = "D:\\UNI\sems\\2024 spring\\Distributed Computing\\Project\\static"
            shutil.move(source_path, destination_path)
            end_time = time.time()
            s3_client.delete_object(Bucket='test-n-final-bucket', Key=key)
            print('Got the object from the bucket directly in', end_time - start_time)
            break
    return key + '.jpg'


# def upload_to_s3(key, op, file):
#     print('entered put_object thread')
#     s3_client.put_object(
#         Bucket='kmna-juju-bucket',
#         Key=key,
#         Body=file,
#         ContentType='image/jpg',  # Adjust content type if needed
#         Metadata={'operation': op}
#     )
#     print('finished putting the object')


# Route to handle file uploads
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index3.html', message='No file part')

        files = request.files.getlist('file')
        option = request.form['options']

        if not files or files[0].filename == '':
            return render_template('index3.html', message='No selected file')

        global paths_list
        key_list = []
        for file in files:
            key = generate_key()
            # thread = threading.Thread(target=upload_to_s3, args=(key, option, file))
            # thread.start()
            # threads.append(thread)
            key_list.append(key)
            paths_list.append((file, key + '.jpg'))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(big(key_list, files,option))
        except Exception as e:
            print('dadada')
            print(f"RuntimeError: {e}")

        for key in key_list:
            while True:
                start_time = time.time()
                if check_object_exists('test-n-final-bucket', key):
                    s3_client.download_file('test-n-final-bucket', key, key + '.jpg')
                    image_name = str(key) + '.jpg'
                    current_directory = os.getcwd()
                    source_path = os.path.join(current_directory, image_name)
                    destination_path = "D:\\UNI\sems\\2024 spring\\Distributed Computing\\Project\\static"
                    shutil.move(source_path, destination_path)
                    end_time = time.time()
                    s3_client.delete_object(Bucket='test-n-final-bucket', Key=key)
                    print('Got the object from the bucket directly in', end_time - start_time)
                    break

        return render_template('success.html', processed_paths=paths_list, enumerate=enumerate)

    return render_template('index3.html')


# Helper function to handle file processing
def process_file(file, option):
    filename = file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    with open(file_path, 'rb') as f:
        image_data = f.read()
    file_size = len(image_data)
    print(file_size)
    processed_path = process_photo(image_data, option)
    global paths_list
    paths_list.append((file, processed_path))
    return processed_path


# Route to display result
@app.route('/result/<filename>/<processed_path>')
def success(filename, processed_path):
    return render_template('result.html', filename=filename, processed_path=processed_path)


# Function to get EC2 instance information
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
            }
            instances.append(instance_info)
    print(instances)
    return instances


# Route to display backend information
@app.route('/backend')
def backend():
    data = get_ec2_info(ec2_client)
    return render_template('backend.html', data=data)


async def upload_to_s3(client, key, file_data, op):
    s3_bucket = 'kmna-juju-bucket'
    await client.put_object(
        Bucket=s3_bucket,
        Key=key,
        Body=file_data,
        ContentType='image/jpg',  # Adjust content type if needed
        Metadata={'operation': op}
    )
    print(f'Finished uploading {key}')


async def big(keys, files, op):
    print('entered big')
    l = ['hush.jpg', 'face.jpg', 'square.jpg', 'phone.jpg', 'star.jpg', '1.jpg', '2.jpg', '3.jpg', '4.jpg', '5.jpg']
    print(len(l))
    session = aioboto3.Session()

    async with session.client('s3') as s3_client:
        tasks = []
        for key, pic in zip(keys, files):
            try:
                print('try to open file')

                file_content = pic.read()
                tasks.append(upload_to_s3(s3_client, key, file_content, op))
                print('passed file to upload')
            except FileNotFoundError:
                print(f"File not found: {key}")

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    app.run(debug=True, port=3000)
