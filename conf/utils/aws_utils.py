# eygarprofile/aws_utils.py
import uuid
import json
import boto3
import os
from dotenv import load_dotenv
load_dotenv()
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

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


s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME,
)

def upload_fileobj_to_s3(file_obj, key_prefix="avatars/"):
    """
    Uploads an InMemoryUploadedFile/file-like object to S3 and returns the public URL.
    key_prefix: path inside bucket, e.g. 'avatars/{user_id}/...'
    """
    ext = os.path.splitext(file_obj.name)[1] or ""
    key = f"{key_prefix}{uuid.uuid4().hex}{ext}"
    extra_args = {
        "ACL": "public-read",               # public: quick & easy — consider CloudFront or presigned URLs for production
        "ContentType": getattr(file_obj, "content_type", "application/octet-stream"),
    }

    s3_client.upload_fileobj(file_obj, settings.AWS_S3_BUCKET_NAME, key, ExtraArgs=extra_args)

    # Construct URL — change if you use a CloudFront domain
    url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}"
    return url, key


def upload_to_eygar_host(key_prefix: str):
    """
    Returns a callable suitable for Django `upload_to`.
    Files will be saved under: {key_prefix}/{eygar_host_id}/{uuid}{ext}
    """
    if not key_prefix.endswith("/"):
        key_prefix = key_prefix + "/"

    def _callable(instance, filename):
        ext = os.path.splitext(filename)[1] or ""
        host_id = getattr(getattr(instance, "eygar_host", None), "id", None) or uuid.uuid4().hex
        filename = f"{uuid.uuid4().hex}{ext}"
        return f"{key_prefix}{host_id}/{filename}"

    return _callable



def send_email_to_sqs(subject, message, recipient_list):
    """
    Constructs an email payload and sends it as a message to an SQS queue.
    This decouples email sending from the main application flow.
    """
    if not recipient_list:
        logger.warning("Attempted to queue an email with no recipients.")
        return

    try:
        sqs_client = boto3.client(
            "sqs",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        # The message payload that the consumer (e.g., a Lambda function) will parse
        message_payload = {
            'subject': subject,
            'message': message,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'recipient_list': recipient_list,
        }

        # Send the message to the SQS queue
        response = sqs_client.send_message(
            QueueUrl=settings.AWS_SQS_EMAIL_QUEUE_URL,
            MessageBody=json.dumps(message_payload)
        )

        logger.info(f"Successfully queued email message. MessageId: {response.get('MessageId')}")

    except Exception as e:
        logger.error(f"Failed to send message to SQS: {str(e)}")
