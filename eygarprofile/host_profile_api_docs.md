# Host Profile API Documentation

## Overview

The Host Profile API allows authenticated users to create and manage their host profiles through a 4-step process:

1. **Business Profile** - Business information, licenses, and documents
2. **Identity Verification** - Document upload and verification
3. **Contact Details** - Address, phone, and social media verification
4. **Review Submission** - Final submission for admin review

## Authentication

All endpoints require authentication using JWT tokens:
```
Authorization: Bearer <jwt_token>
```

## Base URL
```
/api/profiles/
```

## API Endpoints

### 1. Get Current Host Profile
```http
GET api/profiles/host/
```

**Response:**
```json
{
  "id": "uuid",
  "status": "draft",
  "current_step": "business_profile",
  "completion_percentage": 25.0,
  "business_profile_completed": false,
  "identity_verification_completed": false,
  "contact_details_completed": false,
  "review_submission_completed": false,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z",
  "next_step": "business_profile"
}
```

### 2. Step 1: Business Profile
```http
POST /api/profiles/host/business_profile/
Content-Type: multipart/form-data
```

**Request Body:**
```json
{
  "business_name": "My Business LLC",
  "business_type": "Hotel",
  "license_number": "LIC123456789",
  "license_document": "<file>",
  "business_logo": "<file>",
  "business_address_line1": "123 Business Street",
  "business_address_line2": "Suite 100",
  "business_city": "New York",
  "business_state": "NY",
  "business_postal_code": "10001",
  "business_country": "USA",
  "business_description": "A luxury hotel in downtown Manhattan"
}
```

**Response:**
```json
{
  "message": "Business profile saved successfully",
  "data": {
    "business_name": "My Business LLC",
    "license_number": "LIC123456789",
    // ... other fields
  },
  "next_step": "identity_verification"
}
```

### 3. Step 2: Identity Verification
```http
POST /api/profiles/host/identity_verification/
Content-Type: multipart/form-data
```

**Request Body:**
```json
{
  "document_type": "national_id",
  "document_number": "ID123456789",
  "document_image_front": "<file>",
  "document_image_back": "<file>"
}
```

**Response:**
```json
{
  "message": "Identity verification completed successfully",
  "verification_status": "verified",
  "next_step": "contact_details"
}
```

### 4. Step 3: Contact Details
```http
POST /api/profiles/host/contact_details/
```

**Request Body:**
```json
{
  "address_line1": "123 Main Street",
  "address_line2": "Apt 4B",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "mobile_number": "+1234567890",
  "whatsapp_number": "+1234567890",
  "telegram_username": "@myusername",
  "facebook_page_url": "https://facebook.com/mybusiness"
}
```

**Response:**
```json
{
  "message": "Contact details saved successfully",
  "data": {
    "mobile_number": "+1234567890",
    "mobile_verified": "pending",
    // ... other fields
  },
  "next_step": "review_submission"
}
```

### 5. Step 4: Submit for Review
```http
POST /api/profiles/host/submit_for_review/
```

**Request Body:**
```json
{
  "additional_notes": "Please review my application. I'm excited to start hosting!",
  "terms_accepted": true,
  "privacy_policy_accepted": true
}
```

**Response:**
```json
{
  "message": "Profile submitted for review successfully",
  "status": "submitted",
  "submitted_at": "2025-01-15T12:00:00Z"
}
```

### 6. Get Current Step Information
```http
GET /api/profiles/host/current_step/
```

**Response:**
```json
{
  "current_step": "business_profile",
  "next_step": "identity_verification",
  "completion_percentage": 75.0,
  "status": "draft",
  "steps_completed": {
    "business_profile": true,
    "identity_verification": true,
    "contact_details": true,
    "review_submission": false
  }
}
```

## Mobile Verification

### Send Mobile Verification Code
```http
POST /api/profiles/verify/mobile/send/
```

**Request Body:**
```json
{
  "mobile_number": "+1234567890"
}
```

**Response:**
```json
{
  "message": "Verification code sent successfully"
}
```

### Verify Mobile Code
```http
POST /api/profiles/verify/mobile/confirm/
```

**Request Body:**
```json
{
  "verification_code": "123456"
}
```

**Response:**
```json
{
  "message": "Mobile number verified successfully"
}
```

## Admin/Moderator Endpoints

### List Profiles for Review
```http
GET /api/profiles/admin/reviews/
```
*Requires admin/moderator permissions*

### Get Profile Details for Review
```http
GET /api/profiles/admin/reviews/{profile_id}/
```
*Requires admin/moderator permissions*

### Review Profile
```http
POST /api/profiles/admin/reviews/{profile_id}/review/
```

**Request Body:**
```json
{
  "status": "approved",
  "review_notes": "All documents verified and approved."
}
```

**Response:**
```json
{
  "message": "Profile approved successfully",
  "status": "approved"
}
```

## Status Values

- `draft` - Profile is being created
- `submitted` - Profile submitted for review
- `approved` - Profile approved by admin
- `rejected` - Profile rejected by admin
- `pending` - Profile under review
- `on_hold` - Profile temporarily on hold

## Step Values

- `business_profile` - Step 1: Business information
- `identity_verification` - Step 2: Identity documents
- `contact_details` - Step 3: Contact information
- `review_submission` - Step 4: Final submission

## Error Responses

### 400 Bad Request
```json
{
  "error": "Cannot access this step yet",
  "details": "Please complete business profile first"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to save business profile"
}
```

## File Upload Requirements

### Business License Document
- Max size: 5MB
- Formats: PDF, JPG, JPEG, PNG

### Business Logo
- Max size: 2MB
- Formats: JPG, JPEG, PNG, GIF

### Identity Documents
- Max size: 5MB per image
- Formats: JPG, JPEG, PNG

## Frontend Integration Guide

### React/Next.js Example

```javascript
// utils/api.js
const API_BASE_URL = 'http://localhost:8000/api/host-profile';

export const hostProfileAPI = {
  // Get current profile
  getCurrentProfile: () =>
    fetch(`${API_BASE_URL}/profiles/`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }).then(res => res.json()),

  // Submit business profile
  submitBusinessProfile: (data) =>
    fetch(`${API_BASE_URL}/profiles/business_profile/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: createFormData(data)
    }).then(res => res.json()),

  // Submit identity verification
  submitIdentityVerification: (data) =>
    fetch(`${API_BASE_URL}/profiles/identity_verification/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: createFormData(data)
    }).then(res => res.json()),

  // Submit contact details
  submitContactDetails: (data) =>
    fetch(`${API_BASE_URL}/profiles/contact_details/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}` 
      },
      body: JSON.stringify(data)
    }).then(res => res.json()),

  // Submit for review
  submitForReview: (data) =>
    fetch(`${API_BASE_URL}/profiles/submit_for_review/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}` 
      },
      body: JSON.stringify(data)
    }).then(res => res.json()),

  // Get current step
  getCurrentStep: () =>
    fetch(`${API_BASE_URL}/profiles/current_step/`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }).then(res => res.json()),
};

function createFormData(data) {
  const formData = new FormData();
  Object.keys(data).forEach(key => {
    if (data[key] !== null && data[key] !== undefined) {
      formData.append(key, data[key]);
    }
  });
  return formData;
}

function getToken() {
  // Return your JWT token
  return localStorage.getItem('access_token');
}
```

### Step Flow Management

```javascript
// hooks/useHostProfile.js
import { useState, useEffect } from 'react';
import { hostProfileAPI } from '../utils/api';

export function useHostProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await hostProfileAPI.getCurrentProfile();
      setProfile(data);
      const stepData = await hostProfileAPI.getCurrentStep();
      setCurrentStep(stepData);
    } catch (error) {
      console.error('Failed to load profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitStep = async (stepName, data) => {
    try {
      let result;
      switch (stepName) {
        case 'business_profile':
          result = await hostProfileAPI.submitBusinessProfile(data);
          break;
        case 'identity_verification':
          result = await hostProfileAPI.submitIdentityVerification(data);
          break;
        case 'contact_details':
          result = await hostProfileAPI.submitContactDetails(data);
          break;
        case 'review_submission':
          result = await hostProfileAPI.submitForReview(data);
          break;
        default:
          throw new Error(`Unknown step: ${stepName}`);
      }
      
      await loadProfile(); // Refresh profile data
      return result;
    } catch (error) {
      console.error(`Failed to submit ${stepName}:`, error);
      throw error;
    }
  };

  const getStepComponent = () => {
    if (!currentStep) return null;
    
    switch (currentStep.current_step) {
      case 'business_profile':
        return 'BusinessProfileForm';
      case 'identity_verification':
        return 'IdentityVerificationForm';
      case 'contact_details':
        return 'ContactDetailsForm';
      case 'review_submission':
        return 'ReviewSubmissionForm';
      default:
        return 'CompletedForm';
    }
  };

  return {
    profile,
    currentStep,
    loading,
    submitStep,
    getStepComponent,
    reload: loadProfile
  };
}
```

This comprehensive API provides all the functionality needed for a robust host profile management system with proper step validation, file uploads, verification, and admin review capabilities.