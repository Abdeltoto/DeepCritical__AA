"""Tests for optional LLM literature synthesis (mocked agent)."""

from __future__ import annotations

import pytest

from DeepResearch.src.agents import literature_synthesis_llm as mod
from DeepResearch.src.agents.literature_synthesis_llm import (
    LiteratureLLMSynthesisParams,
    synthesize_literature_with_llm,
)
from DeepResearch.src.datatypes.literature_review import (
    LiteratureReviewRequest,
    LiteratureSearchPlan,
    LiteratureSource,
    LiteratureSynthesis,
    LiteratureSynthesisLLMOutput,
)


@pytest.mark.asyncio
async def test_synthesize_literature_with_llm_mock_agent(monkeypatch):
    out_syn = LiteratureSynthesis(
        summary="LLM summary",
        consensus_findings=["finding"],
        conflicting_findings=[],
        themes=[],
        limitations=[],
        gaps=[],
        future_work=[],
    )
    llm_out = LiteratureSynthesisLLMOutput(
        synthesis=out_syn,
        markdown_report="# LLM Markdown\n",
        disclaimer="",
    )

    class FakeResult:
        output = llm_out

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, *args, **kwargs):
            return FakeResult()

    monkeypatch.setattr(mod, "Agent", FakeAgent)

    req = LiteratureReviewRequest(question="Does sleep affect memory?")
    plan = LiteratureSearchPlan(
        question="Does sleep affect memory?", queries=["sleep memory"]
    )
    src = LiteratureSource(
        source_id="s1", title="Study", abstract="Abstract text " * 20
    )

    params = LiteratureLLMSynthesisParams(
        model_name="gpt-4o-mini",
        max_evidence_chars=8000,
    )

    syn, md, meta = await synthesize_literature_with_llm(
        question="Does sleep affect memory?",
        request=req,
        search_plan=plan,
        included_sources=[src],
        excluded_sources=[],
        screening_decisions=[],
        evidence_table=[],
        appraisals=[],
        duplicate_diagnostics=[],
        params=params,
    )

    assert syn.summary == "LLM summary"
    assert "LLM Markdown" in md
    assert "truncation_notes" in meta
