#!/usr/bin/env python3
"""
Gmail Read/Search Script

This script searches for and retrieves emails from Gmail using the Gmail API.
It supports powerful Gmail search syntax and returns results in JSON format.

Usage:
    python gmail_read.py --query "QUERY" [--max-results N] [--format full|metadata|minimal]

Examples:
    # Get unread emails
    python gmail_read.py --query "is:unread" --max-results 10

    # Search for emails from specific sender
    python gmail_read.py --query "from:boss@company.com" --format metadata

    # Get full email bodies
    python gmail_read.py --query "subject:invoice" --format full

Educational Note:
- Gmail search uses the same syntax as the Gmail web interface
- The API returns message IDs, then we fetch full details for each
- Different format options balance detail vs. token usage
"""

import argparse
import sys

from googleapiclient.errors import HttpError

# Import common utilities
from gmail_common import (
    get_gmail_service,
    parse_message,
    format_error,
    format_success,
    log_verbose
)


# OAuth scopes required for reading emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def search_messages(
    query: str,
    max_results: int = 10,
    format_type: str = "metadata",
    verbose: bool = False
) -> dict:
    """
    Search for Gmail messages matching query.

    Args:
        query: Gmail search query (e.g., "is:unread from:user@example.com")
        max_results: Maximum number of messages to return
        format_type: Level of detail - "minimal", "metadata", or "full"
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with search results

    Raises:
        Exception: If API call fails
    """
    log_verbose(f"Searching for: {query}", verbose)
    log_verbose(f"Max results: {max_results}", verbose)
    log_verbose(f"Format: {format_type}", verbose)

    # Get authenticated Gmail service
    service = get_gmail_service(SCOPES)

    try:
        # Search for messages matching query
        # This returns a list of message IDs and threadIds
        log_verbose("Executing search query...", verbose)

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        result_count = len(messages)

        log_verbose(f"Found {result_count} messages", verbose)

        if not messages:
            return {
                "result_count": 0,
                "query": query,
                "messages": []
            }

        # Fetch full message details based on format type
        detailed_messages = []

        for i, msg in enumerate(messages):
            log_verbose(f"Fetching message {i+1}/{result_count}...", verbose)

            # Determine which format to request from API
            # - minimal: Just IDs (already have this)
            # - metadata: Headers only (no body)
            # - full: Complete message including body
            if format_type == "minimal":
                api_format = "minimal"
            elif format_type == "metadata":
                api_format = "metadata"
            else:  # full
                api_format = "full"

            # Fetch message details
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format=api_format
            ).execute()

            # Parse message into standardized format
            parsed = parse_message(full_msg, format_type)
            detailed_messages.append(parsed)

        log_verbose("Search completed successfully", verbose)

        return {
            "result_count": result_count,
            "query": query,
            "messages": detailed_messages
        }

    except HttpError as error:
        # Gmail API HTTP errors
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def main():
    """Main entry point for read script."""
    parser = argparse.ArgumentParser(
        description="Search and read Gmail messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Query Examples:
  Basic Filters:
    is:unread                      - Unread messages
    is:starred                     - Starred messages
    from:user@example.com          - From specific sender
    to:me                          - Sent to you
    subject:invoice                - Subject contains "invoice"

  Date Ranges:
    after:2026/01/01               - After January 1, 2026
    before:2026/01/15              - Before January 15
    newer_than:7d                  - Last 7 days
    older_than:1m                  - Older than 1 month

  Attachments:
    has:attachment                 - Any attachment
    filename:pdf                   - PDF attachments
    larger:5M                      - Larger than 5MB

  Combining Queries:
    from:boss@company.com is:unread              - Unread from boss
    subject:invoice has:attachment after:2026/01/01  - Recent invoices with attachments

For more query syntax:
  https://support.google.com/mail/answer/7190
        """
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Gmail search query (e.g., 'is:unread from:user@example.com')"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of messages to return (default: 10, max: 100)"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["minimal", "metadata", "full"],
        default="metadata",
        help="Output format: minimal (IDs only), metadata (headers), full (includes body)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    args = parser.parse_args()

    # Validate max-results
    if args.max_results < 1 or args.max_results > 100:
        print(format_error(
            "InvalidParameter",
            "max-results must be between 1 and 100",
            provided=args.max_results
        ), file=sys.stderr)
        sys.exit(1)

    # Execute search
    try:
        result = search_messages(
            query=args.query,
            max_results=args.max_results,
            format_type=args.format,
            verbose=args.verbose
        )
        print(format_success(result))
        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("SearchError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
