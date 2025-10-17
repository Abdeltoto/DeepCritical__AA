"""
Tests for specialized agent implementations.

This module tests all specialized agents including ParserAgent, PlannerAgent,
ExecutorAgent, SearchAgent, RAGAgent, BioinformaticsAgent, DeepSearchAgent,
and EvaluatorAgent.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from DeepResearch.agents import (
    BaseAgent,
    BioinformaticsAgent,
    DeepSearchAgent,
    EvaluatorAgent,
    ExecutorAgent,
    ParserAgent,
    PlannerAgent,
    RAGAgent,
    SearchAgent,
)
from DeepResearch.src.datatypes.agents import (
    AgentDependencies,
    AgentType,
    ExecutionHistory,
)
from DeepResearch.src.datatypes.bioinformatics import (
    DataFusionRequest,
    FusedDataset,
    ReasoningTask,
)
from DeepResearch.src.datatypes.rag import RAGQuery, RAGResponse


# Fixtures
@pytest.fixture
def mock_pydantic_agent():
    """Mock Pydantic AI Agent."""
    agent = Mock()
    agent.run = AsyncMock()
    agent.tool = Mock()
    return agent


@pytest.fixture
def execution_history():
    """Create execution history."""
    return ExecutionHistory()


def assert_valid_plan(plan, query_value):
    """Reusable validator for plan structure and params."""
    # Check overall structure
    assert isinstance(plan, list)
    assert len(plan) == 6
    assert all(isinstance(step, dict) for step in plan)
    assert all("tool" in step and "params" in step for step in plan)

    # Check parameter details for each tool
    expected_tools = [
        "rewrite",
        "web_search",
        "summarize",
        "references",
        "finalize",
        "evaluator",
    ]
    assert [step["tool"] for step in plan] == expected_tools, "Tool sequence mismatch"

    # Check specific sequence and keys
    expected_params = [
        {"query": query_value},
        {"query": "${rewrite.queries}"},
        {"snippets": "${web_search.results}"},
        {"answer": "${summarize.summary}", "web": "${web_search.results}"},
        {"draft": "${references.answer_with_refs}"},
        {"question": query_value, "answer": "${finalize.final}"},
    ]

    for step, expected in zip(plan, expected_params, strict=False):
        assert step["params"] == expected, f"Params mismatch for {step['tool']}"


# PlannerAgent Tests
class TestPlannerAgent:
    """Test PlannerAgent functionality."""

    def test_planner_agent_initialization(self):
        """Test PlannerAgent initialization."""
        with patch("DeepResearch.agents.Agent"):
            agent = PlannerAgent()

            assert agent.agent_type == AgentType.PLANNER
            assert agent.model_name == "anthropic:claude-sonnet-4-0"

    def test_planner_custom_model(self):
        """Test PlannerAgent with custom model."""
        with patch("DeepResearch.agents.Agent"):
            agent = PlannerAgent(model_name="openai:gpt-4")

            assert agent.model_name == "openai:gpt-4"

    @pytest.mark.asyncio
    async def test_create_plan_success(self):
        """Test successful plan creation."""
        agent = PlannerAgent()

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            "steps": [
                {"tool": "rewrite", "params": {"query": "test"}},
                {"tool": "search", "params": {"query": "${rewrite.queries}"}},
            ]
        }

        with patch.object(
            BaseAgent, "execute", new=AsyncMock(return_value=mock_result)
        ):
            parsed = {"intent": "research", "query": "test question"}
            plan = await agent.create_plan(parsed)

        # Basic type and length checks
        assert isinstance(plan, list), f"Expected list, got {type(plan)}"
        assert len(plan) == 2, f"Expected 2 steps, got {len(plan)}"
        assert all(isinstance(step, dict) for step in plan), "Each step must be a dict"
        assert all("tool" in step and "params" in step for step in plan), (
            "Each step must contain 'tool' and 'params' keys"
        )

        # Expected tool sequence
        expected_tools = ["rewrite", "search"]
        assert [step["tool"] for step in plan] == expected_tools, (
            f"Expected tools {expected_tools}, got {[step['tool'] for step in plan]}"
        )

        # Detailed parameter validation
        assert plan[0]["params"] == {"query": "test"}, (
            f"Unexpected params for 'rewrite': {plan[0]['params']}"
        )
        assert plan[1]["params"] == {"query": "${rewrite.queries}"}, (
            f"Unexpected params for 'search': {plan[1]['params']}"
        )

    @pytest.mark.asyncio
    async def test_create_plan_fallback(self):
        """Test plan creation falls back to default."""
        agent = PlannerAgent()

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {}  # No steps

        with patch.object(
            BaseAgent, "execute", new=AsyncMock(return_value=mock_result)
        ):
            parsed = {"query": "test question"}
            plan = await agent.create_plan(parsed)
            # Detailed parameter validation
            assert_valid_plan(plan, "test question")

    def test_get_default_plan(self):
        """Test default plan generation."""
        agent = PlannerAgent()
        plan = agent._get_default_plan("test query")
        # Detailed parameter validation
        assert_valid_plan(plan, "test query")

    def test_plan_sync_method(self):
        """Test synchronous plan method."""
        agent = PlannerAgent()

        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {"steps": [{"tool": "test"}]}

        with patch.object(BaseAgent, "execute_sync", return_value=mock_result):
            parsed = {"query": "test"}
            plan = agent.plan(parsed)
        assert len(plan) == 1
        assert plan[0]["tool"] == "test"

    def test_plan_sync_fallback_on_exception(self):
        """Test synchronous plan method falls back when execute_sync raises an exception."""
        agent = PlannerAgent()

        with patch.object(
            BaseAgent, "execute_sync", side_effect=RuntimeError("Model timeout")
        ):
            parsed = {"query": "test fallback"}
            plan = agent.plan(parsed)
        # Detailed parameter validation
        assert_valid_plan(plan, "test fallback")


# # ExecutorAgent Tests
# class TestExecutorAgent:
#     """Test ExecutorAgent functionality."""

#     def test_executor_initialization_default(self):
#         """Test ExecutorAgent initialization with defaults."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = ExecutorAgent()

#             assert agent.agent_type == AgentType.EXECUTOR
#             assert agent.retries == 2

#     def test_executor_initialization_custom_retries(self):
#         """Test ExecutorAgent with custom retries."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = ExecutorAgent(retries=5)

#             assert agent.retries == 5

#     @pytest.mark.asyncio
#     async def test_execute_plan_success(self, execution_history):
#         """Test successful plan execution."""
#         with patch("DeepResearch.agents.Agent"):
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 agent = ExecutorAgent()

#                 # Mock tool runner
#                 mock_runner = Mock()
#                 mock_runner.run.return_value = Mock(
#                     success=True, data={"result": "test_output"}
#                 )
#                 mock_registry.make.return_value = mock_runner

#                 plan = [{"tool": "test_tool", "params": {"query": "test"}}]

#                 result = await agent.execute_plan(plan, execution_history)

#                 assert "test_tool.result" in result
#                 assert result["test_tool.result"] == "test_output"
#                 assert_valid_plan(plan, "test")

#     @pytest.mark.asyncio
#     async def test_execute_plan_with_variable_substitution(
#         self, execution_history
#     ):
#         """Test plan execution with variable substitution."""
#         with patch("DeepResearch.agents.Agent"):
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 agent = ExecutorAgent()

#                 # Mock tool runner
#                 mock_runner = Mock()
#                 mock_runner.run.return_value = Mock(
#                     success=True, data={"queries": ["q1", "q2"]}
#                 )
#                 mock_registry.make.return_value = mock_runner

#                 plan = [
#                     {"tool": "rewrite", "params": {"query": "test"}},
#                     {"tool": "search", "params": {"query": "${rewrite.queries}"}},
#                 ]

#                 result = await agent.execute_plan(plan, execution_history)

#                 assert "rewrite.queries" in result
#                 assert "search.queries" in result or "queries" in result

#     @pytest.mark.asyncio
#     async def test_execute_plan_with_retry(self, execution_history):
#         """Test plan execution with retry logic."""
#         with patch("DeepResearch.agents.Agent"):
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 agent = ExecutorAgent(retries=2)

#                 # Mock tool that fails then succeeds
#                 mock_runner = Mock()
#                 mock_runner.run.side_effect = [
#                     Mock(success=False, error="First attempt failed"),
#                     Mock(success=True, data={"result": "success"}),
#                 ]
#                 mock_registry.make.return_value = mock_runner

#                 plan = [{"tool": "test_tool", "params": {"query": "test"}}]

#                 result = await agent.execute_plan(plan, execution_history)

#                 # Should succeed after retry
#                 assert "test_tool.result" in result or "result" in result

#     @pytest.mark.asyncio
#     async def test_execute_plan_stops_on_failure(self, execution_history):
#         """Test plan execution stops after max retries."""
#         with patch("DeepResearch.agents.Agent"):
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 agent = ExecutorAgent(retries=1)

#                 # Mock tool that always fails
#                 mock_runner = Mock()
#                 mock_runner.run.return_value = Mock(
#                     success=False, error="Always fails"
#                 )
#                 mock_registry.make.return_value = mock_runner

#                 plan = [
#                     {"tool": "failing_tool", "params": {}},
#                     {"tool": "never_reached", "params": {}},
#                 ]

#                 result = await agent.execute_plan(plan, execution_history)

#                 # Should stop after first tool fails
#                 assert "never_reached" not in str(result)

#     def test_materialize_params(self):
#         """Test parameter materialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = ExecutorAgent()

#             bag = {"rewrite.queries": ["q1", "q2"], "search.results": ["r1"]}
#             params = {"query": "${rewrite.queries}", "type": "web"}

#             result = agent._materialize_params(params, bag)

#             assert result["query"] == ["q1", "q2"]
#             assert result["type"] == "web"

#     def test_materialize_params_missing_key(self):
#         """Test parameter materialization with missing key."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = ExecutorAgent()

#             bag = {}
#             params = {"query": "${missing.key}"}

#             result = agent._materialize_params(params, bag)

#             assert result["query"] == ""

#     def test_adjust_parameters(self):
#         """Test parameter adjustment for retries."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = ExecutorAgent()

#             bag = {"search.snippets": "test data"}
#             params = {"query": "", "snippets": ""}

#             adjusted = agent._adjust_parameters(params, bag)

#             assert adjusted["query"] == "general information"
#             assert adjusted["snippets"] == "test data"

#     def test_run_plan_sync(self, execution_history):
#         """Test synchronous run_plan method."""
#         with patch("DeepResearch.agents.Agent"):
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 agent = ExecutorAgent()

#                 mock_runner = Mock()
#                 mock_runner.run.return_value = Mock(
#                     success=True, data={"result": "test"}
#                 )
#                 mock_registry.make.return_value = mock_runner

#                 plan = [{"tool": "test", "params": {}}]

#                 result = agent.run_plan(plan, execution_history)

#                 assert isinstance(result, dict)


# # SearchAgent Tests
# class TestSearchAgent:
#     """Test SearchAgent functionality."""

#     def test_search_agent_initialization(self):
#         """Test SearchAgent initialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = SearchAgent()

#             assert agent.agent_type == AgentType.SEARCH

#     @pytest.mark.asyncio
#     async def test_search_success(self, mock_pydantic_agent):
#         """Test successful search operation."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = SearchAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "results": [
#                     {"title": "Result 1", "url": "http://test1.com"},
#                     {"title": "Result 2", "url": "http://test2.com"},
#                 ]
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.search("test query")

#             assert "results" in result
#             assert len(result["results"]) == 2

#     @pytest.mark.asyncio
#     async def test_search_with_params(self, mock_pydantic_agent):
#         """Test search with custom parameters."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = SearchAgent()

#             mock_result = Mock()
#             mock_result.data = {"results": []}
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.search(
#                 "query", search_type="news", num_results=20
#             )

#             # Verify execution was called
#             mock_pydantic_agent.run.assert_called_once()

#     @pytest.mark.asyncio
#     async def test_search_failure(self, mock_pydantic_agent):
#         """Test search failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = SearchAgent()

#             mock_pydantic_agent.run.side_effect = Exception("Search failed")

#             result = await agent.search("test query")

#             assert "error" in result

#     def test_search_tool_registration(self):
#         """Test that search tools are registered."""
#         with patch("DeepResearch.agents.Agent") as mock_agent_class:
#             with patch("DeepResearch.agents.WebSearchTool"):
#                 with patch("DeepResearch.agents.ChunkedSearchTool"):
#                     mock_agent = Mock()
#                     mock_agent.tool = Mock()
#                     mock_agent_class.return_value = mock_agent

#                     agent = SearchAgent()

#                     # Tools should be registered
#                     assert mock_agent.tool.called


# # RAGAgent Tests
# class TestRAGAgent:
#     """Test RAGAgent functionality."""

#     def test_rag_agent_initialization(self):
#         """Test RAGAgent initialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = RAGAgent()

#             assert agent.agent_type == AgentType.RAG

#     @pytest.mark.asyncio
#     async def test_rag_query_success(self, mock_pydantic_agent):
#         """Test successful RAG query."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = RAGAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "query": "test query",
#                 "retrieved_documents": ["doc1", "doc2"],
#                 "generated_answer": "test answer",
#                 "context": "test context",
#                 "processing_time": 1.5,
#                 "metadata": {},
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             rag_query = RAGQuery(text="test query", top_k=5)
#             result = await agent.query(rag_query)

#             assert isinstance(result, RAGResponse)
#             assert result.generated_answer == "test answer"
#             assert len(result.retrieved_documents) == 2

#     @pytest.mark.asyncio
#     async def test_rag_query_failure(self, mock_pydantic_agent):
#         """Test RAG query failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = RAGAgent()

#             mock_pydantic_agent.run.side_effect = Exception("RAG failed")

#             rag_query = RAGQuery(text="test query", top_k=5)
#             result = await agent.query(rag_query)

#             assert isinstance(result, RAGResponse)
#             assert result.query == "test query"
#             assert result.generated_answer == ""
#             assert "error" in result.metadata

#     @pytest.mark.asyncio
#     async def test_rag_query_empty_results(self, mock_pydantic_agent):
#         """Test RAG query with empty results."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = RAGAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "query": "test",
#                 "retrieved_documents": [],
#                 "generated_answer": "",
#                 "context": "",
#                 "processing_time": 0.5,
#                 "metadata": {},
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             rag_query = RAGQuery(text="test query", top_k=5)
#             result = await agent.query(rag_query)

#             assert len(result.retrieved_documents) == 0


# # BioinformaticsAgent Tests
# class TestBioinformaticsAgent:
#     """Test BioinformaticsAgent functionality."""

#     def test_bioinformatics_agent_initialization(self):
#         """Test BioinformaticsAgent initialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = BioinformaticsAgent()

#             assert agent.agent_type == AgentType.BIOINFORMATICS

#     @pytest.mark.asyncio
#     async def test_fuse_data_success(self, mock_pydantic_agent):
#         """Test successful data fusion."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = BioinformaticsAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "fused_dataset": {
#                     "dataset_id": "test_ds",
#                     "name": "Test Dataset",
#                     "description": "Test description",
#                     "source_databases": ["GO", "PubMed"],
#                 }
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             fusion_request = DataFusionRequest(
#                 request_id="req_1",
#                 fusion_type="MultiSource",
#                 source_databases=["GO", "PubMed"],
#                 quality_threshold=0.8,
#             )

#             result = await agent.fuse_data(fusion_request)

#             assert isinstance(result, FusedDataset)
#             assert result.dataset_id == "test_ds"
#             assert len(result.source_databases) == 2

#     @pytest.mark.asyncio
#     async def test_fuse_data_failure(self, mock_pydantic_agent):
#         """Test data fusion failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = BioinformaticsAgent()

#             mock_pydantic_agent.run.side_effect = Exception("Fusion failed")

#             fusion_request = DataFusionRequest(
#                 request_id="req_1",
#                 fusion_type="MultiSource",
#                 source_databases=["GO"],
#                 quality_threshold=0.8,
#             )

#             result = await agent.fuse_data(fusion_request)

#             assert result.dataset_id == "error"
#             assert "Failed" in result.description

#     @pytest.mark.asyncio
#     async def test_perform_reasoning_success(self, mock_pydantic_agent):
#         """Test successful reasoning operation."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = BioinformaticsAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "reasoning_result": "test result",
#                 "confidence": 0.9,
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             task = ReasoningTask(
#                 task_id="task_1",
#                 task_type="general_reasoning",
#                 question="test question",
#                 difficulty_level="medium",
#             )
#             dataset = FusedDataset(
#                 dataset_id="ds_1",
#                 name="Test",
#                 description="Test dataset",
#                 source_databases=["GO"],
#             )

#             result = await agent.perform_reasoning(task, dataset)

#             assert "reasoning_result" in result
#             assert result["reasoning_result"] == "test result"

#     @pytest.mark.asyncio
#     async def test_perform_reasoning_failure(self, mock_pydantic_agent):
#         """Test reasoning failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = BioinformaticsAgent()

#             mock_pydantic_agent.run.side_effect = Exception("Reasoning failed")

#             task = ReasoningTask(
#                 task_id="task_1",
#                 task_type="general_reasoning",
#                 question="test",
#                 difficulty_level="medium",
#             )
#             dataset = FusedDataset(
#                 dataset_id="ds_1",
#                 name="Test",
#                 description="Test",
#                 source_databases=[],
#             )

#             result = await agent.perform_reasoning(task, dataset)

#             assert "error" in result


# # DeepSearchAgent Tests
# class TestDeepSearchAgent:
#     """Test DeepSearchAgent functionality."""

#     def test_deepsearch_agent_initialization(self):
#         """Test DeepSearchAgent initialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = DeepSearchAgent()

#             assert agent.agent_type == AgentType.DEEPSEARCH

#     @pytest.mark.asyncio
#     async def test_deep_search_success(self, mock_pydantic_agent):
#         """Test successful deep search."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = DeepSearchAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "answer": "Deep search answer",
#                 "iterations": 5,
#                 "sources": ["source1", "source2"],
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.deep_search("test question", max_steps=20)

#             assert "answer" in result
#             assert "iterations" in result

#     @pytest.mark.asyncio
#     async def test_deep_search_with_custom_steps(self, mock_pydantic_agent):
#         """Test deep search with custom max steps."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = DeepSearchAgent()

#             mock_result = Mock()
#             mock_result.data = {"answer": "test", "iterations": 10}
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.deep_search("question", max_steps=10)

#             # Verify execution was called with correct params
#             mock_pydantic_agent.run.assert_called_once()

#     @pytest.mark.asyncio
#     async def test_deep_search_failure(self, mock_pydantic_agent):
#         """Test deep search failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = DeepSearchAgent()

#             mock_pydantic_agent.run.side_effect = Exception("Deep search failed")

#             result = await agent.deep_search("question")

#             assert "error" in result


# # EvaluatorAgent Tests
# class TestEvaluatorAgent:
#     """Test EvaluatorAgent functionality."""

#     def test_evaluator_agent_initialization(self):
#         """Test EvaluatorAgent initialization."""
#         with patch("DeepResearch.agents.Agent"):
#             agent = EvaluatorAgent()

#             assert agent.agent_type == AgentType.EVALUATOR

#     @pytest.mark.asyncio
#     async def test_evaluate_success(self, mock_pydantic_agent):
#         """Test successful evaluation."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = EvaluatorAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "quality_score": 0.85,
#                 "completeness": 0.9,
#                 "accuracy": 0.8,
#                 "feedback": "Good answer",
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.evaluate("What is AI?", "AI is artificial intelligence")

#             assert "quality_score" in result
#             assert result["quality_score"] == 0.85

#     @pytest.mark.asyncio
#     async def test_evaluate_poor_answer(self, mock_pydantic_agent):
#         """Test evaluation of poor answer."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = EvaluatorAgent()

#             mock_result = Mock()
#             mock_result.data = {
#                 "quality_score": 0.3,
#                 "completeness": 0.2,
#                 "accuracy": 0.4,
#                 "feedback": "Needs improvement",
#             }
#             mock_pydantic_agent.run.return_value = mock_result

#             result = await agent.evaluate("Complex question", "Short answer")

#             assert result["quality_score"] < 0.5

#     @pytest.mark.asyncio
#     async def test_evaluate_failure(self, mock_pydantic_agent):
#         """Test evaluation failure handling."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             agent = EvaluatorAgent()

#             mock_pydantic_agent.run.side_effect = Exception("Evaluation failed")

#             result = await agent.evaluate("question", "answer")

#             assert "error" in result


# # Integration Tests
# class TestSpecializedAgentsIntegration:
#     """Integration tests for specialized agents."""

#     @pytest.mark.asyncio
#     async def test_parser_planner_executor_workflow(self):
#         """Test workflow from parser to planner to executor."""
#         with patch("DeepResearch.agents.Agent") as mock_agent_class:
#             with patch("DeepResearch.agents.registry") as mock_registry:
#                 # Setup mocks
#                 mock_agent = Mock()
#                 mock_agent.run = AsyncMock()
#                 mock_agent.tool = Mock()
#                 mock_agent_class.return_value = mock_agent

#                 # Parser result
#                 mock_agent.run.return_value = Mock(
#                     data={"intent": "research", "query": "test"}
#                 )
#                 parser = ParserAgent()
#                 parsed = await parser.parse_question("test question")

#                 # Planner result
#                 mock_agent.run.return_value = Mock(
#                     data={
#                         "steps": [
#                             {"tool": "test_tool", "params": {"query": "test"}}
#                         ]
#                     }
#                 )
#                 planner = PlannerAgent()
#                 plan = await planner.create_plan(parsed)

#                 # Executor
#                 mock_runner = Mock()
#                 mock_runner.run.return_value = Mock(
#                     success=True, data={"result": "final"}
#                 )
#                 mock_registry.make.return_value = mock_runner

#                 executor = ExecutorAgent()
#                 history = ExecutionHistory()
#                 result = await executor.execute_plan(plan, history)

#                 assert "result" in result or "test_tool.result" in result

#     @pytest.mark.asyncio
#     async def test_search_rag_workflow(self, mock_pydantic_agent):
#         """Test workflow from search to RAG."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             # Search
#             search_agent = SearchAgent()
#             mock_pydantic_agent.run.return_value = Mock(
#                 data={"results": [{"content": "doc1"}]}
#             )
#             search_results = await search_agent.search("query")

#             # RAG with search results
#             rag_agent = RAGAgent()
#             mock_pydantic_agent.run.return_value = Mock(
#                 data={
#                     "query": "query",
#                     "retrieved_documents": search_results.get("results", []),
#                     "generated_answer": "answer",
#                     "context": "context",
#                     "processing_time": 1.0,
#                     "metadata": {},
#                 }
#             )

#             rag_query = RAGQuery(text="query", top_k=5)
#             rag_result = await rag_agent.query(rag_query)

#             assert isinstance(rag_result, RAGResponse)

#     @pytest.mark.asyncio
#     async def test_agent_error_propagation(self, mock_pydantic_agent):
#         """Test error propagation through agent chain."""
#         with patch("DeepResearch.agents.Agent", return_value=mock_pydantic_agent):
#             # Parser fails
#             parser = ParserAgent()
#             mock_pydantic_agent.run.side_effect = Exception("Parser error")
#             parsed = await parser.parse_question("test")

#             assert "error" in parsed

#             # Planner uses fallback
#             planner = PlannerAgent()
#             mock_pydantic_agent.run.side_effect = Exception("Planner error")
#             plan = planner.plan(parsed)

#             # Should get default plan
#             assert len(plan) > 0
