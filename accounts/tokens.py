# accounts/tokens.py
from django.core import signing

SALT = "email-confirmation-salt"

def make_token(user):
    return signing.dumps({"user_id": str(user.id)}, salt=SALT)

def parse_token(token, max_age=60*60*24):
    try:
        return signing.loads(token, salt=SALT, max_age=max_age)
    except Exception:
        return None
