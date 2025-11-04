import boto3
import json
import time
import os
from dotenv import load_dotenv
load_dotenv()
import pdb

# --- Configuration ---
# It's best to use environment variables, but you can hardcode them here for a quick test.

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "us-east-1")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "us-east-1")
AWS_REGION = os.getenv("AWS_REGION_NAME", "us-east-1")

SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:user-notifications")
EMAIL_SQS_QUEUE_URL = os.getenv("EMAIL_SQS_QUEUE_URL", "https://sqs.me-central-1.amazonaws.com/637423303507/eygar_email_queue")
# The name of your email sending Lambda function
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "email_sender_lambda")
# --- End Configuration ---


# Initialize Boto3 clients
# session = boto3.Session(region_name=AWS_REGION)
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
sns_client = session.client('sns')
sqs_client = session.client('sqs')
logs_client = session.client('logs')

def publish_email_message(recipient, subject, body):
    """
    Simulates the Django app by publishing an email message to the SNS topic.
    """
    message_payload = {
        'to_email': recipient,
        'subject': subject,
        'message': body
    }

    message = {
        'message_type': 'email',
        'payload': message_payload
    }

    try:
        print(f"Publishing message to SNS Topic: {SNS_TOPIC_ARN}")
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message),
            MessageStructure='string'
        )
        print(f"Successfully published message. Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Error publishing to SNS: {e}")
        return False

def check_sqs_for_message(timeout=10):
    """
    Polls the SQS queue to see if the message arrives.
    If a message is found, it is deleted to prevent the Lambda from processing it.
    """
    print(f"\nPolling SQS Queue for message: {EMAIL_SQS_QUEUE_URL}")
    print(f"Will wait for up to {timeout} seconds...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = sqs_client.receive_message(
                QueueUrl=EMAIL_SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5 # Use long polling
            )

            if 'Messages' in response:
                message = response['Messages'][0]
                receipt_handle = message['ReceiptHandle']

                # The body of the SQS message from an SNS subscription is a JSON string
                # containing the SNS message details.
                body = json.loads(message['Body'])
                actual_message = json.loads(body['Message'])

                print("\n--- SQS Message Received! ---")
                print(f"Message Type: {actual_message.get('message_type')}")
                print(f"Payload: {actual_message.get('payload')}")
                print("------------------------------")

                # Delete the message so it's not processed by Lambda
                print("Deleting message from queue to conclude the test...")
                sqs_client.delete_message(
                    QueueUrl=EMAIL_SQS_QUEUE_URL,
                    ReceiptHandle=receipt_handle
                )
                print("Message deleted successfully.")
                return True

        except Exception as e:
            print(f"An error occurred while checking SQS: {e}")
            return False

    print("\nNo message received in the SQS queue within the timeout period.")
    return False

def check_lambda_logs(start_time, timeout=30):
    """
    Checks the CloudWatch logs for the Lambda function to verify it ran and sent the email.
    """
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    print(f"\nChecking CloudWatch logs in log group: {log_group_name}")
    print(f"Will wait for up to {timeout} seconds for log entry...")

    end_time = time.time()
    while time.time() - end_time < timeout:
        try:
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=int(start_time * 1000), # AWS timestamps are in milliseconds
                filterPattern='"Email sent to success@simulator.amazonses.com"' # Filter for our success message
            )
            if response['events']:
                print("\n--- Success! Log Entry Found in CloudWatch! ---")
                log_event = response['events'][0]
                print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log_event['timestamp']/1000))}")
                print(f"Log Message: {log_event['message'].strip()}")
                print("-------------------------------------------------")
                return True

            time.sleep(5) # Wait before polling again

        except logs_client.exceptions.ResourceNotFoundException:
            print(f"Error: Log group '{log_group_name}' not found. Has the Lambda run at least once?")
            return False
        except Exception as e:
            print(f"An error occurred while checking logs: {e}")
            return False

    print("\nDid not find a success message in the Lambda logs within the timeout period.")
    return False

if __name__ == "__main__":
    print("--- AWS Notification Pipeline Test Script ---")
    pdb.set_trace()

    # --- Test 1: SNS to SQS Connectivity ---
    print("\n\n--- Running Test 1: SNS -> SQS ---")
    print("This test verifies that a message published to SNS arrives in the SQS queue.")

    if publish_email_message("test@example.com", "SQS Test", "Testing SNS to SQS link."):
        if check_sqs_for_message():
            print("\n✅ Test 1 PASSED: Message successfully traveled from SNS to SQS.")
        else:
            print("\n❌ Test 1 FAILED: Message was published but not found in SQS.")
            print("   Troubleshooting: Check the SNS topic subscription and the SQS queue's access policy.")
    else:
        print("\n❌ Test 1 FAILED: Could not publish message to SNS.")


    # --- Test 2: End-to-End Test ---
    print("\n\n--- Running Test 2: SNS -> SQS -> Lambda -> SES (End-to-End) ---")
    print("This test publishes a message and checks Lambda's CloudWatch logs for confirmation of an email being sent.")
    print("NOTE: This test assumes the message is NOT intercepted and is processed by the Lambda.")

    # We use a special SES simulator address that always results in a successful send
    # without delivering an actual email.
    test_recipient = "success@simulator.amazonses.com"
    test_subject = "End-to-End Test"
    test_body = "Testing the full pipeline from SNS to SES."

    # Get the current time before we publish, so we know where to start looking in the logs
    log_check_start_time = time.time()

    if publish_email_message(test_recipient, test_subject, test_body):
        if check_lambda_logs(log_check_start_time):
            print("\n✅ Test 2 PASSED: End-to-end pipeline appears to be working correctly!")
        else:
            print("\n❌ Test 2 FAILED: Could not confirm successful email send via Lambda logs.")
            print("   Troubleshooting:")
            print("   1. Check the Lambda function's CloudWatch logs manually for errors.")
            print("   2. Ensure the Lambda has the correct IAM permissions (for SQS, SES, and CloudWatch Logs).")
            print("   3. Verify the SQS trigger is correctly configured and enabled on the Lambda.")
    else:
        print("\n❌ Test 2 FAILED: Could not publish message to SNS.")
