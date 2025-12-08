# Email Campaigns - Setup Guide

## Overview

The Email Campaigns feature allows you to:
- 🔍 **Discover business contacts** from the web automatically
- 📋 **Manage contact lists** with status tracking
- ✉️ **Create personalized email campaigns** with templates
- 🚀 **Send bulk emails** with delivery tracking

## Prerequisites

### 1. SendGrid Account (Required for sending emails)

SendGrid is used to send professional emails. Free tier includes 100 emails/day.

1. Sign up at https://sendgrid.com/
2. Verify your email address
3. Go to **Settings > API Keys**
4. Click **Create API Key**
5. Choose **Full Access** (or at least Mail Send permissions)
6. Copy the API key (it won't be shown again!)

### 2. Serper.dev Account (Optional - for better search results)

Serper.dev provides Google search results. The system has a free DuckDuckGo fallback if you skip this.

1. Sign up at https://serper.dev/
2. Get your free API key (2,500 free searches)
3. Paid plan: $5/month for 5,000 searches

## Configuration

### Add to Streamlit Secrets

In your Streamlit Cloud app settings, add these secrets:

```toml
# Required for sending emails
SENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SENDGRID_FROM_EMAIL = "noreply@yourdomain.com"  # Your verified sender email

# Optional - for better search results (DuckDuckGo fallback if not set)
SERPER_API_KEY = "your_serper_api_key_here"
```

### Local Development

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-openai-key"

SENDGRID_API_KEY = "your-sendgrid-key"
SENDGRID_FROM_EMAIL = "noreply@yourdomain.com"

# Optional
SERPER_API_KEY = "your-serper-key"

[credentials]
[credentials.usernames]
[credentials.usernames.admin]
name = "Administrator"
password = "$2b$12$6cu1qsgrlyLIUoN6adH2nezrZbgfNp0.39dIFYSZZRwrl0ynWXZtq"

[credentials.usernames.elbitat]
name = "Elbitat Team"
password = "$2b$12$x047S/8YsNREG2neeDws3.Db3WmN.RTUDYV9lyzgde3inZ6V43PTC"
```

## Usage Guide

### Tab 1: 🔍 Find Contacts

Discover business emails from the web.

1. Enter a **search query**: "wellness agencies", "marketing firms", "restaurants"
2. Select a **country**: "Denmark", "Sweden", "USA"
3. Set **max companies** to find (5-50)
4. Click **Start Discovery**
5. Review found contacts
6. Click **Save All Contacts to Database**

**How it works:**
- Searches Google (via Serper.dev) or DuckDuckGo for businesses
- Visits company websites
- Extracts emails from contact pages (/contact, /about, /team, etc.)
- Validates email format
- Filters out fake emails (example.com, test.com, etc.)

### Tab 2: 📋 Contact List

Manage your discovered contacts.

**Features:**
- View all contacts with details
- Filter by status (active, contacted, bounced, unsubscribed)
- Update contact status
- Delete contacts
- Export to CSV

**Contact Statuses:**
- **active**: Ready to receive emails
- **contacted**: Already sent an email
- **bounced**: Email address invalid/unreachable
- **unsubscribed**: Opted out of communications

### Tab 3: ✉️ Create Campaign

Build personalized email campaigns.

**Steps:**
1. Enter **campaign name** (e.g., "Q1 Partnership Outreach")
2. Write **email subject** (e.g., "Partnership Opportunity")
3. Choose a **template** or write custom content
4. Use **personalization tags**:
   - `{{company_name}}` - Company name
   - `{{first_name}}` - Contact's first name
   - `{{email}}` - Contact's email
   - `{{website}}` - Company website
   - `{{country}}` - Country
5. Preview with sample data
6. Click **Save Campaign**

**Default Templates:**
- **Introduction**: Partnership opportunity template
- **Follow-up**: Follow-up after initial contact
- **Service Announcement**: New service launch

### Tab 4: 🚀 Send Campaign

Send your email campaigns to contacts.

**Steps:**
1. Select a **saved campaign**
2. View campaign details and template
3. Choose recipients:
   - Send to all active contacts
   - OR select specific contacts
4. **Send test email** to yourself first (recommended!)
5. Click **Send to X Recipients**
6. Monitor progress and results

**Sending Features:**
- Batch sending (50 emails per batch)
- Rate limiting (2-second pause between batches)
- Personalization for each recipient
- Delivery tracking (sent/failed/skipped)
- Automatic status updates

## Email Personalization

Your email content is automatically personalized for each recipient:

**Template:**
```
Hi {{first_name}},

I noticed {{company_name}} at {{website}} and wanted to reach out.

We specialize in helping businesses in {{country}}...

Best regards
```

**Personalized Result:**
```
Hi John,

I noticed Acme Corp at https://acme.com and wanted to reach out.

We specialize in helping businesses in Denmark...

Best regards
```

## Database Storage

All data is stored in SQLite (`data/elbitat.db`):

- **email_contacts**: Contact information and status
- **email_campaigns**: Campaign templates and metrics
- **email_sends**: Individual send tracking

## API Rate Limits

### SendGrid Free Tier
- 100 emails/day
- Upgrade for more: https://sendgrid.com/pricing/

### Serper.dev Free Tier
- 2,500 searches/month
- Upgrade: $5/month for 5,000 searches

### DuckDuckGo (Fallback)
- No API key needed
- No rate limits
- Slightly less accurate than Google search

## Troubleshooting

### "SendGrid API key not configured"
- Add `SENDGRID_API_KEY` to Streamlit secrets
- Verify the key is correct

### "No contacts found"
- Try a more specific search query
- Check if SERPER_API_KEY is configured (optional)
- DuckDuckGo fallback may return fewer results

### "Failed to send test email"
- Verify `SENDGRID_FROM_EMAIL` matches a verified sender in SendGrid
- Check SendGrid account is active
- Verify API key has Mail Send permissions

### Emails going to spam
- Set up **SPF, DKIM, DMARC** records for your domain
- Use a verified domain in SendGrid
- Follow SendGrid's sender authentication guide: https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication

## Best Practices

1. **Always send a test email first** - Check formatting and personalization
2. **Start small** - Send to 10-20 contacts initially
3. **Monitor bounce rates** - Update contact statuses accordingly
4. **Respect unsubscribes** - Update status immediately
5. **Use clear subject lines** - Avoid spam trigger words
6. **Personalize content** - Use all available placeholders
7. **Follow GDPR/CAN-SPAM** - Include unsubscribe links
8. **Verify sender domain** - Better deliverability

## Legal Compliance

⚠️ **Important:** Ensure you comply with email marketing laws:

- **GDPR (EU)**: Obtain consent before sending emails
- **CAN-SPAM (USA)**: Include physical address and unsubscribe link
- **CASL (Canada)**: Get express consent before sending
- Always provide an easy way to unsubscribe

## Support

For issues or questions:
- Check Streamlit Cloud logs for errors
- Verify all API keys are correctly configured
- Ensure SendGrid sender email is verified
- Test with a single contact first

## Cost Estimate

**Free Tier (100 emails/day):**
- SendGrid: Free
- Serper.dev: Free (2,500 searches) or skip and use DuckDuckGo
- **Total: $0/month**

**Small Business (1,000 emails/month):**
- SendGrid: $19.95/month
- Serper.dev: $5/month or use DuckDuckGo free
- **Total: ~$25/month**

**Growing Business (10,000 emails/month):**
- SendGrid: $89.95/month
- Serper.dev: $5/month or use DuckDuckGo free
- **Total: ~$95/month**
