"""
gmail_utils.py — Shared Gmail helpers.

"""

from __future__ import annotations

import base64
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any


def get_header(message: dict, name: str) -> str:
    """Get a header value from a Gmail message (case-insensitive)."""
    for h in message.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def extract_email_content(message: dict) -> str:
    """Extract readable text content from a Gmail message.

    Handles multipart messages, base64url encoding, and strips
    quoted reply history (lines starting with '>').
    """
    payload = message.get("payload", {})
    body_data = ""

    # Try direct body first
    if payload.get("body", {}).get("data"):
        body_data = payload["body"]["data"]
    else:
        # Search parts for text/plain
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body_data = part["body"]["data"]
                break
            # Nested multipart
            for sub in part.get("parts", []):
                if sub.get("mimeType") == "text/plain" and sub.get("body", {}).get("data"):
                    body_data = sub["body"]["data"]
                    break

    if not body_data:
        return message.get("snippet", "")

    try:
        decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
    except Exception:
        return message.get("snippet", "")

    # Strip quoted reply history
    lines = decoded.split("\n")
    clean_lines = []
    for line in lines:
        if line.strip().startswith(">"):
            break  # Stop at first quoted block
        clean_lines.append(line)

    return "\n".join(clean_lines).strip()


def resolve_recipient(message: dict) -> str:
    """Determine who to reply to.

    If the message is in SENT (we sent it), reply to the 'to' field.
    Otherwise, reply to the 'from' field.
    """
    labels = message.get("labelIds", [])
    if "SENT" in labels:
        return get_header(message, "to")
    return get_header(message, "from")


def build_reply_raw(service: Any, message_id: str, reply_content: str) -> str:
    """Build a properly threaded reply email (base64url-encoded).

    """
    original = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    to = resolve_recipient(original)
    subject = get_header(original, "subject")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg_id = get_header(original, "message-id")
    references = get_header(original, "references")

    mime = MIMEMultipart()
    mime["to"] = to
    mime["subject"] = subject
    if msg_id:
        mime["In-Reply-To"] = msg_id
        mime["References"] = f"{references} {msg_id}" if references else msg_id

    mime.attach(MIMEText(reply_content, "plain"))
    return base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")


def get_user_email(service: Any) -> str:
    """Get the authenticated user's email address.
    Used for agent-detection
    """
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def format_email_for_model(message: dict, index: int) -> str:
    """Format a Gmail message as a readable string for the model."""
    headers = {
        "from": get_header(message, "from"),
        "to": get_header(message, "to"),
        "subject": get_header(message, "subject"),
        "date": get_header(message, "date"),
    }
    labels = message.get("labelIds", [])
    content = extract_email_content(message)
    snippet = message.get("snippet", "")

    return (
        f"--- Email {index} ---\n"
        f"ID: {message['id']}\n"
        f"Thread ID: {message.get('threadId', 'unknown')}\n"
        f"From: {headers['from']}\n"
        f"To: {headers['to']}\n"
        f"Subject: {headers['subject']}\n"
        f"Date: {headers['date']}\n"
        f"Labels: {', '.join(labels)}\n"
        f"Has UNREAD: {'UNREAD' in labels}\n"
        f"Snippet: {snippet}\n"
        f"Full content:\n{content}\n"
    )