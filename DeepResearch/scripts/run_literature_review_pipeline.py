"""
CLI: critical literature review workflow with JSONL events on stdout.

Usage:
  uv run python -m DeepResearch.scripts.run_literature_review_pipeline --question "..."
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from DeepResearch.src.agents.literature_review_pipeline_events import (
    LiteratureReviewJSONLEmitter,
)
from DeepResearch.src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)
from DeepResearch.src.utils.dataset_uploader import (
    DatasetUploadConfig,
    maybe_upload_payload,
    parse_extra_metadata,
)


def _build_cfg(ns: argparse.Namespace) -> dict[str, Any]:
    llm_syn: dict[str, Any] = {
        "enabled": bool(ns.llm_synthesis),
        "temperature": ns.llm_temperature,
        "max_evidence_chars": ns.max_evidence_chars,
        "fallback_on_error": ns.llm_fallback_on_error,
    }
    if ns.llm_model is not None:
        llm_syn["model"] = ns.llm_model
    if ns.llm_model_ref is not None:
        llm_syn["model_ref"] = ns.llm_model_ref
    if ns.llm_base_url is not None:
        llm_syn["base_url"] = ns.llm_base_url
    elif ns.llm_synthesis:
        env_b = os.environ.get("LLM_BASE_URL")
        if env_b:
            llm_syn["base_url"] = env_b.strip()
    if ns.llm_api_key is not None:
        llm_syn["api_key"] = ns.llm_api_key
    elif ns.llm_synthesis:
        env_k = os.environ.get("LLM_API_KEY")
        if env_k:
            llm_syn["api_key"] = env_k

    return {
        "literature_review": {
            "mode": ns.review_mode,
            "source_mode": ns.source_mode,
            "max_sources": ns.max_sources,
            "include_preprints": ns.include_preprints,
            "live_retrieval_enabled": ns.live_retrieval,
            "min_relevance_score": ns.min_relevance,
            "fixture_path": ns.fixture_path,
            "strict_screening": ns.strict_screening,
            "exclude_irrelevant_phrases": ns.exclude_irrelevant_phrases,
            "search": {
                "max_queries": ns.max_queries,
                "year_min": ns.year_min,
            },
            "llm_synthesis": llm_syn,
        }
    }


@contextmanager
def _output_stream(path: str | None):
    if path in (None, "-", ""):
        yield sys.stdout
    else:
        with Path(path).open("w", encoding="utf-8") as fh:
            yield fh


async def _amain(ns: argparse.Namespace) -> int:
    cfg = _build_cfg(ns)
    with _output_stream(ns.output_jsonl) as out_file:
        emitter = LiteratureReviewJSONLEmitter(out_file)
        result = await run_literature_review_workflow(
            ns.question,
            cfg,
            mode=ns.review_mode,
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
            source_label="deepresearch-literature-pipeline",
        )
        maybe_upload_payload(dict(result), up_cfg)
    status = str(result.get("status", ""))
    if status == "success":
        return 0
    return 1


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run critical literature review pipeline (JSONL events on stdout).",
    )
    p.add_argument("--question", required=True, help="Review question")
    p.add_argument(
        "--review-mode",
        default="review",
        dest="review_mode",
        help="Review mode label (default: review)",
    )
    p.add_argument(
        "--source-mode",
        default="pubmed",
        help="fixture | pubmed | openalex | web | mixed (default: pubmed)",
    )
    p.add_argument(
        "--fixture-path",
        default=None,
        help="Optional JSON fixture file (list or {sources: [...]})",
    )
    p.add_argument(
        "--live-retrieval",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable live network retrieval (default: true; use --no-live-retrieval for fixtures)",
    )
    p.add_argument("--max-sources", type=int, default=12)
    p.add_argument("--max-queries", type=int, default=3)
    p.add_argument("--min-relevance", type=float, default=0.35)
    p.add_argument("--year-min", type=int, default=None)
    p.add_argument(
        "--include-preprints",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument(
        "--strict-screening",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    p.add_argument(
        "--exclude-irrelevant-phrases",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    p.add_argument(
        "--output-jsonl",
        default="-",
        help="JSONL event stream (default: stdout)",
    )
    p.add_argument(
        "--llm-synthesis",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use LLM for synthesis (opt-in; requires API credentials unless mocking)",
    )
    p.add_argument(
        "--model",
        dest="llm_model",
        default=None,
        help="LLM model id when --llm-synthesis (default: registry default)",
    )
    p.add_argument(
        "--model-ref",
        dest="llm_model_ref",
        default=None,
        help="Optional registry model_ref for LLM synthesis",
    )
    p.add_argument(
        "--base-url",
        dest="llm_base_url",
        default=None,
        help="OpenAI-compatible API base URL for LLM synthesis",
    )
    p.add_argument(
        "--api-key",
        dest="llm_api_key",
        default=None,
        help="API key for LLM synthesis (prefer LLM_API_KEY env)",
    )
    p.add_argument(
        "--temperature",
        dest="llm_temperature",
        type=float,
        default=0.35,
        help="Sampling temperature for LLM synthesis",
    )
    p.add_argument(
        "--max-evidence-chars",
        dest="max_evidence_chars",
        type=int,
        default=12000,
        help="Cap serialized evidence JSON size for LLM synthesis",
    )
    p.add_argument(
        "--llm-fallback-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="llm_fallback_on_error",
        help="Fall back to heuristic synthesis when LLM fails",
    )
    p.add_argument(
        "--upload-repo-root",
        default=None,
        help="If set, auto-upload produced result payload into this dataset repository directory.",
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
    try:
        return asyncio.run(_amain(ns))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
