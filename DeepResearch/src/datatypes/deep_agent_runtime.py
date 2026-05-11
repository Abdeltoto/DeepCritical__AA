"""
Runtime dependencies for DeepAgent execution.

The models in ``deep_agent_state`` are intentionally serializable. This module
holds live runtime services that should not be written into state snapshots.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .deep_agent_state import DeepAgentState


class DeepAgentDeps(BaseModel):
    """Runtime dependencies passed through Pydantic AI ``RunContext``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: DeepAgentState
    orchestrator: Any | None = None
    tool_registry: Any | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = ["DeepAgentDeps"]
