"""
JSONL events for hypothesis → literature chain pipeline (CLI / OpenTUI).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HypothesisLiteratureChainStarted(BaseModel):
    event_type: str = Field("hypothesis_literature_chain_started", frozen=True)
    parent_question_preview: str = ""
    max_lit_reviews: int = 5


class HypothesisLiteratureHypothesisPhaseCompleted(BaseModel):
    event_type: str = Field(
        "hypothesis_literature_hypothesis_phase_completed",
        frozen=True,
    )
    hypothesis_count: int = 0
    dataset_name: str = ""


class HypothesisLiteratureReviewStarted(BaseModel):
    event_type: str = Field("hypothesis_literature_review_started", frozen=True)
    hypothesis_index: int
    review_question_preview: str = ""


class HypothesisLiteratureReviewCompleted(BaseModel):
    event_type: str = Field("hypothesis_literature_review_completed", frozen=True)
    hypothesis_index: int
    status: str


class HypothesisLiteratureChainCompleted(BaseModel):
    event_type: str = Field("hypothesis_literature_chain_completed", frozen=True)
    status: str
    literature_review_dataset: dict[str, Any] = Field(default_factory=dict)
    hypothesis_dataset: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


HypothesisLiteraturePipelineEvent = (
    HypothesisLiteratureChainStarted
    | HypothesisLiteratureHypothesisPhaseCompleted
    | HypothesisLiteratureReviewStarted
    | HypothesisLiteratureReviewCompleted
    | HypothesisLiteratureChainCompleted
)


class HypothesisLiteratureJSONLEmitter:
    """Writes one JSON object per line to a text stream."""

    def __init__(self, file_obj: Any) -> None:
        self._f = file_obj

    def emit(self, event: HypothesisLiteraturePipelineEvent) -> None:
        self._f.write(event.model_dump_json() + "\n")
        self._f.flush()

    async def aemit(self, event: HypothesisLiteraturePipelineEvent) -> None:
        self.emit(event)


__all__ = [
    "HypothesisLiteratureChainCompleted",
    "HypothesisLiteratureChainStarted",
    "HypothesisLiteratureHypothesisPhaseCompleted",
    "HypothesisLiteratureJSONLEmitter",
    "HypothesisLiteraturePipelineEvent",
    "HypothesisLiteratureReviewCompleted",
    "HypothesisLiteratureReviewStarted",
]
