"""
Centralized configuration for the Gmail Agent.
All tunables live here.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Model / LLM
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.getenv("MY_OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("GMAIL_AGENT_MODEL", "google/gemini-3.5-flash")

# Fallback if no OpenRouter key: use OpenAI directly
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

# ---------------------------------------------------------------------------
# Operation mode
# ---------------------------------------------------------------------------

# "draft" = create drafts for review (default, safe)
# "auto"  = send replies directly (use with caution)
OPERATION_MODE = os.getenv("OPERATION_MODE", "draft")

# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
MAX_STARRED_EMAILS = int(os.getenv("MAX_STARRED_EMAILS", "10"))

# ---------------------------------------------------------------------------
# Thinking
# ---------------------------------------------------------------------------

THINKING_EFFORT = os.getenv("THINKING_EFFORT", "high")  # low | medium | high