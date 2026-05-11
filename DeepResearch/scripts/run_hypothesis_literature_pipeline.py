"""
CLI: hypothesis generation (LLM) then critical literature review per hypothesis.

Usage:
  uv run python -m DeepResearch.scripts.run_hypothesis_literature_pipeline \\
    --question "..." --model gpt-4o-mini \\
    -- --lit-max-lit-reviews 3 --lit-source-mode pubmed

Literature-specific flags follow an optional ``--`` separator (recommended).
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

from DeepResearch.scripts.run_llm_hypothesis_pipeline import (
    build_arg_parser as build_hypothesis_arg_parser,
)
from DeepResearch.scripts.run_llm_hypothesis_pipeline import (
    hypothesis_parameters_from_cli,
)
from DeepResearch.src.agents.hypothesis_generation_agent import HypothesisPipelineError
from DeepResearch.src.agents.hypothesis_literature_chain import (
    run_hypothesis_literature_chain,
)
from DeepResearch.src.agents.hypothesis_literature_pipeline_events import (
    HypothesisLiteratureJSONLEmitter,
)
from DeepResearch.src.utils.dataset_uploader import (
    DatasetUploadConfig,
    maybe_upload_payload,
    parse_extra_metadata,
)

PIPELINE_ERROR = "hypothesis_literature_pipeline_error"


def _build_lit_chain_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Literature phase options (after --).",
        add_help=False,
    )
    p.add_argument(
        "--lit-max-lit-reviews",
        type=int,
        default=5,
        dest="max_lit_reviews",
        help="Max hypotheses to run literature review for (default: 5)",
    )
    p.add_argument(
        "--lit-review-mode",
        default="review",
        dest="review_mode",
        help="Review mode label passed to literature workflow",
    )
    p.add_argument(
        "--lit-source-mode",
        default="pubmed",
        dest="source_mode",
        help="fixture | pubmed | openalex | web | mixed (default: pubmed)",
    )
    p.add_argument("--lit-fixture-path", default=None, dest="fixture_path")
    p.add_argument(
        "--lit-live-retrieval",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="live_retrieval",
        help="Enable live retrieval (default: true)",
    )
    p.add_argument("--lit-max-sources", type=int, default=12, dest="max_sources")
    p.add_argument("--lit-max-queries", type=int, default=3, dest="max_queries")
    p.add_argument(
        "--lit-min-relevance", type=float, default=0.35, dest="min_relevance"
    )
    p.add_argument("--lit-year-min", type=int, default=None, dest="year_min")
    p.add_argument(
        "--lit-include-preprints",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="include_preprints",
    )
    p.add_argument(
        "--lit-strict-screening",
        action=argparse.BooleanOptionalAction,
        default=False,
        dest="strict_screening",
    )
    p.add_argument(
        "--lit-exclude-irrelevant-phrases",
        action=argparse.BooleanOptionalAction,
        default=False,
        dest="exclude_irrelevant_phrases",
    )
    p.add_argument(
        "--lit-llm-synthesis",
        action=argparse.BooleanOptionalAction,
        default=False,
        dest="llm_synthesis",
    )
    p.add_argument("--lit-llm-model", default=None, dest="llm_model")
    p.add_argument("--lit-llm-model-ref", default=None, dest="llm_model_ref")
    p.add_argument("--lit-llm-base-url", default=None, dest="llm_base_url")
    p.add_argument("--lit-llm-api-key", default=None, dest="llm_api_key")
    p.add_argument(
        "--lit-llm-temperature",
        type=float,
        default=0.35,
        dest="llm_temperature",
    )
    p.add_argument(
        "--lit-max-evidence-chars",
        type=int,
        default=12000,
        dest="max_evidence_chars",
    )
    p.add_argument(
        "--lit-llm-fallback-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        dest="llm_fallback_on_error",
    )
    return p


def _literature_cfg_from_lit_ns(lit_ns: argparse.Namespace) -> dict[str, Any]:
    llm_syn: dict[str, Any] = {
        "enabled": bool(lit_ns.llm_synthesis),
        "temperature": lit_ns.llm_temperature,
        "max_evidence_chars": lit_ns.max_evidence_chars,
        "fallback_on_error": lit_ns.llm_fallback_on_error,
    }
    if lit_ns.llm_model is not None:
        llm_syn["model"] = lit_ns.llm_model
    if lit_ns.llm_model_ref is not None:
        llm_syn["model_ref"] = lit_ns.llm_model_ref
    if lit_ns.llm_base_url is not None:
        llm_syn["base_url"] = lit_ns.llm_base_url
    elif lit_ns.llm_synthesis:
        env_b = os.environ.get("LLM_BASE_URL")
        if env_b:
            llm_syn["base_url"] = env_b.strip()
    if lit_ns.llm_api_key is not None:
        llm_syn["api_key"] = lit_ns.llm_api_key
    elif lit_ns.llm_synthesis:
        env_k = os.environ.get("LLM_API_KEY")
        if env_k:
            llm_syn["api_key"] = env_k

    return {
        "literature_review": {
            "mode": lit_ns.review_mode,
            "source_mode": lit_ns.source_mode,
            "max_sources": lit_ns.max_sources,
            "include_preprints": lit_ns.include_preprints,
            "live_retrieval_enabled": lit_ns.live_retrieval,
            "min_relevance_score": lit_ns.min_relevance,
            "fixture_path": lit_ns.fixture_path,
            "strict_screening": lit_ns.strict_screening,
            "exclude_irrelevant_phrases": lit_ns.exclude_irrelevant_phrases,
            "search": {
                "max_queries": lit_ns.max_queries,
                "year_min": lit_ns.year_min,
            },
            "llm_synthesis": llm_syn,
        }
    }


def _split_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" in argv:
        idx = argv.index("--")
        return argv[:idx], argv[idx + 1 :]
    return argv, []


@contextmanager
def _output_stream(path: str | None):
    if path in (None, "-", ""):
        yield sys.stdout
    else:
        with Path(path).open("w", encoding="utf-8") as fh:
            yield fh


async def _amain(ns: argparse.Namespace, lit_ns: argparse.Namespace) -> int:
    lit_cfg = _literature_cfg_from_lit_ns(lit_ns)
    hyp_params = hypothesis_parameters_from_cli(ns)
    input_data = {
        "question": ns.question,
        "workflow_name": ns.workflow_name,
        "dataset_name": ns.dataset_name,
        "dataset_description": ns.dataset_description
        or f"Evidence-grounded hypotheses for: {ns.question[:200]}",
    }

    with _output_stream(ns.output_jsonl) as out_file:
        emitter = HypothesisLiteratureJSONLEmitter(out_file)
        try:
            hds, lds, meta = await run_hypothesis_literature_chain(
                ns.question,
                hyp_params,
                lit_cfg,
                max_lit_reviews=lit_ns.max_lit_reviews,
                hypothesis_input=input_data,
                emitter=emitter,
            )
        except HypothesisPipelineError:
            err_line = (
                '{"event_type":"'
                + PIPELINE_ERROR
                + '","stage":"hypothesis","message":"Hypothesis pipeline failed"}\n'
            )
            out_file.write(err_line)
            out_file.flush()
            return 2
        except Exception as exc:
            err_line = (
                '{"event_type":"'
                + PIPELINE_ERROR
                + '","stage":"chain","message":'
                + json.dumps(str(exc))
                + "}\n"
            )
            out_file.write(err_line)
            out_file.flush()
            return 2

    if ns.upload_repo_root:
        up_cfg = DatasetUploadConfig(
            enabled=True,
            repo_root=Path(ns.upload_repo_root).expanduser().resolve(),
            owner=ns.upload_owner,
            description=str(ns.upload_repo_description),
            dataset_id=ns.upload_dataset_id,
            extra_metadata=parse_extra_metadata(ns.upload_metadata),
            source_label="deepresearch-hypothesis-literature",
        )
        maybe_upload_payload(
            {
                "hypothesis_dataset": hds.model_dump(mode="json"),
                "literature_review_dataset": lds.model_dump(mode="json"),
                "metadata": meta,
                "status": str(meta.get("chain_status") or ""),
            },
            up_cfg,
        )

    chain_status = str(meta.get("chain_status", ""))
    return 0 if chain_status == "success" else 1


def main() -> int:
    argv = sys.argv[1:]
    hyp_argv, lit_argv = _split_argv(argv)
    hyp_ns = build_hypothesis_arg_parser().parse_args(hyp_argv)
    lit_ns = _build_lit_chain_parser().parse_args(lit_argv)
    try:
        return asyncio.run(_amain(hyp_ns, lit_ns))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
