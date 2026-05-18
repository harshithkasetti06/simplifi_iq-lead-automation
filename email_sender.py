"""
email_sender.py
Sends the generated PDF report to the prospect via Gmail SMTP.
Completely free — uses Gmail App Password.
"""

import os
import smtplib
import logging
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EMAIL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  body {{ margin:0; padding:0; background:#0a0a0f; font-family: 'Segoe UI', Arial, sans-serif; }}
  .wrapper {{ max-width:600px; margin:0 auto; background:#0a0a0f; padding:32px 20px; }}
  .card {{ background:#16161f; border:1px solid #2a2a3a; border-radius:16px; overflow:hidden; }}
  .header {{ background:linear-gradient(135deg,#6c63ff,#9b59f5); padding:32px; text-align:center; }}
  .logo {{ font-size:22px; font-weight:800; color:#fff; letter-spacing:1px; }}
  .logo span {{ color:#43e97b; }}
  .header h2 {{ color:#fff; font-size:20px; margin:12px 0 4px; font-weight:700; }}
  .header p {{ color:rgba(255,255,255,0.7); font-size:14px; margin:0; }}
  .body {{ padding:32px; }}
  .greeting {{ color:#f0f0f8; font-size:16px; margin-bottom:16px; }}
  .text {{ color:#8888aa; font-size:14px; line-height:1.7; margin-bottom:16px; }}
  .highlight {{ background:#1e1e2e; border-left:3px solid #6c63ff; padding:16px 20px;
                border-radius:8px; color:#f0f0f8; font-size:14px; margin:20px 0; line-height:1.6; }}
  .report-badge {{ background:rgba(108,99,255,0.1); border:1px solid rgba(108,99,255,0.3);
                   border-radius:10px; padding:20px; text-align:center; margin:24px 0; }}
  .report-badge .icon {{ font-size:36px; margin-bottom:8px; }}
  .report-badge .label {{ color:#a89fff; font-size:12px; font-weight:600; letter-spacing:1px;
                          text-transform:uppercase; margin-bottom:4px; }}
  .report-badge .filename {{ color:#f0f0f8; font-size:14px; font-weight:500; }}
  .features {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:20px 0; }}
  .feature {{ background:#1a1a26; border:1px solid #2a2a3a; border-radius:8px;
               padding:12px 14px; color:#8888aa; font-size:13px; }}
  .feature strong {{ color:#f0f0f8; display:block; margin-bottom:2px; }}
  .cta {{ text-align:center; margin:28px 0; }}
  .cta a {{ background:linear-gradient(135deg,#6c63ff,#9b59f5); color:#fff;
             padding:14px 32px; border-radius:10px; text-decoration:none;
             font-weight:700; font-size:15px; display:inline-block; }}
  .footer {{ border-top:1px solid #2a2a3a; padding:20px 32px; text-align:center; }}
  .footer p {{ color:#444460; font-size:12px; margin:4px 0; }}
  .footer a {{ color:#6c63ff; text-decoration:none; }}
  @media(max-width:480px) {{ .features {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrapper">
  <div style="text-align:center;margin-bottom:20px;">
    <span class="logo">Simplif<span>IQ</span></span>
  </div>
  <div class="card">
    <div class="header">
      <div style="font-size:40px;margin-bottom:10px;">📊</div>
      <h2>Your Business Audit Report is Ready!</h2>
      <p>Personalized AI intelligence report for {company_name}</p>
    </div>
    <div class="body">
      <p class="greeting">Hi {first_name},</p>
      <p class="text">
        Thank you for submitting your details to SimplifIQ. Our AI has completed a thorough
        analysis of <strong style="color:#f0f0f8;">{company_name}</strong> and generated
        a personalized business audit report just for you.
      </p>
      <div class="highlight">
        Your report includes a <strong>digital presence score</strong>, key <strong>strengths &
        opportunities</strong>, tailored <strong>AI automation recommendations</strong>, and
        actionable <strong>next steps</strong> — all specific to {company_name} and the
        <strong>{industry}</strong> industry.
      </div>
      <div class="report-badge">
        <div class="icon">📄</div>
        <div class="label">Your Audit Report</div>
        <div class="filename">{company_name} — Business Intelligence Audit</div>
      </div>
      <p class="text">
        📎 The full report is attached to this email as a PDF. Open it to see your
        complete business analysis and recommendations.
      </p>
      <div class="features">
        <div class="feature"><strong>✦ Executive Summary</strong>Personalized company overview</div>
        <div class="feature"><strong>⚡ Digital Score</strong>Presence & maturity rating</div>
        <div class="feature"><strong>◈ Recommendations</strong>4 prioritized action items</div>
        <div class="feature"><strong>🤖 AI Automation</strong>Industry-specific opportunities</div>
      </div>
      <div class="cta">
        <a href="https://simplifiiq.com">Schedule a Free Consultation →</a>
      </div>
      <p class="text" style="font-size:13px;text-align:center;">
        Questions? Just reply to this email — we read every response.<br/>
        <a href="mailto:career@simplifiiq.com" style="color:#6c63ff;">career@simplifiiq.com</a>
      </p>
    </div>
    <div class="footer">
      <p>© {year} SimplifIQ — Simplifying AI Adoption for Businesses</p>
      <p><a href="https://simplifiiq.com">simplifiiq.com</a></p>
    </div>
  </div>
</div>
</body>
</html>
"""


def send_report_email(lead_data: dict, pdf_path: str) -> bool:
    """
    Send the generated PDF report to the prospect via Gmail SMTP.
    Returns True on success, False on failure.
    """
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        logger.error("Gmail credentials not found in environment variables.")
        return False

    first_name = lead_data.get("first_name", "there")
    last_name = lead_data.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()
    recipient_email = lead_data.get("email")
    company = lead_data.get("company_name", "Your Company")
    industry = lead_data.get("industry", "your industry")

    if not recipient_email:
        logger.error("No recipient email found.")
        return False

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your {company} Business Audit Report — SimplifIQ"
    msg["From"] = formataddr(("SimplifIQ Intelligence", gmail_address))
    msg["To"] = formataddr((full_name, recipient_email))
    msg["Reply-To"] = gmail_address

    # Plain text fallback
    plain_text = f"""Hi {first_name},

Your personalized business audit report for {company} is ready!

Please find the full PDF report attached to this email.

The report includes:
- Executive Summary specific to {company}
- Digital Presence Score & Analysis
- Key Strengths & Opportunities
- AI Automation Recommendations for {industry}
- Prioritized Next Steps

Questions? Reply to this email — we read every response.

Best regards,
The SimplifIQ Team
career@simplifiiq.com
https://simplifiiq.com
"""

    # HTML email
    html_content = EMAIL_HTML_TEMPLATE.format(
        first_name=first_name,
        company_name=company,
        industry=industry,
        year=datetime.now().year,
    )

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Attach PDF
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
        pdf_filename = f"{company.replace(' ', '_')}_Audit_Report.pdf"
        pdf_attachment.add_header(
            "Content-Disposition", "attachment", filename=pdf_filename
        )
        msg.attach(pdf_attachment)
    except FileNotFoundError:
        logger.error(f"PDF file not found: {pdf_path}")
        return False

    # Send via Gmail SMTP
    try:
        logger.info(f"Sending email to {recipient_email}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, recipient_email, msg.as_string())
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail authentication failed. Check your App Password.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error sending email: {e}")
    return False