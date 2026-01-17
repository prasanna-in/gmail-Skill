"""
Gmail RLM Helper Functions

This module provides utility functions for RLM (Recursive Language Model) email analysis.
These functions help with chunking, filtering, grouping, and aggregating email data.

Functions are designed to be used within the gmail_rlm_repl.py environment.

Educational Note:
- RLM approach processes data in chunks to avoid context overflow
- Grouping by sender/date enables focused analysis
- These helpers abstract common patterns from the RLM paper

Pre-built Workflows:
- inbox_triage(emails) - Classify emails into categories
- weekly_summary(emails) - Generate executive summary
- find_action_items(emails) - Extract action items with deadlines
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TYPE_CHECKING
import re

# Type hints for functions imported at runtime from gmail_rlm_repl
if TYPE_CHECKING:
    pass  # Forward references handled by string annotations


def chunk_by_size(emails: list[dict], chunk_size: int = 20) -> list[list[dict]]:
    """
    Split emails into fixed-size chunks for batch processing.

    This is the most common chunking strategy - process N emails at a time
    to avoid context overflow in LLM sub-queries.

    Args:
        emails: List of email dictionaries
        chunk_size: Number of emails per chunk (default: 20)

    Returns:
        List of email chunks

    Example:
        for chunk in chunk_by_size(emails, 20):
            summary = llm_query('Summarize these emails', context=str(chunk))
    """
    return [emails[i:i + chunk_size] for i in range(0, len(emails), chunk_size)]


def chunk_by_sender(emails: list[dict]) -> dict[str, list[dict]]:
    """
    Group emails by sender email address.

    Useful for analyzing communication patterns or summarizing by sender.
    Extracts email address from "Name <email@domain.com>" format.

    Args:
        emails: List of email dictionaries with 'from' field

    Returns:
        Dictionary mapping sender email to list of their emails

    Example:
        by_sender = chunk_by_sender(emails)
        for sender, msgs in by_sender.items():
            summary = llm_query(f'What is {sender} emailing about?', context=str(msgs))
    """
    groups = defaultdict(list)

    for email in emails:
        from_field = email.get('from', '(Unknown)')

        # Extract email address from "Name <email@domain.com>" format
        match = re.search(r'<([^>]+)>', from_field)
        if match:
            sender = match.group(1).lower()
        else:
            # Just use the whole field if no angle brackets
            sender = from_field.lower().strip()

        groups[sender].append(email)

    return dict(groups)


def chunk_by_sender_domain(emails: list[dict]) -> dict[str, list[dict]]:
    """
    Group emails by sender's domain (e.g., 'company.com').

    Useful for categorizing emails by organization.

    Args:
        emails: List of email dictionaries with 'from' field

    Returns:
        Dictionary mapping domain to list of emails

    Example:
        by_domain = chunk_by_sender_domain(emails)
        # Summarize all emails from each company
    """
    groups = defaultdict(list)

    for email in emails:
        from_field = email.get('from', '(Unknown)')

        # Extract email address
        match = re.search(r'<([^>]+)>', from_field)
        if match:
            email_addr = match.group(1).lower()
        else:
            email_addr = from_field.lower().strip()

        # Extract domain
        if '@' in email_addr:
            domain = email_addr.split('@')[1]
        else:
            domain = 'unknown'

        groups[domain].append(email)

    return dict(groups)


def chunk_by_date(emails: list[dict], period: str = 'day') -> dict[str, list[dict]]:
    """
    Group emails by date period (day, week, or month).

    Useful for time-based analysis like "summarize each week's activity".

    Args:
        emails: List of email dictionaries with 'date' field
        period: Grouping period - 'day', 'week', or 'month'

    Returns:
        Dictionary mapping date key to list of emails

    Example:
        by_week = chunk_by_date(emails, 'week')
        for week, msgs in by_week.items():
            summary = llm_query(f'Summarize activity for {week}', context=str(msgs))
    """
    groups = defaultdict(list)

    for email in emails:
        date_str = email.get('date', '')

        # Try to parse the date
        date_key = _parse_date_to_key(date_str, period)
        groups[date_key].append(email)

    return dict(groups)


def _parse_date_to_key(date_str: str, period: str) -> str:
    """Parse email date string and return grouping key."""
    # Try common date formats
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822: "Wed, 15 Jan 2026 10:30:00 -0800"
        '%d %b %Y %H:%M:%S %z',       # Without day: "15 Jan 2026 10:30:00 -0800"
        '%Y-%m-%d %H:%M:%S',          # ISO-like: "2026-01-15 10:30:00"
        '%Y-%m-%d',                   # ISO date: "2026-01-15"
    ]

    dt = None
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            break
        except ValueError:
            continue

    if dt is None:
        return 'unknown_date'

    if period == 'day':
        return dt.strftime('%Y-%m-%d')
    elif period == 'week':
        # ISO week number
        return dt.strftime('%Y-W%W')
    elif period == 'month':
        return dt.strftime('%Y-%m')
    else:
        return dt.strftime('%Y-%m-%d')


def chunk_by_thread(emails: list[dict]) -> dict[str, list[dict]]:
    """
    Group emails by thread ID.

    Useful for analyzing email conversations together.

    Args:
        emails: List of email dictionaries with 'threadId' field

    Returns:
        Dictionary mapping thread ID to list of emails in that thread
    """
    groups = defaultdict(list)

    for email in emails:
        thread_id = email.get('threadId', email.get('id', 'unknown'))
        groups[thread_id].append(email)

    return dict(groups)


def filter_emails(
    emails: list[dict],
    predicate: Callable[[dict], bool]
) -> list[dict]:
    """
    Filter emails using a custom predicate function.

    Args:
        emails: List of email dictionaries
        predicate: Function that takes an email dict and returns True to keep

    Returns:
        Filtered list of emails

    Example:
        # Keep only emails with attachments mentioned
        with_attachments = filter_emails(emails, lambda e: 'attachment' in e.get('snippet', '').lower())
    """
    return [e for e in emails if predicate(e)]


def filter_by_keyword(
    emails: list[dict],
    keyword: str,
    fields: list[str] = None
) -> list[dict]:
    """
    Filter emails containing a keyword in specified fields.

    Args:
        emails: List of email dictionaries
        keyword: Keyword to search for (case-insensitive)
        fields: Fields to search in (default: subject, snippet, body)

    Returns:
        Emails containing the keyword

    Example:
        urgent = filter_by_keyword(emails, 'urgent')
    """
    if fields is None:
        fields = ['subject', 'snippet', 'body']

    keyword_lower = keyword.lower()

    def matches(email: dict) -> bool:
        for field in fields:
            value = email.get(field, '')
            if keyword_lower in value.lower():
                return True
        return False

    return filter_emails(emails, matches)


def filter_by_sender(emails: list[dict], sender_pattern: str) -> list[dict]:
    """
    Filter emails from senders matching a pattern.

    Args:
        emails: List of email dictionaries
        sender_pattern: Substring to match in 'from' field (case-insensitive)

    Returns:
        Emails from matching senders

    Example:
        from_company = filter_by_sender(emails, '@company.com')
    """
    pattern_lower = sender_pattern.lower()

    return filter_emails(
        emails,
        lambda e: pattern_lower in e.get('from', '').lower()
    )


def sort_emails(
    emails: list[dict],
    by: str = 'date',
    reverse: bool = True
) -> list[dict]:
    """
    Sort emails by a field.

    Args:
        emails: List of email dictionaries
        by: Field to sort by ('date', 'from', 'subject')
        reverse: Sort descending if True (default: True for newest first)

    Returns:
        Sorted list of emails
    """
    def get_sort_key(email: dict):
        value = email.get(by, '')
        if by == 'date':
            # Try to parse for proper date sorting
            try:
                for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(value.strip(), fmt)
                    except ValueError:
                        continue
            except:
                pass
            return value
        return value.lower() if isinstance(value, str) else value

    return sorted(emails, key=get_sort_key, reverse=reverse)


def get_top_senders(emails: list[dict], n: int = 10) -> list[tuple[str, int]]:
    """
    Get the top N senders by email count.

    Args:
        emails: List of email dictionaries
        n: Number of top senders to return

    Returns:
        List of (sender, count) tuples, sorted by count descending

    Example:
        top = get_top_senders(emails, 5)
        # [('boss@company.com', 45), ('newsletter@service.com', 30), ...]
    """
    by_sender = chunk_by_sender(emails)
    counts = [(sender, len(msgs)) for sender, msgs in by_sender.items()]
    return sorted(counts, key=lambda x: -x[1])[:n]


def extract_email_summary(email: dict) -> str:
    """
    Create a concise text summary of an email for LLM context.

    Args:
        email: Email dictionary

    Returns:
        Formatted summary string
    """
    parts = []

    if email.get('from'):
        parts.append(f"From: {email['from']}")
    if email.get('subject'):
        parts.append(f"Subject: {email['subject']}")
    if email.get('date'):
        parts.append(f"Date: {email['date']}")
    if email.get('snippet'):
        parts.append(f"Preview: {email['snippet']}")

    return '\n'.join(parts)


def batch_extract_summaries(emails: list[dict], max_chars: int = 4000) -> str:
    """
    Create a combined summary of multiple emails, respecting character limit.

    Useful for creating context for LLM sub-queries without exceeding limits.

    Args:
        emails: List of email dictionaries
        max_chars: Maximum total characters (default: 4000)

    Returns:
        Combined summary string
    """
    summaries = []
    total_chars = 0

    for i, email in enumerate(emails):
        summary = f"[{i+1}] {extract_email_summary(email)}"
        summary_len = len(summary) + 2  # +2 for newlines

        if total_chars + summary_len > max_chars:
            summaries.append(f"... and {len(emails) - i} more emails")
            break

        summaries.append(summary)
        total_chars += summary_len

    return '\n\n'.join(summaries)


def aggregate_results(results: list[str], separator: str = '\n\n---\n\n') -> str:
    """
    Combine multiple LLM sub-query results into a single output.

    Args:
        results: List of result strings from LLM sub-queries
        separator: String to put between results

    Returns:
        Aggregated result string
    """
    # Filter out empty results
    non_empty = [r.strip() for r in results if r and r.strip()]
    return separator.join(non_empty)


def deduplicate_emails(emails: list[dict]) -> list[dict]:
    """
    Remove duplicate emails based on message ID.

    Args:
        emails: List of email dictionaries

    Returns:
        Deduplicated list
    """
    seen = set()
    result = []

    for email in emails:
        msg_id = email.get('id')
        if msg_id and msg_id not in seen:
            seen.add(msg_id)
            result.append(email)
        elif not msg_id:
            result.append(email)

    return result


def prepare_llm_batch(
    chunks: list[list[dict]],
    prompt_template: str,
    context_fields: list[str] = None
) -> list[tuple[str, str]]:
    """
    Prepare batch of (prompt, context) tuples for parallel_llm_query.

    Args:
        chunks: List of email chunks
        prompt_template: Prompt to use for each chunk
        context_fields: Email fields to include in context (default: snippet, subject)

    Returns:
        List of (prompt, context) tuples ready for parallel_llm_query
    """
    if context_fields is None:
        context_fields = ['snippet', 'subject']

    prompts = []
    for chunk in chunks:
        context = str([{f: e.get(f, '') for f in context_fields} for e in chunk])
        prompts.append((prompt_template, context))

    return prompts


# =============================================================================
# Pre-built Workflows (Task 3)
# =============================================================================
#
# These workflow functions are designed to be injected with llm_query and
# parallel_map functions from the gmail_rlm_repl module. They are called
# through the execution context where these dependencies are available.
#
# The workflow functions below are factory functions that create closures
# with the required dependencies.

def create_inbox_triage(llm_query_fn: Callable, parallel_map_fn: Callable):
    """
    Create inbox_triage function with injected dependencies.

    Args:
        llm_query_fn: The llm_query function
        parallel_map_fn: The parallel_map function

    Returns:
        inbox_triage function
    """
    def inbox_triage(emails: list[dict]) -> dict[str, list[dict]]:
        """
        Classify emails into categories using LLM.

        Categories: urgent, action_required, fyi, newsletter

        Args:
            emails: List of email dictionaries

        Returns:
            Dict mapping category to list of emails

        Example:
            result = inbox_triage(emails)
            print(f"Found {len(result.get('urgent', []))} urgent emails")
        """
        if not emails:
            return {"urgent": [], "action_required": [], "fyi": [], "newsletter": []}

        # Process each email individually for classification
        results = parallel_map_fn(
            func_prompt="Classify this email into exactly one category: urgent, action_required, fyi, or newsletter. Respond with ONLY the category name, nothing else.",
            chunks=[[e] for e in emails],
            context_fn=lambda chunk: extract_email_summary(chunk[0])
        )

        # Group by classification
        categories = defaultdict(list)
        valid_categories = {"urgent", "action_required", "fyi", "newsletter"}

        for email, category in zip(emails, results):
            cat = category.strip().lower().replace(" ", "_")
            # Normalize common variations
            if cat in valid_categories:
                categories[cat].append(email)
            elif "urgent" in cat:
                categories["urgent"].append(email)
            elif "action" in cat:
                categories["action_required"].append(email)
            elif "newsletter" in cat or "news" in cat:
                categories["newsletter"].append(email)
            else:
                categories["fyi"].append(email)

        return dict(categories)

    return inbox_triage


def create_weekly_summary(llm_query_fn: Callable, parallel_map_fn: Callable):
    """
    Create weekly_summary function with injected dependencies.

    Args:
        llm_query_fn: The llm_query function
        parallel_map_fn: The parallel_map function

    Returns:
        weekly_summary function
    """
    def weekly_summary(emails: list[dict]) -> str:
        """
        Generate an executive summary of emails.

        Processes emails by day, summarizes each day, then combines
        into an overall executive brief.

        Args:
            emails: List of email dictionaries

        Returns:
            Executive summary string

        Example:
            summary = weekly_summary(emails)
            print(summary)
        """
        if not emails:
            return "No emails to summarize."

        # Group by day
        by_day = chunk_by_date(emails, period='day')

        if not by_day:
            return "No emails with valid dates to summarize."

        # Summarize each day in parallel
        sorted_days = sorted(by_day.keys())
        day_chunks = [by_day[day] for day in sorted_days]

        daily_summaries = parallel_map_fn(
            func_prompt="Summarize the key points from these emails in 2-3 bullet points. Focus on important topics, decisions, and requests.",
            chunks=day_chunks,
            context_fn=batch_extract_summaries
        )

        # Combine daily summaries with dates
        combined = []
        for day, summary in zip(sorted_days, daily_summaries):
            combined.append(f"**{day}**:\n{summary}")

        daily_context = "\n\n".join(combined)

        # Generate executive brief
        final_summary = llm_query_fn(
            "Combine these daily email summaries into a concise executive brief. "
            "Include: 1) Key themes across the week, 2) Important action items, "
            "3) Notable updates or decisions. Keep it under 300 words.",
            context=daily_context
        )

        return final_summary

    return weekly_summary


def create_find_action_items(llm_query_fn: Callable, llm_query_json_fn: Callable = None):
    """
    Create find_action_items function with injected dependencies.

    Args:
        llm_query_fn: The llm_query function
        llm_query_json_fn: The llm_query_json function (optional, falls back to llm_query)

    Returns:
        find_action_items function
    """
    def find_action_items(emails: list[dict]) -> list[dict]:
        """
        Extract action items from emails with deadlines.

        Args:
            emails: List of email dictionaries

        Returns:
            List of action item dicts with: task, deadline, sender, priority

        Example:
            items = find_action_items(emails)
            for item in items:
                print(f"[{item['priority']}] {item['task']} - due: {item.get('deadline', 'N/A')}")
        """
        if not emails:
            return []

        context = batch_extract_summaries(emails)

        prompt = """Extract all action items from these emails. For each action item, provide:
- task: Description of what needs to be done
- deadline: Due date if mentioned (or "none" if not specified)
- sender: Who requested this action
- priority: high, medium, or low based on urgency

Respond with a JSON array of objects. Example:
[{"task": "Review proposal", "deadline": "Friday", "sender": "boss@company.com", "priority": "high"}]

If no action items found, respond with: []"""

        if llm_query_json_fn:
            try:
                result = llm_query_json_fn(prompt, context=context)
                if isinstance(result, list):
                    return result
            except Exception:
                pass  # Fall back to regular llm_query

        # Fallback: parse JSON from regular response
        import json
        result = llm_query_fn(prompt, context=context, json_output=True)
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return parsed
            return []
        except json.JSONDecodeError:
            return []

    return find_action_items


def create_sender_analysis(llm_query_fn: Callable, parallel_map_fn: Callable):
    """
    Create sender_analysis function with injected dependencies.

    Args:
        llm_query_fn: The llm_query function
        parallel_map_fn: The parallel_map function

    Returns:
        sender_analysis function
    """
    def sender_analysis(emails: list[dict], top_n: int = 5) -> dict[str, dict]:
        """
        Analyze communication patterns for top senders.

        Args:
            emails: List of email dictionaries
            top_n: Number of top senders to analyze (default: 5)

        Returns:
            Dict mapping sender to analysis dict with: count, summary, tone

        Example:
            analysis = sender_analysis(emails, top_n=3)
            for sender, info in analysis.items():
                print(f"{sender}: {info['count']} emails - {info['tone']}")
        """
        if not emails:
            return {}

        # Get top senders
        by_sender = chunk_by_sender(emails)
        top_senders = sorted(by_sender.items(), key=lambda x: -len(x[1]))[:top_n]

        if not top_senders:
            return {}

        # Analyze each sender in parallel
        sender_names = [s[0] for s in top_senders]
        sender_emails = [s[1] for s in top_senders]

        analyses = parallel_map_fn(
            func_prompt="Analyze these emails from a single sender. Provide: 1) Main topics they discuss, 2) Communication tone (formal/informal/urgent), 3) Key requests or updates. Be concise.",
            chunks=sender_emails,
            context_fn=batch_extract_summaries
        )

        # Build result
        result = {}
        for sender, sender_msgs, analysis in zip(sender_names, sender_emails, analyses):
            result[sender] = {
                "count": len(sender_msgs),
                "summary": analysis,
                "tone": "formal" if "formal" in analysis.lower() else "informal"
            }

        return result

    return sender_analysis
