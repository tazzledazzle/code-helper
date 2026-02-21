"""Structured logging for Crew API: JSON to stdout with request_id via contextvars."""

import sys
import structlog


def configure_logging() -> None:
    """Configure structlog for JSON lines to stdout; use merge_contextvars for request_id."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
