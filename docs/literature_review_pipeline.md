# Literature review pipeline (CLI and OpenTUI)

The critical literature review workflow runs as a Pydantic Graph (`DeepResearch.src.statemachines.literature_review_workflow`). For terminal UX and automation it exposes **JSONL events** on stdout (same pattern as the LLM hypothesis pipeline).

## Defaults (Hydra `configs/literature_review/default.yaml`)

- **`source_mode`**: `pubmed`
- **`live_retrieval_enabled`**: `true` (network retrieval on)

Use **`--source-mode fixture --no-live-retrieval`** for offline tests and deterministic fixtures.

## CLI

```bash
uv run python -m DeepResearch.scripts.run_literature_review_pipeline \
  --question "Your review question"
```

Fixture mode (no network):

```bash
uv run python -m DeepResearch.scripts.run_literature_review_pipeline \
  --question "Your review question" \
  --source-mode fixture \
  --no-live-retrieval \
  --fixture-path path/to/sources.json
```

Or the installed console script:

```bash
deepresearch-literature-pipeline --question "..."
```

If you set `--no-live-retrieval`, use **`--source-mode fixture`** (or you will get a configuration error for non-fixture modes).

### PubMed and network behavior

PubMed retrieval distinguishes **transport failures** (network / HTTP on esearch) from **zero search hits**. Transport failures surface as tool errors; zero PMIDs after a successful search returns an empty candidate list with warnings upstream.

### Screening flags (Hydra / API)

- `strict_screening`: raises the relevance threshold slightly for inclusion.
- `exclude_irrelevant_phrases`: when enabled, title-only keyword heuristics may exclude sources (off by default).

### Synthesis

By default the final markdown report is produced by **deterministic template assembly** (`LiteratureSynthesisTool`). You can opt in to **LLM synthesis** (Pydantic AI, same stack as the hypothesis pipeline): set `literature_review.llm_synthesis.enabled: true` in Hydra or use the CLI below.

**Behavior**

- When enabled, the workflow runs `synthesize_literature_with_llm` with structured output (`LiteratureSynthesisLLMOutput`). Claims are instructed to stay grounded in the serialized evidence JSON only (no invented PMIDs or citations).
- If the LLM call fails and `fallback_on_error` is true (default), the run falls back to the heuristic tool and sets `metadata["synthesis_mode"]` to `heuristic_fallback`, with a warning. On success, `metadata["synthesis_mode"]` is `llm`.
- Large payloads are trimmed for token budget; truncation notes appear in `metadata["llm_synthesis"]["truncation_notes"]` and may add warnings.

**Environment variables** (optional; used when CLI flags omit values and `--llm-synthesis` is on)

- `LLM_BASE_URL` — OpenAI-compatible API base URL
- `LLM_API_KEY` — API key

**CLI flags** (`run_literature_review_pipeline`)

- `--llm-synthesis` / `--no-llm-synthesis`
- `--model`, `--model-ref`, `--base-url`, `--api-key`
- `--temperature`, `--max-evidence-chars`
- `--llm-fallback-on-error` / `--no-llm-fallback-on-error`

**Cost and latency**

LLM synthesis adds network latency and token cost proportional to evidence size (capped by `max_evidence_chars`). Prefer fixtures or small `max_sources` for experiments.

**JSONL events**

When LLM synthesis is enabled, the stream may include `literature_review_llm_started` and `literature_review_llm_completed` (small `model_preview`, no secrets).

## OpenTUI demo (`tui/`)

```bash
cd tui && bun install
bun run src/main.ts --pipeline literature --question "Your question"
```

Self-test with fake literature events:

```bash
bun run src/main.ts --self-test --pipeline literature
```

Configuration merges `pipeline`, `sourceMode`, `liveRetrieval`, and related keys from `~/.config/deepresearch-tui/tui-config.json`.

### Hypothesis → literature dataset (combined pipeline)

Run evidence-grounded hypothesis generation, then **one critical literature review per hypothesis** (capped). Output JSONL ends with `hypothesis_literature_chain_completed`, including **`literature_review_dataset`** (`LiteratureReviewDataset`) and **`hypothesis_dataset`**.

```bash
uv run python -m DeepResearch.scripts.run_hypothesis_literature_pipeline \
  --question "Your research question" --model gpt-4o-mini \
  -- --lit-max-lit-reviews 3 --lit-source-mode pubmed
```

Console script: `deepresearch-hypothesis-literature`. Literature options use the `--lit-*` prefix and should follow an optional `--` separator (see script docstring).

OpenTUI: `--pipeline hypothesis-literature`.

### Web search mode (`source_mode=web`)

Chunked web search uses Serper; set **`SERPER_API_KEY`** in the environment when using live web retrieval.

## Routing note

When both `flows.literature_review.enabled` and `workflow_orchestration.enabled` are true in Hydra, the main graph **prefers the literature review branch** first; a note is appended to workflow state when both are enabled.
