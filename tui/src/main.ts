/**
 * OpenTUI demo: streams JSONL from hypothesis or literature review pipeline.
 *
 * Usage:
 *   bun install && bun run src/main.ts [--question "..." ] [--pipeline hypothesis|literature] [--self-test]
 */

import { parseArgs } from "node:util";

import { defaultQuestion, loadConfig, saveConfig } from "./config";
import {
  buildCliFlagsForPipeline,
  defaultPythonArgv,
  resolveRepoRoot,
  spawnPipeline,
} from "./python_runner";
import {
  datasetFromCompletedEvent,
  hypothesisLiteratureSummaryFromEvents,
  literatureMarkdownFromEvents,
} from "./screens/result_screen";
import type { PipelineEvent, PipelineMode, RunConfig } from "./types";
import { ensureHypothesisRunsDir, saveJsonRun } from "./utils/save";
import { renderDashboardUi } from "./screens/dashboard_ui";
import type { AppState } from "./ui/state";
import { buildInitialState } from "./ui/state";
import { mapKey } from "./ui/keys";
import { renderSetupUi } from "./screens/setup_ui";
import { renderResultUi } from "./screens/result_ui";
import readline from "node:readline";

function parseCli(argv: string[]) {
  const { values } = parseArgs({
    args: argv,
    options: {
      question: { type: "string" },
      pipeline: { type: "string" },
      "self-test": { type: "boolean", default: false },
      save: { type: "boolean", default: false },
      "save-with-key": { type: "boolean", default: false },
    },
    strict: true,
    allowPositionals: false,
  });
  return values;
}

async function safeBindKeys(
  renderer: any,
  onKey: (ev: any) => void,
): Promise<boolean> {
  const root = renderer?.root;
  const candidate = root?.onKeyPress || root?.onKey || renderer?.onKeyPress || renderer?.onKey;
  if (typeof candidate === "function") {
    try {
      candidate.call(root ?? renderer, onKey);
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

function bindStdinKeys(onKey: (ev: any) => void): void {
  try {
    readline.emitKeypressEvents(process.stdin);
    if (process.stdin.isTTY) {
      process.stdin.setRawMode(true);
    }
    process.stdin.on("keypress", (_str, key) => {
      onKey({ ...key, key: key?.name });
    });
  } catch {
    /* ignore */
  }
}

function clearRoot(root: any): void {
  // Try known APIs first.
  try {
    root?.removeAllChildren?.();
    return;
  } catch {
    /* ignore */
  }
  // Try `children` + `remove(child)` patterns.
  const children: any[] | undefined = root?.children || root?._children;
  if (Array.isArray(children) && typeof root?.remove === "function") {
    for (const ch of [...children]) {
      try {
        root.remove(ch);
      } catch {
        /* ignore */
      }
    }
    return;
  }
  // Try child-level remove.
  if (Array.isArray(children)) {
    for (const ch of [...children]) {
      try {
        ch?.remove?.();
      } catch {
        /* ignore */
      }
    }
  }
}

async function runSelfTest(pipeline: PipelineMode): Promise<void> {
  const { createCliRenderer, Box, Text } = await import("@opentui/core");
  const renderer = await createCliRenderer({ exitOnCtrlC: true });
  const events: PipelineEvent[] = [];
  const fakeHypothesis: PipelineEvent[] = [
    { event_type: "pipeline_started", question_preview: "demo", max_hypotheses: 3 },
    { event_type: "evidence_fetch_started" },
    {
      event_type: "evidence_fetched",
      evidence_degraded: false,
      chunk_count: 2,
      characters: 1200,
    },
    { event_type: "proposer_started" },
    {
      event_type: "proposer_completed",
      n_candidates: 1,
      statements: ["Self-test hypothesis statement."],
    },
    { event_type: "dedupe_applied", hypotheses_truncated: false },
    {
      event_type: "pipeline_completed",
      dataset: { name: "demo", hypotheses: [] },
      metadata: {},
    },
  ];
  const fakeHypothesisLiterature: PipelineEvent[] = [
    ...fakeHypothesis.slice(0, -1),
    {
      event_type: "hypothesis_literature_chain_started",
      parent_question_preview: "demo",
      max_lit_reviews: 3,
    },
    {
      event_type: "hypothesis_literature_hypothesis_phase_completed",
      hypothesis_count: 1,
      dataset_name: "demo",
    },
    {
      event_type: "hypothesis_literature_review_started",
      hypothesis_index: 0,
      review_question_preview: "Critical literature review…",
    },
    {
      event_type: "hypothesis_literature_review_completed",
      hypothesis_index: 0,
      status: "success",
    },
    {
      event_type: "hypothesis_literature_chain_completed",
      status: "success",
      literature_review_dataset: {
        entries: [
          {
            hypothesis_index: 0,
            hypothesis_statement: "Self-test hypothesis statement.",
            status: "success",
          },
        ],
      },
      hypothesis_dataset: {
        hypotheses: [{ statement: "Self-test hypothesis statement." }],
      },
      metadata: { elapsed_seconds: 2.5 },
    },
  ];
  const fakeLiterature: PipelineEvent[] = [
    {
      event_type: "literature_review_started",
      question_preview: "demo",
      source_mode: "fixture",
      live_retrieval_enabled: false,
    },
    { event_type: "literature_review_stage", stage: "parse" },
    {
      event_type: "literature_review_stage_completed",
      stage: "parse",
    },
    {
      event_type: "literature_review_completed",
      status: "success",
      markdown_preview: "# Demo review\n\nFixture-mode preview.",
      markdown_total_chars: 40,
      markdown_truncated: false,
    },
  ];
  const fake =
    pipeline === "literature"
      ? fakeLiterature
      : pipeline === "hypothesis-literature"
        ? fakeHypothesisLiterature
        : fakeHypothesis;
  let idx = 0;
  const endpoint = loadConfig().endpoint;
  const question = "self-test question";
  const startedAtMs = Date.now();

  const tick = () => {
    if (idx < fake.length) {
      events.push(fake[idx]!);
      idx++;
    }
    const body = "self-test";
    try {
      clearRoot(renderer.root);
    } catch {
      /* ignore if API differs */
    }
    renderDashboardUi({
      endpoint,
      question,
      events,
      startedAtMs,
      pipeline,
      focus: "log",
      scroll: { evidence: 0, hypotheses: 0, literature: 0, chain: 0, log: 0 },
    })
      .then((node) => renderer.root.add(node))
      .catch(() =>
        renderer.root.add(
          Box(
            { flexDirection: "column", gap: 1, padding: 1 },
            Text({ content: body }),
          ),
        ),
      );
  };

  tick();
  const id = setInterval(() => {
    tick();
    if (idx >= fake.length) {
      clearInterval(id);
    }
  }, 400);
}

function resolvePipeline(
  optsPipeline: string | undefined,
  cfgPipeline: PipelineMode | undefined,
): PipelineMode {
  const o = optsPipeline?.toLowerCase();
  if (o === "literature") {
    return "literature";
  }
  if (o === "hypothesis-literature" || o === "hypothesis_literature") {
    return "hypothesis-literature";
  }
  if (o === "hypothesis") {
    return "hypothesis";
  }
  return cfgPipeline ?? "hypothesis";
}

async function main(): Promise<void> {
  const opts = parseCli(process.argv.slice(2));
  const cfg = loadConfig();
  const pipeline = resolvePipeline(opts.pipeline, cfg.run.pipeline);

  if (opts["self-test"]) {
    await runSelfTest(pipeline);
    return;
  }

  const repoRoot =
    process.env.DEEPRESEARCH_ROOT && process.env.DEEPRESEARCH_ROOT.length > 0
      ? process.env.DEEPRESEARCH_ROOT
      : resolveRepoRoot();
  ensureHypothesisRunsDir(repoRoot);

  const run: RunConfig = {
    pipeline,
    question: opts.question || cfg.run.question || defaultQuestion,
    maxHypotheses: cfg.run.maxHypotheses,
    numResults: cfg.run.numResults,
    enableCriticPass: cfg.run.enableCriticPass,
    enableEvidenceSynthesis: cfg.run.enableEvidenceSynthesis,
    proposeRetries: cfg.run.proposeRetries,
    failOnEmptyOutput: cfg.run.failOnEmptyOutput,
    failOnCriticDropAll: cfg.run.failOnCriticDropAll,
    extraDocumentTextPath: cfg.run.extraDocumentTextPath,
    sourceMode: cfg.run.sourceMode,
    fixturePath: cfg.run.fixturePath,
    liveRetrieval: cfg.run.liveRetrieval,
    maxSourcesLit: cfg.run.maxSourcesLit,
    maxQueriesLit: cfg.run.maxQueriesLit,
    minRelevanceLit: cfg.run.minRelevanceLit,
    yearMinLit: cfg.run.yearMinLit,
    strictScreeningLit: cfg.run.strictScreeningLit,
    excludeIrrelevantPhrasesLit: cfg.run.excludeIrrelevantPhrasesLit,
    llmSynthesisLit: cfg.run.llmSynthesisLit,
    llmModelLit: cfg.run.llmModelLit,
    llmBaseUrlLit: cfg.run.llmBaseUrlLit,
    llmTemperatureLit: cfg.run.llmTemperatureLit,
    maxEvidenceCharsLit: cfg.run.maxEvidenceCharsLit,
    llmFallbackOnErrorLit: cfg.run.llmFallbackOnErrorLit,
    maxLitReviewsChain: cfg.run.maxLitReviewsChain,
  };

  if (opts.save) {
    saveConfig(cfg, { includeApiKey: Boolean(opts["save-with-key"]) });
  }

  const { createCliRenderer, Box, Text } = await import("@opentui/core");
  const renderer = await createCliRenderer({ exitOnCtrlC: true });

  const state: AppState = buildInitialState(cfg);
  state.screen = "setup";
  state.pipeline = run.pipeline;
  state.question = run.question;
  state.startedAtMs = Date.now();
  state.focus = "log";
  let completedDataset: Record<string, unknown> | null = null;

  {
    const setup = await renderSetupUi({ cfg });
    try {
      clearRoot(renderer.root);
    } catch {
      /* optional */
    }
    renderer.root.add(setup.node);
  }

  let started = false;
  let proc: ReturnType<typeof spawnPipeline> | null = null;
  let lastSavePath: string | null = null;
  const focusOrder = [
    "evidence",
    "hypotheses",
    "chain",
    "literature",
    "log",
  ] as const;
  const scroll = {
    evidence: 0,
    hypotheses: 0,
    chain: 0,
    literature: 0,
    log: 0,
  };
  let resolveStarted: ((p: ReturnType<typeof spawnPipeline>) => void) | null = null;
  const startedPromise = new Promise<ReturnType<typeof spawnPipeline>>((resolve) => {
    resolveStarted = resolve;
  });

  const handleKey = (kev: any) => {
    const action = mapKey(kev);
    // Also allow scroll keys even when not mapped to an action.
    const k = (kev?.key || kev?.name || "").toLowerCase();
    const down = k === "down" || k === "arrowdown" || k === "j";
    const up = k === "up" || k === "arrowup" || k === "k";

    if (down || up) {
      const delta = down ? 1 : -1;
      const f = state.focus as keyof typeof scroll;
      if (f in scroll) {
        scroll[f] = Math.max(0, scroll[f] + delta);
      }
      if (started) {
        clearRoot(renderer.root);
        renderDashboardUi({
          endpoint: cfg.endpoint,
          question: run.question,
          events: state.events,
          startedAtMs: state.startedAtMs,
          errorMessage: state.errorMessage,
          pipeline: run.pipeline,
          focus: state.focus,
          scroll,
        }).then((node) => renderer.root.add(node));
      }
      return;
    }

    if (!action) return;
    if (action === "quit") {
      proc?.kill();
      return;
    }
    if (action === "stop") {
      proc?.kill();
      return;
    }
    if (action === "start" && !started) {
      started = true;
      state.screen = "running";
      state.startedAtMs = Date.now();
      state.events = [];
      state.errorMessage = undefined;
      completedDataset = null;

      const flags = buildCliFlagsForPipeline(run.pipeline, cfg.endpoint, run);
      proc = spawnPipeline(
        {
          question: run.question,
          repoRoot,
          pythonArgv: defaultPythonArgv(),
          flags,
        },
        (ev) => {
          if ("event_type" in ev && ev.event_type === "tui:parse_error") {
            state.errorMessage = (ev as { error: string }).error;
            return;
          }
          state.events.push(ev as PipelineEvent);
          if ((ev as PipelineEvent).event_type === "pipeline_completed") {
            completedDataset = datasetFromCompletedEvent(ev as PipelineEvent);
          }
          if ((ev as PipelineEvent).event_type === "pipeline_error") {
            const pe = ev as { message?: string };
            state.errorMessage = pe.message || "pipeline_error";
          }
          if ((ev as PipelineEvent).event_type === "literature_review_error") {
            const le = ev as { message?: string };
            state.errorMessage = le.message || "literature_review_error";
          }
          try {
            clearRoot(renderer.root);
          } catch {
            /* optional API */
          }
          renderDashboardUi({
            endpoint: cfg.endpoint,
            question: run.question,
            events: state.events,
            startedAtMs: state.startedAtMs,
            errorMessage: state.errorMessage,
            pipeline: run.pipeline,
            focus: state.focus,
            scroll,
          }).then((node) => renderer.root.add(node));
        },
      );
      resolveStarted?.(proc);
      // Draw initial dashboard immediately.
      clearRoot(renderer.root);
      renderDashboardUi({
        endpoint: cfg.endpoint,
        question: run.question,
        events: state.events,
        startedAtMs: state.startedAtMs,
        errorMessage: state.errorMessage,
        pipeline: run.pipeline,
        focus: state.focus,
        scroll,
      }).then((node) => renderer.root.add(node));
      return;
    }
    if (action === "focus_next" || action === "focus_prev") {
      const cur = focusOrder.indexOf(state.focus as any);
      const step = action === "focus_prev" ? -1 : 1;
      const next = (cur + step + focusOrder.length) % focusOrder.length;
      state.focus = focusOrder[next] as any;
      if (started) {
        clearRoot(renderer.root);
        renderDashboardUi({
          endpoint: cfg.endpoint,
          question: run.question,
          events: state.events,
          startedAtMs: state.startedAtMs,
          errorMessage: state.errorMessage,
          pipeline: run.pipeline,
          focus: state.focus,
          scroll,
        }).then((node) => renderer.root.add(node));
      }
    }
    if (action === "save" && completedDataset) {
      try {
        lastSavePath = saveJsonRun(repoRoot, completedDataset);
      } catch {
        /* ignore */
      }
    }
  };

  const bound = await safeBindKeys(renderer, handleKey);
  if (!bound) {
    // OpenTUI key handlers can vary by version; stdin fallback is reliable.
    bindStdinKeys(handleKey);
  }

  const startedProc = await startedPromise;
  const exit = await startedProc.donePromise;
  state.exitCode = exit.code;
  if (exit.code !== 0 && !state.errorMessage) {
    state.errorMessage = `exit ${exit.code}\n${exit.stderrTail}`;
  }

  const litMd = literatureMarkdownFromEvents(state.events);
  const chainSummary = hypothesisLiteratureSummaryFromEvents(state.events);
  if (completedDataset) {
    try {
      clearRoot(renderer.root);
    } catch {
      /* optional */
    }
    const node = await renderResultUi({
      endpoint: cfg.endpoint,
      question: run.question,
      pipeline: run.pipeline,
      events: state.events,
      dataset: completedDataset,
      literatureMarkdown: litMd,
      chainSummary,
      savePath: lastSavePath,
    });
    renderer.root.add(node);
    if (opts.save) {
      const p = saveJsonRun(repoRoot, completedDataset);
      process.stderr.write(`Saved: ${p}\n`);
    }
  } else if (chainSummary) {
    try {
      clearRoot(renderer.root);
    } catch {
      /* optional */
    }
    const node = await renderResultUi({
      endpoint: cfg.endpoint,
      question: run.question,
      pipeline: run.pipeline,
      events: state.events,
      dataset: null,
      literatureMarkdown: litMd,
      chainSummary,
      savePath: lastSavePath,
    });
    renderer.root.add(node);
  } else if (litMd) {
    try {
      clearRoot(renderer.root);
    } catch {
      /* optional */
    }
    const node = await renderResultUi({
      endpoint: cfg.endpoint,
      question: run.question,
      pipeline: run.pipeline,
      events: state.events,
      dataset: null,
      literatureMarkdown: litMd,
      chainSummary: null,
      savePath: lastSavePath,
    });
    renderer.root.add(node);
  }
}

await main();
