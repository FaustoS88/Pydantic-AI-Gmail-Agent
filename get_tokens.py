"""
get_tokens.py — Gmail OAuth token setup with automatic refresh.
Usage:
    python get_tokens.py          # First-time setup or refresh
"""

import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import SCOPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_or_refresh_token() -> Credentials:
    """Get valid credentials, refreshing or re-authorizing as needed."""
    creds = None

    # Try loading existing token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        logger.info("Loaded existing token from token.json")

    # Token is valid — nothing to do
    if creds and creds.valid:
        logger.info("Token is valid. No action needed.")
        return creds

    # Token expired but has a refresh token — refresh it
    if creds and creds.expired and creds.refresh_token:
        logger.info("Token expired. Refreshing...")
        try:
            creds.refresh(Request())
            with open("token.json", "w") as token:
                token.write(creds.to_json())
            logger.info("Token refreshed and saved successfully.")
            return creds
        except Exception as e:
            logger.warning("Token refresh failed: %s. Starting new OAuth flow.", e)

    # No token or refresh failed — full OAuth flow
    logger.info("Starting OAuth authorization flow...")
    if not os.path.exists("credentials.json"):
        logger.error(
            "credentials.json not found. Download it from Google Cloud Console "
            "(APIs & Services → Credentials → Create Credentials → OAuth client ID "
            "→ Desktop app). See README.md for detailed instructions."
        )
        raise FileNotFoundError("credentials.json not found")

    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as token:
        token.write(creds.to_json())
    logger.info("Authorization complete. Token saved to token.json")

    return creds


if __name__ == "__main__":
    get_or_refresh_token()
    print("\nDone! You can now run: python gmail_agent.py")