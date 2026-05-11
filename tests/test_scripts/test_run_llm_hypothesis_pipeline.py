"""CLI stub mode subprocess smoke test."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_stub_emits_pipeline_completed() -> None:
    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "DEEPRESEARCH_HYPOTHESIS_PIPELINE_STUB": "1"}
    cmd = [
        sys.executable,
        "-m",
        "DeepResearch.scripts.run_llm_hypothesis_pipeline",
        "--question",
        "stub question",
        "--output-jsonl",
        "-",
    ]
    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    last = json.loads(lines[-1])
    assert last["event_type"] == "pipeline_completed"
