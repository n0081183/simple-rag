"""OS keychain integration for secrets — never plaintext in repo."""

from __future__ import annotations

import hashlib
import logging

import keyring

# Primary service name; legacy entries remain readable after rebrand.
SERVICE_NAME = "cortex-workbench"
LEGACY_SERVICE_NAMES = ("siwz-rag-lite",)

logger = logging.getLogger(__name__)

_memory_store: dict[str, str] = {}


def _audit_use(secret_name: str) -> None:
    digest = hashlib.sha256(secret_name.encode()).hexdigest()[:12]
    logger.info("keychain_access name_hash=%s", digest)


def set_secret(name: str, value: str) -> None:
    try:
        keyring.set_password(SERVICE_NAME, name, value)
    except keyring.errors.NoKeyringError:
        _memory_store[name] = value


def get_secret(name: str) -> str | None:
    try:
        value = keyring.get_password(SERVICE_NAME, name)
        if not value:
            for legacy in LEGACY_SERVICE_NAMES:
                value = keyring.get_password(legacy, name)
                if value:
                    break
    except keyring.errors.NoKeyringError:
        value = _memory_store.get(name)
    if value:
        _audit_use(name)
    return value


def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, name)
    except keyring.errors.PasswordDeleteError:
        pass
    except keyring.errors.NoKeyringError:
        _memory_store.pop(name, None)
    for legacy in LEGACY_SERVICE_NAMES:
        try:
            keyring.delete_password(legacy, name)
        except (keyring.errors.PasswordDeleteError, keyring.errors.NoKeyringError):
            pass


def has_secret(name: str) -> bool:
    return get_secret(name) is not None
