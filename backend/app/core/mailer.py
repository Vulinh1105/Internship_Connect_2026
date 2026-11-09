import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from app.core import config

def configured():
    return bool(config.SMTP_HOST and config.MAIL_FROM) and bool(config.SMTP_USER) == bool(config.SMTP_PASSWORD)

def deliverable(email):
    # Tài khoản mẫu (@example.invalid) không có hộp thư thật.
    value = (email or "").strip().lower()
    return "@" in value and not value.endswith("@example.invalid")

def app_link(fragment=""):
    return config.APP_URL.rstrip("/") + "/" + (("#" + fragment) if fragment else "")

def send(to, subject, body):
    message = EmailMessage()
    message["From"] = config.MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message.set_content(body)
    if config.SMTP_SECURITY == "ssl":
        client = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=15, context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
    with client:
        if config.SMTP_SECURITY == "starttls":
            client.starttls(context=ssl.create_default_context())
        if config.SMTP_USER:
            client.login(config.SMTP_USER, config.SMTP_PASSWORD)
        client.send_message(message)
