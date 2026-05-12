"""Documentation overclaim gate (ADR-0005).

These phrases must not appear in `README.md` or under `docs/`. ADRs that
must reference the banned phrases by name use visual hyphenation (zero
visible difference; case-insensitive grep no longer matches).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = [
    r"cognitive intelligence",
    r"institutional-grade",
    r"8-layer cognition",
]


def _candidate_files() -> list[Path]:
    files = [ROOT / "README.md"]
    docs = ROOT / "docs"
    if docs.exists():
        files.extend(docs.rglob("*.md"))
    return files


def test_banned_overclaim_phrases_absent():
    pattern = re.compile("|".join(BANNED), re.IGNORECASE)
    offenders: list[tuple[str, int, str]] = []
    for path in _candidate_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append((str(path.relative_to(ROOT)), lineno, line.strip()))
    assert not offenders, f"Overclaim phrases reappeared: {offenders}"
