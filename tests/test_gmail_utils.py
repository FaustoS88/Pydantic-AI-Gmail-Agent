"""Tests for gmail_utils.py — shared Gmail helpers."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock
import pytest

from gmail_utils import (
    extract_email_content,
    format_email_for_model,
    get_header,
    resolve_recipient,
)


@pytest.fixture
def sample_message():
    raw_body = "Hello Sofia,\n\nI have a question about the project.\n\n> Quoted reply to strip"
    encoded_body = base64.urlsafe_b64encode(raw_body.encode("utf-8")).decode("utf-8")

    return {
        "id": "msg123",
        "threadId": "thread456",
        "snippet": "Hello Sofia, I have a question...",
        "labelIds": ["STARRED", "UNREAD", "INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Alex <alex@example.com>"},
                {"name": "To", "value": "Sofia <me@example.com>"},
                {"name": "Subject", "value": "Project Question"},
                {"name": "Date", "value": "Tue, 21 Jul 2026 12:00:00 +0000"},
                {"name": "Message-ID", "value": "<msg123@example.com>"},
            ],
            "body": {"data": encoded_body},
        },
    }


class TestGetHeader:
    def test_case_insensitive_match(self, sample_message):
        assert get_header(sample_message, "from") == "Alex <alex@example.com>"
        assert get_header(sample_message, "SUBJECT") == "Project Question"
        assert get_header(sample_message, "date") == "Tue, 21 Jul 2026 12:00:00 +0000"

    def test_missing_header_returns_empty(self, sample_message):
        assert get_header(sample_message, "nonexistent") == ""


class TestExtractEmailContent:
    def test_extracts_and_strips_quoted_reply(self, sample_message):
        content = extract_email_content(sample_message)
        assert "Hello Sofia," in content
        assert "I have a question about the project." in content
        assert "Quoted reply to strip" not in content

    def test_fallback_to_snippet_if_no_body(self):
        msg = {"snippet": "Fallback snippet"}
        assert extract_email_content(msg) == "Fallback snippet"


class TestResolveRecipient:
    def test_resolves_from_for_received_message(self, sample_message):
        assert resolve_recipient(sample_message) == "Alex <alex@example.com>"

    def test_resolves_to_for_sent_message(self, sample_message):
        sample_message["labelIds"].append("SENT")
        assert resolve_recipient(sample_message) == "Sofia <me@example.com>"


class TestFormatEmailForModel:
    def test_formats_message_readable(self, sample_message):
        formatted = format_email_for_model(sample_message, 1)
        assert "--- Email 1 ---" in formatted
        assert "ID: msg123" in formatted
        assert "From: Alex <alex@example.com>" in formatted
        assert "Subject: Project Question" in formatted
        assert "Has UNREAD: True" in formatted
