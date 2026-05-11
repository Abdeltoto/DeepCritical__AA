# OpenTUI demo (hypothesis + literature review)

Terminal UI (Bun + `@opentui/core`) that runs DeepCritical Python pipelines via subprocess JSONL:

- **Hypothesis** (default): `DeepResearch.scripts.run_llm_hypothesis_pipeline`
- **Literature review**: `DeepResearch.scripts.run_literature_review_pipeline`
- **Hypothesis → literature (dataset)**: `DeepResearch.scripts.run_hypothesis_literature_pipeline`

## Prerequisites

- **Bun** (`https://bun.sh/`)
- **uv** / Python env with DeepCritical installed (`uv sync` from repo root)
- Hypothesis mode: optional `OPENAI_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (see `.env.example`)
- Literature mode with `source_mode=web`: **`SERPER_API_KEY`** for Serper-backed web search

## Setup

```bash
cd tui
cp .env.example .env   # optional
bun install
```

## Run

Self-test (no Python LLM calls — renders fake events):

```bash
bun run src/main.ts --self-test
bun run src/main.ts --self-test --pipeline literature
```

Hypothesis pipeline (default):

```bash
bun run src/main.ts --question "Your research question here"
```

Literature review pipeline:

```bash
bun run src/main.ts --pipeline literature --question "Your review question here"
```

Hypothesis generation followed by one PubMed literature review per hypothesis (defaults match Python CLI; override via `tui-config.json`):

```bash
bun run src/main.ts --pipeline hypothesis-literature --question "Your research question"
```

Persist merged config to `~/.config/deepresearch-tui/tui-config.json`:

```bash
bun run src/main.ts --question "..." --save
```

Add `--save-with-key` to persist API key (avoid sharing this file).

### Environment

| Variable | Purpose |
|----------|---------|
| `DEEPRESEARCH_ROOT` | Repo root for subprocess cwd (defaults to parent of `tui/`) |
| `PYTHON_BIN` | Override launcher (default `uv run python`) |
| `LLM_*` | Hypothesis pipeline LLM endpoint |
| `SERPER_API_KEY` | Web search when using literature `source_mode=web` |

### Outputs

Saved hypothesis runs go to `hypothesis_runs/<timestamp>/` under the repo root when using `--save`.

## Typecheck

```bash
bun run typecheck
```

## Troubleshooting

- **Native OpenTUI binary**: `@opentui/core` downloads a platform-specific native addon on install.
- **`removeAllChildren`**: If your OpenTUI version differs, adjust `src/main.ts` root clearing to match the renderer API.
- **Windows**: Use Git Bash or PowerShell; ensure `uv` is on `PATH`.
