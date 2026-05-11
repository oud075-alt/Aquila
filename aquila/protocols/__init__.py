"""Versioned cognitive protocols.

Lightweight inter-layer schema compatibility matrix. Each layer publishes
its schema_version; the protocol negotiator decides whether a given
upstream output is acceptable to the consuming layer.
"""

from aquila.protocols.compatibility import (
    PROTOCOL_VERSION,
    ProtocolCompatibilityMatrix,
)

__all__ = ["PROTOCOL_VERSION", "ProtocolCompatibilityMatrix"]
