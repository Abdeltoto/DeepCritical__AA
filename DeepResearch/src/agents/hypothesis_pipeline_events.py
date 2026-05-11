"""
JSONL event stream for the LLM hypothesis generation pipeline.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class PipelineStarted(BaseModel):
    event_type: str = Field("pipeline_started", frozen=True)
    question_preview: str = ""
    max_hypotheses: int = 10


class EvidenceFetchStarted(BaseModel):
    event_type: str = Field("evidence_fetch_started", frozen=True)


class EvidenceFetched(BaseModel):
    event_type: str = Field("evidence_fetched", frozen=True)
    evidence_degraded: bool = False
    chunk_count: int = 0
    characters: int = 0


class ProposerStarted(BaseModel):
    event_type: str = Field("proposer_started", frozen=True)


class ProposerCompleted(BaseModel):
    event_type: str = Field("proposer_completed", frozen=True)
    n_candidates: int = 0
    statements: list[str] = Field(default_factory=list)


class CriticStarted(BaseModel):
    event_type: str = Field("critic_started", frozen=True)


class CriticCompleted(BaseModel):
    event_type: str = Field("critic_completed", frozen=True)
    kept_count: int = 0
    dropped_indices: list[int] = Field(default_factory=list)
    invalid_indices: list[int] = Field(default_factory=list)
    critic_dropped_all: bool = False


class DedupeApplied(BaseModel):
    event_type: str = Field("dedupe_applied", frozen=True)
    hypotheses_truncated: bool = False


class DatasetBuilt(BaseModel):
    event_type: str = Field("dataset_built", frozen=True)
    dataset_name: str = ""
    n_hypotheses: int = 0


class PipelineCompleted(BaseModel):
    event_type: str = Field("pipeline_completed", frozen=True)
    dataset: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineError(BaseModel):
    event_type: str = Field("pipeline_error", frozen=True)
    stage: str = ""
    message: str = ""
    detail: str | None = None


PipelineEvent = (
    PipelineStarted
    | EvidenceFetchStarted
    | EvidenceFetched
    | ProposerStarted
    | ProposerCompleted
    | CriticStarted
    | CriticCompleted
    | DedupeApplied
    | DatasetBuilt
    | PipelineCompleted
    | PipelineError
)


@runtime_checkable
class PipelineEventEmitter(Protocol):
    def emit(self, event: PipelineEvent) -> None: ...

    async def aemit(self, event: PipelineEvent) -> None: ...


class NoopEmitter:
    """Discards all events."""

    def emit(self, event: PipelineEvent) -> None:
        pass

    async def aemit(self, event: PipelineEvent) -> None:
        pass


class JSONLEmitter:
    """Writes one JSON object per line to a text stream."""

    def __init__(self, file_obj: Any = sys.stdout) -> None:
        self._f = file_obj

    def emit(self, event: PipelineEvent) -> None:
        line = event.model_dump_json()
        self._f.write(line + "\n")
        self._f.flush()

    async def aemit(self, event: PipelineEvent) -> None:
        self.emit(event)


@dataclass
class PipelineEventBus:
    """Fan-out emitters."""

    emitters: list[PipelineEventEmitter] = field(default_factory=list)

    def emit(self, event: PipelineEvent) -> None:
        for e in self.emitters:
            e.emit(event)

    async def aemit(self, event: PipelineEvent) -> None:
        for em in self.emitters:
            await em.aemit(event)


def parse_jsonl_line(line: str) -> dict[str, Any]:
    """Parse a single JSON object line (for tests / tooling)."""
    return json.loads(line)


__all__ = [
    "CriticCompleted",
    "CriticStarted",
    "DatasetBuilt",
    "DedupeApplied",
    "EvidenceFetchStarted",
    "EvidenceFetched",
    "JSONLEmitter",
    "NoopEmitter",
    "PipelineCompleted",
    "PipelineError",
    "PipelineEvent",
    "PipelineEventBus",
    "PipelineEventEmitter",
    "PipelineStarted",
    "ProposerCompleted",
    "ProposerStarted",
    "parse_jsonl_line",
]
