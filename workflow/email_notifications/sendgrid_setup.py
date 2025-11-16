"""
SendGrid Email Service for Render Deployment.
Uses SendGrid API instead of SMTP for reliable email delivery.
"""

import os
import sendgrid
from sendgrid.helpers.mail import Mail


class SendGridSender:
    """SendGrid API email sender."""
    
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
        self.sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
    
    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via SendGrid API."""
        try:
            # Basic email validation
            if not to_email or '@' not in to_email or '.' not in to_email.split('@')[1]:
                print(f"Invalid email format: {to_email}")
                return False
            
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=body
            )
            
            response = self.sg.send(message)
            
            if response.status_code == 202:
                print(f"Email sent successfully to: {to_email}")
                return True
            else:
                print(f"SendGrid error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"SendGrid send failed to {to_email}: {e}")
            return False


# Setup Instructions:
"""
1. Sign up for SendGrid (free tier: 100 emails/day)
2. Create an API key in SendGrid dashboard
3. Add to .env file:
   SENDGRID_API_KEY=your_sendgrid_api_key
   FROM_EMAIL=noreply@yourdomain.com
4. Install dependency: pip install sendgrid
"""