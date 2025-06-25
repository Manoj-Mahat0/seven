import os
import aiosmtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SMTP configuration from .env
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 25))  # default fallback to 25
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# ====================
# Renders a template file by replacing {{key}} with context[key]
def render_template(template_path: str, context: dict) -> str:
    try:
        with open(template_path, "r", encoding="utf-8") as file:
            content = file.read()
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
    except Exception as e:
        print(f"❌ Failed to render template {template_path}: {e}")
        return ""

# ====================
# Sends an email with optional HTML content
async def send_email(to_email: str, subject: str, text_body: str, html_body: str = None):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=False,
            use_tls=False,
            username=SMTP_USER,
            password=SMTP_PASS,
        )
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
