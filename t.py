import sendgrid
from sendgrid.helpers.mail import Mail

sg = sendgrid.SendGridAPIClient(api_key="your_sendgrid_api_key_here")

message = Mail(
    from_email="arvindmeena220479@acropolis.in",
    to_emails="abhishekrajput20252025@gmail.com",
    subject="Test Email",
    html_content="This is a test email"
)

try:
    response = sg.send(message)
    print("Status:", response.status_code)
    print("Body:", response.body)
except Exception as e:
    print("Error:", e)
