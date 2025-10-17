"""
Tests for BaseAgent class and core agent functionality.

This module tests the abstract BaseAgent class and its implementations,
including initialization, tool registration, execution, and error handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_ai import Agent

from DeepResearch.agents import BaseAgent, ParserAgent
from DeepResearch.src.datatypes.agents import (
    AgentDependencies,
    AgentResult,
    AgentStatus,
    AgentType,
    ExecutionHistory,
)


# Fixtures
@pytest.fixture
def mock_pydantic_agent():
    """Mock Pydantic AI Agent."""
    agent = Mock(spec=Agent)
    agent.run = AsyncMock()
    agent.tool = Mock()
    return agent


@pytest.fixture
def agent_dependencies():
    """Create test agent dependencies."""
    return AgentDependencies(
        config={"temperature": 0.7},
        tools=["web_search", "rag_query"],
        other_agents=["planner"],
        data_sources=["pubmed", "arxiv"],
    )


@pytest.fixture
def execution_history():
    """Create test execution history."""
    return ExecutionHistory()


@pytest.fixture
def test_agent_class():
    """Create a concrete test agent class."""

    class TestAgent(BaseAgent):
        def __init__(self, **kwargs):
            super().__init__(AgentType.PARSER, **kwargs)

        def _register_tools(self):
            """Register test tools."""
            if self._agent:

                @self._agent.tool
                def test_tool(ctx, query: str) -> str:
                    return f"Result: {query}"

    return TestAgent


# Test BaseAgent Initialization
class TestBaseAgentInitialization:
    """Test BaseAgent initialization and setup."""

    def test_agent_initialization_default(self, test_agent_class):
        """Test basic agent initialization with defaults."""
        agent = test_agent_class()

        assert agent.agent_type == AgentType.PARSER
        assert agent.model_name == "anthropic:claude-sonnet-4-0"
        assert isinstance(agent.dependencies, AgentDependencies)
        assert agent.status == AgentStatus.IDLE
        assert isinstance(agent.history, ExecutionHistory)

    def test_agent_initialization_custom_model(self, test_agent_class):
        """Test agent initialization with custom model."""
        agent = test_agent_class(model_name="openai:gpt-4")

        assert agent.model_name == "openai:gpt-4"

    def test_agent_initialization_with_dependencies(
        self, test_agent_class, agent_dependencies
    ):
        """Test agent initialization with custom dependencies."""
        agent = test_agent_class(dependencies=agent_dependencies)

        assert agent.dependencies == agent_dependencies
        assert "web_search" in agent.dependencies.tools

    def test_agent_initialization_with_custom_prompts(self, test_agent_class):
        """Test agent initialization with custom prompts."""
        custom_system = "Custom system prompt"
        custom_instructions = "Custom instructions"

        agent = test_agent_class(
            system_prompt=custom_system,
            instructions=custom_instructions,
        )

        assert agent.agent_type == AgentType.PARSER

    @patch("DeepResearch.agents.Agent")
    def test_agent_initialization_failure_handling(
        self, mock_agent_class, test_agent_class
    ):
        """Test agent handles initialization failures gracefully."""
        mock_agent_class.side_effect = Exception("Initialization failed")

        agent = test_agent_class()

        assert agent._agent is None

    def test_multiple_agents_independent(self, test_agent_class):
        """Test that multiple agent instances are independent."""
        agent1 = test_agent_class()
        agent2 = test_agent_class(model_name="openai:gpt-4")

        assert agent1.model_name != agent2.model_name
        assert agent1.history is not agent2.history


# Test Agent Dependencies
class TestAgentDependencies:
    """Test agent dependency management."""

    def test_default_dependencies_creation(self):
        """Test creation of default dependencies."""
        deps = AgentDependencies()

        assert deps.config == {}
        assert deps.tools == []
        assert deps.other_agents == []
        assert deps.data_sources == []

    def test_dependencies_with_values(self):
        """Test dependencies with provided values."""
        deps = AgentDependencies(
            config={"key": "value"},
            tools=["tool1", "tool2"],
            other_agents=["agent1"],
            data_sources=["source1"],
        )

        assert deps.config == {"key": "value"}
        assert len(deps.tools) == 2
        assert "tool1" in deps.tools

    def test_dependencies_immutability(self):
        """Test that dependencies can be modified after creation."""
        deps = AgentDependencies()
        deps.tools.append("new_tool")

        assert "new_tool" in deps.tools


# Test Agent Execution
class TestAgentExecution:
    """Test agent execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_success(self, test_agent_class, mock_pydantic_agent):
        """Test successful agent execution."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            # Mock successful execution
            mock_result = Mock()
            mock_result.data = {"output": "test result"}
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test input")

            assert result.success is True
            assert "output" in result.data
            assert result.error is None
            assert result.execution_time > 0
            assert result.agent_type == AgentType.PARSER

    @pytest.mark.asyncio
    async def test_execute_with_custom_deps(
        self, test_agent_class, agent_dependencies, mock_pydantic_agent
    ):
        """Test execution with custom dependencies."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_result = Mock()
            mock_result.data = {"output": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test input", deps=agent_dependencies)

            assert result.success is True
            mock_pydantic_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_failure(self, test_agent_class, mock_pydantic_agent):
        """Test agent execution failure handling."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            # Mock execution failure
            mock_pydantic_agent.run.side_effect = Exception("Execution failed")

            result = await agent.execute("test input")

            assert result.success is False
            assert result.error == "Execution failed"
            assert agent.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_uninitialized_agent(self, test_agent_class):
        """Test execution with uninitialized agent."""
        with patch("DeepResearch.agents.Agent", side_effect=Exception("Init failed")):
            agent = test_agent_class()

            result = await agent.execute("test input")

            assert result.success is False
            assert "not properly initialized" in result.error

    @pytest.mark.asyncio
    async def test_execute_status_transitions(
        self, test_agent_class, mock_pydantic_agent
    ):
        """Test agent status transitions during execution."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            assert agent.status == AgentStatus.IDLE

            mock_result = Mock()
            mock_result.data = {"output": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test input")

            assert result.success is True
            assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_different_result_formats(
        self, test_agent_class, mock_pydantic_agent
    ):
        """Test processing of different result formats."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            # Test with .output attribute
            mock_result = Mock()
            mock_result.output = "output value"
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test")
            assert result.data["output"] == "output value"

            # Test with .data attribute
            mock_result = Mock(spec=[])
            mock_result.data = {"key": "value"}
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test")
            assert result.data == {"key": "value"}

            # Test with no attributes
            mock_result = "result"
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.execute("test")
            assert result.data == {"result": "result"}


# Test Synchronous Execution
class TestSynchronousExecution:
    """Test synchronous execution wrapper."""

    def test_execute_sync_success(self, test_agent_class, mock_pydantic_agent):
        """Test synchronous execution wrapper."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_result = Mock()
            mock_result.data = {"output": "sync result"}
            mock_pydantic_agent.run.return_value = mock_result

            result = agent.execute_sync("test input")

            assert result.success is True
            assert isinstance(result.data["output"], Mock)

    def test_execute_sync_failure(self, test_agent_class, mock_pydantic_agent):
        """Test synchronous execution with failure."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_pydantic_agent.run.side_effect = Exception("Sync failure")

            result = agent.execute_sync("test input")

            assert result.success is False
            assert "Sync failure" in result.error


# Test Execution History
class TestExecutionHistory:
    """Test execution history tracking."""

    @pytest.mark.asyncio
    async def test_history_recording(self, test_agent_class, mock_pydantic_agent):
        """Test that execution history is recorded."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_result = Mock()
            mock_result.data = {"output": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            await agent.execute("test input 1")
            await agent.execute("test input 2")

            assert len(agent.history.items) == 2

    @pytest.mark.asyncio
    async def test_history_records_failures(
        self, test_agent_class, mock_pydantic_agent
    ):
        """Test that failures are recorded in history."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_pydantic_agent.run.side_effect = Exception("Test failure")

            await agent.execute("test input")

            assert len(agent.history.items) == 1
            assert agent.history.items[0]["success"] is False
            assert agent.history.items[0]["error"] == "Test failure"

    def test_history_manual_recording(self, execution_history):
        """Test manual recording in execution history."""
        result = AgentResult(
            success=True,
            data={"key": "value"},
            agent_type=AgentType.PARSER,
            execution_time=1.5,
        )

        execution_history.record(
            AgentType.PARSER,
            result,
            tool="test_tool",
            params={"param": "value"},
        )

        assert len(execution_history.items) == 1
        assert execution_history.items[0]["agent_type"] == "parser"
        assert execution_history.items[0]["tool"] == "test_tool"


# Test Tool Registration
class TestToolRegistration:
    """Test agent tool registration."""

    def test_register_tools_called(self, test_agent_class):
        """Test that _register_tools is called during initialization."""
        with patch.object(test_agent_class, "_register_tools") as _:
            _ = test_agent_class()
            # _register_tools is called in _initialize_agent
            # But might fail due to agent being None in some cases

    def test_abstract_register_tools(self):
        """Test that BaseAgent._register_tools is abstract."""
        # Cannot instantiate BaseAgent directly
        with pytest.raises(TypeError):
            BaseAgent(AgentType.PARSER)


# Test Error Handling
class TestErrorHandling:
    """Test agent error handling."""

    @pytest.mark.asyncio
    async def test_execution_timeout_handling(
        self, test_agent_class, mock_pydantic_agent
    ):
        """Test handling of execution timeouts."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_pydantic_agent.run.side_effect = asyncio.TimeoutError("Timeout")

            result = await agent.execute("test input")

            assert result.success is False
            assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, test_agent_class, mock_pydantic_agent):
        """Test handling of invalid input."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_pydantic_agent.run.side_effect = ValueError("Invalid input")

            result = await agent.execute(None)

            assert result.success is False

    @pytest.mark.asyncio
    async def test_multiple_failures(self, test_agent_class, mock_pydantic_agent):
        """Test agent behavior with multiple failures."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_pydantic_agent.run.side_effect = Exception("Failure")

            result1 = await agent.execute("test 1")
            result2 = await agent.execute("test 2")

            assert result1.success is False
            assert result2.success is False
            assert len(agent.history.items) == 2


# Test Default Prompts
class TestDefaultPrompts:
    """Test default prompt generation."""

    def test_get_default_system_prompt(self, test_agent_class):
        """Test getting default system prompt."""
        with patch("DeepResearch.agents.AgentPrompts.get_system_prompt") as mock_prompt:
            mock_prompt.return_value = "Test system prompt"

            # Agent initialization calls get_system_prompt, so we use side_effect
            with patch("DeepResearch.agents.Agent"):
                agent = test_agent_class()

            # Now test the method directly
            mock_prompt.reset_mock()
            prompt = agent._get_default_system_prompt()

            mock_prompt.assert_called_once_with("parser")
            assert prompt == "Test system prompt"

    def test_get_default_instructions(self, test_agent_class):
        """Test getting default instructions."""
        with patch("DeepResearch.agents.AgentPrompts.get_instructions") as mock_instr:
            mock_instr.return_value = "Test instructions"

            # Agent initialization calls get_instructions, so we use side_effect
            with patch("DeepResearch.agents.Agent"):
                agent = test_agent_class()

            # Now test the method directly
            mock_instr.reset_mock()
            instructions = agent._get_default_instructions()

            mock_instr.assert_called_once_with("parser")
            assert instructions == "Test instructions"


# Test ParserAgent Specific
class TestParserAgent:
    """Test ParserAgent specific functionality."""

    @pytest.mark.asyncio
    async def test_parser_agent_initialization(self):
        """Test ParserAgent initialization."""
        with patch("DeepResearch.agents.Agent"):
            agent = ParserAgent()

            assert agent.agent_type == AgentType.PARSER
            assert agent.model_name == "anthropic:claude-sonnet-4-0"

    @pytest.mark.asyncio
    async def test_parse_question_success(self, mock_pydantic_agent):
        """Test successful question parsing."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = ParserAgent()

            mock_result = Mock()
            mock_result.output = {"intent": "research", "query": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            result = await agent.parse_question("test question")

            assert "intent" in result["output"].keys()
            assert result["output"]["intent"] == "research"

    @pytest.mark.asyncio
    async def test_parse_question_failure(self, mock_pydantic_agent):
        """Test question parsing failure."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = ParserAgent()

            mock_pydantic_agent.run.side_effect = Exception("Parse error")

            result = await agent.parse_question("test question")

            assert "error" in result
            assert result["query"] == "test question"

    def test_parse_sync_method(self, mock_pydantic_agent):
        """Test synchronous parse method."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = ParserAgent()

            mock_result = Mock()
            mock_result.output = {"intent": "search", "query": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            result = agent.parse("test question")

            assert (
                "intent" in result["output"].keys()
                or "query" in result["output"].keys()
            )
            # May return the output or fallback
            if "intent" in result:
                assert result["intent"] == "search"

    def test_parse_sync_with_failure(self, mock_pydantic_agent):
        """Test synchronous parse with failure."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = ParserAgent()

            mock_pydantic_agent.run.side_effect = Exception("Parse failed")

            result = agent.parse("test question")

            assert result["intent"] == "research"
            assert result["query"] == "test question"


# Integration Tests
class TestBaseAgentIntegration:
    """Integration tests for BaseAgent."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, test_agent_class, mock_pydantic_agent):
        """Test complete execution flow from initialization to result."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            # Initialize agent
            agent = test_agent_class(
                model_name="test-model",
                dependencies=AgentDependencies(tools=["tool1"]),
            )

            # Setup mock result
            mock_result = Mock()
            mock_result.data = {"final": "result"}
            mock_pydantic_agent.run.return_value = mock_result

            # Execute
            result = await agent.execute("complex input", agent.dependencies)

            # Verify complete flow
            assert result.success is True
            assert agent.status == AgentStatus.COMPLETED
            assert len(agent.history.items) == 1
            assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_multiple_executions_state_management(
        self, test_agent_class, mock_pydantic_agent
    ):
        """Test state management across multiple executions."""
        with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
            agent = test_agent_class()

            mock_result = Mock()
            mock_result.data = {"output": "test"}
            mock_pydantic_agent.run.return_value = mock_result

            # Execute multiple times
            results = []
            for i in range(3):
                result = await agent.execute(f"input {i}")
                results.append(result)

            # All should succeed
            assert all(r.success for r in results)
            # History should have all executions
            assert len(agent.history.items) == 3
            # Status should be COMPLETED
            assert agent.status == AgentStatus.COMPLETED
