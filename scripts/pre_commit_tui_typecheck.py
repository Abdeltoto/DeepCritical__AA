#!/usr/bin/env python3
"""Run ``bun run typecheck`` in ``tui/`` when Bun is available (non-blocking skip otherwise)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tui = root / "tui"
    if not tui.is_dir():
        return 0
    bun = shutil.which("bun")
    if not bun:
        return 0
    package_json = tui / "package.json"
    if not package_json.is_file():
        return 0
    try:
        return subprocess.call(
            [bun, "run", "typecheck"],
            cwd=tui,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0


if __name__ == "__main__":
    sys.exit(main())
