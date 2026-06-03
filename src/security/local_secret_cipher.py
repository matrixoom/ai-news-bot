"""本地配置密钥加解密工具。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


class LocalSecretCipher:
    """使用本地密钥派生流加密保存配置密钥。

    Args:
        secret_key: 本地根密钥；生产环境可由环境变量注入。

    Returns:
        初始化后的加解密工具。
    """

    def __init__(self, secret_key: str | None = None) -> None:
        self._secret_key = (secret_key or os.getenv("LOCAL_SECRET_KEY") or "trend-insight-local-secret").encode()

    def encrypt(self, plaintext: str) -> str:
        """加密明文密钥。

        Args:
            plaintext: 待加密文本。

        Returns:
            `v1:salt:nonce:ciphertext:mac` 格式密文；空文本返回空字符串。
        """

        if not plaintext:
            return ""
        salt = os.urandom(16)
        nonce = os.urandom(16)
        key = self._derive_key(salt)
        plaintext_bytes = plaintext.encode()
        stream = _keystream(key, nonce, len(plaintext_bytes))
        ciphertext = bytes(left ^ right for left, right in zip(plaintext_bytes, stream, strict=True))
        mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        return "v1:" + ":".join(_b64(part) for part in (salt, nonce, ciphertext, mac))

    def decrypt(self, payload: str) -> str:
        """解密密文。

        Args:
            payload: `encrypt` 生成的密文。

        Returns:
            解密后的明文；空密文返回空字符串。
        """

        if not payload:
            return ""
        version, salt_text, nonce_text, ciphertext_text, mac_text = payload.split(":", 4)
        if version != "v1":
            raise ValueError("unsupported secret payload version")
        salt = _unb64(salt_text)
        nonce = _unb64(nonce_text)
        ciphertext = _unb64(ciphertext_text)
        expected_mac = _unb64(mac_text)
        key = self._derive_key(salt)
        actual_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(actual_mac, expected_mac):
            raise ValueError("secret payload integrity check failed")
        stream = _keystream(key, nonce, len(ciphertext))
        plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=True))
        return plaintext.decode()

    def _derive_key(self, salt: bytes) -> bytes:
        """从本地根密钥派生加密 key。"""

        return hashlib.pbkdf2_hmac("sha256", self._secret_key, salt, 120_000, dklen=32)


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """使用 HMAC-SHA256 生成指定长度密钥流。"""

    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        chunks.append(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(chunks)[:length]


def _b64(value: bytes) -> str:
    """URL 安全 base64 编码。"""

    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    """URL 安全 base64 解码。"""

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
