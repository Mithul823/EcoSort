import re
import smtplib
import ssl
from email.message import EmailMessage

from settings import get_setting


class EmailError(Exception):
    pass


def valid_email(address):
    return len(address) <= 254 and re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", address
    ) is not None


def send_report(recipient, report):
    if not valid_email(recipient):
        raise EmailError("Enter one valid email address.")
    host = get_setting("SMTP_HOST", "smtp.gmail.com")
    username = get_setting("SMTP_USERNAME")
    password = get_setting("SMTP_PASSWORD")
    sender = get_setting("SMTP_FROM") or username
    if not all([host, username, password]):
        raise EmailError("Email is not configured. Add SMTP_USERNAME and SMTP_PASSWORD to your .env or Streamlit secrets.")
    if not valid_email(sender):
        raise EmailError("The sender must be a valid email address. Check SMTP_FROM or SMTP_USERNAME.")
    try:
        port = int(get_setting("SMTP_PORT", "587"))
        if port not in (465, 587):
            raise ValueError
    except ValueError:
        raise EmailError("Use SMTP_PORT 587 for STARTTLS or 465 for TLS.") from None

    message = EmailMessage()
    message["Subject"] = "Your EcoSort AI Report"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(report)
    context = ssl.create_default_context()
    try:
        connection = (smtplib.SMTP_SSL(host, port, timeout=20, context=context)
                      if port == 465 else smtplib.SMTP(host, port, timeout=20))
        with connection as server:
            if port == 587:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(username, password)
            if server.send_message(message):
                raise EmailError("The mail server rejected the recipient. Check the address.")
    except smtplib.SMTPAuthenticationError:
        raise EmailError("Email login failed. Check your Gmail address and Google app password.") from None
    except smtplib.SMTPRecipientsRefused:
        raise EmailError("The mail server rejected the recipient. Check the address.") from None
    except (smtplib.SMTPException, OSError):
        raise EmailError("Email delivery could not be confirmed. Check your inbox before retrying.") from None
