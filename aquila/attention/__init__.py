"""Cognitive attention allocator — prioritizes anomalies, contradictions,
regime-critical events. Outputs salience scores, never trade actions.
"""

from aquila.attention.engine import AttentionAllocator
from aquila.attention.schemas import AttentionReport, SalienceScore

__all__ = ["AttentionAllocator", "AttentionReport", "SalienceScore"]
