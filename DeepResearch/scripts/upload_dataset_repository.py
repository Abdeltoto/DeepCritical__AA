"""
CLI: upload DeepCritical datasets into a local dataset repository.

This is intentionally stdlib-only and works on Windows/macOS/Linux.

Repository layout (created on first upload):

  <repo_root>/
    repo.json
    datasets/
      <dataset_id_or_timestamp>/
        payload.json
        metadata.json

The "repository" is just a structured directory you can sync or publish later.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UploadOutcome:
    repo_root: Path
    dataset_dir: Path
    dataset_kind: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _guess_dataset_kind(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("hypotheses"), list) and payload.get("dataset_id"):
        return "hypothesis_dataset"
    if isinstance(payload.get("entries"), list) and payload.get("parent_question"):
        return "literature_review_dataset"
    # Chain event payloads often include both
    if payload.get("literature_review_dataset") and payload.get("hypothesis_dataset"):
        return "hypothesis_literature_chain"
    return "unknown"


def _ensure_repo(repo_root: Path, *, owner: str | None, description: str) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "datasets").mkdir(parents=True, exist_ok=True)
    repo_file = repo_root / "repo.json"
    if repo_file.exists():
        return
    repo_meta = {
        "version": 1,
        "created_at_unix": int(time.time()),
        "owner": owner or "",
        "description": description,
    }
    repo_file.write_text(json.dumps(repo_meta, indent=2), encoding="utf-8")


def upload_dataset_to_local_repo(
    payload_path: Path,
    *,
    repo_root: Path,
    owner: str | None = None,
    description: str = "DeepCritical dataset repository",
    dataset_id_override: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> UploadOutcome:
    payload = _read_json(payload_path)
    kind = _guess_dataset_kind(payload)

    _ensure_repo(repo_root, owner=owner, description=description)

    inferred_id = (
        str(payload.get("dataset_id") or "")
        or str(payload.get("name") or "")
        or f"dataset-{int(time.time())}"
    )
    dataset_id = dataset_id_override or inferred_id
    safe = "".join(ch for ch in dataset_id if ch.isalnum() or ch in ("-", "_"))[:80]
    if not safe:
        safe = f"dataset-{int(time.time())}"

    out_dir = repo_root / "datasets" / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "payload.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    meta = {
        "kind": kind,
        "source_file": str(payload_path),
        "uploaded_at_unix": int(time.time()),
        "dataset_id": dataset_id,
        "payload_keys": sorted(payload.keys()),
        "extra": dict(extra_metadata or {}),
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return UploadOutcome(repo_root=repo_root, dataset_dir=out_dir, dataset_kind=kind)


def upload_payload_object_to_local_repo(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    owner: str | None = None,
    description: str = "DeepCritical dataset repository",
    dataset_id_override: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
    source_label: str = "in_memory",
) -> UploadOutcome:
    """Upload a payload dict directly (no intermediate file required)."""

    kind = _guess_dataset_kind(payload)
    _ensure_repo(repo_root, owner=owner, description=description)

    inferred_id = (
        str(payload.get("dataset_id") or "")
        or str(payload.get("name") or "")
        or f"dataset-{int(time.time())}"
    )
    dataset_id = dataset_id_override or inferred_id
    safe = "".join(ch for ch in dataset_id if ch.isalnum() or ch in ("-", "_"))[:80]
    if not safe:
        safe = f"dataset-{int(time.time())}"

    out_dir = repo_root / "datasets" / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "payload.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    meta = {
        "kind": kind,
        "source_file": source_label,
        "uploaded_at_unix": int(time.time()),
        "dataset_id": dataset_id,
        "payload_keys": sorted(payload.keys()),
        "extra": dict(extra_metadata or {}),
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return UploadOutcome(repo_root=repo_root, dataset_dir=out_dir, dataset_kind=kind)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Upload a DeepCritical dataset JSON into a local dataset repository.",
    )
    p.add_argument(
        "--payload",
        required=True,
        help="Path to dataset payload JSON (HypothesisDataset, LiteratureReviewDataset, or chain payload).",
    )
    p.add_argument(
        "--repo-root",
        required=True,
        help="Directory for the dataset repository (created if missing).",
    )
    p.add_argument("--owner", default=None, help="Optional repository owner label.")
    p.add_argument(
        "--repo-description",
        default="DeepCritical dataset repository",
        help="Description stored in repo.json when creating a new repo.",
    )
    p.add_argument(
        "--dataset-id",
        default=None,
        help="Override dataset id directory name (otherwise derived from payload).",
    )
    p.add_argument(
        "--metadata",
        default=None,
        help="Optional JSON string merged into metadata.json under 'extra'.",
    )
    return p


def main() -> int:
    ns = build_arg_parser().parse_args()
    payload_path = Path(ns.payload).expanduser().resolve()
    repo_root = Path(ns.repo_root).expanduser().resolve()
    extra: dict[str, Any] | None = None
    if ns.metadata:
        extra = json.loads(ns.metadata)
    outcome = upload_dataset_to_local_repo(
        payload_path,
        repo_root=repo_root,
        owner=ns.owner,
        description=str(ns.repo_description),
        dataset_id_override=ns.dataset_id,
        extra_metadata=extra,
    )
    print(
        json.dumps(
            {
                "repo_root": str(outcome.repo_root),
                "dataset_dir": str(outcome.dataset_dir),
                "dataset_kind": outcome.dataset_kind,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
