"""Build a clean source distribution zip of the MSPIS project.

Run with:

.. code-block:: bash

    python scripts/build_zip.py

Produces ``dist/mspis-<version>.zip`` ready for offline distribution.
"""

from __future__ import annotations

import fnmatch
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "1.0.0"
PACKAGE_NAME = f"mspis-{VERSION}"

EXCLUDE_DIRS = {".git", ".pytest_cache", "__pycache__", "dist", ".venv", "venv",
                ".mypy_cache", ".ruff_cache", ".idea", ".vscode", "data"}
EXCLUDE_GLOBS = ["*.pyc", "*.pyo", "*.egg-info", ".DS_Store", "Thumbs.db"]


def _should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    name = path.name
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS)


def build_zip() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{PACKAGE_NAME}.zip"
    if out.exists():
        out.unlink()

    files: list[Path] = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if _should_skip(rel):
            continue
        if p.is_file():
            files.append(p)

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(files):
            rel = f.relative_to(ROOT)
            arcname = Path(PACKAGE_NAME) / rel
            zf.write(f, arcname.as_posix())

    print(f"Created {out} ({out.stat().st_size / 1024:.1f} KB, {len(files)} files)")
    return out


if __name__ == "__main__":
    try:
        build_zip()
    except Exception as e:
        print(f"build_zip failed: {e}", file=sys.stderr)
        sys.exit(1)
