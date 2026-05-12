"""Phase 0H — FastAPI surface for MSPIS.

All response models are versioned (`schema_version` carried by inner
DiagnosisEnvelope) and async. The behavior boundary CI test (Appendix P)
inspects every JSON response shape from this surface.
"""

from api.main import app

__all__ = ["app"]
