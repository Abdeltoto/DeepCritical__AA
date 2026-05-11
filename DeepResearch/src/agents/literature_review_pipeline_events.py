"""
JSONL event stream for the critical literature review workflow (CLI / OpenTUI).
"""

from __future__ import annotations

import json
import sys
from typing import Any, Literal

from pydantic import BaseModel, Field

LiteratureReviewStageName = Literal[
    "parse", "plan", "retrieve", "curate", "appraise", "synthesize"
]


class LiteratureReviewStarted(BaseModel):
    event_type: str = Field("literature_review_started", frozen=True)
    question_preview: str = ""
    source_mode: str = "fixture"
    live_retrieval_enabled: bool = False


class LiteratureReviewStage(BaseModel):
    event_type: str = Field("literature_review_stage", frozen=True)
    stage: LiteratureReviewStageName


class LiteratureReviewStageCompleted(BaseModel):
    event_type: str = Field("literature_review_stage_completed", frozen=True)
    stage: LiteratureReviewStageName
    n_candidates: int | None = None
    n_unique: int | None = None
    n_included: int | None = None
    n_excluded: int | None = None


class LiteratureReviewCompleted(BaseModel):
    event_type: str = Field("literature_review_completed", frozen=True)
    status: str
    markdown_preview: str = ""
    markdown_total_chars: int = 0
    markdown_truncated: bool = False


class LiteratureReviewError(BaseModel):
    event_type: str = Field("literature_review_error", frozen=True)
    stage: str
    message: str
    detail: str | None = None


class LiteratureReviewLLMStarted(BaseModel):
    event_type: str = Field("literature_review_llm_started", frozen=True)
    model_preview: str = ""


class LiteratureReviewLLMCompleted(BaseModel):
    event_type: str = Field("literature_review_llm_completed", frozen=True)
    ok: bool = True
    synthesis_mode: str = "llm"


LiteratureReviewPipelineEvent = (
    LiteratureReviewStarted
    | LiteratureReviewStage
    | LiteratureReviewStageCompleted
    | LiteratureReviewCompleted
    | LiteratureReviewError
    | LiteratureReviewLLMStarted
    | LiteratureReviewLLMCompleted
)


class LiteratureReviewJSONLEmitter:
    """Writes one JSON object per line to a text stream."""

    def __init__(self, file_obj: Any = sys.stdout) -> None:
        self._f = file_obj

    def emit(self, event: LiteratureReviewPipelineEvent) -> None:
        line = event.model_dump_json()
        self._f.write(line + "\n")
        self._f.flush()

    async def aemit(self, event: LiteratureReviewPipelineEvent) -> None:
        self.emit(event)


def parse_jsonl_line(line: str) -> dict[str, Any]:
    return json.loads(line)


__all__ = [
    "LiteratureReviewCompleted",
    "LiteratureReviewError",
    "LiteratureReviewJSONLEmitter",
    "LiteratureReviewLLMCompleted",
    "LiteratureReviewLLMStarted",
    "LiteratureReviewPipelineEvent",
    "LiteratureReviewStage",
    "LiteratureReviewStageCompleted",
    "LiteratureReviewStageName",
    "LiteratureReviewStarted",
    "parse_jsonl_line",
]
