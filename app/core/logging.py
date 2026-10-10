"""Application logging configuration with secret redaction and correlation IDs."""
import contextvars
import logging
import re
import sys

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")

SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|password|token|secret|authorization)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"), r"\1: [REDACTED]"),
    (re.compile(r"(?i)(Bearer)\s+([a-zA-Z0-9_\-\.]{15,})"), r"\1 [REDACTED]"),
]

class RedactionFilter(logging.Filter):
    """Filter that masks sensitive strings and tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.redact(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact(str(v)) for v in record.args)
        return True

    @classmethod
    def redact(cls, text: str) -> str:
        res = text
        for pat, repl in SECRET_PATTERNS:
            res = pat.sub(repl, res)
        return res

class CorrelationIdFilter(logging.Filter):
    """Injects current correlation ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get() or "none"
        return True

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with formatting, redaction, and correlation tracking."""
    logger = logging.getLogger("scd_assistant")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [corr=%(correlation_id)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    handler.addFilter(RedactionFilter())

    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = setup_logging()
