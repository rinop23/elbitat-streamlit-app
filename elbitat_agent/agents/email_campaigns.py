"""Email campaign management and sending with SendGrid integration."""

import re
from typing import Dict, List, Optional
from datetime import datetime
import streamlit as st


def personalize_email(template: str, contact: Dict) -> str:
    """Replace placeholders in email template with contact data.
    
    Supported placeholders:
        {{email}}, {{company_name}}, {{website}}, {{first_name}}, {{country}}
    
    Args:
        template: Email template with placeholders
        contact: Contact dictionary with data
    
    Returns:
        Personalized email text
    """
    personalized = template
    
    # Extract first name from email if not provided
    first_name = contact.get('first_name', '')
    if not first_name and contact.get('email'):
        first_name = contact['email'].split('@')[0].split('.')[0].capitalize()
    
    # Replace all placeholders
    replacements = {
        '{{email}}': contact.get('email', ''),
        '{{company_name}}': contact.get('company_name', ''),
        '{{website}}': contact.get('website', ''),
        '{{first_name}}': first_name,
        '{{country}}': contact.get('country', ''),
    }
    
    for placeholder, value in replacements.items():
        personalized = personalized.replace(placeholder, value)
    
    return personalized


def send_email_sendgrid(to_email: str, subject: str, html_content: str, 
                       from_email: str = None) -> Dict[str, any]:
    """Send an email using SendGrid API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML email content
        from_email: Sender email (defaults to configured email in secrets)
    
    Returns:
        Dictionary with 'success' boolean and 'error' message if failed
    """
    try:
        # Check if SendGrid is configured
        if not hasattr(st, 'secrets') or 'SENDGRID_API_KEY' not in st.secrets:
            return {
                'success': False,
                'error': 'SendGrid API key not configured in secrets'
            }
        
        # Import SendGrid (only when needed)
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        api_key = st.secrets['SENDGRID_API_KEY']
        
        # Use configured sender email or default
        if not from_email:
            from_email = st.secrets.get('SENDGRID_FROM_EMAIL', 'noreply@elbitat.com')
        
        # Create email message
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Send email
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        return {
            'success': response.status_code in [200, 201, 202],
            'status_code': response.status_code,
            'message_id': response.headers.get('X-Message-Id', '')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def send_test_email(template: str, subject: str, test_email: str) -> Dict[str, any]:
    """Send a test email with dummy data to verify template.
    
    Args:
        template: Email HTML template
        subject: Email subject
        test_email: Email address to send test to
    
    Returns:
        Result dictionary with success status
    """
    # Create dummy contact data for testing
    test_contact = {
        'email': test_email,
        'company_name': 'Test Company AS',
        'website': 'https://testcompany.com',
        'first_name': 'John',
        'country': 'Denmark'
    }
    
    # Personalize template
    personalized_content = personalize_email(template, test_contact)
    
    # Send email
    return send_email_sendgrid(test_email, subject, personalized_content)


def send_campaign(campaign_id: int, contact_ids: List[int], 
                 subject: str, template: str, batch_size: int = 50) -> Dict[str, int]:
    """Send email campaign to multiple contacts.
    
    Args:
        campaign_id: Database ID of the campaign
        contact_ids: List of contact IDs to send to
        subject: Email subject line
        template: Email HTML template
        batch_size: Number of emails to send before pausing (rate limiting)
    
    Returns:
        Statistics dictionary with sent, failed, and skipped counts
    """
    from .database import get_all_email_contacts, record_email_send, update_email_contact_status
    
    stats = {'sent': 0, 'failed': 0, 'skipped': 0}
    
    # Get all contacts
    all_contacts = get_all_email_contacts()
    contacts_to_send = [c for c in all_contacts if c['id'] in contact_ids]
    
    for i, contact in enumerate(contacts_to_send, 1):
        try:
            # Skip if already contacted
            if contact.get('status') == 'contacted':
                stats['skipped'] += 1
                continue
            
            # Personalize email
            personalized_content = personalize_email(template, contact)
            personalized_subject = personalize_email(subject, contact)
            
            # Send email
            result = send_email_sendgrid(
                to_email=contact['email'],
                subject=personalized_subject,
                html_content=personalized_content
            )
            
            if result.get('success'):
                # Record successful send
                record_email_send(campaign_id, contact['id'], status='sent')
                update_email_contact_status(contact['id'], 'contacted')
                stats['sent'] += 1
                print(f"[{i}/{len(contacts_to_send)}] Sent to {contact['email']}")
            else:
                # Record failed send
                record_email_send(campaign_id, contact['id'], status='failed')
                stats['failed'] += 1
                print(f"[{i}/{len(contacts_to_send)}] Failed: {result.get('error')}")
            
            # Rate limiting: pause every batch_size emails
            if i % batch_size == 0:
                import time
                time.sleep(2)  # 2 second pause between batches
                
        except Exception as e:
            print(f"Error sending to {contact.get('email')}: {e}")
            stats['failed'] += 1
    
    return stats


def create_html_template(content: str, include_unsubscribe: bool = True) -> str:
    """Wrap plain content in professional HTML email template.
    
    Args:
        content: Main email content (can include HTML)
        include_unsubscribe: Whether to add unsubscribe link
    
    Returns:
        Full HTML email template
    """
    unsubscribe_html = ""
    if include_unsubscribe:
        unsubscribe_html = """
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999;">
            <p>If you no longer wish to receive these emails, <a href="{{unsubscribe_url}}" style="color: #999;">unsubscribe here</a>.</p>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                text-align: center;
                padding: 20px 0;
                border-bottom: 2px solid #f0f0f0;
            }}
            .content {{
                padding: 30px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #007bff;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px 0;
                font-size: 12px;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Elbitat</h2>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            {unsubscribe_html}
            <p>&copy; {datetime.now().year} Elbitat. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html_template


def get_default_templates() -> Dict[str, Dict[str, str]]:
    """Get default email templates for common scenarios.
    
    Returns:
        Dictionary of template name -> {subject, body}
    """
    return {
        "Introduction": {
            "subject": "Partnership Opportunity with Elbitat",
            "body": """
            <p>Hi {{first_name}},</p>
            
            <p>I came across {{company_name}} and was impressed by your work in the wellness industry.</p>
            
            <p>I'm reaching out from Elbitat, a digital marketing agency specializing in holistic wellness brands. We help agencies like yours amplify their reach through strategic social media campaigns and content creation.</p>
            
            <p>I'd love to explore how we might collaborate. Are you open to a brief call next week?</p>
            
            <a href="#" class="button">Schedule a Call</a>
            
            <p>Best regards,<br>
            The Elbitat Team</p>
            """
        },
        "Follow-up": {
            "subject": "Following up - {{company_name}}",
            "body": """
            <p>Hi {{first_name}},</p>
            
            <p>I wanted to follow up on my previous message about potential collaboration opportunities between Elbitat and {{company_name}}.</p>
            
            <p>We've recently helped several wellness agencies in {{country}} increase their social media engagement by an average of 150%. I believe we could create similar results for your agency.</p>
            
            <p>Would you be interested in seeing some case studies?</p>
            
            <p>Best regards,<br>
            The Elbitat Team</p>
            """
        },
        "Service Announcement": {
            "subject": "New Social Media Management Services",
            "body": """
            <p>Hi {{first_name}},</p>
            
            <p>I hope this email finds you well!</p>
            
            <p>I wanted to share an exciting update from Elbitat - we've launched a comprehensive social media management service specifically designed for wellness agencies.</p>
            
            <p><strong>What's included:</strong></p>
            <ul>
                <li>AI-powered content creation</li>
                <li>Multi-platform scheduling</li>
                <li>Performance analytics</li>
                <li>Dedicated account manager</li>
            </ul>
            
            <a href="#" class="button">Learn More</a>
            
            <p>Best regards,<br>
            The Elbitat Team</p>
            """
        }
    }
