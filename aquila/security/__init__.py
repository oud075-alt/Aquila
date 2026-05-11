"""Cognitive security boundaries.

- Immutable replay protection
- Ontology integrity validation
- Event tampering detection (via audit hash chain)
- Schema trust validation
"""

from aquila.security.integrity import IntegrityValidator

__all__ = ["IntegrityValidator"]
