from __future__ import annotations

from pathlib import Path

import yaml

from DeepResearch.src.datatypes.deep_agent_types import AgentCapability
from DeepResearch.src.utils.deep_agent_config import (
    normalize_capabilities,
    validate_deep_agent_config,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_config(path: str) -> dict:
    with (ROOT / path).open() as f:
        return yaml.safe_load(f)


def test_basic_and_default_configs_validate_for_mvp_tools() -> None:
    for path in ["configs/deep_agent/basic.yaml", "configs/deep_agent/default.yaml"]:
        result = validate_deep_agent_config(_load_config(path))
        assert result.valid, path


def test_comprehensive_config_reports_future_tool_names() -> None:
    result = validate_deep_agent_config(
        _load_config("configs/deep_agent/comprehensive.yaml")
    )

    assert result.valid is False
    assert "planning_agent" in result.unknown_tools
    assert "analyze_requirements" in result.unknown_tools["planning_agent"]


def test_capability_aliases_normalize_to_canonical_values() -> None:
    capabilities = normalize_capabilities(
        ["research", "task_management", "task_delegation"]
    )

    assert AgentCapability.SEARCH in capabilities
    assert AgentCapability.ANALYSIS in capabilities
    assert AgentCapability.PLANNING in capabilities
    assert AgentCapability.TASK_ORCHESTRATION in capabilities
