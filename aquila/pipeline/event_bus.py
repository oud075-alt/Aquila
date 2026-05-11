"""In-process pub/sub event bus. Closes audit gap #6.

Each `LayerOutput` is dispatched on a topic named after its layer. The bus
copies references (frozen models) — no mutation possible. For distributed
runtime, the `EventTransport` interface in `aquila.runtime` mirrors this
API and is swap-in compatible.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName

Handler = Callable[[LayerOutput], None]


@dataclass
class Subscription:
    layer: LayerName
    handler: Handler


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[LayerName, list[Handler]] = defaultdict(list)

    def subscribe(self, layer: LayerName, handler: Handler) -> Subscription:
        self._subs[layer].append(handler)
        return Subscription(layer=layer, handler=handler)

    def unsubscribe(self, sub: Subscription) -> None:
        handlers = self._subs.get(sub.layer, [])
        if sub.handler in handlers:
            handlers.remove(sub.handler)

    def publish(self, output: LayerOutput) -> None:
        for h in list(self._subs.get(output.layer, [])):
            h(output)
