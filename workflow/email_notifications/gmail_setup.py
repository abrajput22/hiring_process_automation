"""
Gmail SMTP Setup for Free Email Sending.
Uses Gmail's free SMTP service with App Passwords.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class GmailSender:
    """Free Gmail SMTP email sender."""
    
    def __init__(self):
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587
        self.username = os.getenv("GMAIL_USERNAME")  # your-email@gmail.com
        self.password = os.getenv("GMAIL_APP_PASSWORD")  # 16-character app password
    
    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via Gmail SMTP."""
        try:
            # Basic email validation
            if not to_email or '@' not in to_email or '.' not in to_email.split('@')[1]:
                print(f"Invalid email format: {to_email}")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            print(f"Email sent successfully to: {to_email}")
            return True
        except smtplib.SMTPRecipientsRefused as e:
            print(f"Invalid recipient email: {to_email} - {e}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            print(f"Gmail authentication failed: {e}")
            return False
        except Exception as e:
            print(f"Gmail send failed to {to_email}: {e}")
            return False


# Setup Instructions:
"""
1. Enable 2-Factor Authentication on your Gmail account
2. Go to Google Account Settings > Security > App Passwords
3. Generate an App Password for "Mail"
4. Add to .env file:
   GMAIL_USERNAME=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-app-password
"""