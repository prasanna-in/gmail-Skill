"""
Gmail API Common Utilities

This module provides shared authentication and utility functions for all Gmail scripts.
It handles OAuth2 credential management, token refresh, and common operations.

Educational Note:
- OAuth2 Flow: Check for existing token → Auto-refresh if expired → Use credentials
- Token Management: Tokens are saved and reused to avoid repeated authentication
- Error Handling: All functions return standardized JSON for easy parsing by Claude
"""

import base64
import json
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Determine credential directory (relative to this script's location)
# Structure: skills/gmail/scripts/gmail_common.py -> credentials/
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
CRED_DIR = PROJECT_ROOT / "credentials"
TOKEN_FILE = CRED_DIR / "token.json"
CREDENTIALS_FILE = CRED_DIR / "credentials.json"


def get_gmail_service(scopes: list[str]):
    """
    Returns authenticated Gmail API service.

    OAuth2 Flow:
    1. Check if token.json exists (previously authenticated)
    2. Load credentials from token
    3. If expired but has refresh_token, auto-refresh
    4. If no valid credentials, raise error (user needs to run gmail_auth.py)

    Args:
        scopes: List of OAuth scopes required (e.g., ['https://www.googleapis.com/auth/gmail.modify'])

    Returns:
        Authenticated Gmail API service object

    Raises:
        FileNotFoundError: If credentials are missing
        Exception: If authentication fails
    """
    creds = None

    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)

    # Refresh token if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Auto-refresh expired token
            try:
                creds.refresh(Request())
                # Save refreshed token for future use
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                raise Exception(
                    f"Token refresh failed: {str(e)}\n"
                    f"Please re-authenticate by running: python {SCRIPT_DIR}/gmail_auth.py"
                )
        else:
            # No valid credentials - user needs to authenticate
            raise FileNotFoundError(
                f"No valid credentials found.\n"
                f"Please run: python {SCRIPT_DIR}/gmail_auth.py\n"
                f"Ensure {CREDENTIALS_FILE} exists before running authentication."
            )

    # Build and return Gmail API service
    return build('gmail', 'v1', credentials=creds)


def format_error(error_type: str, message: str, **kwargs) -> str:
    """
    Standardized JSON error output for all scripts.

    Args:
        error_type: Type of error (e.g., "AuthenticationError", "APIError")
        message: Human-readable error message
        **kwargs: Additional error context fields

    Returns:
        JSON string with error details
    """
    error_dict = {
        "status": "error",
        "error_type": error_type,
        "message": message
    }
    error_dict.update(kwargs)
    return json.dumps(error_dict, indent=2)


def format_success(data: dict) -> str:
    """
    Standardized JSON success output for all scripts.

    Args:
        data: Dictionary containing response data

    Returns:
        JSON string with success status and data
    """
    result = {"status": "success"}
    result.update(data)
    return json.dumps(result, indent=2)


def parse_message(raw_message: dict, format_type: str = "metadata") -> dict:
    """
    Extract fields from Gmail API message object.

    Args:
        raw_message: Raw message dict from Gmail API
        format_type: Level of detail - "minimal", "metadata", or "full"

    Returns:
        Parsed message dictionary with selected fields
    """
    message = {
        "id": raw_message.get("id"),
        "threadId": raw_message.get("threadId")
    }

    if format_type == "minimal":
        return message

    # Extract headers for metadata and full formats
    headers = raw_message.get("payload", {}).get("headers", [])
    header_dict = {h["name"].lower(): h["value"] for h in headers}

    message["subject"] = header_dict.get("subject", "(No subject)")
    message["from"] = header_dict.get("from", "(Unknown sender)")
    message["to"] = header_dict.get("to", "")
    message["date"] = header_dict.get("date", "")
    message["snippet"] = raw_message.get("snippet", "")

    if format_type == "full":
        # Extract message body (plain text)
        message["body"] = decode_body(raw_message.get("payload", {}))

    return message


def decode_body(payload: dict) -> str:
    """
    Extract plain text body from message payload.

    Gmail messages can have complex MIME structures:
    - Plain text messages: body directly in payload
    - Multipart messages: body in parts array
    - Nested parts: recursively search for text/plain

    Args:
        payload: Message payload from Gmail API

    Returns:
        Decoded plain text body
    """
    # Check if body data is directly available
    if "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    # Check parts for multipart messages
    if "parts" in payload:
        for part in payload["parts"]:
            # Look for text/plain MIME type
            if part.get("mimeType") == "text/plain":
                if "data" in part.get("body", {}):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")

            # Recursively check nested parts
            if "parts" in part:
                text = decode_body(part)
                if text:
                    return text

    return "(Body could not be decoded)"


def create_message(
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    attachments: Optional[list[str]] = None
) -> str:
    """
    Build RFC822 MIME message for sending via Gmail API.

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Plain text email body
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        attachments: Optional list of file paths to attach

    Returns:
        Base64url-encoded RFC822 message string
    """
    # Create multipart message
    message = MIMEMultipart()
    message["To"] = ", ".join(to)
    message["Subject"] = subject

    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)

    # Attach body as text/plain
    message.attach(MIMEText(body, "plain"))

    # Attach files if provided
    if attachments:
        for filepath in attachments:
            path = Path(filepath)
            if not path.exists():
                raise FileNotFoundError(f"Attachment not found: {filepath}")

            # Read file and create attachment
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())

            # Encode in base64
            encoders.encode_base64(part)

            # Add header with filename
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {path.name}"
            )

            message.attach(part)

    # Encode message as base64url string
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return raw_message


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        True if email appears valid, False otherwise
    """
    # Simple validation: contains @ and at least one dot after @
    if "@" not in email:
        return False

    local, domain = email.rsplit("@", 1)
    if not local or not domain:
        return False

    if "." not in domain:
        return False

    return True


def log_verbose(message: str, verbose: bool = False):
    """
    Log message to stderr if verbose mode is enabled.

    Args:
        message: Message to log
        verbose: Whether verbose logging is enabled
    """
    if verbose:
        print(f"[VERBOSE] {message}", file=sys.stderr)


def status_start(message: str):
    """Print start status (→) to stderr."""
    print(f"→ {message}", file=sys.stderr, flush=True)


def status_done(message: str):
    """Print completion status (✓) to stderr."""
    print(f"✓ {message}", file=sys.stderr, flush=True)


def status_async(message: str):
    """Print async/LLM operation status (⟳) to stderr."""
    print(f"⟳ {message}", file=sys.stderr, flush=True)
