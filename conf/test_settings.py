from .settings import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable email sending in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable SMS sending in tests
TWILIO_ACCOUNT_SID = 'test'
TWILIO_AUTH_TOKEN = 'test'

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable real AWS calls in tests
AWS_ACCESS_KEY_ID = 'test-key'
AWS_SECRET_ACCESS_KEY = 'test-secret'
AWS_REGION_NAME = 'us-east-1'
AWS_SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/000000000000/test-queue'
AWS_S3_BUCKET_NAME = 'test-bucket'

# Social auth test credentials
SOCIAL_AUTH_GOOGLE_CLIENT_ID = 'test-google-client-id'
SOCIAL_AUTH_GOOGLE_CLIENT_SECRET = 'test-google-secret'
SOCIAL_AUTH_FACEBOOK_APP_ID = 'test-facebook-app-id'
SOCIAL_AUTH_FACEBOOK_APP_SECRET = 'test-facebook-secret'

# Stripe disabled in tests by default
STRIPE_ENABLED = False
STRIPE_SECRET_KEY = 'sk_test_fake_key'

# Override ENV so email utility uses direct mode
ENV = 'local'
DEBUG = True

# Disable migration checks for faster tests
DISABLE_MIGRATIONS = None