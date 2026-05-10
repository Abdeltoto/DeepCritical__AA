from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState
from DeepResearch.src.tools.base import registry


def test_deep_agent_tool_runners_are_registered() -> None:
    registered = set(registry.list())

    assert {
        "write_todos",
        "list_files",
        "read_file",
        "write_file",
        "edit_file",
        "task",
    }.issubset(registered)


def test_registered_write_file_runner_uses_state() -> None:
    state = DeepAgentState(session_id="registry")
    runner = registry.make("write_file")

    result = runner.run(
        {
            "state": state,
            "file_path": "/registry.txt",
            "content": "registered",
        }
    )

    assert result.success
    assert state.get_file("/registry.txt").content == "registered"


def test_registered_task_runner_reports_missing_subagent() -> None:
    state = DeepAgentState(session_id="missing-task-runner")
    runner = registry.make("task")

    result = runner.run(
        {
            "state": state,
            "description": "Do work",
            "subagent_type": "unknown",
            "parameters": {},
        }
    )

    assert result.success is False
    assert "No subagent" in result.error
    assert not state.active_tasks
    assert not state.completed_tasks


def test_registered_task_runner_delegates_to_state_subagent() -> None:
    state = DeepAgentState(session_id="task-runner")
    subagent = MagicMock()
    subagent.run = AsyncMock(return_value=SimpleNamespace(output={"ok": True}))
    state.shared_state["subagent_registry"] = {"research": subagent}
    runner = registry.make("task")

    result = runner.run(
        {
            "state": state,
            "description": "Research topic",
            "subagent_type": "research",
            "parameters": {},
        }
    )

    assert result.success
    assert result.data["result"]["ok"] is True
    assert result.data["task_id"] in state.completed_tasks
    assert result.data["task_id"] not in state.active_tasks
    subagent.run.assert_awaited_once_with("Research topic")
