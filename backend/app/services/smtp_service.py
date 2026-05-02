import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_reminder_email(subject: str, body_html: str, to_email: str) -> None:
    if not settings.smtp_configured:
        logger.warning("SMTP not configured, skipping reminder email: %s", subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_user, to_email, msg.as_string())
        logger.info("Reminder email sent to %s: %s", to_email, subject)
    except Exception:
        logger.exception("Failed to send reminder email: %s", subject)
