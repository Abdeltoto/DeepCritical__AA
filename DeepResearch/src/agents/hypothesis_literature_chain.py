"""
Run hypothesis generation, then one critical literature review per retained hypothesis.
"""

from __future__ import annotations

import time
from typing import Any

from DeepResearch.src.agents.hypothesis_generation_agent import (
    HypothesisPipelineError,
    run_hypothesis_generation_pipeline,
)
from DeepResearch.src.agents.hypothesis_literature_pipeline_events import (
    HypothesisLiteratureChainCompleted,
    HypothesisLiteratureChainStarted,
    HypothesisLiteratureHypothesisPhaseCompleted,
    HypothesisLiteratureReviewCompleted,
    HypothesisLiteratureReviewStarted,
)
from DeepResearch.src.datatypes.literature_review import (
    LiteratureReviewDataset,
    LiteratureReviewDatasetEntry,
)
from DeepResearch.src.datatypes.workflow_orchestration import HypothesisDataset
from DeepResearch.src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)


class _NoopChainEmitter:
    async def aemit(self, event: Any) -> None:
        return


def build_literature_review_question(
    parent_question: str, hypothesis_statement: str
) -> str:
    """Turn a hypothesis statement into a scoped literature review question."""

    pq = " ".join(parent_question.split()).strip()
    hs = " ".join(hypothesis_statement.split()).strip()
    return (
        "Critical literature review: survey empirical evidence, methods, controversies, "
        "and gaps relevant to the following testable hypothesis.\n\n"
        f"Hypothesis: {hs}\n\n"
        f"Original research question: {pq}"
    )


async def run_hypothesis_literature_chain(
    parent_question: str,
    hypothesis_parameters: dict[str, Any],
    literature_review_cfg: dict[str, Any],
    *,
    max_lit_reviews: int = 5,
    hypothesis_input: dict[str, Any] | None = None,
    emitter: Any = None,
) -> tuple[HypothesisDataset, LiteratureReviewDataset, dict[str, Any]]:
    """
    Execute hypothesis LLM pipeline, then run literature review per hypothesis (capped).

    Returns hypothesis dataset, combined literature review dataset, and metadata.
    """

    emit: Any = emitter if emitter is not None else _NoopChainEmitter()

    input_data = dict(hypothesis_input or {})
    input_data.setdefault("question", parent_question)

    meta: dict[str, Any] = {
        "parent_question": parent_question[:500],
        "max_lit_reviews": max_lit_reviews,
    }
    t0 = time.perf_counter()

    await emit.aemit(
        HypothesisLiteratureChainStarted(
            parent_question_preview=parent_question[:240],
            max_lit_reviews=max_lit_reviews,
        )
    )

    try:
        hypothesis_ds, hypo_meta = await run_hypothesis_generation_pipeline(
            input_data,
            hypothesis_parameters,
            default_model=hypothesis_parameters.get("model_name"),
            emitter=None,
        )
    except Exception as exc:
        meta["hypothesis_phase_error"] = str(exc)
        meta["elapsed_seconds"] = time.perf_counter() - t0
        raise HypothesisPipelineError(str(exc)) from exc

    meta.update(hypo_meta)
    hypotheses_list = list(hypothesis_ds.hypotheses or [])
    await emit.aemit(
        HypothesisLiteratureHypothesisPhaseCompleted(
            hypothesis_count=len(hypotheses_list),
            dataset_name=hypothesis_ds.name,
        )
    )

    entries: list[LiteratureReviewDatasetEntry] = []
    cap = max(0, min(max_lit_reviews, len(hypotheses_list)))

    for idx in range(cap):
        row = hypotheses_list[idx]
        statement = ""
        if isinstance(row, dict):
            statement = str(row.get("statement") or "").strip()
        if not statement:
            entries.append(
                LiteratureReviewDatasetEntry(
                    hypothesis_index=idx,
                    hypothesis_statement="",
                    review_question="",
                    literature_result={"error": "missing hypothesis statement"},
                    status="skipped",
                )
            )
            continue

        review_q = build_literature_review_question(parent_question, statement)
        await emit.aemit(
            HypothesisLiteratureReviewStarted(
                hypothesis_index=idx,
                review_question_preview=review_q[:240],
            )
        )
        try:
            lit_result = await run_literature_review_workflow(
                review_q,
                literature_review_cfg,
                mode="review",
                emitter=None,
            )
            st = str(lit_result.get("status", ""))
            entries.append(
                LiteratureReviewDatasetEntry(
                    hypothesis_index=idx,
                    hypothesis_statement=statement,
                    review_question=review_q,
                    literature_result=dict(lit_result),
                    status="success" if st == "success" else "failed",
                )
            )
            await emit.aemit(
                HypothesisLiteratureReviewCompleted(hypothesis_index=idx, status=st)
            )
        except Exception as exc:
            entries.append(
                LiteratureReviewDatasetEntry(
                    hypothesis_index=idx,
                    hypothesis_statement=statement,
                    review_question=review_q,
                    literature_result={"error": str(exc)},
                    status="failed",
                )
            )
            await emit.aemit(
                HypothesisLiteratureReviewCompleted(
                    hypothesis_index=idx,
                    status="failed",
                )
            )

    lit_dataset = LiteratureReviewDataset(
        parent_question=parent_question,
        hypothesis_dataset_id=hypothesis_ds.dataset_id,
        hypothesis_dataset_name=hypothesis_ds.name,
        entries=entries,
        metadata={
            "hypothesis_count": len(hypotheses_list),
            "literature_runs_attempted": cap,
            "elapsed_seconds": time.perf_counter() - t0,
        },
    )

    meta["literature_entries"] = len(entries)
    elapsed = time.perf_counter() - t0
    meta["elapsed_seconds"] = elapsed

    chain_ok = bool(hypotheses_list) and all(e.status == "success" for e in entries)
    if not hypotheses_list:
        meta["chain_status"] = "empty_hypotheses"
    elif chain_ok:
        meta["chain_status"] = "success"
    else:
        meta["chain_status"] = "partial"

    await emit.aemit(
        HypothesisLiteratureChainCompleted(
            status="success" if chain_ok else meta["chain_status"],
            literature_review_dataset=lit_dataset.model_dump(mode="json"),
            hypothesis_dataset=hypothesis_ds.model_dump(mode="json"),
            metadata=meta,
        )
    )

    return hypothesis_ds, lit_dataset, meta


__all__ = [
    "build_literature_review_question",
    "run_hypothesis_literature_chain",
]
