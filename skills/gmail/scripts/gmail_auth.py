#!/usr/bin/env python3
"""
Gmail OAuth2 Authentication Setup

This script handles the initial OAuth2 authentication flow for Gmail API access.
It opens a browser for user consent and saves the resulting tokens for future use.

Usage:
    python gmail_auth.py [--scopes SCOPE1,SCOPE2]

Educational Note:
- This is a one-time setup (unless scopes change or tokens are revoked)
- The browser flow allows users to grant specific permissions
- Tokens are automatically refreshed by other scripts using gmail_common.py
"""

import argparse
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Import common utilities
from gmail_common import (
    CREDENTIALS_FILE,
    TOKEN_FILE,
    format_error,
    format_success,
    log_verbose,
    status_start,
    status_done
)


# Default OAuth scopes for full Gmail access
DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify'
]


def authenticate(scopes: list[str], verbose: bool = False) -> dict:
    """
    Perform OAuth2 authentication flow.

    Steps:
    1. Check if credentials.json exists
    2. Launch browser-based OAuth consent flow
    3. User grants permissions in browser
    4. Save resulting tokens to token.json
    5. Validate tokens by making a test API call

    Args:
        scopes: List of OAuth scopes to request
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with authentication result

    Raises:
        FileNotFoundError: If credentials.json is missing
        Exception: If authentication fails
    """
    # Check if credentials file exists
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {CREDENTIALS_FILE}\n\n"
            f"Setup instructions:\n"
            f"1. Visit https://console.cloud.google.com\n"
            f"2. Create a new project or select existing one\n"
            f"3. Enable Gmail API for your project\n"
            f"4. Configure OAuth consent screen (Desktop app type)\n"
            f"5. Create OAuth 2.0 Client ID credentials\n"
            f"6. Download credentials as JSON\n"
            f"7. Save to: {CREDENTIALS_FILE}\n\n"
            f"Documentation: https://developers.google.com/workspace/gmail/api/quickstart/python"
        )

    log_verbose(f"Found credentials file: {CREDENTIALS_FILE}", verbose)
    log_verbose(f"Requesting scopes: {scopes}", verbose)

    # Create OAuth2 flow from credentials file
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes
    )

    status_start("Opening browser for authentication...")
    log_verbose("Starting OAuth2 consent flow...", verbose)
    log_verbose("Browser will open for authentication", verbose)

    # Run local server and open browser for consent
    # This will:
    # 1. Start a local web server on localhost
    # 2. Open user's default browser
    # 3. Redirect to Google OAuth consent screen
    # 4. User grants permissions
    # 5. Google redirects back to local server with auth code
    # 6. Server exchanges code for tokens
    creds = flow.run_local_server(port=0)

    status_done("Authentication complete")
    log_verbose("Authentication successful", verbose)
    log_verbose("Saving tokens for future use...", verbose)

    # Save credentials for future use
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())

    log_verbose(f"Tokens saved to: {TOKEN_FILE}", verbose)

    # Validate tokens by making a test API call
    log_verbose("Validating tokens with test API call...", verbose)

    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')

        log_verbose(f"Successfully authenticated as: {email_address}", verbose)

        return {
            "message": "Authentication successful",
            "email": email_address,
            "scopes": scopes,
            "token_file": str(TOKEN_FILE)
        }

    except Exception as e:
        raise Exception(f"Token validation failed: {str(e)}")


def main():
    """Main entry point for authentication script."""
    parser = argparse.ArgumentParser(
        description="Gmail API OAuth2 Authentication Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Authenticate with default scopes (gmail.modify)
  python gmail_auth.py

  # Authenticate with specific scopes
  python gmail_auth.py --scopes gmail.readonly,gmail.send

  # Verbose output for debugging
  python gmail_auth.py --verbose

Available OAuth Scopes:
  - gmail.readonly: Read-only access to all emails
  - gmail.send: Send emails only
  - gmail.modify: Full access (read, send, modify, delete)
  - gmail.compose: Create, read, update drafts
  - gmail.labels: Create, read, update, delete labels

For more information:
  https://developers.google.com/gmail/api/auth/scopes
        """
    )

    parser.add_argument(
        "--scopes",
        type=str,
        help="Comma-separated list of OAuth scopes (default: gmail.modify)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    args = parser.parse_args()

    # Parse scopes argument
    if args.scopes:
        # Convert short names to full URLs
        scope_mapping = {
            "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
            "gmail.send": "https://www.googleapis.com/auth/gmail.send",
            "gmail.modify": "https://www.googleapis.com/auth/gmail.modify",
            "gmail.compose": "https://www.googleapis.com/auth/gmail.compose",
            "gmail.labels": "https://www.googleapis.com/auth/gmail.labels",
        }

        scopes = []
        for scope in args.scopes.split(","):
            scope = scope.strip()
            # Check if it's a short name or full URL
            if scope in scope_mapping:
                scopes.append(scope_mapping[scope])
            elif scope.startswith("https://"):
                scopes.append(scope)
            else:
                print(format_error(
                    "InvalidScope",
                    f"Unknown scope: {scope}",
                    help="Use --help to see available scopes"
                ))
                sys.exit(1)
    else:
        scopes = DEFAULT_SCOPES

    # Perform authentication
    try:
        result = authenticate(scopes, verbose=args.verbose)
        print(format_success(result))
        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("AuthenticationError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
