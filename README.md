# Eygar AUTH & PROFILE Backend API

## Overview

Welcome to the Eygar Backend API. This project is a robust and scalable backend system built with Django and Django REST Framework. It provides a comprehensive user authentication system and a multi-step profile management module specifically designed for "Eygar Hosts".

The system features a custom user model, JWT-based authentication with email verification, and a detailed, step-by-step process for hosts to build their profiles. This includes business information, identity verification, contact details, and a final submission for admin review. The API is well-structured, permission-based, and includes endpoints for both users and administrators.

---

## Features

### Accounts & Authentication (`accounts` app)

-   **Custom User Model:** Extends Django's `AbstractUser` with UUID as the primary key and uses email for authentication.
-   **JWT Authentication:** Secure stateless authentication using `djangorestframework-simplejwt`.
-   **User Registration:** A simple registration endpoint that creates a new user.
-   **Email Activation:** New users receive an activation link via email to verify their account before they can log in.
-   **Login/Logout:** Standard endpoints for obtaining and blacklisting JWT refresh tokens.
-   **Password Management:** A secure endpoint for authenticated users to change their password.
-   **User Profile:** Endpoints for users to view and update their own profile information.

### Host Profile Management (`eygarprofile` app)

-   **Multi-Step Profile Creation:** A guided, four-step process for hosts to complete their profile.
    1.  **Business Profile:** Collects business name, type, license, address, and description.
    2.  **Identity Verification:** A mock endpoint for uploading and verifying identity documents (e.g., National ID, Passport).
    3.  **Contact Details:** Gathers physical address, contact numbers, and social media links.
    4.  **Review & Submission:** Allows users to accept terms and submit their completed profile for review.
-   **Profile Status Tracking:** The `EygarHost` profile tracks the current step, completion percentage, and overall status (e.g., `Draft`, `Submitted`, `Approved`).
-   **Mobile Number Verification:**
    -   Sends a 6-digit verification code via a mock SMS service.
    -   Provides an endpoint to confirm the code and verify the mobile number.
-   **Admin Review System:**
    -   A dedicated set of endpoints for administrators to list, view, and review submitted host profiles.
    -   Admins can `approve` or `reject` profiles and provide review notes.
-   **Email Notifications:** Automatic emails are sent to users upon profile submission and after an admin has completed the review.
-   **Combined Profile Endpoint:** A convenient endpoint (`/api/profiles/`) that retrieves all profile information for the authenticated user (User, EygarHost, etc.) in a single request.

---

## API Endpoints

The API endpoints are organized by application. All endpoints are prefixed with `/api/`.

### Authentication (`/api/auth/`)

| Method | Endpoint | Description | Permissions |
| --- | --- | --- | --- |
| `POST` | `/register/` | Registers a new user and sends an activation email. | Allow Any |
| `GET` | `/activate/` | Activates a user's account using a token from email. | Allow Any |
| `POST` | `/login/` | Obtains JWT access and refresh tokens. | Allow Any |
| `POST` | `/token/refresh/` | Refreshes an expired JWT access token. | Allow Any |
| `POST` | `/token/verify/` | Verifies a JWT access token. | Allow Any |
| `POST` | `/logout/` | Blacklists a refresh token to log the user out. | Is Authenticated |
| `GET`, `PUT`, `PATCH` | `/me/` | Retrieves or updates the authenticated user's basic info. | Is Authenticated |
| `GET`, `PUT`, `PATCH` | `/profile/` | Retrieves or updates the authenticated user's profile details. | Is Authenticated |
| `POST` | `/change-password/` | Changes the authenticated user's password. | Is Authenticated |

### Host Profiles (`/api/profiles/`)

| Method | Endpoint | Description | Permissions |
| --- | --- | --- | --- |
| `GET` | `/` | Retrieves the combined profile for the authenticated user. | Is Authenticated |
| `GET` | `/hosts/my/` | Retrieves the `EygarHost` profile for the authenticated user. | Is Authenticated |
| `GET` | `/hosts/` | (Admin) Lists all `EygarHost` profiles. | Is Admin |
| `GET` | `/hosts/{id}/` | (Admin/Owner) Retrieves a specific `EygarHost` profile. | Is Admin or Owner |
| `POST` | `/hosts/business_profile/` | Creates/updates the Business Profile (Step 1). | Is Authenticated |
| `POST` | `/hosts/identity_verification/` | Creates/updates Identity Verification (Step 2). | Is Authenticated |
| `POST` | `/hosts/contact_details/` | Creates/updates Contact Details (Step 3). | Is Authenticated |
| `POST` | `/hosts/submit_for_review/` | Submits the completed profile for review (Step 4). | Is Authenticated |
| `GET` | `/hosts/current_status/` | Gets the current status and completion percentage. | Is Authenticated |

### Mobile Verification (`/api/verify/`)

| Method | Endpoint | Description | Permissions |
| --- | --- | --- | --- |
| `POST` | `/mobile/send/` | Sends a verification code to the user's mobile number. | Is Authenticated |
| `POST` | `/mobile/confirm/` | Verifies the received mobile verification code. | Is Authenticated |

### Admin Review (`/api/admin/reviews/`)

| Method | Endpoint | Description | Permissions |
| --- | --- | --- | --- |
| `GET` | `/` | Lists all host profiles submitted for review. | Is Admin/Moderator |
| `GET` | `/{id}/` | Retrieves a specific host profile for detailed review. | Is Admin/Moderator |
| `POST` | `/{id}/review/` | Approves or rejects a host profile. | Is Admin/Moderator |

---

## Getting Started

### Prerequisites

-   Python 3.8+
-   Django 4.0+
-   PostgreSQL (Recommended) or another Django-supported database
-   Virtual Environment (e.g., `venv`)

### Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd eygar-backend
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root and add your configuration details. At a minimum, you'll need:
    ```env
    SECRET_KEY='your-secret-key'
    DEBUG=True
    DATABASE_URL='your-database-connection-string' # e.g., postgres://user:password@host:port/dbname
    
    # Email Settings (for registration)
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST='your-smtp-host'
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER='your-email@example.com'
    EMAIL_HOST_PASSWORD='your-email-password'
    DEFAULT_FROM_EMAIL='your-email@example.com'
    
    # Site URL (for activation links)
    SITE_URL='http://localhost:8000'
    ```

5.  **Run Database Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser (for admin access):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```

The API will now be running at `http://127.0.0.1:8000/`.

---

## API Documentation

The API is self-documented using `drf-spectacular`. Once the server is running, you can access the interactive Swagger UI and the OpenAPI schema at the following endpoints:

-   **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
-   **OpenAPI Schema:** `http://127.0.0.1:8000/api/schema/`