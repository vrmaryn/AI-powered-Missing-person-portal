# pages/helper/email_service.py
"""
Simple Email Service - Sends to Public Subscribers Only
When case registered in Delhi → Send email to all Delhi subscribers
"""

import yagmail
import os
from dotenv import load_dotenv

load_dotenv()

KNOWN_AREAS = [
    "delhi",
    "mumbai",
    "noida",
    "gurgaon",
    "bangalore",
    "hyderabad",
    "chennai",
    "pune",
    "kolkata",
]


def _get_email_credentials():
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")
    if not sender_email or not sender_password:
        return None, None, "Email config missing: EMAIL_ADDRESS/EMAIL_PASSWORD"
    return sender_email, sender_password, None


def _normalize_area(text: str) -> str:
    value = (text or "").strip().lower()
    if not value:
        return ""
    for area in KNOWN_AREAS:
        if area in value:
            return area
    return value


def _send_email(to, subject, body):
    sender_email, sender_password, err = _get_email_credentials()
    if err:
        return {"status": False, "error": err}
    try:
        yag = yagmail.SMTP(sender_email, sender_password)
        yag.send(to=to, subject=subject, contents=body)
        return {"status": True}
    except Exception as e:
        return {"status": False, "error": str(e)}


def send_missing_person_alert(case_details):
    """
    Send email to public subscribers in the same area
    Works with both dict and SQLModel objects
    """

    sender_email, sender_password, err = _get_email_credentials()
    if err:
        print(f"⚠️ {err}")
        return {"status": False, "error": err, "sent_count": 0}

    try:
        print("📧 Preparing email notification system...")

        # Safe getter (works for dict OR object)
        def get_value(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        name = get_value(case_details, "name")
        age = get_value(case_details, "age")
        last_seen = get_value(case_details, "last_seen")
        complainant_mobile = get_value(case_details, "complainant_mobile")
        birth_marks = get_value(case_details, "birth_marks")

        # Import database modules
        from pages.helper import db_queries
        from pages.helper.data_models import NotificationSubscribers
        from sqlmodel import Session, select
        from sqlalchemy import func

        area_key = _normalize_area(last_seen)
        with Session(db_queries.engine) as session:
            subscribers = session.exec(
                select(NotificationSubscribers)
                .where(func.lower(NotificationSubscribers.area) == area_key)
                .where(NotificationSubscribers.is_active == True)
            ).all()

        print(f"🔎 Subscribers found for '{area_key or last_seen}': {len(subscribers)}")

        recipient_emails = [sub.email for sub in subscribers]

        if not recipient_emails:
            print("⚠️ No subscribers found for this area. Email not sent.")
            return {"status": False, "error": "No subscribers in area", "sent_count": 0}

        subject = f"🚨 Missing Person in {last_seen}: {name}"

        body = f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2 style="color: #d32f2f;">🚨 Missing Person Alert - {last_seen}</h2>
            
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Age:</strong> {age} years</p>
            <p><strong>Last Seen:</strong> {last_seen}</p>
            <p><strong>Contact:</strong> {complainant_mobile}</p>
            <p><strong>Identifying Marks:</strong> {birth_marks or 'None'}</p>
            
            <div style="background: #fff3cd; padding: 15px; margin: 20px 0;">
                <strong>⚠️ If you see this person, please contact immediately.</strong>
            </div>
            
            <p style="color: #888; font-size: 11px;">
                You're receiving this because you subscribed to missing person alerts for {last_seen}.
            </p>
        </body>
        </html>
        """

        print(f"📨 Sending email to {len(recipient_emails)} subscribers...")

        _ = sender_email, sender_password  # kept for clarity, credentials already validated
        send_result = _send_email(
            to=recipient_emails,
            subject=subject,
            body=body,
        )
        if not send_result.get("status"):
            return {"status": False, "error": send_result.get("error"), "sent_count": 0}

        print("✅ Email sent successfully!")
        return {"status": True, "sent_count": len(recipient_emails), "area": area_key or last_seen}

    except Exception as e:
        print("❌ Email sending failed")
        print("Error details:", e)
        return {"status": False, "error": str(e), "sent_count": 0}


def send_sighting_alert(sighting_details):
    """
    Notify subscribers in the sighting location area.
    """
    try:
        from pages.helper import db_queries
        from pages.helper.data_models import NotificationSubscribers
        from sqlmodel import Session, select
        from sqlalchemy import func

        location = (sighting_details or {}).get("location", "")
        area_key = _normalize_area(location)
        if not area_key:
            return {"status": False, "error": "Invalid sighting area", "sent_count": 0}

        with Session(db_queries.engine) as session:
            subscribers = session.exec(
                select(NotificationSubscribers)
                .where(func.lower(NotificationSubscribers.area) == area_key)
                .where(NotificationSubscribers.is_active == True)
            ).all()

        recipient_emails = [sub.email for sub in subscribers]
        if not recipient_emails:
            return {"status": False, "error": "No subscribers in area", "sent_count": 0}

        reporter = (sighting_details or {}).get("reported_by", "Public User")
        mobile = (sighting_details or {}).get("mobile", "")
        features = (sighting_details or {}).get("features", "")
        subject = f"📍 New Sighting Alert in {area_key.title()}"
        body = f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📍 New Sighting Alert</h2>
            <p><strong>Location:</strong> {location}</p>
            <p><strong>Reported by:</strong> {reporter}</p>
            <p><strong>Contact:</strong> {mobile}</p>
            <p><strong>Details:</strong> {features or 'N/A'}</p>
        </body>
        </html>
        """
        send_result = _send_email(recipient_emails, subject, body)
        if not send_result.get("status"):
            return {"status": False, "error": send_result.get("error"), "sent_count": 0}
        return {"status": True, "sent_count": len(recipient_emails), "area": area_key}
    except Exception as e:
        return {"status": False, "error": str(e), "sent_count": 0}


def send_subscription_confirmation(email: str, area: str):
    """
    Send confirmation mail to newly subscribed user.
    """
    if not email:
        return {"status": False, "error": "Email missing"}

    subject = "✅ Subscription Confirmed - Missing Person Alerts"
    body = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2>✅ You're subscribed</h2>
        <p>You will now receive missing person alerts for <strong>{area}</strong>.</p>
        <p>Thank you for supporting community safety.</p>
    </body>
    </html>
    """
    result = _send_email(email, subject, body)
    if not result.get("status"):
        return {"status": False, "error": result.get("error")}
    return {"status": True}


def send_otp_email(email: str, otp: str):
    """Send OTP verification email to user."""
    subject = "🔐 Your OTP for Sighting Submission"
    body = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2>🔐 OTP Verification</h2>
        <p>Your one-time password for submitting a sighting report is:</p>
        <h1 style="color: #0f766e; letter-spacing: 8px;">{otp}</h1>
        <p>This OTP is valid for <strong>5 minutes</strong>.</p>
        <p style="color: #888; font-size: 11px;">If you did not request this, ignore this email.</p>
    </body>
    </html>
    """
    return _send_email(email, subject, body)