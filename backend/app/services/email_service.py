# Why: Email delivery service supporting console and SMTP backends (e.g. Mailtrap).
# Dispatches booking confirmations, reschedules, cancellations, 24h reminders,
# and waitlist 15-minute slot offers via FastAPI BackgroundTasks.

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Any

from app.core.config import settings

logger = logging.getLogger("stylify.email")

# In-memory log of dispatched emails for unit testing and local audit
sent_emails_log: list[dict[str, Any]] = []


def clear_sent_emails_log() -> None:
    """Clears the in-memory email log (used in test fixtures)."""
    sent_emails_log.clear()


def send_email_sync(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> None:
    """
    Synchronous email worker invoked via FastAPI BackgroundTasks.
    Switches dynamically between 'console' (dev/test logging) and 'smtp' (Mailtrap / real server).
    """
    record = {
        "to": to_email,
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
    }
    sent_emails_log.append(record)

    if settings.EMAIL_BACKEND == "console":
        logger.info(
            f"[EMAIL:CONSOLE] To: {to_email} | Subject: '{subject}'\n{body_text}\n"
        )
        return

    # SMTP delivery
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        part1 = MIMEText(body_text, "plain")
        msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"[EMAIL:SMTP] Sent email to {to_email} via {settings.SMTP_HOST}")
    except Exception as exc:
        logger.error(f"[EMAIL:ERROR] Failed to send email to {to_email}: {exc}")


# ── Templated Email Helpers ──

def build_booking_confirmation_content(
    customer_name: str,
    service_name: str,
    stylist_name: str,
    start_ts_str: str,
    end_ts_str: str,
) -> tuple[str, str]:
    subject = "Booking Confirmed - Stylify Salon"
    body = (
        f"Hello {customer_name},\n\n"
        f"Your appointment has been confirmed!\n\n"
        f"• Service: {service_name}\n"
        f"• Stylist: {stylist_name}\n"
        f"• Time: {start_ts_str} to {end_ts_str} UTC\n\n"
        f"Thank you for choosing Stylify. See you soon!"
    )
    return subject, body


def build_booking_reschedule_content(
    customer_name: str,
    service_name: str,
    stylist_name: str,
    new_start_ts_str: str,
    new_end_ts_str: str,
) -> tuple[str, str]:
    subject = "Appointment Rescheduled - Stylify Salon"
    body = (
        f"Hello {customer_name},\n\n"
        f"Your appointment has been successfully rescheduled.\n\n"
        f"• Service: {service_name}\n"
        f"• Stylist: {stylist_name}\n"
        f"• New Time: {new_start_ts_str} to {new_end_ts_str} UTC\n\n"
        f"If you need to make further adjustments, please visit your Stylify account."
    )
    return subject, body


def build_booking_cancellation_content(
    customer_name: str,
    service_name: str,
    start_ts_str: str,
) -> tuple[str, str]:
    subject = "Appointment Cancelled - Stylify Salon"
    body = (
        f"Hello {customer_name},\n\n"
        f"Your appointment for {service_name} on {start_ts_str} UTC has been cancelled.\n\n"
        f"We hope to see you again soon. Feel free to re-book anytime on Stylify!"
    )
    return subject, body


def build_booking_reminder_content(
    customer_name: str,
    service_name: str,
    stylist_name: str,
    start_ts_str: str,
) -> tuple[str, str]:
    subject = "Upcoming Appointment Reminder (24 Hours) - Stylify Salon"
    body = (
        f"Hello {customer_name},\n\n"
        f"This is a reminder that you have an appointment in 24 hours:\n\n"
        f"• Service: {service_name}\n"
        f"• Stylist: {stylist_name}\n"
        f"• Start Time: {start_ts_str} UTC\n\n"
        f"Please arrive 5 minutes early. See you tomorrow!"
    )
    return subject, body


def build_waitlist_offer_content(
    customer_name: str,
    service_name: str,
    stylist_name: str,
    slot_start_str: str,
    expires_at_str: str,
    claim_url: str,
) -> tuple[str, str]:
    subject = "Slot Available! You Have 15 Minutes to Claim - Stylify Salon"
    body = (
        f"Hello {customer_name},\n\n"
        f"Great news! A slot has opened up for your waitlisted appointment:\n\n"
        f"• Service: {service_name}\n"
        f"• Stylist: {stylist_name}\n"
        f"• Slot Time: {slot_start_str} UTC\n"
        f"• Claim Window Closes At: {expires_at_str} UTC (15 minutes)\n\n"
        f"Claim this slot right away before it expires and cascades to the next person:\n"
        f"{claim_url}\n\n"
        f"Best regards,\nStylify Salon Team"
    )
    return subject, body

