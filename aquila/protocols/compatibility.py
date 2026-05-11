from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName

PROTOCOL_VERSION = "1.0.0"


class ProtocolCompatibilityMatrix:
    """Pin layer schema_versions and check incoming outputs."""

    def __init__(self) -> None:
        self._pinned: dict[LayerName, str] = {ln: "1.0.0" for ln in LayerName}

    def pin(self, layer: LayerName, version: str) -> None:
        self._pinned[layer] = version

    def is_compatible(self, output: LayerOutput) -> bool:
        return output.schema_version.split(".")[0] == self._pinned[output.layer].split(".")[0]
