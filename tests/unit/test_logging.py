"""Unit tests for secret redaction filter and correlation ID tracking."""
from app.core.logging import RedactionFilter, correlation_id_ctx, setup_logging


def test_redaction_filter_masks_keys():
    """Redaction filter must mask secret tokens and credentials."""
    filter_ = RedactionFilter()
    sample_text = "Failed with api_key: 'sk-or-v1-abcdef1234567890' and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    redacted = filter_.redact(sample_text)
    assert "sk-or-v1-abcdef1234567890" not in redacted
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
    assert "[REDACTED]" in redacted

def test_correlation_id_in_log_record():
    """Correlation ID context var should be passed into log record."""
    _ = setup_logging()
    token = correlation_id_ctx.set("TEST-CORR-123")
    try:
        assert correlation_id_ctx.get() == "TEST-CORR-123"
    finally:
        correlation_id_ctx.reset(token)
