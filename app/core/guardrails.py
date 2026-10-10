"""Input validation, prompt injection prevention, off-topic detection, and PII redaction."""
import re

from app.core.config import load_yaml_config

GUARDRAIL_CONFIG = load_yaml_config("guardrails.yaml")
TAXONOMY_CONFIG = load_yaml_config("taxonomy.yaml")

INJECTION_PATTERNS = [
    re.compile(pat) for pat in GUARDRAIL_CONFIG.get("injection_patterns", [
        r"(?i)ignore\s+(all\s+)?(previous|above)\s+instructions",
        r"(?i)system\s+prompt",
        r"(?i)reveal\s+(the\s+)?(api[\s_-]*)?(keys|passwords|credentials|secrets|token)",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)<\s*script",
        r"(?i)DAN\s+mode",
        r"(?i)role\s*:\s*system",
    ])
]

OFF_TOPIC_KEYWORDS = set(
    GUARDRAIL_CONFIG.get("off_topic_keywords", [
        "recipe", "movie review", "poem", "sports score", "celebrity gossip", "horoscope"
    ])
)

PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4})\b"),
    "long_digits": re.compile(r"\b\d{12,19}\b"),
}


def sanitize_text(text: str) -> str:
    """Strip dangerous control characters and trim whitespace."""
    if not text:
        return ""
    # Strip non-printable ascii control characters except newline and tab
    sanitized = "".join(ch for ch in text if ch in ("\n", "\t", "\r") or ord(ch) >= 32)
    return sanitized.strip()


def check_prompt_injection(text: str) -> bool:
    """Returns True if prompt injection attack patterns are detected."""
    for pat in INJECTION_PATTERNS:
        if pat.search(text):
            return True
    return False


def check_off_topic(text: str) -> bool:
    """Returns True if input text appears completely off-topic."""
    lower_text = text.lower()
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in lower_text:
            return True
    return False


def redact_pii(text: str) -> str:
    """Redact email addresses, phone numbers, and long numeric sequences."""
    res = text
    res = PII_PATTERNS["email"].sub("[EMAIL_REDACTED]", res)
    res = PII_PATTERNS["phone"].sub("[PHONE_REDACTED]", res)
    res = PII_PATTERNS["long_digits"].sub("[NUM_REDACTED]", res)
    return res


def map_or_validate_category(
    column_name: str, value: str | None
) -> tuple[str | None, bool, bool]:
    """Map a categorical value via synonyms, check taxonomy, or flag as novel.
    Returns: (canonical_value, is_valid, is_novel)
    """
    if not value or not value.strip():
        return None, True, False

    clean_val = value.strip()
    col_tax = TAXONOMY_CONFIG.get(column_name, {})
    allowed = col_tax.get("allowed_values", [])
    synonyms = col_tax.get("synonyms", {})

    # Exact case match
    if clean_val in allowed:
        return clean_val, True, False

    # Synonym lookup (case-insensitive)
    lower_val = clean_val.lower()
    if lower_val in synonyms:
        return synonyms[lower_val], True, False

    # Case-insensitive match on allowed values
    for item in allowed:
        if item.lower() == lower_val:
            return item, True, False

    # If it's disruption_type or industry and not in taxonomy, flag as NOVEL (not invalid)
    if column_name in ("disruption_type", "industry"):
        return clean_val, True, True

    # Other closed categoricals (e.g. tier, severity, size) must conform
    return clean_val, False, False
