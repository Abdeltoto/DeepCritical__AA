"""
Tests for the centralized model resolver.

Model strings used in assertions and env patches are pinned as module-level
constants so expectations stay explicit and easy to update in one place.
"""

import os
from unittest.mock import patch

import pytest

from DeepResearch.src.utils.model_resolver import (
    DEFAULT_MODEL,
    get_model,
    get_model_with_fallback,
    override_default_model,
)

# --- Pinned model strings (single source of truth within this test module) ---

_PIN_OPENAI_GPT4O = "openai:gpt-4o"
_PIN_GOOGLE_GEMINI_PRO = "google:gemini-pro"
_PIN_ANTHROPIC_CLAUDE_OPUS_4 = "anthropic:claude-opus-4"
_PIN_ANTHROPIC_CLAUDE_SONNET_4 = "anthropic:claude-sonnet-4-0"

_PIN_CUSTOM_MODEL = "custom:model"
_PIN_TEST_REASONING = "test:reasoning-model"
_PIN_TEST_MOCK = "test:mock-model"
_PIN_TEST_OUTER = "test:outer"
_PIN_TEST_INNER = "test:inner"
_PIN_ENV_MODEL = "env:model"
_PIN_INTEGRATION_MODEL = "test:integration-model"
_PIN_EXPLICIT_MODEL = "custom:explicit-model"
_PIN_ENV_TEST_MODEL = "env:test-model"


class TestGetModel:
    """Tests for get_model function."""

    def test_returns_default_when_no_overrides(self):
        """get_model returns DEFAULT_MODEL when no env vars or config are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model()
            assert result == DEFAULT_MODEL

    def test_global_env_override(self):
        """DEEPCRITICAL_MODEL env var overrides the default."""
        with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": _PIN_OPENAI_GPT4O}):
            result = get_model()
            assert result == _PIN_OPENAI_GPT4O

    def test_agent_specific_env_override(self):
        """DEEPCRITICAL_MODEL_<AGENT> env var overrides for a specific agent."""
        with patch.dict(
            os.environ,
            {"DEEPCRITICAL_MODEL_BIOINFORMATICS": _PIN_GOOGLE_GEMINI_PRO},
        ):
            result = get_model("bioinformatics")
            assert result == _PIN_GOOGLE_GEMINI_PRO

    def test_agent_env_takes_priority_over_global(self):
        """Agent-specific env var takes priority over global env var."""
        with patch.dict(
            os.environ,
            {
                "DEEPCRITICAL_MODEL": _PIN_OPENAI_GPT4O,
                "DEEPCRITICAL_MODEL_CODE_GENERATION": _PIN_ANTHROPIC_CLAUDE_OPUS_4,
            },
        ):
            result = get_model("code_generation")
            assert result == _PIN_ANTHROPIC_CLAUDE_OPUS_4

    def test_global_env_used_when_no_agent_specific(self):
        """Global env var is used when agent-specific env var is not set."""
        with patch.dict(
            os.environ,
            {"DEEPCRITICAL_MODEL": _PIN_OPENAI_GPT4O},
            clear=True,
        ):
            result = get_model("bioinformatics")
            assert result == _PIN_OPENAI_GPT4O

    def test_agent_type_none_skips_agent_lookup(self):
        """When agent_type is None, only global env and default are checked."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model(None)
            assert result == DEFAULT_MODEL

    def test_default_model_is_anthropic_claude(self):
        """Verify the default model constant is the expected value."""
        assert DEFAULT_MODEL == _PIN_ANTHROPIC_CLAUDE_SONNET_4


class TestGetModelWithFallback:
    """Tests for get_model_with_fallback function."""

    def test_returns_primary_when_provided(self):
        """Returns the primary model string when it is non-empty."""
        result = get_model_with_fallback(primary=_PIN_CUSTOM_MODEL)
        assert result == _PIN_CUSTOM_MODEL

    def test_resolves_when_primary_is_none(self):
        """Falls back to get_model when primary is None."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model_with_fallback(primary=None)
            assert result == DEFAULT_MODEL

    def test_resolves_when_primary_is_empty(self):
        """Falls back to get_model when primary is an empty string."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model_with_fallback(primary="")
            assert result == DEFAULT_MODEL

    def test_passes_agent_type_to_get_model(self):
        """agent_type is forwarded to get_model when falling back."""
        with patch.dict(
            os.environ,
            {"DEEPCRITICAL_MODEL_REASONING": _PIN_TEST_REASONING},
        ):
            result = get_model_with_fallback(primary=None, agent_type="reasoning")
            assert result == _PIN_TEST_REASONING


class TestOverrideDefaultModel:
    """Tests for the override_default_model context manager."""

    def test_overrides_inside_context(self):
        """DEFAULT_MODEL is overridden inside the context manager."""
        with override_default_model(_PIN_TEST_MOCK):
            assert get_model() == _PIN_TEST_MOCK

    def test_restores_after_context(self):
        """DEFAULT_MODEL is restored after the context manager exits."""
        original = DEFAULT_MODEL
        with override_default_model(_PIN_TEST_MOCK):
            pass
        with patch.dict(os.environ, {}, clear=True):
            assert get_model() == original

    def test_nested_overrides(self):
        """Nested context managers work correctly."""
        with override_default_model(_PIN_TEST_OUTER):
            assert get_model() == _PIN_TEST_OUTER
            with override_default_model(_PIN_TEST_INNER):
                assert get_model() == _PIN_TEST_INNER
            assert get_model() == _PIN_TEST_OUTER

    def test_env_still_takes_priority_over_override(self):
        """Environment variables still take priority even inside override."""
        with override_default_model(_PIN_TEST_MOCK):
            with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": _PIN_ENV_MODEL}):
                assert get_model() == _PIN_ENV_MODEL


class TestAgentsIntegration:
    """Test that agents.py correctly uses the model resolver."""

    @pytest.mark.optional
    def test_base_agent_uses_resolver(self):
        """BaseAgent subclasses should use get_model when no model_name given."""
        from DeepResearch.agents import ParserAgent

        with override_default_model(_PIN_INTEGRATION_MODEL):
            agent = ParserAgent()
            assert agent.model_name == _PIN_INTEGRATION_MODEL

    @pytest.mark.optional
    def test_base_agent_accepts_explicit_model(self):
        """BaseAgent subclasses should accept an explicit model_name."""
        from DeepResearch.agents import ParserAgent

        agent = ParserAgent(model_name=_PIN_EXPLICIT_MODEL)
        assert agent.model_name == _PIN_EXPLICIT_MODEL

    @pytest.mark.optional
    def test_base_agent_with_env_override(self):
        """BaseAgent subclasses should respect env var overrides."""
        from DeepResearch.agents import ParserAgent

        with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": _PIN_ENV_TEST_MODEL}):
            agent = ParserAgent()
            assert agent.model_name == _PIN_ENV_TEST_MODEL
