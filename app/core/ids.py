"""Unique ID generation utilities with semantic prefixes."""
import time
import uuid


def generate_id(prefix: str = "ID") -> str:
    """Generate a collision-resistant prefixed identifier."""
    ts = int(time.time() * 1000) % 1000000
    random_suffix = uuid.uuid4().hex[:6]
    return f"{prefix}-{ts:06d}-{random_suffix}"

def generate_run_id() -> str:
    return generate_id("RUN")

def generate_evidence_id() -> str:
    return generate_id("EV")

def generate_claim_id() -> str:
    return generate_id("CLM")

def generate_feedback_id() -> str:
    return generate_id("FB")
