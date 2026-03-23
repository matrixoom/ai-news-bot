import smtplib
import socket
import unittest
from unittest.mock import patch

from src.notifiers.email_notifier import EmailNotifier


class FallbackSmtpSslClient:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_calls = []
        self.sendmail_calls = []
        type(self).instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return 250, b"ok"

    def login(self, username, password):
        self.login_calls.append((username, password))
        return 235, b"ok"

    def sendmail(self, from_address, recipients, message):
        self.sendmail_calls.append((from_address, recipients, message))
        return {}


class EmailNotifierTests(unittest.TestCase):
    def setUp(self):
        FallbackSmtpSslClient.instances = []

    def test_qq_server_falls_back_to_ssl_when_starttls_connection_is_closed(self):
        notifier = EmailNotifier(
            smtp_server="smtp.qq.com",
            smtp_port=587,
            smtp_use_tls=True,
            username="571255945@qq.com",
            password="secret",
            from_address="571255945@qq.com",
            email_to="receiver@example.com",
        )

        with patch(
            "src.notifiers.email_notifier.socket.getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0)),
            ],
        ), patch(
            "src.notifiers.email_notifier.smtplib.SMTP",
            side_effect=smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
        ), patch(
            "src.notifiers.email_notifier.smtplib.SMTP_SSL",
            new=FallbackSmtpSslClient,
        ):
            sent = notifier.send("hello", subject="Test")

        self.assertTrue(sent)
        self.assertEqual(len(FallbackSmtpSslClient.instances), 1)
        client = FallbackSmtpSslClient.instances[0]
        self.assertEqual(client.host, "smtp.qq.com")
        self.assertEqual(client.port, 465)
        self.assertEqual(client.login_calls, [("571255945@qq.com", "secret")])
        self.assertEqual(len(client.sendmail_calls), 1)

    def test_suspicious_dns_resolution_fails_fast_with_clear_error(self):
        notifier = EmailNotifier(
            smtp_server="smtp.qq.com",
            smtp_port=587,
            smtp_use_tls=True,
            username="571255945@qq.com",
            password="secret",
            from_address="571255945@qq.com",
            email_to="receiver@example.com",
        )

        with patch(
            "src.notifiers.email_notifier.socket.getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.223", 0)),
            ],
        ):
            sent = notifier.send("hello", subject="Test")

        self.assertFalse(sent)
        self.assertIn("smtp_endpoint_unreachable", notifier.last_error)
        self.assertIn("198.18.0.223", notifier.last_error)


if __name__ == "__main__":
    unittest.main()
