"""Pluggable event transport for distributed runtime. Closes audit gap #55."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName

Handler = Callable[[LayerOutput], None]


class EventTransport(ABC):
    @abstractmethod
    def publish(self, output: LayerOutput) -> None:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, layer: LayerName, handler: Handler) -> None:  # pragma: no cover
        raise NotImplementedError


class InProcTransport(EventTransport):
    def __init__(self) -> None:
        self._h: dict[LayerName, list[Handler]] = defaultdict(list)

    def publish(self, output: LayerOutput) -> None:
        for h in list(self._h.get(output.layer, [])):
            h(output)

    def subscribe(self, layer: LayerName, handler: Handler) -> None:
        self._h[layer].append(handler)
