"""SMS / WhatsApp sending.

Providers (Settings -> Messaging):
  log           - nothing leaves the server; messages are written to the message log as 'simulated' (default, safe for demos)
  twilio        - SMS + WhatsApp through Twilio's REST API
  africastalking- SMS through Africa's Talking (popular in Kenya)
"""
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
    data = {"username": user, "to": to, "message": body}
    if sender:
        data["from"] = sender
    r = requests.post("https://api.africastalking.com/version1/messaging", data=data, timeout=20,
                      headers={"apiKey": key, "Accept": "application/json"})
    if r.status_code >= 300:
        raise RuntimeError(f"Africa's Talking error {r.status_code}: {r.text[:150]}")


def enabled_channels():
    ch = []
    if get_setting("channel_sms") == "1":
        ch.append("sms")
    if get_setting("channel_whatsapp") == "1":
        ch.append("whatsapp")
    return ch


def already_sent(dedupe_key):
    return bool(dedupe_key) and MessageLog.query.filter(
        MessageLog.dedupe_key == dedupe_key, MessageLog.status.in_(["sent", "simulated"])).first() is not None


def send_to_student(student, kind, body, dedupe_key=None, channels=None):
    """Sends `body` to the student's phone on each enabled channel and logs the result."""
    provider = get_setting("msg_provider")
    to = normalize_phone(student.phone)
    results = []
    for ch in (channels or enabled_channels()):
        key = f"{dedupe_key}:{ch}" if dedupe_key else None
        if key and already_sent(key):
            continue
        status, err = "sent", None
        try:
            if not to:
                raise RuntimeError("Student has no phone number")
            if provider == "twilio":
                _twilio(ch, to, body)
            elif provider == "africastalking":
                _africastalking(ch, to, body)
            else:
                status = "simulated"
        except Exception as e:  # never let a provider failure break the main workflow
            status, err = "failed", str(e)[:250]
        db.session.add(MessageLog(student_id=student.id, channel=ch, kind=kind, dedupe_key=key,
                                  to_number=to, body=body, status=status, error=err))
        results.append((ch, status))
    return results
