import smtplib
import unittest
from unittest.mock import patch

from email_service import EmailError, send_report


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.values = {"SMTP_USERNAME": "sender@gmail.com", "SMTP_PASSWORD": "fake-password"}
        setting = patch("email_service.get_setting", side_effect=lambda key, default="": self.values.get(key, default))
        setting.start()
        self.addCleanup(setting.stop)

    def test_invalid_recipient(self):
        for recipient in ["", "invalid", "a@b.com\nBcc: other@b.com"]:
            with self.assertRaises(EmailError):
                send_report(recipient, "report")

    def test_missing_configuration(self):
        self.values.clear()
        with self.assertRaisesRegex(EmailError, "not configured"):
            send_report("recipient@example.com", "report")

    @patch("email_service.smtplib.SMTP")
    def test_starttls_and_report_body(self, smtp):
        server = smtp.return_value.__enter__.return_value
        server.send_message.return_value = {}
        send_report("recipient@example.com", "Waste report\nBottle: recycle")
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("sender@gmail.com", "fake-password")
        message = server.send_message.call_args.args[0]
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertEqual(message["From"], "sender@gmail.com")
        self.assertIn("Bottle: recycle", message.get_content())

    @patch("email_service.smtplib.SMTP_SSL")
    def test_ssl_port(self, smtp):
        self.values["SMTP_PORT"] = "465"
        server = smtp.return_value.__enter__.return_value
        server.send_message.return_value = {}
        send_report("recipient@example.com", "report")
        server.starttls.assert_not_called()
        server.send_message.assert_called_once()

    @patch("email_service.smtplib.SMTP")
    def test_authentication_error(self, smtp):
        server = smtp.return_value.__enter__.return_value
        server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"private provider details")
        with self.assertRaisesRegex(EmailError, "login failed"):
            send_report("recipient@example.com", "report")
        server.send_message.assert_not_called()

    @patch("email_service.smtplib.SMTP")
    def test_timeout_not_retried(self, smtp):
        smtp.side_effect = TimeoutError("private details")
        with self.assertRaisesRegex(EmailError, "could not be confirmed"):
            send_report("recipient@example.com", "report")
        smtp.assert_called_once()

    def test_bad_port(self):
        self.values["SMTP_PORT"] = "25"
        with self.assertRaisesRegex(EmailError, "SMTP_PORT"):
            send_report("recipient@example.com", "report")
