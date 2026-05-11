"""Tests for hypothesis → literature chain (mocked network / LLM)."""

from __future__ import annotations

import pytest

from DeepResearch.src.agents import hypothesis_literature_chain as mod
from DeepResearch.src.agents.hypothesis_literature_chain import (
    build_literature_review_question,
    run_hypothesis_literature_chain,
)
from DeepResearch.src.datatypes.workflow_orchestration import HypothesisDataset


@pytest.mark.asyncio
async def test_build_literature_review_question_contains_hypothesis_and_parent():
    q = build_literature_review_question("Why X?", "Hypothesis H.")
    assert "Hypothesis H." in q
    assert "Why X?" in q


@pytest.mark.asyncio
async def test_run_hypothesis_literature_chain_smoke(monkeypatch):
    async def fake_hyp_pipeline(*_a, **_k):
        ds = HypothesisDataset(
            name="t",
            description="d",
            hypotheses=[
                {
                    "statement": "Sleep improves recall.",
                    "confidence": 0.9,
                    "hypothesis_type": "causal",
                },
            ],
            metadata={},
            source_workflows=["w"],
        )
        return ds, {"hypothesis_count": 1}

    async def fake_lit(q: str, cfg, mode=None, emitter=None):
        return {
            "question": q,
            "status": "success",
            "markdown_report": "# ok",
            "report": None,
            "metadata": {},
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr(mod, "run_hypothesis_generation_pipeline", fake_hyp_pipeline)
    monkeypatch.setattr(mod, "run_literature_review_workflow", fake_lit)

    lit_cfg = {
        "literature_review": {
            "source_mode": "fixture",
            "live_retrieval_enabled": False,
            "fixture_path": None,
            "llm_synthesis": {"enabled": False},
        }
    }

    _h, lit_ds, meta = await run_hypothesis_literature_chain(
        "Does sleep help memory?",
        {"model_name": "gpt-4o-mini"},
        lit_cfg,
        max_lit_reviews=3,
        hypothesis_input={"question": "Does sleep help memory?"},
        emitter=None,
    )

    assert len(lit_ds.entries) == 1
    assert lit_ds.entries[0].status == "success"
    assert meta["chain_status"] == "success"
