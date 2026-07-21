"""Tests for gmail_agent.py — agent capabilities and structure."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock
import pytest

from gmail_agent import GmailDependencies, GmailResult, gmail_agent
from capabilities.gmail_tools import gmail_tools
from capabilities.sofia_persona import sofia_persona
from capabilities.email_memory import email_memory


class TestGmailResult:
    def test_schema_validates(self):
        res = GmailResult(
            processed_emails=2,
            replies_created=2,
            emails_archived=5,
            summary="Processed 2 emails, created 2 drafts.",
        )
        assert res.processed_emails == 2
        assert res.replies_created == 2
        assert res.emails_archived == 5

    def test_json_roundtrip(self):
        res = GmailResult(
            processed_emails=1,
            replies_created=1,
            emails_archived=0,
            summary="Processed 1 email",
        )
        json_str = res.model_dump_json()
        restored = GmailResult.model_validate_json(json_str)
        assert restored == res


class TestAgentCapabilities:
    def test_agent_output_type(self):
        assert gmail_agent._output_type is not None

    def test_capabilities_registered(self):
        assert gmail_tools is not None
        assert sofia_persona is not None
        assert email_memory is not None
        assert "fetch_starred_emails" in gmail_tools._function_toolset.tools
        assert "get_thread_context" in gmail_tools._function_toolset.tools
        assert "create_reply_draft" in gmail_tools._function_toolset.tools
        assert "send_reply" in gmail_tools._function_toolset.tools
        assert "remove_star" in gmail_tools._function_toolset.tools
        assert "archive_unwanted" in gmail_tools._function_toolset.tools

    def test_agent_deps_type(self):
        deps = GmailDependencies(service=MagicMock(), user_email="test@example.com")
        assert deps.user_email == "test@example.com"
