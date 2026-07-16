"""
tests/unit/test_email_service.py
"""

from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.email_service import EmailService


def test_disabled_when_smtp_host_not_configured() -> None:
    original_host = settings.SMTP_HOST
    settings.SMTP_HOST = ""
    try:
        service = EmailService()
        assert service.enabled is False

        result = service.send_onboarding_welcome(
            to_address="new.hire@example.com",
            full_name="Priya Sharma",
            username="priya.sharma",
            employee_code="EMP-0001",
            temp_password="Tmp#Passw0rd123",
            login_url="https://workhours.example.com/login",
        )
        assert result is False
    finally:
        settings.SMTP_HOST = original_host


@patch("app.services.email_service.smtplib.SMTP")
def test_sends_via_smtp_when_configured(mock_smtp_class: MagicMock) -> None:
    original_host, original_user = settings.SMTP_HOST, settings.SMTP_USERNAME
    settings.SMTP_HOST = "smtp.example.com"
    settings.SMTP_USERNAME = "apikey"
    try:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService()
        assert service.enabled is True

        result = service.send_onboarding_welcome(
            to_address="new.hire@example.com",
            full_name="Priya Sharma",
            username="priya.sharma",
            employee_code="EMP-0001",
            temp_password="Tmp#Passw0rd123",
            login_url="https://workhours.example.com/login",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()

        # The temp password and employee code must actually be in the sent body —
        # otherwise the whole point of this email is defeated.
        sent_body = mock_server.sendmail.call_args.args[2]
        assert "Tmp#Passw0rd123" in sent_body
        assert "EMP-0001" in sent_body
    finally:
        settings.SMTP_HOST = original_host
        settings.SMTP_USERNAME = original_user


@patch("app.services.email_service.smtplib.SMTP")
def test_smtp_failure_is_caught_and_returns_false(mock_smtp_class: MagicMock) -> None:
    import smtplib

    original_host = settings.SMTP_HOST
    settings.SMTP_HOST = "smtp.example.com"
    try:
        mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, "Service not available")

        service = EmailService()
        result = service.send_onboarding_welcome(
            to_address="new.hire@example.com",
            full_name="Priya Sharma",
            username="priya.sharma",
            employee_code="EMP-0001",
            temp_password="Tmp#Passw0rd123",
            login_url="https://workhours.example.com/login",
        )

        # A mail-server hiccup must never bubble up and take onboarding down with it.
        assert result is False
    finally:
        settings.SMTP_HOST = original_host
