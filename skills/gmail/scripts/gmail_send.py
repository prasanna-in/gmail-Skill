#!/usr/bin/env python3
"""
Gmail Send Script

This script composes and sends emails via the Gmail API.
It supports multiple recipients, CC, BCC, and file attachments.

Usage:
    python gmail_send.py --to EMAIL --subject "SUBJECT" --body "BODY"
    python gmail_send.py --to EMAIL --subject "SUBJECT" --body-file message.txt
    python gmail_send.py --to EMAIL --subject "SUBJECT" --body "BODY" --attach file.pdf

Examples:
    # Send simple email
    python gmail_send.py --to recipient@example.com --subject "Hello" --body "Hi there!"

    # Send with CC and BCC
    python gmail_send.py --to recipient@example.com --cc team@example.com --bcc archive@example.com --subject "Update" --body "Status update"

    # Send with attachment
    python gmail_send.py --to recipient@example.com --subject "Report" --body "See attached" --attach report.pdf

Educational Note:
- Emails are constructed as RFC822 MIME messages
- Multiple recipients are supported via comma-separated lists
- Gmail automatically saves sent messages to "Sent" folder
"""

import argparse
import sys
from pathlib import Path

from googleapiclient.errors import HttpError

# Import common utilities
from gmail_common import (
    get_gmail_service,
    create_message,
    validate_email,
    format_error,
    format_success,
    log_verbose
)


# OAuth scopes required for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] = None,
    bcc: list[str] = None,
    attachments: list[str] = None,
    verbose: bool = False
) -> dict:
    """
    Send an email via Gmail API.

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Plain text email body
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        attachments: Optional list of file paths to attach
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with send result (message ID, thread ID)

    Raises:
        ValueError: If email validation fails
        FileNotFoundError: If attachment file not found
        Exception: If API call fails
    """
    log_verbose(f"Preparing to send email to: {', '.join(to)}", verbose)

    # Validate all email addresses
    all_emails = to + (cc or []) + (bcc or [])
    for email in all_emails:
        if not validate_email(email):
            raise ValueError(f"Invalid email address: {email}")

    log_verbose("All email addresses validated", verbose)

    # Validate attachments exist
    if attachments:
        for filepath in attachments:
            if not Path(filepath).exists():
                raise FileNotFoundError(f"Attachment not found: {filepath}")
        log_verbose(f"Found {len(attachments)} attachment(s)", verbose)

    # Create RFC822 MIME message
    log_verbose("Creating MIME message...", verbose)

    raw_message = create_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        attachments=attachments
    )

    log_verbose("MIME message created successfully", verbose)

    # Get authenticated Gmail service
    service = get_gmail_service(SCOPES)

    try:
        # Send the message
        log_verbose("Sending email via Gmail API...", verbose)

        message_body = {'raw': raw_message}
        sent_message = service.users().messages().send(
            userId='me',
            body=message_body
        ).execute()

        message_id = sent_message.get('id')
        thread_id = sent_message.get('threadId')

        log_verbose(f"Email sent successfully! Message ID: {message_id}", verbose)

        return {
            "message_id": message_id,
            "thread_id": thread_id,
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "subject": subject,
            "attachments": len(attachments) if attachments else 0
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
    """Main entry point for send script."""
    parser = argparse.ArgumentParser(
        description="Send email via Gmail API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple email
  python gmail_send.py --to recipient@example.com --subject "Hello" --body "Hi!"

  # Multiple recipients
  python gmail_send.py --to "user1@example.com,user2@example.com" --subject "Team Update" --body "Meeting at 3pm"

  # With CC and BCC
  python gmail_send.py --to recipient@example.com --cc manager@example.com --bcc archive@example.com --subject "Report" --body "Q1 results"

  # With attachment
  python gmail_send.py --to recipient@example.com --subject "Invoice" --body "Please see attached invoice" --attach invoice.pdf

  # Multiple attachments
  python gmail_send.py --to recipient@example.com --subject "Files" --body "Documents attached" --attach file1.pdf --attach file2.xlsx

  # Body from file
  python gmail_send.py --to recipient@example.com --subject "Newsletter" --body-file newsletter.txt

Notes:
  - Gmail has a 25MB attachment size limit
  - Sent messages automatically appear in your "Sent" folder
  - Use quotes around email lists with commas
        """
    )

    parser.add_argument(
        "--to",
        type=str,
        required=True,
        help="Recipient email address(es), comma-separated"
    )

    parser.add_argument(
        "--subject",
        type=str,
        required=True,
        help="Email subject line"
    )

    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument(
        "--body",
        type=str,
        help="Email body text"
    )

    body_group.add_argument(
        "--body-file",
        type=str,
        help="Path to file containing email body"
    )

    parser.add_argument(
        "--cc",
        type=str,
        help="CC recipient(s), comma-separated"
    )

    parser.add_argument(
        "--bcc",
        type=str,
        help="BCC recipient(s), comma-separated"
    )

    parser.add_argument(
        "--attach",
        type=str,
        action="append",
        help="File to attach (can be used multiple times)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    args = parser.parse_args()

    # Parse recipient lists
    to_list = [email.strip() for email in args.to.split(",")]
    cc_list = [email.strip() for email in args.cc.split(",")] if args.cc else None
    bcc_list = [email.strip() for email in args.bcc.split(",")] if args.bcc else None

    # Get body text
    if args.body:
        body_text = args.body
    else:  # args.body_file
        body_path = Path(args.body_file)
        if not body_path.exists():
            print(format_error(
                "FileNotFound",
                f"Body file not found: {args.body_file}"
            ), file=sys.stderr)
            sys.exit(1)

        body_text = body_path.read_text()

    # Send email
    try:
        result = send_email(
            to=to_list,
            subject=args.subject,
            body=body_text,
            cc=cc_list,
            bcc=bcc_list,
            attachments=args.attach,
            verbose=args.verbose
        )
        print(format_success(result))
        sys.exit(0)

    except ValueError as e:
        print(format_error("ValidationError", str(e)), file=sys.stderr)
        sys.exit(1)

    except FileNotFoundError as e:
        print(format_error("FileNotFound", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("SendError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
