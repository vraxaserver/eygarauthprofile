# eygarprofile/aws_utils.py

import json
import boto3
import os
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings


SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "us-east-1")


sqs = boto3.client("sqs", region_name=AWS_REGION_NAME)

def publish_to_sns(message_type, payload):
    """
    Publishes a message to the SNS topic.

    :param message_type: A string to identify the message type (e.g., 'email', 'sms').
    :param payload: A dictionary with the message details.
    """
    if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_REGION_NAME, settings.SNS_TOPIC_ARN]):
        # Log an error or handle the case where AWS settings are not configured
        print("AWS settings are not fully configured.")
        return

    sns_client = boto3.client(
        'sns',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME
    )

    message = {
        'message_type': message_type,
        'payload': payload
    }

    try:
        response = sns_client.publish(
            TopicArn=settings.SNS_TOPIC_ARN,
            Message=json.dumps(message),
            MessageStructure='string'
        )
        return response
    except Exception as e:
        # Log the exception
        print(f"Error publishing to SNS: {e}")
        return None
        

def publish_to_sqs(email):
    resp = sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(email),
        MessageAttributes={
            "MessageType": {
                "DataType": "String",
                "StringValue": "UserRegistration"
            }
        }
    )
    return resp