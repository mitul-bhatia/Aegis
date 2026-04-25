"""
Aegis — Structured Logging Setup

Uses structlog to produce consistent, searchable log lines.
Every log line automatically includes timestamp and log level.

Pipeline logs also carry scan_id, repo, and commit so you can
grep/filter all logs for a single scan run.

Usage:
    from utils.logging import get_logger
    log = get_logger(__name__)

    # Basic log
    log.info("scan.started")

    # Bind context so every subsequent log carries these fields
    log = log.bind(scan_id=42, repo="owner/repo", commit="abc1234")
    log.info("pipeline.running")
    log.warning("exploit.failed", reason="timeout")
"""

import logging
import structlog


def setup_structured_logging(level: int = logging.INFO):
    """
    Configure structlog for the entire application.
    Call this once at startup (in config.setup_logging).

    Output format (dev-friendly, coloured):
        2026-04-25T10:30:00Z [info     ] scan.started  scan_id=42 repo=owner/repo
    """
    structlog.configure(
        processors=[
            # Merge any context variables bound via structlog.contextvars
            structlog.contextvars.merge_contextvars,
            # Add the log level string (info, warning, error…)
            structlog.processors.add_log_level,
            # Add ISO-8601 timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Pretty coloured output for local dev
            # Swap to structlog.processors.JSONRenderer() for production
            structlog.dev.ConsoleRenderer(),
        ],
        # Use standard logging levels (INFO, WARNING, etc.)
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # Cache the logger on first use for performance
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    """
    Return a structlog logger bound to the given module name.
    Drop-in replacement for logging.getLogger(__name__).
    """
    return structlog.get_logger(name)
