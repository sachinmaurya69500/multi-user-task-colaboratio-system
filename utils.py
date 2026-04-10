import os
import smtplib
import ssl
import hashlib
import hmac
import secrets
from datetime import datetime
from email.message import EmailMessage


def _secret_key() -> str:
    return os.getenv("OTP_SECRET_KEY", "change-this-in-production")


def generate_otp(length: int = 6) -> str:
    # Generate a numeric OTP code.
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_otp(otp: str) -> str:
    payload = f"{_secret_key()}:{otp}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_otp(otp: str, hashed_otp: str) -> bool:
    return hmac.compare_digest(hash_otp(otp), hashed_otp)


def send_email(to_email: str, subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "")

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        raise RuntimeError(
            "SMTP configuration missing. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM."
        )

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def send_otp_email(to_email: str, otp: str, purpose: str, expires_at: datetime) -> None:
    purpose_text = "registration" if purpose == "register" else "login"
    subject = f"Your OTP for {purpose_text}"
    body = (
        f"Your OTP code is: {otp}\n\n"
        f"This OTP is for {purpose_text} and expires at {expires_at.isoformat()} UTC."
    )
    send_email(to_email, subject, body)


def send_task_assignment_email(to_email: str, task_title: str, due_date: str | None = None) -> None:
    due_text = due_date if due_date else "Not specified"
    subject = "New task assigned to you"
    body = (
        "A new task has been assigned to you.\n\n"
        f"Title: {task_title}\n"
        f"Due Date: {due_text}\n"
        "Please log in to your dashboard to update task status."
    )
    send_email(to_email, subject, body)
