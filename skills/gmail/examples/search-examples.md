# Gmail Search Query Examples

This document provides comprehensive Gmail search query patterns for use with `gmail_read.py`.

Gmail search uses the same powerful syntax as the Gmail web interface. Queries can be combined using spaces (AND logic) or curly braces for OR logic.

## Basic Filters

### Read/Unread Status
```
is:unread          # Unread messages only
is:read            # Read messages only
is:starred         # Starred messages
is:important       # Gmail's important classification
```

### Sender and Recipient
```
from:john@example.com           # From specific sender
from:example.com                # From anyone at domain
to:me                           # Sent directly to you
to:john@example.com             # Sent to specific address
cc:team@example.com             # CC'd to address
bcc:me                          # BCC'd to you (sent by you)
```

### Subject and Content
```
subject:invoice                 # Subject contains "invoice"
subject:"exact phrase"          # Exact phrase in subject
invoice                         # "invoice" anywhere in email
"exact phrase"                  # Exact phrase anywhere
```

### Labels and Folders
```
label:important                 # Has "important" label
in:inbox                        # In inbox (system label)
in:sent                         # In sent folder
in:drafts                       # Draft messages
in:trash                        # Trash
in:spam                         # Spam folder
-label:processed                # Does NOT have "processed" label
```

## Date and Time Filters

### Specific Dates
```
after:2026/01/01                # After January 1, 2026
after:2026/1/1                  # Same (leading zeros optional)
before:2026/01/15               # Before January 15, 2026
after:2026/01/01 before:2026/01/31   # Date range (January 2026)
```

### Relative Dates
```
newer_than:1d                   # Last 24 hours
newer_than:7d                   # Last 7 days
newer_than:1m                   # Last month
newer_than:1y                   # Last year
older_than:7d                   # Older than 7 days
older_than:1m                   # Older than 1 month
older_than:1y                   # Older than 1 year
```

## Attachment Filters

### Attachment Presence
```
has:attachment                  # Any attachment
has:drive                       # Google Drive attachment
has:document                    # Document attachment
has:spreadsheet                 # Spreadsheet attachment
has:presentation                # Presentation attachment
has:youtube                     # YouTube video link
```

### Attachment Filename
```
filename:pdf                    # PDF files
filename:xlsx                   # Excel files
filename:"report.pdf"           # Exact filename
filename:invoice                # Filename contains "invoice"
```

### Attachment Size
```
larger:5M                       # Larger than 5 megabytes
larger:10M                      # Larger than 10MB
smaller:1M                      # Smaller than 1 megabyte
size:10M                        # Approximately 10MB
```

## Advanced Operators

### Boolean Logic
```
from:alice OR from:bob                          # From Alice OR Bob
{from:alice from:bob}                           # Alternative OR syntax
from:alice is:unread                            # From Alice AND unread (space = AND)
from:alice -is:starred                          # From Alice but NOT starred
```

### Exact Match
```
from:(alice@example.com)                        # Exact email
subject:("quarterly report")                    # Exact phrase
```

### Wildcards
```
from:*@example.com                              # Anyone from domain
subject:report*                                 # Subject starts with "report"
```

## Practical Examples

### Work Email Management
```
# Unread emails from your boss
from:boss@company.com is:unread

# Important emails from last week
is:important newer_than:7d

# All emails about a specific project
subject:project-alpha OR subject:"Project Alpha"

# Emails requiring action (custom label)
label:action-required is:unread

# Team emails with attachments from this month
from:team@company.com has:attachment after:2026/01/01
```

### Customer Support
```
# Unread support tickets
from:*@customerdomain.com is:unread

# High priority support emails
from:support subject:urgent OR subject:critical

# Support emails with attachments needing review
from:support has:attachment -label:reviewed
```

### Newsletter and Bulk Email Management
```
# Unread newsletters
label:newsletters is:unread

# Large promotional emails
larger:1M from:promotions

# Social media notifications older than 1 week
from:*@facebook.com OR from:*@twitter.com older_than:7d
```

### Financial and Invoice Management
```
# Recent invoices with PDFs
subject:invoice has:attachment filename:pdf after:2026/01/01

# Unpaid invoices (using custom label)
subject:invoice -label:paid

# Bank statements from last 3 months
from:bank@example.com subject:statement newer_than:3m
```

### Travel and Booking Confirmations
```
# Flight confirmations
subject:"flight confirmation" OR subject:"boarding pass"

# Hotel bookings
subject:reservation from:*@booking.com OR from:*@hotels.com

# All travel docs with attachments
(subject:flight OR subject:hotel OR subject:rental) has:attachment
```

### Academic and Research
```
# Papers from specific conference
from:*@conference.org subject:paper

# Collaboration emails with documents
from:collaborator@university.edu has:document

# Review requests not yet addressed
subject:review -label:completed is:starred
```

## Complex Query Patterns

### Multiple Conditions (AND)
```
# Combine with spaces for AND logic
from:alice@example.com is:unread has:attachment after:2026/01/01
```

### Multiple Options (OR)
```
# Use curly braces for OR logic
{from:alice@example.com from:bob@example.com from:charlie@example.com}

# Or use OR keyword
from:alice@example.com OR from:bob@example.com OR from:charlie@example.com
```

### Exclusions (NOT)
```
# Use minus sign to exclude
from:alice -subject:meeting                     # From Alice, but not about meetings
is:unread -label:processed                      # Unread and not processed
has:attachment -filename:png -filename:jpg      # Attachments but not images
```

### Nested Conditions
```
# Complex multi-level queries
(from:alice OR from:bob) is:unread has:attachment after:2026/01/01

# Exclude multiple senders
is:unread -(from:spam@example.com OR from:promo@example.com)

# Multiple subjects or senders
{from:boss from:manager} {subject:urgent subject:asap}
```

## Query Performance Tips

1. **Be Specific**: More specific queries return faster
   - ✅ `from:alice@example.com subject:invoice after:2026/01/01`
   - ❌ `invoice` (too broad)

2. **Use Date Ranges**: Limit search scope with dates
   - ✅ `newer_than:30d` instead of searching all time
   - ✅ `after:2026/01/01 before:2026/02/01` for specific month

3. **Combine Filters**: Use multiple operators to narrow results
   - ✅ `from:sender is:unread has:attachment`

4. **Use Labels**: Pre-label emails for faster searching
   - ✅ `label:project-alpha` (fast)
   - ❌ Searching through all emails every time (slow)

## Common Mistakes to Avoid

### Incorrect Syntax
```
# ❌ Wrong
from = alice@example.com
is = unread
subject contains invoice

# ✅ Correct
from:alice@example.com
is:unread
subject:invoice
```

### Quote Usage
```
# ❌ Wrong - quotes should contain exact phrase
subject:"invoice"                               # Unnecessary quotes

# ✅ Correct
subject:invoice                                 # Single word, no quotes needed
subject:"quarterly invoice report"              # Multi-word phrase, quotes needed
```

### Date Format
```
# ❌ Wrong
after:01/15/2026                                # Wrong format
after:Jan 15 2026                               # Wrong format

# ✅ Correct
after:2026/01/15                                # YYYY/MM/DD format
after:2026/1/15                                 # Also valid
newer_than:7d                                   # Relative dates
```

## Testing Your Queries

Before using queries with the skill, test them in the Gmail web interface:

1. Open https://mail.google.com
2. Type your query in the search box
3. Verify it returns expected results
4. Use the exact same query with `gmail_read.py`

## Additional Resources

- **Gmail Search Operators**: https://support.google.com/mail/answer/7190
- **Advanced Search**: https://support.google.com/mail/answer/6593
- **Gmail API Query Reference**: https://developers.google.com/gmail/api/guides/filtering

## Examples by Use Case

### Daily Email Triage
```bash
# Morning routine - check priority emails
python gmail_read.py --query "is:unread (is:important OR is:starred)"

# Unread from key people
python gmail_read.py --query "{from:boss from:client from:partner} is:unread"

# Action items
python gmail_read.py --query "label:action-required -label:completed"
```

### Weekly Cleanup
```bash
# Old read emails with large attachments
python gmail_read.py --query "is:read older_than:30d larger:10M"

# Processed newsletters
python gmail_read.py --query "label:newsletters is:read older_than:7d"

# Archived conversations
python gmail_read.py --query "-in:inbox older_than:90d"
```

### Project Management
```bash
# Project emails from this week
python gmail_read.py --query "subject:ProjectX newer_than:7d"

# Pending approvals
python gmail_read.py --query "subject:approval is:unread"

# Meeting notes with attachments
python gmail_read.py --query "subject:meeting has:attachment -in:trash"
```

This comprehensive guide should help you construct effective Gmail search queries for any use case.
