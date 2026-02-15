"""
Centralized model configuration resolver.

Provides a single source of truth for LLM model strings across the codebase,
replacing hardcoded "anthropic:claude-sonnet-4-0" occurrences.

Resolution order (highest priority first):
    1. Environment variable (DEEPCRITICAL_MODEL or agent-specific override)
    2. Hydra config via BioinformaticsConfigLoader (if available)
    3. Default constant

Usage:
    from DeepResearch.src.utils.model_resolver import get_model, DEFAULT_MODEL

    # Simple usage — returns the resolved model string
    model = get_model()

    # Agent-specific override via env var DEEPCRITICAL_MODEL_BIOINFORMATICS
    model = get_model("bioinformatics")
"""

from __future__ import annotations

import os

DEFAULT_MODEL: str = "anthropic:claude-sonnet-4-0"

_ENV_PREFIX: str = "DEEPCRITICAL_MODEL"

# Mutable container for the override mechanism (avoids ``global`` statements)
_state: dict[str, str] = {"default": DEFAULT_MODEL}


def get_model(agent_type: str | None = None) -> str:
    """Resolve the LLM model string for a given agent type.

    Resolution order:
        1. ``DEEPCRITICAL_MODEL_<AGENT_TYPE>`` environment variable (if *agent_type* given)
        2. ``DEEPCRITICAL_MODEL`` environment variable (global override)
        3. Hydra / BioinformaticsConfigLoader value (if config is loaded)
        4. ``DEFAULT_MODEL`` constant

    Args:
        agent_type: Optional agent identifier (e.g. ``"bioinformatics"``,
            ``"code_generation"``).  Used to look up an agent-specific
            environment variable.

    Returns:
        A model string such as ``"anthropic:claude-sonnet-4-0"``.
    """
    if agent_type:
        agent_env = f"{_ENV_PREFIX}_{agent_type.upper()}"
        env_value = os.environ.get(agent_env)
        if env_value:
            return env_value

    global_env = os.environ.get(_ENV_PREFIX)
    if global_env:
        return global_env

    config_model = _resolve_from_config(agent_type)
    if config_model:
        return config_model

    return _state["default"]


def _resolve_from_config(agent_type: str | None = None) -> str | None:
    """Attempt to read the model from the Hydra config loader.

    Returns ``None`` when the config infrastructure is unavailable
    (e.g. outside a Hydra run or in tests).
    """
    try:
        from DeepResearch.src.utils.config_loader import BioinformaticsConfigLoader

        loader = BioinformaticsConfigLoader()
        if agent_type:
            model = loader.get_agent_model(agent_type)
        else:
            model = loader.get_default_model()

        if model and model != _state["default"]:
            return model
    except Exception:
        pass

    return None


def get_model_with_fallback(
    primary: str | None = None,
    agent_type: str | None = None,
) -> str:
    """Return *primary* if it is a non-empty string, otherwise resolve via :func:`get_model`.

    Useful during incremental migration where callers may still pass an
    explicit ``model_name`` parameter.

    Args:
        primary: An explicitly provided model string (may be ``None``).
        agent_type: Passed through to :func:`get_model` when *primary* is
            ``None`` or empty.

    Returns:
        A model string.
    """
    if primary:
        return primary
    return get_model(agent_type)


def override_default_model(model: str) -> _ModelOverride:
    """Context manager that temporarily overrides the module-level default.

    Intended for tests:

        with override_default_model("test:mock-model"):
            assert get_model() == "test:mock-model"

    Args:
        model: The temporary default model string.

    Returns:
        A context manager.
    """
    return _ModelOverride(model)


class _ModelOverride:
    """Context manager backing :func:`override_default_model`."""

    def __init__(self, model: str) -> None:
        self._model = model
        self._previous: str | None = None

    def __enter__(self) -> None:
        self._previous = _state["default"]
        _state["default"] = self._model

    def __exit__(self, *_: object) -> None:
        if self._previous is not None:
            _state["default"] = self._previous
