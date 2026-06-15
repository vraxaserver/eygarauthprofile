# accounts/domain/notification_events.py
"""
Self-contained notification envelopes published to SNS.

Each envelope carries everything the downstream Notification Service needs
to send SMS and/or email without calling back to the Auth Service.

The ``event_type`` field reflects *what happened* (e.g. "UserRegistration",
"PasswordResetRequested") so the Notification Service can use SNS filter
policies without inspecting the template name.

Example payload:
    {
      "event_id": "evt_abc123",
      "event_type": "UserRegistration",
      "notification": {
        "template": "SIGNUP_OTP",
        "channels": ["SMS", "EMAIL"]
      },
      "recipient": {
        "email": "john@example.com",
        "phone": "+97412345678"
      },
      "variables": {
        "otp": "123456",
        "expiry_minutes": 5,
        "app_name": "EYGAR"
      }
    }
"""
from dataclasses import dataclass, field, asdict
import uuid


@dataclass(frozen=True)
class RecipientInfo:
    """Who receives the notification."""
    email: str | None = None
    phone: str | None = None


@dataclass(frozen=True)
class NotificationConfig:
    """What to send and how."""
    template: str = ""
    channels: tuple[str, ...] = ("EMAIL",)


@dataclass(frozen=True)
class NotificationEnvelope:
    """
    Complete, self-contained notification payload for SNS.

    The downstream Notification Service can process this without any
    additional lookups or calls back to the Auth Service.
    """
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str = "SendNotification"
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    recipient: RecipientInfo = field(default_factory=RecipientInfo)
    variables: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON encoding."""
        result = asdict(self)
        # Convert channels tuple to list for JSON compatibility
        result['notification']['channels'] = list(
            self.notification.channels
        )
        # Remove None recipient fields for a cleaner payload
        result['recipient'] = {
            k: v for k, v in result['recipient'].items() if v is not None
        }
        return result
