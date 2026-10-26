"""SMS / WhatsApp / Email sending.

Providers (Settings -> Messaging):
  log           - nothing leaves the server; messages are written to the message log as 'simulated' (default, safe for demos)
  twilio        - SMS + WhatsApp through Twilio's REST API
  africastalking- SMS through Africa's Talking (popular in Kenya)
Email is separate: it uses the SMTP settings (Gmail by default) whatever the SMS provider is.
"""
import smtplib
import ssl
from email.message import EmailMessage

import requests

from ..extensions import db
from ..models import MessageLog
from ..utils import get_setting, normalize_phone


def _twilio(channel, to, body):
    sid, token = get_setting("twilio_sid"), get_setting("twilio_token")
    frm = get_setting("twilio_whatsapp_from" if channel == "whatsapp" else "twilio_sms_from")
    if not (sid and token and frm):
        raise RuntimeError("Twilio credentials / sender number not configured")
    if channel == "whatsapp":
        to, frm = f"whatsapp:{to}", (frm if frm.startswith("whatsapp:") else f"whatsapp:{frm}")
    r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                      data={"To": to, "From": frm, "Body": body}, auth=(sid, token), timeout=20)
    if r.status_code >= 300:
        raise RuntimeError(f"Twilio error {r.status_code}: {r.text[:150]}")


def _africastalking(channel, to, body):
    if channel != "sms":
        raise RuntimeError("Africa's Talking provider only supports SMS; use Twilio for WhatsApp")
    user, key, sender = get_setting("at_username"), get_setting("at_api_key"), get_setting("at_sender_id")
    if not (user and key):
        raise RuntimeError("Africa's Talking credentials not configured")
    sandbox = user.lower() == "sandbox"
    host = "api.sandbox.africastalking.com" if sandbox else "api.africastalking.com"
    data = {"username": user, "to": to, "message": body}
    if sender and not sandbox:
        data["from"] = sender
    r = requests.post(f"https://{host}/version1/messaging", data=data, timeout=20,
                      headers={"apiKey": key, "Accept": "application/json"})
    if r.status_code >= 300:
        raise RuntimeError(f"Africa's Talking error {r.status_code}: {r.text[:150]}")


SUBJECTS = {
    "reminder_before": "Fee payment reminder",
    "reminder_overdue": "Overdue fee payment reminder",
    "payment": "Payment received",
    "completion": "Course completed",
    "certificate": "Your certificate is ready",
}


def _email(to, kind, body):
    """Sends an email through any SMTP server (Gmail by default). Returns 'sent' or 'simulated'
    (when no SMTP login has been configured yet)."""
    user, password = get_setting("smtp_user").strip(), get_setting("smtp_password").replace(" ", "")
    if not (user and password):
        return "simulated"
    host, port = get_setting("smtp_host").strip() or "smtp.gmail.com", int(get_setting("smtp_port") or 587)
    academy = get_setting("academy_name")
    msg = EmailMessage()
    msg["Subject"] = f"{academy}: {SUBJECTS.get(kind, 'Notification')}"
    msg["From"] = f"{academy} <{get_setting('smtp_from').strip() or user}>"
    msg["To"] = to
    msg.set_content(body)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.send_message(msg)
    return "sent"


def enabled_channels():
    ch = []
    if get_setting("channel_email") == "1":
        ch.append("email")
    if get_setting("channel_sms") == "1":
        ch.append("sms")
    if get_setting("channel_whatsapp") == "1":
        ch.append("whatsapp")
    return ch


def already_sent(dedupe_key):
    return bool(dedupe_key) and MessageLog.query.filter(
        MessageLog.dedupe_key == dedupe_key, MessageLog.status.in_(["sent", "simulated"])).first() is not None


def send_to_student(student, kind, body, dedupe_key=None, channels=None):
    """Sends `body` to the student on each enabled channel and logs the result."""
    provider = get_setting("msg_provider")
    to = normalize_phone(student.phone)
    results = []
    for ch in (channels or enabled_channels()):
        if ch == "email" and not (student.email or "").strip():
            continue  # no email address on file: nothing to send, nothing to log
        key = f"{dedupe_key}:{ch}" if dedupe_key else None
        if key and already_sent(key):
            continue
        status, err = "sent", None
        dest = to
        try:
            if ch == "email":
                dest = student.email.strip()
                status = _email(dest, kind, body)
            elif not to:
                raise RuntimeError("Student has no phone number")
            elif provider == "twilio":
                _twilio(ch, to, body)
            elif provider == "africastalking":
                _africastalking(ch, to, body)
            else:
                status = "simulated"
        except Exception as e:  # never let a provider failure break the main workflow
            status, err = "failed", str(e)[:250]
        db.session.add(MessageLog(student_id=student.id, channel=ch, kind=kind, dedupe_key=key,
                                  to_number=dest, body=body, status=status, error=err))
        results.append((ch, status))
    return results