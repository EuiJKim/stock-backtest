class TraderError(Exception):
    """Base exception for the live trader."""


class SafetyError(TraderError):
    """Safety check failed (mode, limits, drift, kill-switch)."""


class BrokerError(TraderError):
    """Broker API call failed or returned unexpected response."""


class CredentialsError(TraderError):
    """Credentials missing, malformed, or disallowed mode."""


class StateError(TraderError):
    """State file corrupted or invariant violated."""
