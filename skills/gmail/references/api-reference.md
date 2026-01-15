# Gmail API Reference

This document provides detailed technical information about the Gmail API as used by this skill.

## Table of Contents

1. [OAuth 2.0 Scopes](#oauth-20-scopes)
2. [Message Format](#message-format)
3. [Label Structure](#label-structure)
4. [Query Operators](#query-operators)
5. [API Rate Limits](#api-rate-limits)
6. [Error Codes](#error-codes)

---

## OAuth 2.0 Scopes

Gmail API uses OAuth 2.0 scopes to define access permissions. Choose the minimum scope necessary for your use case.

### Available Scopes

| Scope | Full URL | Permissions | Use Case |
|-------|----------|-------------|----------|
| `gmail.readonly` | `https://www.googleapis.com/auth/gmail.readonly` | Read all emails, labels, and settings | Safe for read-only operations |
| `gmail.send` | `https://www.googleapis.com/auth/gmail.send` | Send emails only | When only sending is needed |
| `gmail.labels` | `https://www.googleapis.com/auth/gmail.labels` | Create, update, delete labels | Label management only |
| `gmail.modify` | `https://www.googleapis.com/auth/gmail.modify` | Read, write, send, delete | **Recommended for this skill** - covers all operations |
| `gmail.compose` | `https://www.googleapis.com/auth/gmail.compose` | Create, read, update drafts; send | Draft management |
| `gmail.insert` | `https://www.googleapis.com/auth/gmail.insert` | Insert messages directly | Advanced use cases |
| `gmail.metadata` | `https://www.googleapis.com/auth/gmail.metadata` | Read email metadata only | Headers without body |
| `mail.google.com` | `https://mail.google.com/` | Full access | Maximum permissions |

### Scope Combinations

This skill uses `gmail.modify` by default, which includes:
- ✅ Read all emails (`gmail.readonly`)
- ✅ Send emails (`gmail.send`)
- ✅ Manage labels (`gmail.labels`)
- ✅ Modify messages (archive, trash, star)

### Changing Scopes

To change scopes, re-authenticate:

```bash
# Read-only access
python gmail_auth.py --scopes gmail.readonly

# Read and send only
python gmail_auth.py --scopes "gmail.readonly,gmail.send"

# Full access
python gmail_auth.py --scopes gmail.modify
```

**Important:** Changing scopes requires re-authentication. The new token will replace the existing one.

---

## Message Format

Gmail API represents messages as complex JSON objects. This skill simplifies the format.

### Message Structure (Full)

```json
{
  "id": "string",
  "threadId": "string",
  "labelIds": ["string"],
  "snippet": "string",
  "payload": {
    "partId": "string",
    "mimeType": "string",
    "filename": "string",
    "headers": [
      {
        "name": "string",
        "value": "string"
      }
    ],
    "body": {
      "attachmentId": "string",
      "size": number,
      "data": "string"
    },
    "parts": [
      {
        "partId": "string",
        "mimeType": "string",
        "filename": "string",
        "headers": [],
        "body": {}
      }
    ]
  },
  "sizeEstimate": number,
  "historyId": "string",
  "internalDate": "string"
}
```

### Simplified Message Format (This Skill)

The skill simplifies this to:

**Minimal Format:**
```json
{
  "id": "18d1a2b3c4d5e6f7",
  "threadId": "18d1a2b3c4d5e6f7"
}
```

**Metadata Format:**
```json
{
  "id": "18d1a2b3c4d5e6f7",
  "threadId": "18d1a2b3c4d5e6f7",
  "subject": "Meeting Tomorrow",
  "from": "John Doe <john@example.com>",
  "to": "user@gmail.com",
  "date": "Wed, 15 Jan 2026 10:30:00 -0800",
  "snippet": "Quick reminder about our meeting..."
}
```

**Full Format:**
```json
{
  "id": "18d1a2b3c4d5e6f7",
  "threadId": "18d1a2b3c4d5e6f7",
  "subject": "Meeting Tomorrow",
  "from": "John Doe <john@example.com>",
  "to": "user@gmail.com",
  "date": "Wed, 15 Jan 2026 10:30:00 -0800",
  "snippet": "Quick reminder about our meeting...",
  "body": "Full plain text email body content here..."
}
```

### Important Headers

Common email headers extracted by this skill:

| Header | Description | Example |
|--------|-------------|---------|
| `From` | Sender email and name | `John Doe <john@example.com>` |
| `To` | Primary recipients | `user@example.com, team@example.com` |
| `Cc` | Carbon copy recipients | `manager@example.com` |
| `Subject` | Email subject line | `Meeting Tomorrow` |
| `Date` | Send timestamp | `Wed, 15 Jan 2026 10:30:00 -0800` |
| `Message-ID` | Unique message identifier | `<abc123@mail.gmail.com>` |
| `In-Reply-To` | ID of message being replied to | `<xyz789@mail.gmail.com>` |

### MIME Types

Common MIME types in email messages:

- `text/plain` - Plain text body
- `text/html` - HTML formatted body
- `multipart/alternative` - Both plain and HTML versions
- `multipart/mixed` - Message with attachments
- `application/pdf` - PDF attachment
- `image/jpeg` - JPEG image attachment
- `application/octet-stream` - Generic binary file

This skill extracts `text/plain` content when available.

---

## Label Structure

Gmail labels are like folders but more flexible (messages can have multiple labels).

### Label Object

```json
{
  "id": "string",
  "name": "string",
  "messageListVisibility": "show|hide",
  "labelListVisibility": "labelShow|labelHide",
  "type": "system|user",
  "messagesTotal": number,
  "messagesUnread": number,
  "threadsTotal": number,
  "threadsUnread": number,
  "color": {
    "textColor": "string",
    "backgroundColor": "string"
  }
}
```

### System Labels

Built-in labels that cannot be created or deleted:

| Label ID | Name | Purpose |
|----------|------|---------|
| `INBOX` | Inbox | Primary inbox |
| `SENT` | Sent | Sent mail |
| `DRAFT` | Drafts | Draft messages |
| `SPAM` | Spam | Spam folder |
| `TRASH` | Trash | Deleted items |
| `UNREAD` | Unread | Unread messages |
| `STARRED` | Starred | Starred/flagged |
| `IMPORTANT` | Important | Gmail's importance marking |
| `CATEGORY_PERSONAL` | Personal | Personal category (Gmail tabs) |
| `CATEGORY_SOCIAL` | Social | Social networks category |
| `CATEGORY_PROMOTIONS` | Promotions | Marketing emails category |
| `CATEGORY_UPDATES` | Updates | Transactional emails category |
| `CATEGORY_FORUMS` | Forums | Mailing lists category |

### User Labels

User-created labels:

- Can have any name (except system label names)
- Support hierarchy with "/" separator: `Work/Projects/Q1`
- Can be colored (via Gmail web interface)
- Can be nested unlimited levels deep

### Label Visibility

- `messageListVisibility`: Whether messages with this label show in message list
  - `show`: Show in message list (default)
  - `hide`: Hide from message list

- `labelListVisibility`: Whether label appears in label list
  - `labelShow`: Show in label list (default)
  - `labelHide`: Hide from label list

---

## Query Operators

Gmail search syntax supported by the API.

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `from:` | Messages from sender | `from:alice@example.com` |
| `to:` | Messages to recipient | `to:bob@example.com` |
| `subject:` | Words in subject line | `subject:meeting` |
| `label:` | Messages with label | `label:important` |
| `has:` | Messages with feature | `has:attachment` |
| `filename:` | Attachment filename | `filename:report.pdf` |
| `in:` | Messages in location | `in:inbox` |
| `is:` | Messages with property | `is:unread` |
| `after:` | Messages after date | `after:2026/01/01` |
| `before:` | Messages before date | `before:2026/12/31` |
| `older_than:` | Messages older than | `older_than:7d` |
| `newer_than:` | Messages newer than | `newer_than:30d` |
| `larger:` | Messages larger than | `larger:5M` |
| `smaller:` | Messages smaller than | `smaller:1M` |
| `size:` | Messages of size | `size:10M` |

### Boolean Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `OR` | Logical OR | `from:alice OR from:bob` |
| `{ }` | Alternative OR syntax | `{from:alice from:bob}` |
| `-` | NOT (exclude) | `-from:spam@example.com` |
| `" "` | Exact phrase | `"quarterly report"` |
| `( )` | Grouping | `(from:alice OR from:bob) is:unread` |

### Date Formats

**Absolute dates:**
- `YYYY/MM/DD`: `2026/01/15`
- `YYYY/M/D`: `2026/1/15` (leading zeros optional)

**Relative dates:**
- `d`: days (`newer_than:7d`)
- `m`: months (`older_than:3m`)
- `y`: years (`older_than:1y`)

### Size Units

- `M`: Megabytes (`larger:5M`)
- `K`: Kilobytes (`larger:500K`)
- No unit: Bytes (`larger:1000`)

### Special Values

| Value | Description |
|-------|-------------|
| `me` | Current user's email |
| `*` | Wildcard (in domains) |

### Complex Query Examples

```
# Unread emails from last week, from specific domain, with attachments
from:*@company.com is:unread has:attachment newer_than:7d

# Important emails not yet processed
is:important -label:processed -in:trash

# Large PDF invoices from Q1
filename:pdf subject:invoice after:2026/01/01 before:2026/04/01 larger:1M

# Team emails excluding automated messages
(from:alice OR from:bob OR from:charlie) -from:noreply
```

---

## API Rate Limits

Gmail API enforces quota limits to prevent abuse.

### Quota Units

Different operations consume different quota units:

| Operation | Quota Cost | Example |
|-----------|------------|---------|
| `users.messages.list` | 5 units | List messages in inbox |
| `users.messages.get` | 5 units | Get single message |
| `users.messages.send` | 100 units | Send an email |
| `users.messages.modify` | 5 units | Add/remove labels |
| `users.labels.list` | 5 units | List all labels |
| `users.labels.create` | 5 units | Create a label |
| `users.getProfile` | 1 unit | Get user profile |

### Default Quotas

**Per User:**
- 250 quota units per user per second
- 1 billion quota units per day

**Example Calculations:**

```
# Reading 20 emails (metadata format)
- users.messages.list: 5 units
- users.messages.get × 20: 100 units
Total: 105 units

# Sending 10 emails
- users.messages.send × 10: 1000 units
Total: 1000 units

# Labeling 50 messages
- users.labels.list: 5 units
- users.messages.modify × 50: 250 units
Total: 255 units
```

### Best Practices

1. **Use minimal format when possible:**
   ```bash
   # ✅ Efficient (5 units per message)
   --format minimal

   # ❌ Less efficient (5 units per message but transfers more data)
   --format full
   ```

2. **Limit max-results:**
   ```bash
   # ✅ Get only what you need
   --max-results 10

   # ❌ Fetching unnecessary data
   --max-results 100
   ```

3. **Use specific queries:**
   ```bash
   # ✅ Narrow query
   from:sender after:2026/01/01 is:unread

   # ❌ Broad query
   from:sender
   ```

4. **Batch operations** when possible

5. **Cache results** to avoid repeated calls

### Quota Exceeded Response

```json
{
  "error": {
    "errors": [
      {
        "domain": "usageLimits",
        "reason": "quotaExceeded",
        "message": "Quota exceeded"
      }
    ],
    "code": 429,
    "message": "Quota exceeded"
  }
}
```

**Solution:** Wait 60 seconds and retry. For sustained high usage, request quota increase in Google Cloud Console.

---

## Error Codes

Common HTTP error codes returned by Gmail API.

### HTTP Status Codes

| Code | Name | Cause | Solution |
|------|------|-------|----------|
| 200 | OK | Success | N/A |
| 400 | Bad Request | Invalid parameter | Check query syntax |
| 401 | Unauthorized | Invalid credentials | Re-authenticate |
| 403 | Forbidden | Insufficient permissions | Check OAuth scopes |
| 404 | Not Found | Resource doesn't exist | Verify message/label ID |
| 409 | Conflict | Resource already exists | Label name already used |
| 429 | Too Many Requests | Rate limit exceeded | Wait and retry |
| 500 | Internal Server Error | Gmail API issue | Retry after delay |
| 503 | Service Unavailable | Temporary outage | Retry with backoff |

### Error Response Format

```json
{
  "error": {
    "errors": [
      {
        "domain": "string",
        "reason": "string",
        "message": "string",
        "locationType": "string",
        "location": "string"
      }
    ],
    "code": number,
    "message": "string"
  }
}
```

### Common Error Reasons

| Reason | Description | Solution |
|--------|-------------|----------|
| `authError` | Authentication failed | Re-run gmail_auth.py |
| `invalidArgument` | Invalid parameter value | Check parameter format |
| `invalidQuery` | Invalid search syntax | Fix query syntax |
| `quotaExceeded` | Rate limit hit | Wait and retry |
| `insufficientPermissions` | Missing OAuth scope | Re-auth with broader scope |
| `notFound` | Resource doesn't exist | Verify ID |
| `backendError` | Temporary Gmail issue | Retry with exponential backoff |

### Error Handling Strategy

1. **400 errors:** Fix the request (bad syntax)
2. **401/403 errors:** Re-authenticate with correct scopes
3. **404 errors:** Resource doesn't exist (expected in some cases)
4. **409 errors:** Resource already exists (may be acceptable)
5. **429 errors:** Rate limiting - implement retry with backoff
6. **500/503 errors:** Temporary - retry with exponential backoff

### Retry Logic Example

```python
import time

max_retries = 3
retry_delay = 1  # seconds

for attempt in range(max_retries):
    try:
        result = api_call()
        break
    except HttpError as e:
        if e.status_code == 429 or e.status_code >= 500:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
        raise
```

---

## Additional Resources

### Official Documentation

- **Gmail API Overview:** https://developers.google.com/gmail/api/guides
- **API Reference:** https://developers.google.com/gmail/api/reference/rest
- **Python Client Library:** https://googleapis.github.io/google-api-python-client/
- **OAuth 2.0:** https://developers.google.com/identity/protocols/oauth2

### Python Client Examples

- **Quickstart:** https://developers.google.com/gmail/api/quickstart/python
- **Samples:** https://github.com/googleworkspace/python-samples/tree/main/gmail

### Search Syntax

- **Gmail Search Operators:** https://support.google.com/mail/answer/7190
- **Advanced Search:** https://support.google.com/mail/answer/6593

### Quota Management

- **Usage Limits:** https://developers.google.com/gmail/api/reference/quota
- **Request Quota Increase:** Google Cloud Console → APIs & Services → Quotas

---

## Version Information

This reference is for Gmail API v1.

**Last Updated:** 2026-01-15

For the latest API documentation, always refer to the official Google documentation.
