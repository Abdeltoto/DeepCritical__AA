"""Shared helpers for CLI dataset repository uploads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from DeepResearch.scripts.upload_dataset_repository import (
    UploadOutcome,
    upload_payload_object_to_local_repo,
)


@dataclass(frozen=True)
class DatasetUploadConfig:
    enabled: bool = False
    repo_root: Path | None = None
    owner: str | None = None
    description: str = "DeepCritical dataset repository"
    dataset_id: str | None = None
    extra_metadata: dict[str, Any] | None = None
    source_label: str = "cli"


def parse_extra_metadata(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        msg = "--upload-metadata must be a JSON object"
        raise ValueError(msg)
    return obj


def maybe_upload_payload(
    payload: dict[str, Any], cfg: DatasetUploadConfig
) -> UploadOutcome | None:
    if not cfg.enabled or cfg.repo_root is None:
        return None
    return upload_payload_object_to_local_repo(
        payload,
        repo_root=cfg.repo_root,
        owner=cfg.owner,
        description=cfg.description,
        dataset_id_override=cfg.dataset_id,
        extra_metadata=cfg.extra_metadata,
        source_label=cfg.source_label,
    )
