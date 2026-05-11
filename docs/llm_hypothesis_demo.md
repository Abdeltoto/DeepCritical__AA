# LLM hypothesis generation (CLI + JSONL + OpenTUI)

This path uses `run_hypothesis_generation_pipeline` in
[`DeepResearch/src/agents/hypothesis_generation_agent.py`](../DeepResearch/src/agents/hypothesis_generation_agent.py):
evidence retrieval (`chunked_search` via the canonical registry), a structured **proposer**
(`HypothesisBatchOutput`), optional **critic**, dedupe/cap, and a `HypothesisDataset`.

It is **distinct** from the template-based graph in
`DeepResearch/src/statemachines/hypothesis_workflow.py` (enabled via `flows.hypothesis_generation`).

## CLI

Console entry (after install):

```bash
uv run deepresearch-llm-hypothesis --question "Why might X correlate with Y?" --base-url https://api.openai.com/v1 --model gpt-4o-mini
```

Or module form:

```bash
uv run python -m DeepResearch.scripts.run_llm_hypothesis_pipeline --question "..." --output-jsonl -
```

### OpenAI-compatible endpoints

Pass `--base-url` and `--api-key` (or rely on `LLM_API_KEY` / `OpenAICompatibleModel` defaults).
Use `--model-ref` to resolve a profile from the Hydra model registry instead of a raw model string.

Example Hydra snippet: [`configs/hypothesis_llm/openai_compatible.yaml`](../configs/hypothesis_llm/openai_compatible.yaml).

### JSONL event schema

Each line is one JSON object with `event_type`:

`pipeline_started`, `evidence_fetch_started`, `evidence_fetched`, `proposer_started`,
`proposer_completed`, `critic_started`, `critic_completed`, `dedupe_applied`,
`dataset_built`, `pipeline_completed`, `pipeline_error`.

Implementation: [`DeepResearch/src/agents/hypothesis_pipeline_events.py`](../DeepResearch/src/agents/hypothesis_pipeline_events.py).

### Stub mode (tests)

Set `DEEPRESEARCH_HYPOTHESIS_PIPELINE_STUB=1` for a deterministic stream without LLM/network calls.

## OpenTUI demo

See [`tui/README.md`](../tui/README.md). Requires [Bun](https://bun.sh/) and `@opentui/core`.

The demo spawns the Python CLI as a subprocess, parses JSONL lines with Zod, and renders status panes.

## Primary orchestrator tool

The `run_hypothesis_generation` tool on `PrimaryWorkflowOrchestrator` calls the same pipeline and may run an optional quality judge; use `fail_on_judge_failure` in parameters to mark overall `success: false` when the judge fails.
