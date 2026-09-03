import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, token: str) -> None:
    if not settings.gmail_username or not settings.gmail_app_password:
        logger.error("Password reset email was not sent: Gmail SMTP is not configured")
        return

    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your VeriGate password"
    message["From"] = f"{settings.email_from_name} <{settings.gmail_username}>"
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your VeriGate password.\n\n"
        f"Open this link to choose a new password:\n{reset_url}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes. "
        "If you did not request this reset, you can ignore this email."
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(settings.gmail_username, settings.gmail_app_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Unable to send password reset email")
