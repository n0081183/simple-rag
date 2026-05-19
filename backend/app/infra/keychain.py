"""OS keychain integration for secrets — never plaintext in repo."""

from __future__ import annotations

import hashlib
import logging

import keyring

SERVICE_NAME = "siwz-rag-lite"

logger = logging.getLogger(__name__)


def _audit_use(secret_name: str) -> None:
    digest = hashlib.sha256(secret_name.encode()).hexdigest()[:12]
    logger.info("keychain_access name_hash=%s", digest)


def set_secret(name: str, value: str) -> None:
    keyring.set_password(SERVICE_NAME, name, value)


def get_secret(name: str) -> str | None:
    value = keyring.get_password(SERVICE_NAME, name)
    if value:
        _audit_use(name)
    return value


def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, name)
    except keyring.errors.PasswordDeleteError:
        pass


def has_secret(name: str) -> bool:
    return get_secret(name) is not None
