"""
LLM pipeline: evidence-grounded hypothesis proposal, optional critic, dedupe, dataset build.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from DeepResearch.src.agents.hypothesis_pipeline_events import (
    CriticCompleted,
    CriticStarted,
    DatasetBuilt,
    DedupeApplied,
    EvidenceFetched,
    EvidenceFetchStarted,
    NoopEmitter,
    PipelineCompleted,
    PipelineError,
    PipelineEventEmitter,
    PipelineStarted,
    ProposerCompleted,
    ProposerStarted,
)
from DeepResearch.src.datatypes.hypothesis_generation import (
    HypothesisCandidate,
    HypothesisGenerationParams,
    build_hypothesis_dataset,
    dedupe_and_cap,
)
from DeepResearch.src.datatypes.llm_models import LLMModelConfig, LLMProvider
from DeepResearch.src.datatypes.workflow_orchestration import HypothesisDataset
from DeepResearch.src.models.openai_compatible_model import OpenAICompatibleModel
from DeepResearch.src.prompts.hypothesis_generation import (
    SYSTEM_CRITIC,
    SYSTEM_PROPOSER,
    build_critic_user_prompt,
    build_proposer_user_prompt,
)
from DeepResearch.src.utils.hypothesis_evidence import fetch_hypothesis_evidence
from DeepResearch.src.utils.model_registry import (
    resolve_model_name,
    resolve_pydantic_ai_model,
)


class HypothesisPipelineError(RuntimeError):
    """Structured failure from the hypothesis generation pipeline."""


class HypothesisBatchOutput(BaseModel):
    hypotheses: list[HypothesisCandidate] = Field(default_factory=list)


class CritiqueItem(BaseModel):
    index: int = Field(ge=0)
    keep: bool = True
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class CritiqueBatch(BaseModel):
    critiques: list[CritiqueItem] = Field(default_factory=list)


@dataclass
class CritiqueOutcome:
    """Structured result of applying critic output to a hypothesis list."""

    hypotheses: list[HypothesisCandidate]
    dropped_indices: list[int] = field(default_factory=list)
    kept_indices: list[int] = field(default_factory=list)
    invalid_indices: list[int] = field(default_factory=list)
    all_dropped: bool = False


def _extract_question(input_data: dict[str, Any]) -> str:
    for key in ("question", "task_description", "research_brief", "query"):
        v = input_data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _attach_global_evidence(
    candidates: list[HypothesisCandidate],
    global_refs: list[Any],
    max_refs_per: int = 3,
) -> None:
    """Attach top evidence refs to each candidate when it has none."""
    if not global_refs:
        return
    for c in candidates:
        if not c.evidence:
            c.evidence = global_refs[:max_refs_per]


def _apply_critiques(
    hypotheses: list[HypothesisCandidate],
    batch: CritiqueBatch,
) -> CritiqueOutcome:
    if not batch.critiques:
        return CritiqueOutcome(
            hypotheses=list(hypotheses),
            kept_indices=list(range(len(hypotheses))),
            all_dropped=False,
        )

    invalid_indices: list[int] = []
    drops: set[int] = set()
    conf_overrides: dict[int, float] = {}

    for c in batch.critiques:
        if c.index < 0 or c.index >= len(hypotheses):
            invalid_indices.append(c.index)
            continue
        if not c.keep:
            drops.add(c.index)
        else:
            conf_overrides[c.index] = c.confidence

    out: list[HypothesisCandidate] = []
    kept_indices: list[int] = []
    dropped_sorted = sorted(drops)

    for i, h in enumerate(hypotheses):
        if i in drops:
            continue
        conf = conf_overrides.get(i, h.confidence)
        out.append(h.model_copy(update={"confidence": conf}))
        kept_indices.append(i)

    all_dropped = len(hypotheses) > 0 and len(out) == 0

    return CritiqueOutcome(
        hypotheses=out,
        dropped_indices=dropped_sorted,
        kept_indices=kept_indices,
        invalid_indices=invalid_indices,
        all_dropped=all_dropped,
    )


def resolve_model_for_pipeline(params: HypothesisGenerationParams) -> str | object:
    """Resolve model for Pydantic AI Agent (registry role, OpenAI-compatible URL, or string)."""
    if params.model_ref:
        return resolve_pydantic_ai_model(None, params.model_ref)

    if params.base_url and str(params.base_url).strip():
        cfg = LLMModelConfig(
            provider=LLMProvider.CUSTOM,
            model_name=params.model_name,
            base_url=str(params.base_url).strip(),
            api_key=params.api_key,
        )
        return OpenAICompatibleModel.from_config(cfg)

    return params.model_name


async def _run_critic(
    model: str | object,
    question: str,
    evidence_context: str,
    hypotheses: list[HypothesisCandidate],
) -> CritiqueBatch:
    agent = Agent(
        model=model,
        output_type=CritiqueBatch,
        system_prompt=SYSTEM_CRITIC,
    )
    hy_payload = [h.model_dump(mode="json") for h in hypotheses]
    prompt = build_critic_user_prompt(
        question,
        evidence_context,
        json.dumps(hy_payload, indent=2, default=str),
    )
    run = await agent.run(prompt)
    out = run.output
    if not isinstance(out, CritiqueBatch):
        msg = f"Critic returned unexpected output type: {type(out)!r}"
        raise HypothesisPipelineError(msg)
    return out


async def run_hypothesis_generation_pipeline(
    input_data: dict[str, Any],
    parameters: dict[str, Any],
    *,
    default_model: str | None = None,
    emitter: PipelineEventEmitter | None = None,
) -> tuple[HypothesisDataset, dict[str, Any]]:
    """
    Full async pipeline: evidence → propose → optional critic → dedupe → HypothesisDataset.

    Returns:
        dataset, metadata (timing, flags, evidence info).
    """
    emit = emitter or NoopEmitter()

    try:
        dm = default_model or resolve_model_name(None, "default")
        params = HypothesisGenerationParams.from_mapping(parameters, default_model=dm)
        question = _extract_question(input_data)
        if not question:
            msg = (
                "Missing question, task_description, research_brief, or query "
                "in input_data"
            )
            raise ValueError(msg)

        resolved_model = resolve_model_for_pipeline(params)

        await emit.aemit(
            PipelineStarted(
                question_preview=question[:200],
                max_hypotheses=params.max_hypotheses,
            )
        )

        t0 = time.perf_counter()
        meta: dict[str, Any] = {
            "hypotheses_truncated": False,
            "truncated": False,
            "evidence_degraded": False,
            "chunk_count": 0,
        }

        await emit.aemit(EvidenceFetchStarted())
        evidence_text, evidence_refs, ev_meta = await fetch_hypothesis_evidence(
            question, params
        )
        meta.update(ev_meta)
        await emit.aemit(
            EvidenceFetched(
                evidence_degraded=bool(meta.get("evidence_degraded")),
                chunk_count=int(meta.get("chunk_count", 0)),
                characters=len(evidence_text or ""),
            )
        )

        proposer = Agent(
            model=resolved_model,
            output_type=HypothesisBatchOutput,
            system_prompt=SYSTEM_PROPOSER,
        )
        user_prompt = build_proposer_user_prompt(
            question,
            evidence_text,
            params.hypothesis_types,
            params.max_hypotheses,
        )

        await emit.aemit(ProposerStarted())
        candidates: list[HypothesisCandidate] = []
        attempts = max(0, params.propose_retries) + 1
        bout: HypothesisBatchOutput | None = None
        for attempt in range(attempts):
            jitter = (attempt * 0.05) + random.uniform(0, 0.02)
            temp = min(2.0, params.temperature + jitter)
            run = await proposer.run(
                user_prompt,
                model_settings=ModelSettings(temperature=temp),
            )
            raw_out = run.output
            if not isinstance(raw_out, HypothesisBatchOutput):
                msg = f"Proposer returned unexpected output type: {type(raw_out)!r}"
                raise HypothesisPipelineError(msg)
            bout = raw_out
            candidates = list(bout.hypotheses)
            if candidates:
                break

        if not isinstance(bout, HypothesisBatchOutput):
            raise HypothesisPipelineError("Proposer produced no valid batch output")

        await emit.aemit(
            ProposerCompleted(
                n_candidates=len(candidates),
                statements=[c.statement[:500] for c in candidates],
            )
        )

        if not candidates:
            meta["empty_proposer_output"] = True
            meta["status"] = "empty"
            meta["elapsed_seconds"] = time.perf_counter() - t0
            meta["hypothesis_count"] = 0
            if params.fail_on_empty_output:
                raise HypothesisPipelineError(
                    "Proposer returned zero hypotheses after retries",
                )
            wf_name = str(input_data.get("workflow_name", "hypothesis_generation"))
            ds_name = str(input_data.get("dataset_name", "Generated hypotheses"))
            ds_desc = str(
                input_data.get(
                    "dataset_description",
                    f"Evidence-grounded hypotheses for: {question[:200]}",
                )
            )
            dataset = build_hypothesis_dataset(
                ds_name,
                ds_desc,
                [],
                [wf_name],
                extra_metadata=meta,
            )
            await emit.aemit(
                DedupeApplied(hypotheses_truncated=meta["hypotheses_truncated"])
            )
            await emit.aemit(
                DatasetBuilt(dataset_name=ds_name, n_hypotheses=0),
            )
            await emit.aemit(
                PipelineCompleted(
                    dataset=dataset.model_dump(mode="json"),
                    metadata=dict(meta),
                )
            )
            return dataset, meta

        _attach_global_evidence(candidates, evidence_refs)
        before_critic = [c.model_copy() for c in candidates]

        if params.enable_critic_pass and candidates:
            await emit.aemit(CriticStarted())
            critique = await _run_critic(
                resolved_model,
                question,
                evidence_text,
                candidates,
            )
            outcome = _apply_critiques(candidates, critique)
            meta["critic_invalid_indices"] = outcome.invalid_indices
            meta["critic_kept_count"] = len(outcome.hypotheses)
            meta["critic_dropped_all"] = outcome.all_dropped

            if outcome.all_dropped:
                if params.fail_on_critic_drop_all:
                    raise HypothesisPipelineError(
                        "Critic dropped all hypotheses; fail_on_critic_drop_all is True",
                    )
                meta["critic_fallback_original"] = True
                candidates = before_critic
            else:
                candidates = outcome.hypotheses

            await emit.aemit(
                CriticCompleted(
                    kept_count=len(candidates),
                    dropped_indices=outcome.dropped_indices,
                    invalid_indices=outcome.invalid_indices,
                    critic_dropped_all=outcome.all_dropped,
                )
            )

        truncated: bool
        candidates, truncated = dedupe_and_cap(candidates, params.max_hypotheses)
        meta["hypotheses_truncated"] = truncated
        meta["truncated"] = truncated
        meta["elapsed_seconds"] = time.perf_counter() - t0
        meta["hypothesis_count"] = len(candidates)

        await emit.aemit(DedupeApplied(hypotheses_truncated=truncated))

        wf_name = str(input_data.get("workflow_name", "hypothesis_generation"))
        ds_name = str(input_data.get("dataset_name", "Generated hypotheses"))
        ds_desc = str(
            input_data.get(
                "dataset_description",
                f"Evidence-grounded hypotheses for: {question[:200]}",
            )
        )
        dataset = build_hypothesis_dataset(
            ds_name,
            ds_desc,
            candidates,
            [wf_name],
            extra_metadata=meta,
        )

        await emit.aemit(
            DatasetBuilt(dataset_name=ds_name, n_hypotheses=len(candidates)),
        )
        await emit.aemit(
            PipelineCompleted(
                dataset=dataset.model_dump(mode="json"),
                metadata=dict(meta),
            ),
        )

        return dataset, meta

    except Exception as e:
        stage = "pipeline"
        if isinstance(e, KeyboardInterrupt):
            stage = "cancelled"
        await emit.aemit(
            PipelineError(stage=stage, message=str(e), detail=type(e).__name__),
        )
        raise


def summarize_hypotheses_for_answer(candidates: list[HypothesisCandidate]) -> str:
    """Short text summary for evaluator / primary workflow."""
    lines: list[str] = []
    for i, h in enumerate(candidates, start=1):
        lines.append(
            f"{i}. [{h.hypothesis_type.value}] {h.statement} (confidence={h.confidence:.2f})"
        )
    return "\n".join(lines) if lines else "No hypotheses generated."


__all__ = [
    "CritiqueBatch",
    "CritiqueItem",
    "CritiqueOutcome",
    "HypothesisBatchOutput",
    "HypothesisPipelineError",
    "resolve_model_for_pipeline",
    "run_hypothesis_generation_pipeline",
    "summarize_hypotheses_for_answer",
]
