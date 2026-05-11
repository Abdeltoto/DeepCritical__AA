"""hypothesis_generation tool must not nest asyncio loops."""

from __future__ import annotations

import pytest

from DeepResearch.src.tools.hypothesis_generation_tool import (
    HypothesisGenerationToolRunner,
)


@pytest.mark.asyncio
async def test_sync_run_rejected_inside_running_loop() -> None:
    runner = HypothesisGenerationToolRunner()
    result = runner.run({"question": "q", "parameters": "{}"})
    assert result.success is False
    assert result.error
    assert "event loop" in (result.error or "").lower()
