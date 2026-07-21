"""
gmail_agent.py — Pydantic AI v2 Gmail Agent.

"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import (
    DEFAULT_MODEL,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPERATION_MODE,
    SCOPES,
    THINKING_EFFORT,
)
from capabilities.gmail_tools import gmail_tools
from capabilities.sofia_persona import sofia_persona
from capabilities.email_memory import email_memory
from gmail_utils import get_user_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schema — produced BY the agent, not manually constructed
# ---------------------------------------------------------------------------

class GmailResult(BaseModel):
    processed_emails: int = Field(
        description="Number of starred emails that were processed"
    )
    replies_created: int = Field(
        description="Number of replies created (drafts or sent)"
    )
    emails_archived: int = Field(
        description="Number of spam/promotional emails archived"
    )
    summary: str = Field(
        description="Brief human-readable summary of what was done"
    )


# ---------------------------------------------------------------------------
# Dependencies — simplified: no more api / openrouter side channel
# ---------------------------------------------------------------------------

@dataclass
class GmailDependencies:
    """Runtime dependencies injected per run."""
    service: Any          # Gmail API service (sync, wrapped in asyncio.to_thread)
    user_email: str       # Authenticated user's email (for agent detection)


# ---------------------------------------------------------------------------
# Model — v2 native routing, no custom OpenRouterModel class
# ---------------------------------------------------------------------------

def create_model():
    """Create the LLM model using v2's native provider system."""
    api_key = OPENROUTER_API_KEY or os.getenv("OPENAI_API_KEY") or "mock_key_for_init"
    base_url = OPENROUTER_BASE_URL if OPENROUTER_API_KEY else None
    model_name = DEFAULT_MODEL if OPENROUTER_API_KEY else OPENAI_MODEL

    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key,
    )
    logger.info("Using model %s (provider base_url: %s)", model_name, base_url or "default")
    return OpenAIChatModel(model_name, provider=provider)


# ---------------------------------------------------------------------------
# The Agent — thin composition root
# ---------------------------------------------------------------------------

gmail_agent = Agent(
    create_model(),
    deps_type=GmailDependencies,
    output_type=GmailResult,
    capabilities=[
        Thinking(effort=THINKING_EFFORT),  # reason about which emails need replies
        gmail_tools,                        # fetch, draft, send, star, archive
        sofia_persona,                      # warm, professional, language-matching
        email_memory,                       # thread context before replying
    ],
)


# ---------------------------------------------------------------------------
# Credentials — with token refresh (v1 was missing this)
# ---------------------------------------------------------------------------

def load_credentials() -> Credentials:
    """Load Gmail OAuth credentials, refreshing if expired."""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            logger.info("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())
        logger.info("Token saved to token.json")

    return creds


# ---------------------------------------------------------------------------
# Main — the agent RUNS. No DummyRunContext. No manual tool calls.
# ---------------------------------------------------------------------------

async def main():
    """Run the Gmail agent."""
    logger.info("Starting Gmail Agent (mode: %s)", OPERATION_MODE)

    # Load credentials and build Gmail service
    creds = load_credentials()
    service = build("gmail", "v1", credentials=creds)
    user_email = get_user_email(service)
    logger.info("Authenticated as: %s", user_email)

    deps = GmailDependencies(service=service, user_email=user_email)

    # Build the instruction based on operation mode
    if OPERATION_MODE == "auto":
        action = "send the reply directly using send_reply"
    else:
        action = "create a draft reply using create_reply_draft"

    instruction = (
        f"Process my starred emails. My email address is {user_email}.\n\n"
        f"For each starred email:\n"
        f"1. Check if it has the UNREAD label. Skip it if not.\n"
        f"2. Check the thread context. If the latest message is from "
        f"{user_email} (me), skip it — I already replied.\n"
        f"3. Skip spam and promotional emails.\n"
        f"4. For emails that need a reply: read the thread context, "
        f"then generate a helpful, comprehensive reply and {action}.\n"
        f"5. Remove the star after processing each email.\n\n"
        f"After processing all starred emails, archive spam and "
        f"promotional emails.\n\n"
        f"Produce a summary of everything you did."
    )

    # THE AGENT RUNS. It decides which tools to call, in what order,
    # generates the reply text itself, and produces the GmailResult.
    result = await gmail_agent.run(instruction, deps=deps)

    # Print the structured output
    output = result.output
    print("\n" + "=" * 60)
    print("GMAIL AGENT RESULTS")
    print("=" * 60)
    print(f"  Emails processed:  {output.processed_emails}")
    print(f"  Replies created:   {output.replies_created}")
    print(f"  Emails archived:   {output.emails_archived}")
    print(f"  Summary:           {output.summary}")
    print("=" * 60)

    return output


if __name__ == "__main__":
    asyncio.run(main())