#!/usr/bin/env python3
"""
Gmail Labels Management Script

This script manages Gmail labels (folders) including listing, creating,
applying to messages, and removing from messages.

Usage:
    python gmail_labels.py --action list
    python gmail_labels.py --action create --name "Work/Projects"
    python gmail_labels.py --action apply --label-name "Important" --message-ids ID1,ID2
    python gmail_labels.py --action remove --label-name "Important" --message-ids ID1,ID2

Examples:
    # List all labels
    python gmail_labels.py --action list

    # Create new label
    python gmail_labels.py --action create --name "Urgent"

    # Create nested label (uses / for hierarchy)
    python gmail_labels.py --action create --name "Work/Projects/Q1"

    # Apply label to messages
    python gmail_labels.py --action apply --label-name "Important" --message-ids "18d1a2b3c4d5e6f7,18d1a2b3c4d5e6f8"

Educational Note:
- Gmail labels are similar to folders but messages can have multiple labels
- System labels (INBOX, SENT, TRASH) cannot be modified
- Label names with "/" create hierarchical organization
"""

import argparse
import sys

from googleapiclient.errors import HttpError

# Import common utilities
from gmail_common import (
    get_gmail_service,
    format_error,
    format_success,
    log_verbose,
    status_start,
    status_done
)


# OAuth scopes required for label management
SCOPES = ['https://www.googleapis.com/auth/gmail.labels']


def list_labels(verbose: bool = False) -> dict:
    """
    List all Gmail labels.

    Args:
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with list of labels

    Raises:
        Exception: If API call fails
    """
    status_start("Fetching labels...")
    log_verbose("Fetching labels...", verbose)

    service = get_gmail_service(SCOPES)

    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        status_done(f"Found {len(labels)} labels")
        log_verbose(f"Found {len(labels)} labels", verbose)

        # Separate system and user labels
        system_labels = []
        user_labels = []

        for label in labels:
            label_data = {
                "id": label['id'],
                "name": label['name'],
                "type": label.get('type', 'user').lower()
            }

            # Add optional fields if present
            if 'messageListVisibility' in label:
                label_data['messageListVisibility'] = label['messageListVisibility']
            if 'labelListVisibility' in label:
                label_data['labelListVisibility'] = label['labelListVisibility']

            if label_data['type'] == 'system':
                system_labels.append(label_data)
            else:
                user_labels.append(label_data)

        return {
            "total_count": len(labels),
            "system_count": len(system_labels),
            "user_count": len(user_labels),
            "labels": labels,
            "system_labels": system_labels,
            "user_labels": user_labels
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def create_label(name: str, verbose: bool = False) -> dict:
    """
    Create a new Gmail label.

    Args:
        name: Label name (use "/" for hierarchy, e.g., "Work/Projects")
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with created label info

    Raises:
        Exception: If API call fails
    """
    status_start("Creating label...")
    log_verbose(f"Creating label: {name}", verbose)

    service = get_gmail_service(SCOPES)

    try:
        # Create label request body
        label_object = {
            'name': name,
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        }

        created_label = service.users().labels().create(
            userId='me',
            body=label_object
        ).execute()

        status_done("Label created")
        log_verbose(f"Label created with ID: {created_label['id']}", verbose)

        return {
            "action": "create",
            "label_id": created_label['id'],
            "label_name": created_label['name']
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []

        # Check for duplicate label error
        if error.status_code == 409:
            raise Exception(f"Label '{name}' already exists")

        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def apply_label(
    label_name: str,
    message_ids: list[str],
    verbose: bool = False
) -> dict:
    """
    Apply a label to specified messages.

    Args:
        label_name: Name of existing label
        message_ids: List of message IDs to label
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with operation result

    Raises:
        Exception: If label not found or API call fails
    """
    status_start(f"Applying label to {len(message_ids)} messages...")
    log_verbose(f"Applying label '{label_name}' to {len(message_ids)} message(s)", verbose)

    service = get_gmail_service(SCOPES)

    try:
        # First, find the label ID from name
        labels = service.users().labels().list(userId='me').execute()
        label_id = None

        for label in labels.get('labels', []):
            if label['name'] == label_name:
                label_id = label['id']
                break

        if not label_id:
            raise Exception(f"Label not found: {label_name}")

        log_verbose(f"Found label ID: {label_id}", verbose)

        # Apply label to each message
        successful = 0
        for msg_id in message_ids:
            log_verbose(f"Applying label to message: {msg_id}", verbose)

            service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': [label_id]}
            ).execute()

            successful += 1

        status_done("Label applied")
        log_verbose(f"Successfully labeled {successful} message(s)", verbose)

        return {
            "action": "apply",
            "label_name": label_name,
            "label_id": label_id,
            "affected_messages": successful,
            "message_ids": message_ids
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def remove_label(
    label_name: str,
    message_ids: list[str],
    verbose: bool = False
) -> dict:
    """
    Remove a label from specified messages.

    Args:
        label_name: Name of existing label
        message_ids: List of message IDs to unlabel
        verbose: Whether to log detailed progress

    Returns:
        Dictionary with operation result

    Raises:
        Exception: If label not found or API call fails
    """
    status_start(f"Removing label from {len(message_ids)} messages...")
    log_verbose(f"Removing label '{label_name}' from {len(message_ids)} message(s)", verbose)

    service = get_gmail_service(SCOPES)

    try:
        # First, find the label ID from name
        labels = service.users().labels().list(userId='me').execute()
        label_id = None

        for label in labels.get('labels', []):
            if label['name'] == label_name:
                label_id = label['id']
                break

        if not label_id:
            raise Exception(f"Label not found: {label_name}")

        log_verbose(f"Found label ID: {label_id}", verbose)

        # Remove label from each message
        successful = 0
        for msg_id in message_ids:
            log_verbose(f"Removing label from message: {msg_id}", verbose)

            service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': [label_id]}
            ).execute()

            successful += 1

        status_done("Label removed")
        log_verbose(f"Successfully removed label from {successful} message(s)", verbose)

        return {
            "action": "remove",
            "label_name": label_name,
            "label_id": label_id,
            "affected_messages": successful,
            "message_ids": message_ids
        }

    except HttpError as error:
        error_details = error.error_details if hasattr(error, 'error_details') else []
        raise Exception(
            f"Gmail API error: {error.reason}\n"
            f"Status code: {error.status_code}\n"
            f"Details: {error_details}"
        )


def main():
    """Main entry point for labels script."""
    parser = argparse.ArgumentParser(
        description="Manage Gmail labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all labels
  python gmail_labels.py --action list

  # Create simple label
  python gmail_labels.py --action create --name "Urgent"

  # Create nested label (hierarchical)
  python gmail_labels.py --action create --name "Work/Projects/Q1"

  # Apply label to messages
  python gmail_labels.py --action apply --label-name "Important" --message-ids "18d1a2b3,18d1a2b4"

  # Remove label from messages
  python gmail_labels.py --action remove --label-name "Important" --message-ids "18d1a2b3,18d1a2b4"

Notes:
  - System labels (INBOX, SENT, TRASH, etc.) cannot be created or deleted
  - Use "/" in label names to create hierarchical organization
  - Messages can have multiple labels
  - Removing a label doesn't delete the message
        """
    )

    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=["list", "create", "apply", "remove"],
        help="Action to perform: list, create, apply, or remove"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Label name (required for 'create' action)"
    )

    parser.add_argument(
        "--label-name",
        type=str,
        help="Existing label name (required for 'apply' and 'remove' actions)"
    )

    parser.add_argument(
        "--message-ids",
        type=str,
        help="Comma-separated message IDs (required for 'apply' and 'remove' actions)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr"
    )

    args = parser.parse_args()

    # Validate arguments based on action
    if args.action == "create":
        if not args.name:
            print(format_error(
                "MissingParameter",
                "The 'create' action requires --name parameter"
            ), file=sys.stderr)
            sys.exit(1)

    elif args.action in ["apply", "remove"]:
        if not args.label_name or not args.message_ids:
            print(format_error(
                "MissingParameter",
                f"The '{args.action}' action requires --label-name and --message-ids parameters"
            ), file=sys.stderr)
            sys.exit(1)

    # Execute requested action
    try:
        if args.action == "list":
            result = list_labels(verbose=args.verbose)

        elif args.action == "create":
            result = create_label(name=args.name, verbose=args.verbose)

        elif args.action == "apply":
            message_ids = [msg_id.strip() for msg_id in args.message_ids.split(",")]
            result = apply_label(
                label_name=args.label_name,
                message_ids=message_ids,
                verbose=args.verbose
            )

        elif args.action == "remove":
            message_ids = [msg_id.strip() for msg_id in args.message_ids.split(",")]
            result = remove_label(
                label_name=args.label_name,
                message_ids=message_ids,
                verbose=args.verbose
            )

        print(format_success(result))
        sys.exit(0)

    except FileNotFoundError as e:
        print(format_error("MissingCredentials", str(e)), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(format_error("LabelError", str(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
