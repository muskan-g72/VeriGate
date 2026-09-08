"""Email service for transactional notifications."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """
    Send a password reset link to the given recipient.
    If SMTP is configured, sends via SMTP.
    Otherwise, logs the link for development/test inspection.
    """
    subject = "Reset your VeriGate password"
    text_content = (
        f"Hello,\n\n"
        f"We received a request to reset your VeriGate password.\n\n"
        f"Click the link below to set a new password:\n"
        f"{reset_link}\n\n"
        f"This link will expire in {settings.password_reset_token_expire_minutes} minutes.\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )
    html_content = (
        f"<p>Hello,</p>"
        f"<p>We received a request to reset your VeriGate password.</p>"
        f'<p><a href="{reset_link}" style="display:inline-block;padding:10px 20px;background:#7c3aed;color:#ffffff;text-decoration:none;border-radius:6px;">Reset Password</a></p>'
        f'<p>Or copy and paste this link into your browser:<br><a href="{reset_link}">{reset_link}</a></p>'
        f"<p>This link will expire in {settings.password_reset_token_expire_minutes} minutes.</p>"
        f"<p>If you did not request this, you can safely ignore this email.</p>"
    )

    if settings.smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.emails_from
            msg["To"] = to_email

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)

            logger.info("Sent password reset email via SMTP to %s", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to send password reset email via SMTP to %s: %s", to_email, exc)
            return False

    # Development & Testing fallback: Log the link
    logger.info(
        "[DEV EMAIL] Password reset email for %s: %s (expires in %s min)",
        to_email,
        reset_link,
        settings.password_reset_token_expire_minutes,
    )
    return True
