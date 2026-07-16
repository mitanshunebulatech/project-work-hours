"""
app/services/email_service.py

Plain SMTP via the stdlib smtplib/email modules — no vendor SDK, works with
any SMTP server (Gmail app password, a self-hosted Postfix box, Mailhog for
local dev, SES/SendGrid's SMTP interface, etc.). Provider is picked later via
config; this code doesn't care which one.

If SMTP_HOST isn't configured (empty string, the default), send_* methods
log a warning and return without raising — so onboarding an employee doesn't
hard-fail just because nobody's set up email yet in a dev/demo environment.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.enabled = bool(settings.SMTP_HOST)

    def _send(self, *, to_address: str, subject: str, text_body: str, html_body: str) -> bool:
        """
        Returns True if the message was handed off to the SMTP server,
        False if email isn't configured or sending failed. Callers (e.g.
        OnboardingService) should treat False as "log it and move on", not
        as a reason to fail the whole operation — the account still gets
        created either way.
        """
        if not self.enabled:
            logger.warning(
                "SMTP_HOST not configured — skipping email to %s (subject: %s)",
                to_address,
                subject,
            )
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_ADDRESS}>"
        message["To"] = to_address
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_ADDRESS, [to_address], message.as_string())
            return True
        except (smtplib.SMTPException, OSError) as exc:
            # Never let a mail-server hiccup take down onboarding — log and
            # let the caller decide what "email failed" means for the flow.
            logger.error("Failed to send email to %s: %s", to_address, exc)
            return False

    def send_onboarding_welcome(
        self,
        *,
        to_address: str,
        full_name: str,
        username: str,
        employee_code: str,
        temp_password: str,
        login_url: str,
    ) -> bool:
        subject = f"Welcome to {settings.SMTP_FROM_NAME} — your account is ready"

        text_body = (
            f"Hi {full_name},\n\n"
            f"Your {settings.SMTP_FROM_NAME} account has been created.\n\n"
            f"Employee ID: {employee_code}\n"
            f"Username: {username}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Log in here: {login_url}\n"
            "You'll be asked to set a new password the first time you log in.\n\n"
            "If you weren't expecting this account, please contact your HR team.\n"
        )

        html_body = f"""\
<html>
  <body style="font-family: sans-serif; color: #1a1a1a;">
    <p>Hi {full_name},</p>
    <p>Your {settings.SMTP_FROM_NAME} account has been created.</p>
    <table cellpadding="4">
      <tr><td><strong>Employee ID</strong></td><td>{employee_code}</td></tr>
      <tr><td><strong>Username</strong></td><td>{username}</td></tr>
      <tr><td><strong>Temporary password</strong></td><td><code>{temp_password}</code></td></tr>
    </table>
    <p><a href="{login_url}">Log in here</a> — you'll be asked to set a new
       password the first time you log in.</p>
    <p style="color: #666; font-size: 0.9em;">
      If you weren't expecting this account, please contact your HR team.
    </p>
  </body>
</html>
"""

        return self._send(
            to_address=to_address, subject=subject, text_body=text_body, html_body=html_body
        )
