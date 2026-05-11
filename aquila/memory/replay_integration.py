"""Replay integration for Layer 4.

During replay we typically want read-only memory: no writes to durable
archive, deterministic recall. This module wires those policies.
"""

from __future__ import annotations

from aquila.memory.engine import EpisodicMemoryLayer


def make_replay_memory(*args, **kwargs) -> EpisodicMemoryLayer:
    """Factory: builds an `EpisodicMemoryLayer` configured for replay
    (no writes, deterministic top-k).
    """
    kwargs.setdefault("write_on_real", False)
    return EpisodicMemoryLayer(*args, **kwargs)
