import requests
import logging
from django.conf import settings
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)


def send_sms_verification(phone_number: str, verification_code: str) -> bool:
    """
    Send SMS verification code using your preferred SMS provider.
    This is a placeholder implementation - integrate with your SMS provider.
    """
    try:
        # Example integration with Twilio
        # from twilio.rest import Client
        
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=f"Your verification code is: {verification_code}",
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )
        
        # For development/testing, just log the code
        logger.info(f"SMS Verification code for {phone_number}: {verification_code}")
        
        # Simulate successful SMS sending
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
        return False


def verify_identity_document(identity_verification) -> Dict[str, Any]:
    """
    Verify identity document using OCR or document verification service.
    This is a placeholder implementation - integrate with your document verification provider.
    """
    try:
        # Example integration with a document verification service
        # You can integrate with services like:
        # - AWS Textract
        # - Google Cloud Document AI
        # - Microsoft Form Recognizer
        # - Third-party services like Jumio, Onfido, etc.
        
        document_type = identity_verification.document_type
        document_number = identity_verification.document_number
        
        # Simulate document verification process
        # In real implementation, you would:
        # 1. Upload document images to verification service
        # 2. Extract text and data from documents
        # 3. Validate document authenticity
        # 4. Return extracted information
        
        # Mock verification logic
        if document_number and len(document_number) >= 8:
            # Simulate successful verification
            return {
                'success': True,
                'full_name': 'John Doe',  # Extracted from document
                'fathers_name': 'Richard Doe',  # Extracted from document
                'date_of_birth': '1990-01-01',
                'id_address_line1': '123 Main St',
                'id_city': 'Cityville',
                'id_state': 'State',
                'id_postal_code': '12345',
                'id_country': 'Country',
                'confidence_score': 95.5
            }
        else:
            return {
                'success': False,
                'error': 'Invalid document number format'
            }
            
    except Exception as e:
        logger.error(f"Document verification failed: {str(e)}")
        return {
            'success': False,
            'error': 'Document verification service unavailable'
        }


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number format
    """
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone_number))


def validate_email_format(email: str) -> bool:
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def verify_whatsapp_number(whatsapp_number: str) -> bool:
    """
    Verify WhatsApp number exists.
    This is a placeholder - implement with WhatsApp Business API if needed.
    """
    try:
        # In real implementation, you might use WhatsApp Business API
        # to verify if the number has WhatsApp
        
        # For now, just validate the format
        return validate_phone_number(whatsapp_number)
        
    except Exception as e:
        logger.error(f"WhatsApp verification failed for {whatsapp_number}: {str(e)}")
        return False


def verify_telegram_username(telegram_username: str) -> bool:
    """
    Verify Telegram username exists.
    This is a placeholder implementation.
    """
    try:
        # Basic username format validation
        if not telegram_username.startswith('@'):
            telegram_username = '@' + telegram_username
            
        # Username should be 5-32 characters, alphanumeric plus underscore
        username_pattern = r'^@[a-zA-Z0-9_]{5,32}$'
        
        return bool(re.match(username_pattern, telegram_username))
        
    except Exception as e:
        logger.error(f"Telegram verification failed for {telegram_username}: {str(e)}")
        return False


def verify_facebook_page(facebook_url: str) -> bool:
    """
    Verify Facebook page URL is valid and accessible.
    """
    try:
        # Basic URL validation
        facebook_patterns = [
            r'^https://www\.facebook\.com/[a-zA-Z0-9\.]+/?$',
            r'^https://facebook\.com/[a-zA-Z0-9\.]+/?$',
            r'^https://www\.facebook\.com/pages/[a-zA-Z0-9\-\.]+/\d+/?$'
        ]
        
        for pattern in facebook_patterns:
            if re.match(pattern, facebook_url):
                # In real implementation, you might make a request to check if page exists
                # response = requests.head(facebook_url, timeout=5)
                # return response.status_code == 200
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Facebook page verification failed for {facebook_url}: {str(e)}")
        return False


def generate_verification_token() -> str:
    """
    Generate a random verification token
    """
    import secrets
    return secrets.token_urlsafe(32)


def send_email_verification(email: str, verification_token: str) -> bool:
    """
    Send email verification link
    """
    try:
        from django.core.mail import send_mail
        from django.urls import reverse
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification_token}"
        
        subject = "Verify your email address"
        message = f"""
        Please click the following link to verify your email address:
        
        {verification_url}
        
        This link will expire in 24 hours.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email verification to {email}: {str(e)}")
        return False


def calculate_profile_completeness(eygar_host) -> Dict[str, Any]:
    """
    Calculate profile completeness score and missing fields
    """
    total_fields = 0
    completed_fields = 0
    missing_fields = []
    
    # Business Profile fields
    if hasattr(eygar_host, 'business_profile'):
        bp = eygar_host.business_profile
        business_fields = [
            ('business_name', bp.business_name),
            ('license_number', bp.license_number),
            ('license_document', bp.license_document),
            ('business_address_line1', bp.business_address_line1),
            ('business_city', bp.business_city),
            ('business_state', bp.business_state),
        ]
        
        for field_name, field_value in business_fields:
            total_fields += 1
            if field_value:
                completed_fields += 1
            else:
                missing_fields.append(f"business_profile.{field_name}")
    
    # Identity Verification fields
    if hasattr(eygar_host, 'identity_verification'):
        iv = eygar_host.identity_verification
        identity_fields = [
            ('document_type', iv.document_type),
            ('document_number', iv.document_number),
            ('document_image_front', iv.document_image_front),
            ('verification_status', iv.verification_status == 'verified'),
        ]
        
        for field_name, field_value in identity_fields:
            total_fields += 1
            if field_value:
                completed_fields += 1
            else:
                missing_fields.append(f"identity_verification.{field_name}")
    
    # Contact Details fields
    if hasattr(eygar_host, 'contact_details'):
        cd = eygar_host.contact_details
        contact_fields = [
            ('address_line1', cd.address_line1),
            ('city', cd.city),
            ('mobile_number', cd.mobile_number),
            ('latitude', cd.latitude),
            ('longitude', cd.longitude),
        ]
        
        for field_name, field_value in contact_fields:
            total_fields += 1
            if field_value:
                completed_fields += 1
            else:
                missing_fields.append(f"contact_details.{field_name}")
    
    completeness_percentage = (completed_fields / total_fields * 100) if total_fields > 0 else 0
    
    return {
        'total_fields': total_fields,
        'completed_fields': completed_fields,
        'missing_fields': missing_fields,
        'completeness_percentage': round(completeness_percentage, 2)
    }