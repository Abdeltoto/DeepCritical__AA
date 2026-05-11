"""
CLI: LLM hypothesis generation pipeline with JSONL events on stdout.

Usage:
  uv run python -m DeepResearch.scripts.run_llm_hypothesis_pipeline --question "..."
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from DeepResearch.src.agents.hypothesis_generation_agent import (
    HypothesisCandidate,
    HypothesisPipelineError,
    run_hypothesis_generation_pipeline,
)
from DeepResearch.src.agents.hypothesis_pipeline_events import (
    EvidenceFetched,
    EvidenceFetchStarted,
    JSONLEmitter,
    PipelineCompleted,
    PipelineError,
    PipelineStarted,
    ProposerCompleted,
    ProposerStarted,
)
from DeepResearch.src.datatypes.hypothesis_generation import (
    HypothesisType,
    build_hypothesis_dataset,
)
from DeepResearch.src.utils.dataset_uploader import (
    DatasetUploadConfig,
    maybe_upload_payload,
    parse_extra_metadata,
)
from DeepResearch.src.utils.model_registry import resolve_model_name


def hypothesis_parameters_from_cli(ns: argparse.Namespace) -> dict[str, Any]:
    """Public helper for merged CLIs (hypothesis → literature chain)."""

    return _build_parameters(ns)


def _build_parameters(ns: argparse.Namespace) -> dict[str, Any]:
    dm = resolve_model_name(None, "default")
    params: dict[str, Any] = {
        "hypothesis_types": ["causal", "correlational", "mechanistic"],
        "enable_evidence_synthesis": ns.enable_evidence_synthesis,
        "enable_critic_pass": ns.enable_critic_pass,
        "max_hypotheses": ns.max_hypotheses,
        "max_evidence_chars": ns.max_evidence_chars,
        "model_name": ns.model or dm,
        "temperature": ns.temperature,
        "num_results": ns.num_results,
        "chunk_size": ns.chunk_size,
        "chunk_overlap": ns.chunk_overlap,
        "search_type": ns.search_type,
        "extra_document_text": "",
        "propose_retries": ns.propose_retries,
        "fail_on_empty_output": ns.fail_on_empty_output,
        "fail_on_critic_drop_all": ns.fail_on_critic_drop_all,
        "run_quality_judge": False,
    }
    if ns.model_ref:
        params["model_ref"] = ns.model_ref
    if ns.base_url:
        params["base_url"] = ns.base_url
    if ns.api_key is not None:
        params["api_key"] = ns.api_key
    if ns.extra_document_text_file:
        path = Path(ns.extra_document_text_file)
        params["extra_document_text"] = path.read_text(encoding="utf-8")
    return params


async def _stub_pipeline(
    emitter: JSONLEmitter,
    ns: argparse.Namespace,
) -> int:
    """Deterministic JSONL stream for subprocess tests (no network / LLM)."""
    await emitter.aemit(
        PipelineStarted(question_preview=ns.question[:200], max_hypotheses=3)
    )
    await emitter.aemit(EvidenceFetchStarted())
    await emitter.aemit(
        EvidenceFetched(evidence_degraded=False, chunk_count=0, characters=0)
    )
    await emitter.aemit(ProposerStarted())
    c = HypothesisCandidate(
        statement="Stub hypothesis for testing.",
        hypothesis_type=HypothesisType.CAUSAL,
        confidence=0.75,
    )
    await emitter.aemit(
        ProposerCompleted(n_candidates=1, statements=[c.statement[:500]])
    )
    ds = build_hypothesis_dataset(
        ns.dataset_name or "stub",
        ns.dataset_description or "stub",
        [c],
        [ns.workflow_name or "stub_wf"],
        extra_metadata={"stub": True},
    )
    meta = {"stub": True, "hypothesis_count": 1}
    await emitter.aemit(
        PipelineCompleted(dataset=ds.model_dump(mode="json"), metadata=meta)
    )
    if ns.print_dataset:
        print(json.dumps(ds.model_dump(mode="json"), indent=2), file=sys.stderr)
    return 0


async def _run_pipeline_main(ns: argparse.Namespace, emitter: JSONLEmitter) -> int:
    parameters = _build_parameters(ns)
    input_data: dict[str, Any] = {
        "question": ns.question,
        "workflow_name": ns.workflow_name,
        "dataset_name": ns.dataset_name,
        "dataset_description": ns.dataset_description,
    }
    try:
        dataset, meta = await run_hypothesis_generation_pipeline(
            input_data,
            parameters,
            default_model=ns.model,
            emitter=emitter,
        )
        if ns.upload_repo_root:
            up_cfg = DatasetUploadConfig(
                enabled=True,
                repo_root=Path(ns.upload_repo_root).expanduser().resolve(),
                owner=ns.upload_owner,
                description=str(ns.upload_repo_description),
                dataset_id=ns.upload_dataset_id,
                extra_metadata=parse_extra_metadata(ns.upload_metadata),
                source_label="deepresearch-llm-hypothesis",
            )
            maybe_upload_payload(dataset.model_dump(mode="json"), up_cfg)
        if ns.print_dataset and not ns.quiet:
            print(
                json.dumps(dataset.model_dump(mode="json"), indent=2),
                file=sys.stderr,
            )
            print(json.dumps(meta, indent=2, default=str), file=sys.stderr)
        return 0
    except (HypothesisPipelineError, Exception):
        return 2


@contextmanager
def _output_stream(ns: argparse.Namespace):
    if ns.output_jsonl in (None, "-", ""):
        yield sys.stdout
    else:
        with Path(ns.output_jsonl).open("w", encoding="utf-8") as fh:
            yield fh


async def amain(ns: argparse.Namespace) -> int:
    with _output_stream(ns) as out_file:
        emitter = JSONLEmitter(out_file)
        if os.environ.get("DEEPRESEARCH_HYPOTHESIS_PIPELINE_STUB"):
            return await _stub_pipeline(emitter, ns)
        return await _run_pipeline_main(ns, emitter)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run evidence-grounded LLM hypothesis generation (JSONL events).",
    )
    p.add_argument("--question", required=True, help="Research question")
    p.add_argument("--workflow-name", default="cli_hypothesis_generation")
    p.add_argument("--dataset-name", default="CLI hypotheses")
    p.add_argument(
        "--dataset-description",
        default="",
        help="Dataset description (default: derived from question)",
    )
    p.add_argument("--model", default=None, help="Model id or registry default")
    p.add_argument(
        "--model-ref",
        default=None,
        help="Registry role for resolve_pydantic_ai_model (overrides plain model)",
    )
    p.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    p.add_argument("--api-key", default=None, help="API key for OpenAI-compatible URL")
    p.add_argument("--temperature", type=float, default=0.4)
    p.add_argument("--max-hypotheses", type=int, default=6)
    p.add_argument("--num-results", type=int, default=4)
    p.add_argument("--max-evidence-chars", type=int, default=12000)
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--chunk-overlap", type=int, default=0)
    p.add_argument("--search-type", default="search")
    p.add_argument("--enable-critic-pass", action="store_true")
    p.add_argument(
        "--enable-evidence-synthesis",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument("--propose-retries", type=int, default=0)
    p.add_argument("--fail-on-empty-output", action="store_true")
    p.add_argument("--fail-on-critic-drop-all", action="store_true")
    p.add_argument(
        "--extra-document-text-file",
        default=None,
        help="Optional UTF-8 text file merged into evidence context",
    )
    p.add_argument(
        "--output-jsonl",
        default="-",
        help="Write JSONL events here (default: stdout)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stderr meta dump from --print-dataset",
    )
    p.add_argument(
        "--print-dataset",
        action="store_true",
        help="Print dataset/meta JSON to stderr at end",
    )
    p.add_argument(
        "--upload-repo-root",
        default=None,
        help="If set, auto-upload produced dataset into this dataset repository directory.",
    )
    p.add_argument(
        "--upload-owner", default=None, help="Optional dataset repo owner label."
    )
    p.add_argument(
        "--upload-repo-description",
        default="DeepCritical dataset repository",
        help="Repo description stored in repo.json on first create.",
    )
    p.add_argument(
        "--upload-dataset-id",
        default=None,
        help="Override dataset id directory name in the repository.",
    )
    p.add_argument(
        "--upload-metadata",
        default=None,
        help="Optional JSON object merged into metadata.json under 'extra'.",
    )
    return p


def main() -> int:
    ns = build_arg_parser().parse_args()
    if not ns.dataset_description:
        ns.dataset_description = (
            f"Evidence-grounded hypotheses for: {ns.question[:200]}"
        )
    try:
        return asyncio.run(amain(ns))
    except KeyboardInterrupt:
        JSONLEmitter(sys.stdout).emit(
            PipelineError(stage="cancelled", message="Interrupted")
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
