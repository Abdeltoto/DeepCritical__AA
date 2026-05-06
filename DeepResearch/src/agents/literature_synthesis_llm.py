"""
Optional LLM synthesis for the critical literature review workflow (Pydantic AI).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from DeepResearch.src.datatypes.literature_review import (
    CriticalAppraisal,
    EvidenceTableRow,
    LiteratureReviewRequest,
    LiteratureSearchPlan,
    LiteratureSource,
    LiteratureSynthesis,
    LiteratureSynthesisLLMOutput,
)
from DeepResearch.src.datatypes.llm_models import LLMModelConfig, LLMProvider
from DeepResearch.src.models.openai_compatible_model import OpenAICompatibleModel
from DeepResearch.src.prompts.literature_review_llm import (
    SYSTEM_LITERATURE_SYNTHESIS_LLM,
    build_literature_synthesis_user_prompt,
)
from DeepResearch.src.utils.model_registry import (
    resolve_model_name,
    resolve_pydantic_ai_model,
)


class LiteratureSynthesisLLMError(RuntimeError):
    """Failure from the literature LLM synthesis step."""


@dataclass
class LiteratureLLMSynthesisParams:
    """Runtime parameters for `synthesize_literature_with_llm`."""

    model_name: str
    model_ref: str | None = None
    temperature: float = 0.35
    base_url: str | None = None
    api_key: str | None = None
    max_evidence_chars: int = 12000


def resolve_model_for_literature_synthesis(
    params: LiteratureLLMSynthesisParams,
) -> str | object:
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

    name = params.model_name or resolve_model_name(None, "default")
    return name


def _truncate_text(
    text: str | None, budget: int, *, note: str, notes: list[str]
) -> str:
    if text is None:
        return ""
    s = text.strip()
    if len(s) <= budget:
        return s
    notes.append(note)
    return s[: max(0, budget - 3)] + "..."


def _pack_context(
    *,
    question: str,
    request: dict[str, Any],
    search_plan: dict[str, Any],
    included_sources: list[dict[str, Any]],
    excluded_sources: list[dict[str, Any]],
    screening_decisions: list[dict[str, Any]],
    evidence_table: list[dict[str, Any]],
    appraisals: list[dict[str, Any]],
    duplicate_diagnostics: list[dict[str, Any]],
    max_evidence_chars: int,
) -> tuple[dict[str, Any], list[str]]:
    """Trim lists and text so serialized JSON stays within budget; record truncation notes."""

    notes: list[str] = []
    per_abstract_cap = max(
        200, min(4000, max_evidence_chars // max(8, len(included_sources) or 1))
    )

    def trim_source(src: dict[str, Any]) -> dict[str, Any]:
        out = dict(src)
        abstract = _truncate_text(
            str(out.get("abstract") or ""),
            per_abstract_cap,
            note=f"abstract_truncated:{out.get('source_id', '?')}",
            notes=notes,
        )
        extracted = _truncate_text(
            str(out.get("extracted_text") or ""),
            min(per_abstract_cap, 1500),
            note=f"extracted_text_truncated:{out.get('source_id', '?')}",
            notes=notes,
        )
        out["abstract"] = abstract
        out["extracted_text"] = extracted if extracted else None
        return out

    included_trimmed = [trim_source(dict(s)) for s in included_sources[:50]]
    if len(included_sources) > 50:
        notes.append(f"included_sources_capped:{len(included_sources)}->50")

    excluded_trimmed = [trim_source(dict(s)) for s in excluded_sources[:30]]
    if len(excluded_sources) > 30:
        notes.append(f"excluded_sources_capped:{len(excluded_sources)}->30")

    decisions_trimmed = screening_decisions[:200]
    if len(screening_decisions) > 200:
        notes.append(f"screening_decisions_capped:{len(screening_decisions)}->200")

    plan_summary = {
        "queries": (search_plan.get("queries") or [])[:10],
        "focus_terms": (search_plan.get("focus_terms") or [])[:20],
        "source_mode": search_plan.get("source_mode"),
        "max_sources": search_plan.get("max_sources"),
    }

    payload: dict[str, Any] = {
        "question": question.strip(),
        "request_summary": {
            "mode": request.get("mode"),
            "source_mode": request.get("source_mode"),
            "max_sources": request.get("max_sources"),
            "min_relevance_score": request.get("min_relevance_score"),
        },
        "search_plan_summary": plan_summary,
        "counts": {
            "included": len(included_sources),
            "excluded": len(excluded_sources),
            "evidence_rows": len(evidence_table),
            "appraisals": len(appraisals),
        },
        "included_sources": included_trimmed,
        "excluded_sources": excluded_trimmed,
        "screening_decisions": decisions_trimmed,
        "evidence_table": evidence_table[:100],
        "appraisals": appraisals[:100],
        "duplicate_diagnostics": duplicate_diagnostics[:20],
    }
    if len(evidence_table) > 100:
        notes.append(f"evidence_table_capped:{len(evidence_table)}->100")
    if len(appraisals) > 100:
        notes.append(f"appraisals_capped:{len(appraisals)}->100")

    serialized = json.dumps(payload, default=str)
    while len(serialized) > max_evidence_chars and per_abstract_cap > 120:
        per_abstract_cap = max(120, per_abstract_cap // 2)
        notes.append(f"payload_oversized_retry_abstract_cap:{per_abstract_cap}")
        included_trimmed = [trim_source(dict(s)) for s in included_sources[:50]]
        excluded_trimmed = [trim_source(dict(s)) for s in excluded_sources[:30]]
        payload["included_sources"] = included_trimmed
        payload["excluded_sources"] = excluded_trimmed
        serialized = json.dumps(payload, default=str)

    if len(serialized) > max_evidence_chars:
        notes.append("payload_still_over_budget_after_trimming")

    return payload, notes


async def synthesize_literature_with_llm(
    *,
    question: str,
    request: LiteratureReviewRequest | dict[str, Any],
    search_plan: LiteratureSearchPlan | dict[str, Any],
    included_sources: list[LiteratureSource] | list[dict[str, Any]],
    excluded_sources: list[LiteratureSource] | list[dict[str, Any]],
    screening_decisions: list[dict[str, Any]],
    evidence_table: list[EvidenceTableRow] | list[dict[str, Any]],
    appraisals: list[CriticalAppraisal] | list[dict[str, Any]],
    duplicate_diagnostics: list[dict[str, Any]],
    params: LiteratureLLMSynthesisParams,
) -> tuple[LiteratureSynthesis, str, dict[str, Any]]:
    """
    Run one LLM synthesis pass. Returns synthesis, markdown, and metadata (truncation notes).

    Raises LiteratureSynthesisLLMError on invalid output or agent failure.
    """

    req_dict = (
        request.model_dump(mode="json")
        if isinstance(request, LiteratureReviewRequest)
        else dict(request)
    )
    plan_dict = (
        search_plan.model_dump(mode="json")
        if isinstance(search_plan, LiteratureSearchPlan)
        else dict(search_plan)
    )

    inc = [
        s.model_dump(mode="json") if isinstance(s, LiteratureSource) else dict(s)
        for s in included_sources
    ]
    exc = [
        s.model_dump(mode="json") if isinstance(s, LiteratureSource) else dict(s)
        for s in excluded_sources
    ]
    ev_rows = [
        r.model_dump(mode="json") if isinstance(r, EvidenceTableRow) else dict(r)
        for r in evidence_table
    ]
    appr = [
        a.model_dump(mode="json") if isinstance(a, CriticalAppraisal) else dict(a)
        for a in appraisals
    ]

    packed, truncation_notes = _pack_context(
        question=question,
        request=req_dict,
        search_plan=plan_dict,
        included_sources=inc,
        excluded_sources=exc,
        screening_decisions=screening_decisions,
        evidence_table=ev_rows,
        appraisals=appr,
        duplicate_diagnostics=duplicate_diagnostics,
        max_evidence_chars=params.max_evidence_chars,
    )

    user_prompt = build_literature_synthesis_user_prompt(packed)
    model = resolve_model_for_literature_synthesis(params)
    agent = Agent(
        model=model,
        output_type=LiteratureSynthesisLLMOutput,
        system_prompt=SYSTEM_LITERATURE_SYNTHESIS_LLM,
    )

    try:
        run = await agent.run(
            user_prompt,
            model_settings=ModelSettings(temperature=params.temperature),
        )
    except Exception as exc:
        raise LiteratureSynthesisLLMError(str(exc)) from exc

    out = run.output
    if not isinstance(out, LiteratureSynthesisLLMOutput):
        msg = f"Unexpected synthesis output type: {type(out)!r}"
        raise LiteratureSynthesisLLMError(msg)

    synthesis = out.synthesis
    if not isinstance(synthesis, LiteratureSynthesis):
        synthesis = LiteratureSynthesis.model_validate(synthesis)

    md = (out.markdown_report or "").strip()
    if out.disclaimer:
        md = md + "\n\n" + out.disclaimer.strip()
    if not md:
        raise LiteratureSynthesisLLMError("Empty markdown_report from LLM")

    meta: dict[str, Any] = {
        "truncation_notes": truncation_notes,
        "packed_chars": len(json.dumps(packed, default=str)),
    }
    return synthesis, md, meta


__all__ = [
    "LiteratureLLMSynthesisParams",
    "LiteratureSynthesisLLMError",
    "resolve_model_for_literature_synthesis",
    "synthesize_literature_with_llm",
]
