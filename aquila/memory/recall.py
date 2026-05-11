"""Structural-sequence recall — matches recent state transition sequences."""

from __future__ import annotations

from typing import Iterable

from aquila.memory.schemas import EpisodeRecord


def sequence_match(
    recent_states: list[str],
    records: Iterable[EpisodeRecord],
    n: int = 3,
) -> list[str]:
    """Find episode_ids whose preceding n-state sequence matches `recent_states`."""
    if len(recent_states) < n:
        return []
    target = tuple(recent_states[-n:])
    matches: list[str] = []
    history: list[tuple[str, str]] = []
    for rec in records:
        history.append((rec.episode_id, rec.diagnosis.state.value))
        if len(history) >= n:
            seq = tuple(s for _, s in history[-n:])
            if seq == target:
                matches.append(rec.episode_id)
    return matches
