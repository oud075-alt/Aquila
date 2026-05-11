"""Pytest fixtures shared across the suite."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from tests.fixtures.generate_btcusdt_sample import write_default


@pytest.fixture(scope="session")
def sample_parquet() -> Path:
    target = Path(__file__).with_name("fixtures") / "btcusdt_1m_sample.parquet"
    if not target.exists():
        write_default(target)
    return target


@pytest.fixture
def tmp_data_root(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    tmp = tempfile.mkdtemp(prefix="mspis-test-")
    monkeypatch.setenv("MSPIS_DATA_ROOT", tmp)
    yield Path(tmp)
