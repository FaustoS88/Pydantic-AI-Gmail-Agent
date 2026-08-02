# Gmail Pydantic AI Agent (v2)

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

An intelligent, autonomous AI agent built with **Pydantic AI v2** to monitor, triage, and reply to Gmail messages.

Unlike traditional linear pipelines that call LLMs as step-by-step helper functions, this architecture puts **Pydantic AI in full control**: the agent evaluates unread starred emails, reads thread context, decides whether to generate replies, constructs drafts or sends messages, and manages stars — producing structured output (`GmailResult`) directly.

## 🚀 Key Improvements in v2

- **True Agentic Control**: `gmail_agent.run()` orchestrates tool calls, reasoning loops, and structured output. No manual tool invocation or dummy context hacks.
- **Pydantic AI v2 Capability Architecture**:
  - `gmail_tools`: 6 atomic Gmail actions (`fetch_starred_emails`, `get_thread_context`, `create_reply_draft`, `send_reply`, `remove_star`, `archive_unwanted`).
  - `sofia_persona`: Persona instructions for warm, professional, language-matching email generation.
  - `email_memory`: Contextual thread awareness instructions (replaces 400+ lines of fragile regex extraction).
- **Thinking Capability**: Integrated `Thinking(effort="high")` for extended reasoning across complex email threads.
- **Safe Archiving**: Unwanted spam/promotions are archived (moved to All Mail) rather than permanently deleted.
- **Token Management**: Automatic OAuth token refresh in `load_credentials()` and `get_tokens.py`.
- **Security & Prompt Guard**: Explicit prompt injection protection enforcing email content as untrusted data.

---

## 🛠️ Architecture

```
Pydantic-AI-Gmail-Agent/
├── config.py                 # Centralized configuration & environment tunables
├── gmail_utils.py            # Shared Gmail helpers (header extraction, MIME threading)
├── gmail_agent.py            # Entry point: agent initialization & agent.run()
├── get_tokens.py             # OAuth token setup and automatic refresh
├── capabilities/             # Pydantic AI v2 Capability modules
│   ├── gmail_tools.py        # Gmail API action tools
│   ├── sofia_persona.py      # Reply persona and prompt injection guardrails
│   └── email_memory.py       # Thread context & continuity instructions
├── requirements.txt          # Explicit dependency declarations
├── credentials.json.example  # Google OAuth client example
├── .env.example              # Environment variables template
└── tests/                    # Unit test suite
    ├── test_gmail_utils.py
    └── test_agent.py
```

---

## 💻 Installation

1. **Clone the repository and install dependencies**:
   ```bash
   git clone https://github.com/FaustoS88/Pydantic-AI-Gmail-Agent.git
   cd Pydantic-AI-Gmail-Agent
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   MY_OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPERATION_MODE=draft   # "draft" (creates drafts for review) or "auto" (sends directly)
   ```

3. **Set Up Google OAuth Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the **Gmail API** under *APIs & Services*
   - Configure *OAuth consent screen* and add your email to *Test Users*
   - Create *OAuth Client ID* (Desktop application)
   - Download the JSON credentials file and save it as `credentials.json` in the root directory.

4. **Authorize Access**:
   ```bash
   python get_tokens.py
   ```
   Follow the browser prompt. `token.json` will be generated with automatic refresh support.

---

## ⚡ Usage

Run the agent:
```bash
python gmail_agent.py
```

### Agent Execution Workflow

```
1. Fetch Starred Emails  ──►  Reads unread messages from starred threads
2. Thread Context       ──►  Fetches full message history per thread
3. Reason & Draft/Send  ──►  Sofia persona generates language-matched reply
4. Unstar & Archive     ──►  Removes star flag & archives promotional spam
5. Structured Result    ──►  Returns GmailResult(processed, replies, archived, summary)
```

---

## 🧪 Testing

Run the automated test suite:
```bash
pytest tests/
```

---

## 📜 License

AGPL-3.0-or-later — see [`LICENSE`](LICENSE).

Copyright © 2025–2026 Fausto Saccoccio.
