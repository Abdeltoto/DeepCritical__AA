"""Pipeline JSONL event ordering with mocked LLM calls."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest

from DeepResearch.src.agents.hypothesis_generation_agent import (
    HypothesisBatchOutput,
    HypothesisCandidate,
    run_hypothesis_generation_pipeline,
)
from DeepResearch.src.agents.hypothesis_pipeline_events import JSONLEmitter
from DeepResearch.src.datatypes.hypothesis_generation import (
    HypothesisGenerationParams,
    HypothesisType,
)


@pytest.mark.asyncio
async def test_pipeline_emits_ordered_events() -> None:
    buf = io.StringIO()
    emitter = JSONLEmitter(buf)

    cand = HypothesisCandidate(
        statement="Event-order hypothesis.",
        hypothesis_type=HypothesisType.CAUSAL,
        confidence=0.9,
    )

    async def fake_evidence(*_a: object, **_k: object):
        return "evidence ctx", [], {"evidence_degraded": False, "chunk_count": 0}

    fake_run = AsyncMock(
        return_value=type(
            "R", (), {"output": HypothesisBatchOutput(hypotheses=[cand])}
        )()
    )

    params = HypothesisGenerationParams(
        enable_evidence_synthesis=False,
        enable_critic_pass=False,
        max_hypotheses=5,
        model_name="openai:gpt-4o-mini",
    ).model_dump(mode="python")

    with (
        patch(
            "DeepResearch.src.agents.hypothesis_generation_agent.fetch_hypothesis_evidence",
            new=fake_evidence,
        ),
        patch(
            "DeepResearch.src.agents.hypothesis_generation_agent.Agent",
        ) as agent_cls,
    ):
        agent_cls.return_value.run = fake_run
        await run_hypothesis_generation_pipeline(
            {"question": "Why X?", "dataset_name": "ds"},
            params,
            emitter=emitter,
        )

    lines = [ln for ln in buf.getvalue().strip().split("\n") if ln.strip()]
    types = [__import__("json").loads(ln)["event_type"] for ln in lines]
    assert types[0] == "pipeline_started"
    assert "evidence_fetch_started" in types
    assert "evidence_fetched" in types
    assert "proposer_started" in types
    assert "proposer_completed" in types
    assert "dedupe_applied" in types
    assert "dataset_built" in types
    assert types[-1] == "pipeline_completed"
