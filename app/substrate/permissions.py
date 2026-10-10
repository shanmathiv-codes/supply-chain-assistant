"""Gateway tier permission constants and role enforcement."""

from enum import Enum


class SubstrateTier(str, Enum):
    READ = "read"
    FEEDBACK = "feedback"
    ADMIN = "admin"


class SubstratePermissionError(PermissionError):
    """Raised when an operation is attempted that exceeds the tier's permissions."""

    pass
