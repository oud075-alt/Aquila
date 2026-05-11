"""Cold-start / warm-up policy. Closes audit gap #46.

When the system has not yet accumulated enough history, layers report
`visibility="degraded"` and confidence is capped. The orchestrator threads
the warm-up state through the context.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WarmupPolicy:
    min_primitive_bars: int = 50
    min_structural_events: int = 5
    min_memory_episodes: int = 10

    def primitive_ready(self, bars: int) -> bool:
        return bars >= self.min_primitive_bars

    def structural_ready(self, events: int) -> bool:
        return events >= self.min_structural_events

    def memory_ready(self, episodes: int) -> bool:
        return episodes >= self.min_memory_episodes
