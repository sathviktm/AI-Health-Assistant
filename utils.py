from datetime import datetime, timedelta
from dateutil import parser
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def send_email(to_email, subject, body):
    """
    Send an email using SMTP.
    
    Parameters:
    to_email (str): Recipient's email address
    subject (str): Email subject
    body (str): Email content
    
    Returns:
    bool: True if email was sent successfully, False otherwise
    """
    # Email credentials
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("SMTP_PASSWORD")  # Use App Password if using Gmail
    receiver_email = to_email
    
    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    # SMTP server configuration (Gmail example)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    try:
        # Connect to SMTP server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure connection
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {to_email}!")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def parse_natural_date(text: str) -> datetime:
    try:
        # Handle relative dates
        now = datetime.now()
        if "tomorrow" in text.lower():
            base_date = now + timedelta(days=1)
            return parser.parse(text, default=base_date)
        return parser.parse(text)
    except Exception as e:
        raise ValueError(f"Could not parse date: {str(e)}")