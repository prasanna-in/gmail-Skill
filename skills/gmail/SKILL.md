---
name: gmail
description: Use when the user asks to "read my email", "search my gmail", "send an email", "check my inbox", "manage gmail labels", "organize my email", or mentions Gmail operations like reading messages, composing emails, searching for emails, or managing folders/labels. Provides direct Gmail API integration for email reading, sending, and label management on personal Gmail accounts.
version: 0.1.0
---

# Gmail Integration Skill

This skill provides direct Gmail API integration for reading, searching, sending emails, and managing labels. All operations use standalone Python scripts that return JSON output for easy parsing.

## Prerequisites & Setup

Before using this skill, the user must complete a one-time OAuth2 setup:

### Step 1: Google Cloud Console Setup

The user needs to create OAuth2 credentials:

1. Visit https://console.cloud.google.com
2. Create a new project (or select existing)
3. Enable "Gmail API" for the project
4. Configure OAuth consent screen (Desktop app type)
5. Create "OAuth 2.0 Client ID" credentials
6. Download credentials JSON file
7. Save as `/Users/pk/work/gmail_skill/credentials/credentials.json`

### Step 2: Run Initial Authentication

Execute the authentication script to obtain tokens:

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_auth.py
```

This will:
- Open a browser for OAuth consent
- User grants permissions
- Save tokens to `/Users/pk/work/gmail_skill/credentials/token.json`
- Tokens auto-refresh in future operations

**If you encounter authentication errors**, the user needs to re-run `gmail_auth.py`.

For detailed setup instructions, refer to [references/troubleshooting.md](references/troubleshooting.md).

## Reading and Searching Emails

Use `gmail_read.py` to search for and retrieve emails.

### Basic Usage

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_read.py \
  --query "SEARCH_QUERY" \
  --max-results 10 \
  --format metadata
```

### Arguments

- `--query`: Gmail search query (required)
- `--max-results`: Number of emails to return (default: 10, max: 100)
- `--format`: Output detail level
  - `minimal`: Just message IDs and thread IDs
  - `metadata`: Includes subject, from, to, date, snippet (recommended)
  - `full`: Includes complete email body text

### Output Format

The script returns JSON with this structure:

```json
{
  "status": "success",
  "result_count": 2,
  "query": "is:unread",
  "messages": [
    {
      "id": "18d1a2b3c4d5e6f7",
      "threadId": "18d1a2b3c4d5e6f7",
      "subject": "Meeting Tomorrow",
      "from": "John Doe <john@example.com>",
      "to": "user@gmail.com",
      "date": "Wed, 15 Jan 2026 10:30:00 -0800",
      "snippet": "Quick reminder about our meeting...",
      "body": "..." // Only in 'full' format
    }
  ]
}
```

Parse the `messages` array to access email data.

### Common Search Queries

For comprehensive query syntax, see [examples/search-examples.md](examples/search-examples.md).

**Basic filters:**
- `is:unread` - Unread messages only
- `is:starred` - Starred messages
- `from:user@example.com` - From specific sender
- `to:me` - Sent directly to user
- `subject:invoice` - Subject contains "invoice"

**Date ranges:**
- `after:2026/01/01` - After specific date
- `newer_than:7d` - Last 7 days
- `older_than:1m` - Older than 1 month

**Attachments:**
- `has:attachment` - Any attachment
- `filename:pdf` - PDF files
- `larger:5M` - Files larger than 5MB

**Combining queries:**
- `from:boss@company.com is:unread` - Unread from specific sender
- `subject:invoice has:attachment after:2026/01/01` - Recent invoices with attachments

### Example: Check Unread Emails

When the user asks "check my unread emails":

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_read.py \
  --query "is:unread" \
  --max-results 20 \
  --format metadata
```

Then parse the JSON output and summarize the results for the user.

## Sending Emails

Use `gmail_send.py` to compose and send emails.

### Basic Usage

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_send.py \
  --to "recipient@example.com" \
  --subject "Email Subject" \
  --body "Email body text"
```

### Arguments

- `--to`: Recipient email(s), comma-separated (required)
- `--subject`: Email subject line (required)
- `--body`: Email body text (required, OR use --body-file)
- `--body-file`: Path to file containing body text (alternative to --body)
- `--cc`: CC recipient(s), comma-separated (optional)
- `--bcc`: BCC recipient(s), comma-separated (optional)
- `--attach`: File path to attach (optional, can use multiple times)

### Output Format

```json
{
  "status": "success",
  "message_id": "18d1a2b3c4d5e6f7",
  "thread_id": "18d1a2b3c4d5e6f7",
  "to": ["recipient@example.com"],
  "subject": "Meeting Tomorrow"
}
```

### Examples

**Simple email:**
```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_send.py \
  --to "colleague@example.com" \
  --subject "Quick Update" \
  --body "The project is on track for delivery next week."
```

**Multiple recipients with CC:**
```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_send.py \
  --to "team@example.com,manager@example.com" \
  --cc "stakeholder@example.com" \
  --subject "Q1 Results" \
  --body "Please see Q1 performance summary attached." \
  --attach /path/to/report.pdf
```

**Important Notes:**
- Gmail has a 25MB total attachment size limit
- Sent messages automatically appear in the "Sent" folder
- Email addresses are validated before sending
- Use quotes around recipient lists containing commas

## Managing Labels

Use `gmail_labels.py` to create labels and organize emails.

### List All Labels

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_labels.py \
  --action list
```

Returns JSON with all labels (system and user-created).

### Create New Label

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_labels.py \
  --action create \
  --name "Work/Projects"
```

**Note:** Use "/" for hierarchical labels (like folders).

### Apply Label to Messages

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_labels.py \
  --action apply \
  --label-name "Important" \
  --message-ids "18d1a2b3c4d5e6f7,18d1a2b3c4d5e6f8"
```

### Remove Label from Messages

```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_labels.py \
  --action remove \
  --label-name "Important" \
  --message-ids "18d1a2b3c4d5e6f7"
```

### Label Management Notes

- Messages can have multiple labels (unlike traditional folders)
- System labels (INBOX, SENT, TRASH, SPAM) cannot be created or deleted
- Removing a label doesn't delete the message
- Label names are case-sensitive

## Common Workflows

### Workflow 1: Find and Organize Emails

When user asks to "organize my support emails with a label":

1. **Search for emails:**
   ```bash
   python gmail_read.py --query "from:support@company.com" --format minimal
   ```

2. **Create label:**
   ```bash
   python gmail_labels.py --action create --name "Support"
   ```

3. **Apply label to messages:**
   ```bash
   python gmail_labels.py --action apply --label-name "Support" --message-ids "ID1,ID2,ID3"
   ```

### Workflow 2: Read and Reply

When user asks to "read my emails from John and send a reply":

1. **Search for emails:**
   ```bash
   python gmail_read.py --query "from:john@example.com" --max-results 5 --format full
   ```

2. **Parse the response and present to user**

3. **Send reply:**
   ```bash
   python gmail_send.py --to "john@example.com" --subject "Re: Previous Subject" --body "Reply text"
   ```

### Workflow 3: Daily Email Summary

When user asks "what emails did I get today?":

```bash
python gmail_read.py --query "newer_than:1d" --max-results 50 --format metadata
```

Parse the JSON and present a summary organized by sender or label.

## Error Handling

### Authentication Errors

If you see errors like:
- `"No valid credentials found"`
- `"Token refresh failed"`

**Solution:** User needs to re-authenticate:
```bash
python /Users/pk/work/gmail_skill/skills/gmail/scripts/gmail_auth.py
```

### Permission Errors

If you see `"Insufficient permissions"`:

**Cause:** The token was created with insufficient OAuth scopes.

**Solution:** Re-authenticate with broader scopes:
```bash
python gmail_auth.py --scopes gmail.modify
```

### Invalid Query Errors

If search fails with `"Invalid query"`:

**Solution:** Check query syntax. Refer to [examples/search-examples.md](examples/search-examples.md) for valid patterns.

### Common Error Types in JSON Output

All scripts return errors in this format:

```json
{
  "status": "error",
  "error_type": "ErrorTypeName",
  "message": "Human-readable description"
}
```

Error types:
- `MissingCredentials`: OAuth setup not completed
- `AuthenticationError`: Token issues
- `SearchError`: Invalid search query
- `SendError`: Email sending failed
- `LabelError`: Label operation failed
- `ValidationError`: Invalid email address or parameters

## Additional Resources

- **API Reference:** [references/api-reference.md](references/api-reference.md) - Complete Gmail API details
- **Troubleshooting:** [references/troubleshooting.md](references/troubleshooting.md) - Common issues and solutions
- **Search Examples:** [examples/search-examples.md](examples/search-examples.md) - Comprehensive query patterns
- **Google Documentation:** https://developers.google.com/gmail/api

## Implementation Notes

**For Claude:**

1. **Always use absolute paths** when calling scripts
2. **Parse JSON output** - all scripts return structured JSON on stdout
3. **Check status field** - `"success"` or `"error"`
4. **Handle errors gracefully** - provide clear guidance to user
5. **Combine operations** when appropriate (search → filter → label)
6. **Respect user privacy** - don't log email contents

**Token Management:**
- Tokens auto-refresh automatically in all scripts
- No need to manually manage authentication after initial setup
- If refresh fails, user needs to re-run `gmail_auth.py`

**Performance Considerations:**
- Use `--format metadata` for most queries (faster, less data)
- Use `--format full` only when body content is needed
- Limit `--max-results` to avoid excessive API calls
- Gmail API has rate limits (see api-reference.md)

**Security:**
- Credentials are stored in `/Users/pk/work/gmail_skill/credentials/`
- Never log or display credential contents
- Token files are gitignored
- All OAuth flows use HTTPS

## Skill Version

Version: 0.1.0
Last Updated: 2026-01-15

For skill updates or issues, check the project README.
