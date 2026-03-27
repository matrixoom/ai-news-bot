"""
Email notification module using configurable SMTP settings.
"""
from __future__ import annotations

from datetime import datetime
import ipaddress
import os
import socket
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..logger import setup_logger


logger = setup_logger(__name__)
BENCHMARK_TEST_NET = ipaddress.ip_network("198.18.0.0/15")


class EmailNotifier:
    """Send email notifications with configurable SMTP transport."""

    def __init__(
        self,
        gmail_address: Optional[str] = None,
        gmail_app_password: Optional[str] = None,
        email_to: Optional[str] = None,
        *,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_use_tls: Optional[bool] = None,
        smtp_use_ssl: Optional[bool] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_address: Optional[str] = None,
    ):
        """
        Initialize EmailNotifier.

        Backward compatibility:
        - `gmail_address` maps to the SMTP username by default
        - `gmail_app_password` maps to the SMTP password by default
        - when no SMTP server is given, Gmail defaults are kept
        """
        env_username = os.getenv("SMTP_USERNAME") or os.getenv("GMAIL_ADDRESS")
        env_password = os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
        env_from = os.getenv("SMTP_FROM_ADDRESS") or os.getenv("GMAIL_ADDRESS")

        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER") or "smtp.gmail.com"
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT") or 587)
        self.smtp_use_tls = (
            bool(smtp_use_tls)
            if smtp_use_tls is not None
            else os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.smtp_use_ssl = (
            bool(smtp_use_ssl)
            if smtp_use_ssl is not None
            else os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
        self.username = username or gmail_address or env_username
        self.password = password or gmail_app_password or env_password
        self.from_address = from_address or self.username or env_from
        self.email_to = email_to or os.getenv("EMAIL_TO")
        self.timeout_seconds = float(os.getenv("SMTP_TIMEOUT_SECONDS", "20"))
        self.last_error = ""

        if not all([self.smtp_server, self.smtp_port, self.from_address, self.email_to]):
            logger.warning(
                "Email notifier not fully configured. "
                "Required: SMTP server, sender, and recipient."
            )
        else:
            logger.info(
                "EmailNotifier initialized (server=%s, from=%s)",
                self.smtp_server,
                self.from_address,
            )

    def send(
        self,
        content: str,
        subject: Optional[str] = None,
        language: str = "en",
        *,
        html_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email notification.

        Args:
            content: Plain text body
            subject: Email subject. If None, uses default with current date
            language: Language code to include in subject
            html_content: Optional pre-rendered HTML body
        """
        if subject is None:
            today = datetime.now().strftime("%Y-%m-%d")
            lang_suffix = f" [{language.upper()}]" if language != "en" else ""
            subject = f"AI News Digest - {today}{lang_suffix}"

        recipients = [item.strip() for item in str(self.email_to or "").split(",") if item.strip()]
        if not all([self.smtp_server, self.from_address, recipients]):
            logger.error("Email notifier is not fully configured. Skipping email send.")
            self.last_error = "email_config_incomplete"
            return False
        endpoint_error = self._diagnose_endpoint()
        if endpoint_error:
            logger.error("SMTP endpoint diagnosis failed: %s", endpoint_error)
            self.last_error = endpoint_error
            return False

        try:
            rendered_html = html_content or self._create_html_email(content, subject)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = ", ".join(recipients)

            msg.attach(MIMEText(content, "plain", "utf-8"))
            msg.attach(MIMEText(rendered_html, "html", "utf-8"))

            logger.info("Sending email via SMTP to %s", msg["To"])

            self._send_message(msg, recipients)

            logger.info("Email sent successfully via SMTP")
            self.last_error = ""
            return True

        except smtplib.SMTPAuthenticationError as error:
            logger.error("SMTP authentication failed: %s", error)
            self.last_error = f"smtp_auth_failed: {error}"
            return False
        except Exception as error:
            logger.error("Failed to send email via SMTP: %s", error, exc_info=True)
            self.last_error = str(error)
            return False

    def _send_message(self, msg: MIMEMultipart, recipients: list[str]) -> None:
        errors: list[Exception] = []
        candidates = self._connection_candidates()
        for index, candidate in enumerate(candidates):
            try:
                with self._open_connection(candidate) as server:
                    self._prepare_connection(server, candidate)
                    server.sendmail(self.from_address, recipients, msg.as_string())
                return
            except smtplib.SMTPServerDisconnected as error:
                errors.append(error)
                if self._should_retry_with_next_candidate(
                    candidate,
                    error,
                    has_more_candidates=index + 1 < len(candidates),
                ):
                    logger.warning(
                        "SMTP disconnected during %s connection to %s:%s, retrying alternate mode.",
                        candidate["label"],
                        self.smtp_server,
                        candidate["port"],
                    )
                    continue
                raise
            except Exception as error:
                errors.append(error)
                if self._should_retry_with_next_candidate(
                    candidate,
                    error,
                    has_more_candidates=index + 1 < len(candidates),
                ):
                    logger.warning(
                        "SMTP %s connection to %s:%s failed with %s, retrying alternate mode.",
                        candidate["label"],
                        self.smtp_server,
                        candidate["port"],
                        error,
                    )
                    continue
                raise
        if errors:
            raise errors[-1]

    def _should_retry_with_next_candidate(
        self,
        candidate: dict[str, object],
        error: Exception,
        *,
        has_more_candidates: bool,
    ) -> bool:
        if not has_more_candidates or not candidate.get("use_tls") or candidate.get("use_ssl"):
            return False
        return isinstance(error, (smtplib.SMTPServerDisconnected, ssl.SSLError, OSError))

    def _connection_candidates(self) -> list[dict[str, object]]:
        candidates = [
            {
                "use_ssl": self.smtp_use_ssl,
                "use_tls": self.smtp_use_tls and not self.smtp_use_ssl,
                "port": self.smtp_port,
                "label": "SSL" if self.smtp_use_ssl else ("STARTTLS" if self.smtp_use_tls else "plain"),
            }
        ]
        host = str(self.smtp_server or "").lower()
        should_try_qq_ssl_fallback = (
            not self.smtp_use_ssl
            and self.smtp_use_tls
            and ("smtp.qq.com" in host or "exmail.qq.com" in host)
            and self.smtp_port in {465, 587}
        )
        if should_try_qq_ssl_fallback:
            candidates.append(
                {
                    "use_ssl": True,
                    "use_tls": False,
                    "port": 465,
                    "label": "SSL fallback",
                }
            )
        return candidates

    def _open_connection(self, candidate: dict[str, object]):
        port = int(candidate["port"])
        if candidate["use_ssl"]:
            return smtplib.SMTP_SSL(self.smtp_server, port, timeout=self.timeout_seconds)
        return smtplib.SMTP(self.smtp_server, port, timeout=self.timeout_seconds)

    def _prepare_connection(self, server, candidate: dict[str, object]) -> None:
        server.ehlo()
        if candidate["use_tls"]:
            server.starttls()
            server.ehlo()
        if self.username and self.password:
            server.login(self.username, self.password)

    def _diagnose_endpoint(self) -> str:
        host = str(self.smtp_server or "").strip()
        if not host:
            return "smtp_server_missing"
        if host.lower() == "localhost":
            return ""
        try:
            infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            return f"smtp_dns_resolution_failed: {host} ({error})"

        addresses: list[str] = []
        suspicious: list[str] = []
        for info in infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            address = str(sockaddr[0])
            if address in addresses:
                continue
            addresses.append(address)
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            if self._is_suspicious_smtp_ip(ip):
                suspicious.append(address)

        if not addresses:
            return f"smtp_dns_resolution_failed: {host} (no addresses)"
        if suspicious and len(suspicious) == len(addresses):
            return (
                f"smtp_endpoint_unreachable: {host} resolved only to suspicious addresses "
                f"{', '.join(suspicious)}; likely DNS/proxy/TUN hijack or outbound SMTP blocked"
            )
        return ""

    def _is_suspicious_smtp_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if isinstance(ip, ipaddress.IPv4Address) and ip in BENCHMARK_TEST_NET:
            return True
        return any(
            (
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_unspecified,
            )
        )

    def _create_html_email(self, content: str, subject: str) -> str:
        """
        Create an HTML version of the email.
        """
        try:
            import markdown

            html_content = markdown.markdown(
                content,
                extensions=[
                    "nl2br",
                    "tables",
                    "fenced_code",
                    "sane_lists",
                ],
            )
        except ImportError:
            logger.warning("markdown library not installed, using basic HTML formatting")
            import html

            html_content = html.escape(content).replace("\n", "<br>\n")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 24px;
                    background: #f7f5ef;
                    color: #1b1b1b;
                    font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
                    line-height: 1.75;
                }}
                .container {{
                    max-width: 820px;
                    margin: 0 auto;
                    background: #fffdf7;
                    border: 1px solid #d6ccb8;
                    padding: 32px;
                }}
                h1, h2, h3 {{
                    color: #171717;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    border-bottom: 1px solid #ddd3bc;
                    padding: 8px 0;
                    text-align: left;
                }}
                a {{
                    color: #7a4f00;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                {html_content}
            </div>
        </body>
        </html>
        """
