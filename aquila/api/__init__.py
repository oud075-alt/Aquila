"""FastAPI surface for Aquila/MSPIS.

Closes prompt requirement #9: API endpoint expansion. Existing endpoints
(primitives/structural/pathology) are preserved by contract; new endpoints
expose the additional layers, replay, query, simulation, validation, and
narrative emission.
"""

from aquila.api.app import create_app

__all__ = ["create_app"]
