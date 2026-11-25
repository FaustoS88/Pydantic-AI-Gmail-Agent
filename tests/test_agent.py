# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Fausto Saccoccio
"""Tests for gmail_agent.py — agent capabilities and structure."""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
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
        assert "remove_star" in gmail_tools._function_toolset.tools
        assert "archive_unwanted" in gmail_tools._function_toolset.tools

    def test_agent_deps_type(self):
        deps = GmailDependencies(service=MagicMock(), user_email="test@example.com")
        assert deps.user_email == "test@example.com"


_MODEL_VIEW = """
import asyncio, json
from unittest.mock import MagicMock
import dotenv
dotenv.load_dotenv = lambda *a, **k: False  # a local .env must not set the mode
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from gmail_agent import GmailDependencies, gmail_agent

seen = {}

def model(messages, info):
    seen["tools"] = sorted(t.name for t in info.function_tools)
    seen["instructions"] = messages[-1].instructions or ""
    args = {"processed_emails": 0, "replies_created": 0, "emails_archived": 0, "summary": ""}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

async def main():
    deps = GmailDependencies(service=MagicMock(), user_email="me@example.com")
    with gmail_agent.override(model=FunctionModel(model)):
        await gmail_agent.run("Process my starred emails.", deps=deps)

asyncio.run(main())
print(json.dumps(seen))
"""


def _model_view_in_mode(mode: str | None) -> dict:
    """Tools and instructions the model receives, from a fresh interpreter since the mode is read at import time."""
    env = {k: v for k, v in os.environ.items() if k != "OPERATION_MODE"}
    if mode is not None:
        env["OPERATION_MODE"] = mode
    out = subprocess.run(
        [sys.executable, "-c", _MODEL_VIEW],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.splitlines()[-1])


class TestOperationMode:
    @pytest.mark.parametrize("mode", [None, "draft"])
    def test_draft_mode_has_no_send_tool(self, mode):
        res = _model_view_in_mode(mode)
        assert "create_reply_draft" in res["tools"]
        assert "create_reply_draft" in res["instructions"]
        assert "send_reply" not in res["tools"]
        assert "send_reply" not in res["instructions"]

    def test_auto_mode_has_send_tool(self):
        res = _model_view_in_mode("auto")
        assert "send_reply" in res["tools"]
        assert "send_reply" in res["instructions"]
