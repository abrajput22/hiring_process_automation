"""
Unified Email Workflow for Hiring Process.
Handles all email notifications with template-based system.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime


class EmailWorkflow:
    """Unified email workflow for all hiring process stages."""
    
    def __init__(self):
        self.email_service = os.getenv("EMAIL_SERVICE", "sendgrid").lower()
        self.email_templates = self._load_templates()
        self.sender = None
        self._setup_email_service()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load email templates for different hiring stages."""
        return {
            "resume_shortlisted": {
                "subject": "🎉 Resume Shortlisted - {process_name}",
                "body": """
Dear {candidate_name},

Congratulations! Your resume has been shortlisted for the position: {process_name}

Your resume score: {score}/100

Next Steps - Online Assessment:
- Assessment Date: {oa_date}
- Duration: 30 minutes
- Questions: 5 Python MCQs

Online Assessment Links:
🔗 Localhost: {localhost_link}
🌐 Render: {render_link}

Important: 
- Use localhost link for local testing
- Use Render link for production access
- Links will be active only on the scheduled date

Best regards,
Hiring Team
"""
            },
            "online_assessment_cleared": {
                "subject": "✅ Online Assessment Cleared - {process_name}",
                "body": """
Dear {candidate_name},

Excellent work! You have successfully cleared the online assessment for: {process_name}

Your assessment score: {score}/100

Next Steps:
- You will be contacted for the offline interview
- Interview details will be shared soon

Best regards,
Hiring Team
"""
            },
            "offline_interview_cleared": {
                "subject": "🚀 Interview Cleared - {process_name}",
                "body": """
Dear {candidate_name},

Congratulations! You have successfully cleared the offline interview for: {process_name}

Your interview performance was excellent!

Next Steps:
- HR will contact you regarding the final offer
- Please wait for further communication

Best regards,
Hiring Team
"""
            },
            "rejection": {
                "subject": "Application Update - {process_name}",
                "body": """
Dear {candidate_name},

Thank you for your interest in the position: {process_name}

After careful consideration, we have decided to move forward with other candidates at this time.

We encourage you to apply for future opportunities that match your skills.

Best regards,
Hiring Team
"""
            },
            "interview_notification": {
                "subject": "📅 Interview Scheduled - {process_name}",
                "body": """
Dear {candidate_name},

Congratulations! You have been selected for the offline interview for: {process_name}

Interview Details:
- Date: {interview_date}
- Time: {interview_time}
- Venue: {company_address}
- Duration: 1 hour

Please bring:
- Valid ID proof
- Resume copies
- Any relevant certificates

Best regards,
Hiring Team
"""
            },
            "final_selection": {
                "subject": "🎉 Congratulations! You're Selected - {process_name}",
                "body": """
Dear {candidate_name},

Congratulations! We are delighted to inform you that you have been selected for the position: {process_name}

After careful evaluation of your resume, online assessment, and interviews, we are impressed with your qualifications.

Package Details:
{package_offered}

Next Steps:
- Our HR team will contact you within 2 business days with the offer letter
- Please keep your documents ready for the onboarding process

We look forward to welcoming you to our team!

Best regards,
Hiring Team
"""
            },

        }
    
    async def send_email(self, template_type: str, recipient_email: str, **kwargs) -> Dict[str, Any]:
        """Unified method to send emails using templates."""
        try:
            if template_type not in self.email_templates:
                return {"status": "error", "message": f"Template '{template_type}' not found"}
            
            template = self.email_templates[template_type]
            subject = template["subject"].format(**kwargs)
            body = template["body"].format(**kwargs)
            
            # Send email
            if self._is_email_configured():
                success = await self._send_real_email(recipient_email, subject, body)
                if not success:
                    return {"status": "error", "message": "Failed to send email"}
            else:
                print(f"[EMAIL MOCK] To: {recipient_email}")
                print(f"[EMAIL MOCK] Subject: {subject}")
                print(f"[EMAIL MOCK] Body: {body}")
            
            return {
                "status": "success",
                "message": f"Email sent to {recipient_email}",
                "template": template_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}",
                "template": template_type
            }
    
    def _setup_email_service(self):
        """Setup email service based on configuration."""
        if self.email_service == "sendgrid":
            from .sendgrid_setup import SendGridSender
            self.sender = SendGridSender()
        elif self.email_service == "gmail":
            from .gmail_setup import GmailSender
            self.sender = GmailSender()
        else:
            self.sender = None
    
    def _is_email_configured(self) -> bool:
        """Check if email service is configured."""
        return self.sender is not None
    
    async def _send_real_email(self, recipient: str, subject: str, body: str) -> bool:
        """Send email using configured service."""
        if self.sender:
            return await self.sender.send_email(recipient, subject, body)
        return False


# Global email workflow instance
email_workflow = EmailWorkflow()


# Unified functions for different hiring stages
async def send_resume_shortlisted_email(candidate_email: str, candidate_name: str, 
                                      process_name: str, score: int, localhost_link: str = "TBD", 
                                      render_link: str = "TBD", oa_date: str = "TBD") -> Dict[str, Any]:
    """Send email when resume is shortlisted."""
    return await email_workflow.send_email(
        "resume_shortlisted",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name,
        score=score,
        localhost_link=localhost_link,
        render_link=render_link,
        oa_date=oa_date
    )


async def send_online_assessment_cleared_email(candidate_email: str, candidate_name: str,
                                             process_name: str, score: int) -> Dict[str, Any]:
    """Send email when online assessment is cleared."""
    return await email_workflow.send_email(
        "online_assessment_cleared",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name,
        score=score
    )


async def send_offline_interview_cleared_email(candidate_email: str, candidate_name: str,
                                             process_name: str) -> Dict[str, Any]:
    """Send email when offline interview is cleared."""
    return await email_workflow.send_email(
        "offline_interview_cleared",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name
    )


async def send_rejection_email(candidate_email: str, candidate_name: str,
                             process_name: str, stage: str = None) -> Dict[str, Any]:
    """Send rejection email at any stage."""
    return await email_workflow.send_email(
        "rejection",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name,
        stage=stage or "application"
    )


async def send_interview_notification_email(candidate_email: str, candidate_name: str,
                                          process_name: str, interview_date: str, 
                                          interview_time: str, company_address: str) -> Dict[str, Any]:
    """Send interview notification email with date, time and venue."""
    return await email_workflow.send_email(
        "interview_notification",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name,
        interview_date=interview_date,
        interview_time=interview_time,
        company_address=company_address
    )


async def send_final_selection_email(candidate_email: str, candidate_name: str,
                                   process_name: str, package_offered: str) -> Dict[str, Any]:
    """Send final selection email."""
    return await email_workflow.send_email(
        "final_selection",
        candidate_email,
        candidate_name=candidate_name,
        process_name=process_name,
        package_offered=package_offered
    )



