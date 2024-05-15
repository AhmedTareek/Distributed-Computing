import boto3

# Create SQS client
sqs = boto3.client('sqs')

queue_url = 'https://sqs.eu-north-1.amazonaws.com/992382542532/image-processing-s3-to-ec2-queue'

response = sqs.send_message(QueueUrl=queue_url, MessageBody=('give the bucket name and file name to process'))

print(response)
print(response['MessageId'])