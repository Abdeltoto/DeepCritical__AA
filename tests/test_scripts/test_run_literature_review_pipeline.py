"""Smoke tests for literature review JSONL CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_literature_review_pipeline_jsonl_sequence():
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "DeepResearch.scripts.run_literature_review_pipeline",
            "--question",
            "What links sleep to memory?",
            "--source-mode",
            "fixture",
            "--no-live-retrieval",
            "--output-jsonl",
            "-",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) >= 3
    types = []
    for ln in lines:
        obj = json.loads(ln)
        types.append(obj["event_type"])
    assert "literature_review_started" in types
    assert "literature_review_completed" in types
    assert types.index("literature_review_started") < types.index(
        "literature_review_completed"
    )
