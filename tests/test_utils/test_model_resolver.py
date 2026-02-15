"""
Tests for the centralized model resolver.
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


class TestGetModel:
    """Tests for get_model function."""

    def test_returns_default_when_no_overrides(self):
        """get_model returns DEFAULT_MODEL when no env vars or config are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model()
            assert result == DEFAULT_MODEL

    def test_global_env_override(self):
        """DEEPCRITICAL_MODEL env var overrides the default."""
        with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": "openai:gpt-4o"}):
            result = get_model()
            assert result == "openai:gpt-4o"

    def test_agent_specific_env_override(self):
        """DEEPCRITICAL_MODEL_<AGENT> env var overrides for a specific agent."""
        with patch.dict(
            os.environ,
            {"DEEPCRITICAL_MODEL_BIOINFORMATICS": "google:gemini-pro"},
        ):
            result = get_model("bioinformatics")
            assert result == "google:gemini-pro"

    def test_agent_env_takes_priority_over_global(self):
        """Agent-specific env var takes priority over global env var."""
        with patch.dict(
            os.environ,
            {
                "DEEPCRITICAL_MODEL": "openai:gpt-4o",
                "DEEPCRITICAL_MODEL_CODE_GENERATION": "anthropic:claude-opus-4",
            },
        ):
            result = get_model("code_generation")
            assert result == "anthropic:claude-opus-4"

    def test_global_env_used_when_no_agent_specific(self):
        """Global env var is used when agent-specific env var is not set."""
        with patch.dict(
            os.environ,
            {"DEEPCRITICAL_MODEL": "openai:gpt-4o"},
            clear=True,
        ):
            result = get_model("bioinformatics")
            assert result == "openai:gpt-4o"

    def test_agent_type_none_skips_agent_lookup(self):
        """When agent_type is None, only global env and default are checked."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_model(None)
            assert result == DEFAULT_MODEL

    def test_default_model_is_anthropic_claude(self):
        """Verify the default model constant is the expected value."""
        assert DEFAULT_MODEL == "anthropic:claude-sonnet-4-0"


class TestGetModelWithFallback:
    """Tests for get_model_with_fallback function."""

    def test_returns_primary_when_provided(self):
        """Returns the primary model string when it is non-empty."""
        result = get_model_with_fallback(primary="custom:model")
        assert result == "custom:model"

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
            {"DEEPCRITICAL_MODEL_REASONING": "test:reasoning-model"},
        ):
            result = get_model_with_fallback(primary=None, agent_type="reasoning")
            assert result == "test:reasoning-model"


class TestOverrideDefaultModel:
    """Tests for the override_default_model context manager."""

    def test_overrides_inside_context(self):
        """DEFAULT_MODEL is overridden inside the context manager."""
        with override_default_model("test:mock-model"):
            assert get_model() == "test:mock-model"

    def test_restores_after_context(self):
        """DEFAULT_MODEL is restored after the context manager exits."""
        original = DEFAULT_MODEL
        with override_default_model("test:mock-model"):
            pass
        with patch.dict(os.environ, {}, clear=True):
            assert get_model() == original

    def test_nested_overrides(self):
        """Nested context managers work correctly."""
        with override_default_model("test:outer"):
            assert get_model() == "test:outer"
            with override_default_model("test:inner"):
                assert get_model() == "test:inner"
            assert get_model() == "test:outer"

    def test_env_still_takes_priority_over_override(self):
        """Environment variables still take priority even inside override."""
        with override_default_model("test:mock-model"):
            with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": "env:model"}):
                assert get_model() == "env:model"


class TestAgentsIntegration:
    """Test that agents.py correctly uses the model resolver."""

    @pytest.mark.optional
    def test_base_agent_uses_resolver(self):
        """BaseAgent subclasses should use get_model when no model_name given."""
        from DeepResearch.agents import ParserAgent

        with override_default_model("test:integration-model"):
            agent = ParserAgent()
            assert agent.model_name == "test:integration-model"

    @pytest.mark.optional
    def test_base_agent_accepts_explicit_model(self):
        """BaseAgent subclasses should accept an explicit model_name."""
        from DeepResearch.agents import ParserAgent

        agent = ParserAgent(model_name="custom:explicit-model")
        assert agent.model_name == "custom:explicit-model"

    @pytest.mark.optional
    def test_base_agent_with_env_override(self):
        """BaseAgent subclasses should respect env var overrides."""
        from DeepResearch.agents import ParserAgent

        with patch.dict(os.environ, {"DEEPCRITICAL_MODEL": "env:test-model"}):
            agent = ParserAgent()
            assert agent.model_name == "env:test-model"
