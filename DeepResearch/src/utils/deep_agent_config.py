"""Validation helpers for DeepAgent Hydra configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from ..datatypes.deep_agent_types import AgentCapability
from ..tools.deep_agent_tools import DEEP_AGENT_TOOL_MAP

CAPABILITY_ALIASES: dict[str, list[AgentCapability]] = {
    "planning": [AgentCapability.PLANNING],
    "task_management": [AgentCapability.PLANNING],
    "filesystem": [AgentCapability.FILESYSTEM],
    "content_management": [AgentCapability.FILESYSTEM],
    "research": [AgentCapability.SEARCH, AgentCapability.ANALYSIS],
    "analysis": [AgentCapability.ANALYSIS],
    "orchestration": [AgentCapability.TASK_ORCHESTRATION],
    "task_delegation": [AgentCapability.TASK_ORCHESTRATION],
}


@dataclass(frozen=True)
class DeepAgentConfigValidationResult:
    """Result of validating enabled DeepAgent agent configuration."""

    valid: bool
    unknown_tools: dict[str, list[str]]
    unknown_capabilities: dict[str, list[str]]

    def raise_for_errors(self) -> None:
        if self.valid:
            return
        messages: list[str] = []
        if self.unknown_tools:
            messages.append(f"unknown tools: {self.unknown_tools}")
        if self.unknown_capabilities:
            messages.append(f"unknown capabilities: {self.unknown_capabilities}")
        raise ValueError("Invalid DeepAgent config; " + "; ".join(messages))


def normalize_capabilities(names: Iterable[str]) -> list[AgentCapability]:
    """Normalize config capability names to canonical ``AgentCapability`` values."""

    capabilities: list[AgentCapability] = []
    for name in names:
        if isinstance(name, AgentCapability):
            expanded = [name]
        else:
            try:
                expanded = [AgentCapability(str(name))]
            except ValueError:
                expanded = CAPABILITY_ALIASES.get(str(name), [])
        for cap in expanded:
            if cap not in capabilities:
                capabilities.append(cap)
    return capabilities


def unknown_capabilities(names: Iterable[str]) -> list[str]:
    """Return capability names that are neither canonical nor supported aliases."""

    unknown: list[str] = []
    for name in names:
        if isinstance(name, AgentCapability):
            continue
        text = str(name)
        if text in CAPABILITY_ALIASES:
            continue
        try:
            AgentCapability(text)
        except ValueError:
            unknown.append(text)
    return unknown


def validate_deep_agent_config(
    config: Mapping[str, Any],
    *,
    allowed_tools: Sequence[str] | None = None,
) -> DeepAgentConfigValidationResult:
    """Validate enabled agent tool and capability names in a DeepAgent config."""

    known_tools = set(allowed_tools or DEEP_AGENT_TOOL_MAP.keys())
    unknown_tool_names: dict[str, list[str]] = {}
    unknown_capability_names: dict[str, list[str]] = {}

    agents = config.get("deep_agent", {}).get("agents", {})
    for agent_name, agent_config in agents.items():
        if not isinstance(agent_config, Mapping):
            continue
        if not bool(agent_config.get("enabled", True)):
            continue

        tools = [str(name) for name in agent_config.get("tools", [])]
        bad_tools = [name for name in tools if name not in known_tools]
        if bad_tools:
            unknown_tool_names[str(agent_name)] = bad_tools

        caps = agent_config.get("capabilities", [])
        bad_caps = unknown_capabilities(caps)
        if bad_caps:
            unknown_capability_names[str(agent_name)] = bad_caps

    return DeepAgentConfigValidationResult(
        valid=not unknown_tool_names and not unknown_capability_names,
        unknown_tools=unknown_tool_names,
        unknown_capabilities=unknown_capability_names,
    )


__all__ = [
    "CAPABILITY_ALIASES",
    "DeepAgentConfigValidationResult",
    "normalize_capabilities",
    "unknown_capabilities",
    "validate_deep_agent_config",
]
