
import json
import boto3
import os
from dotenv import load_dotenv
load_dotenv()
import pdb

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "me-central-1")


sqs = boto3.client("sqs", region_name=AWS_REGION_NAME)

def publish_to_sqs(email):
    pdb.set_trace()
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


if __name__ == "__main__":
    # Run basic test
    activation_url = "https://localhost:8000"
    email_payload = {
        'to_email': "mamun@gmail.com",
        'subject': "Activate your account",
        'message': f"Click here to activate your account: {activation_url}"
    }
    publish_to_sqs(email_payload)
    
    # Example: Run subscription test (uncomment and modify as needed)
    # topic_arn = "arn:aws:sns:us-east-1:123456789012:my-topic"
    # run_subscription_test(
    #     topic_arn=topic_arn,
    #     email="test@example.com",
    #     phone="+1234567890"
    # )