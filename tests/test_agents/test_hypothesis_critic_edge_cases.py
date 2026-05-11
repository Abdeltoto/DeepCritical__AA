"""Critic edge cases for hypothesis_generation_agent."""

from __future__ import annotations

import pytest

from DeepResearch.src.agents.hypothesis_generation_agent import (
    CritiqueBatch,
    CritiqueItem,
    HypothesisCandidate,
    HypothesisPipelineError,
    _apply_critiques,
)
from DeepResearch.src.datatypes.hypothesis_generation import (
    HypothesisGenerationParams,
    HypothesisType,
)


def test_apply_critiques_invalid_indices_tracked() -> None:
    hs = [
        HypothesisCandidate(statement="A", hypothesis_type=HypothesisType.CAUSAL),
        HypothesisCandidate(statement="B", hypothesis_type=HypothesisType.CAUSAL),
    ]
    batch = CritiqueBatch(
        critiques=[
            CritiqueItem(index=99, keep=False),
            CritiqueItem(index=0, keep=True, confidence=0.8),
            CritiqueItem(index=1, keep=False),
        ]
    )
    out = _apply_critiques(hs, batch)
    assert 99 in out.invalid_indices
    assert len(out.hypotheses) == 1
    assert out.hypotheses[0].statement == "A"
    assert out.hypotheses[0].confidence == 0.8


def test_apply_critiques_all_dropped_flag() -> None:
    hs = [
        HypothesisCandidate(statement="A", hypothesis_type=HypothesisType.CAUSAL),
    ]
    batch = CritiqueBatch(critiques=[CritiqueItem(index=0, keep=False)])
    out = _apply_critiques(hs, batch)
    assert out.all_dropped is True
    assert out.hypotheses == []


def test_fail_on_critic_drop_all_param_exists() -> None:
    p = HypothesisGenerationParams(fail_on_critic_drop_all=True)
    assert p.fail_on_critic_drop_all is True


def test_hypothesis_pipeline_error_is_exception() -> None:
    assert isinstance(HypothesisPipelineError("x"), Exception)
