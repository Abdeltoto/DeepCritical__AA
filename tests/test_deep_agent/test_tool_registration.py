from __future__ import annotations

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from DeepResearch.src.datatypes.deep_agent_runtime import DeepAgentDeps
from DeepResearch.src.tools.deep_agent_tools import (
    DEEP_AGENT_TOOL_MAP,
    get_deep_agent_tools,
    resolve_deep_agent_tools,
)


def test_deep_agent_tools_construct_pydantic_ai_agent() -> None:
    agent = Agent(
        TestModel(),
        deps_type=DeepAgentDeps,
        tools=get_deep_agent_tools(),
    )

    assert set(agent._function_toolset.tools) == set(DEEP_AGENT_TOOL_MAP)


def test_resolved_tools_use_configured_names() -> None:
    tools = resolve_deep_agent_tools(["write_todos", "read_file"])

    assert [tool.name for tool in tools] == ["write_todos", "read_file"]


def test_tool_names_are_stable() -> None:
    assert set(DEEP_AGENT_TOOL_MAP) == {
        "write_todos",
        "list_files",
        "read_file",
        "write_file",
        "edit_file",
        "task",
    }


def test_resolve_deep_agent_tools_rejects_unknown_names() -> None:
    with pytest.raises(ValueError, match="missing_tool") as exc_info:
        resolve_deep_agent_tools(["write_todos", "missing_tool"])
    assert "write_todos" in str(exc_info.value)
