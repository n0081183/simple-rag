"""Structured JSONL logging via structlog."""

import logging
import sys
from pathlib import Path

import structlog

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    log_dir = settings.logs_path
    log_dir.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app"):
    return structlog.get_logger(name).bind(channel=name)


def app_log_path() -> Path:
    return get_settings().logs_path / "app.jsonl"
