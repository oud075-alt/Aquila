"""Aquila exception hierarchy."""


class AquilaError(Exception):
    """Base for every Aquila-specific error."""


class LayerExecutionError(AquilaError):
    """Raised when a cognitive layer fails to produce an output."""

    def __init__(self, layer: str, message: str, cause: Exception | None = None):
        super().__init__(f"[{layer}] {message}")
        self.layer = layer
        self.cause = cause


class SafetyViolationError(AquilaError):
    """Raised by Safety Kernel when a layer attempts forbidden output.

    Closes prompt audit gap #4 / #16 — centrally enforce "no trade signals".
    """


class SchemaValidationError(AquilaError):
    """Raised when a payload fails schema validation."""


class MemoryStoreError(AquilaError):
    """Raised by the episodic memory store on persistence failure."""
