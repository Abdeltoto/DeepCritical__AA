import { spawn } from "node:child_process";
import readline from "node:readline";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { pipelineEventSchema, type PipelineEvent } from "./types";

export interface PipelineSpawnArgs {
  question: string;
  repoRoot: string;
  pythonArgv: string[];
  flags: string[];
}

export function resolveRepoRoot(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "..");
}

export function defaultPythonArgv(): string[] {
  const raw = process.env.PYTHON_BIN || "uv run python";
  return raw.trim().split(/\s+/);
}

export interface ExitInfo {
  code: number | null;
  stderrTail: string;
}

export function spawnPipeline(
  args: PipelineSpawnArgs,
  onEvent: (ev: PipelineEvent | { event_type: "tui:parse_error"; line: string; error: string }) => void,
): { kill: () => void; donePromise: Promise<ExitInfo> } {
  const stderrBuf: string[] = [];
  const proc = spawn(args.pythonArgv[0], [...args.pythonArgv.slice(1), ...args.flags], {
    cwd: args.repoRoot,
    env: { ...process.env },
    stdio: ["ignore", "pipe", "pipe"],
  });

  const rl = readline.createInterface({ input: proc.stdout! });
  rl.on("line", (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }
    try {
      const obj = JSON.parse(trimmed) as unknown;
      const parsed = pipelineEventSchema.safeParse(obj);
      if (!parsed.success) {
        onEvent({
          event_type: "tui:parse_error",
          line: trimmed,
          error: parsed.error.message,
        });
        return;
      }
      onEvent(parsed.data);
    } catch (e) {
      onEvent({
        event_type: "tui:parse_error",
        line: trimmed,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  });

  proc.stderr?.on("data", (ch: Buffer | string) => {
    const s = ch.toString();
    stderrBuf.push(s);
    if (stderrBuf.join("").length > 8000) {
      stderrBuf.shift();
    }
  });

  const kill = () => {
    proc.kill("SIGINT");
    setTimeout(() => {
      if (!proc.killed) {
        proc.kill("SIGKILL");
      }
    }, 3000);
  };

  const donePromise = new Promise<ExitInfo>((resolve) => {
    proc.on("close", (code) => {
      resolve({
        code,
        stderrTail: stderrBuf.slice(-12).join(""),
      });
    });
  });

  return { kill, donePromise };
}

export function buildCliFlags(
  endpoint: import("./types").EndpointConfig,
  run: import("./types").RunConfig,
): string[] {
  const flags = [
    "-m",
    "DeepResearch.scripts.run_llm_hypothesis_pipeline",
    "--question",
    run.question,
    "--model",
    endpoint.model,
    "--base-url",
    endpoint.baseUrl,
    "--temperature",
    String(endpoint.temperature),
    "--max-hypotheses",
    String(run.maxHypotheses),
    "--num-results",
    String(run.numResults),
    "--max-evidence-chars",
    "12000",
    "--propose-retries",
    String(run.proposeRetries),
    "--output-jsonl",
    "-",
  ];
  if (endpoint.apiKey) {
    flags.push("--api-key", endpoint.apiKey);
  }
  if (endpoint.modelRef) {
    flags.push("--model-ref", endpoint.modelRef);
  }
  if (run.enableCriticPass) {
    flags.push("--enable-critic-pass");
  }
  if (!run.enableEvidenceSynthesis) {
    flags.push("--no-enable-evidence-synthesis");
  }
  if (run.failOnEmptyOutput) {
    flags.push("--fail-on-empty-output");
  }
  if (run.failOnCriticDropAll) {
    flags.push("--fail-on-critic-drop-all");
  }
  if (run.extraDocumentTextPath) {
    flags.push("--extra-document-text-file", run.extraDocumentTextPath);
  }
  return flags;
}

export function buildLiteratureCliFlags(
  run: import("./types").RunConfig,
  endpoint?: import("./types").EndpointConfig,
): string[] {
  const flags = [
    "-m",
    "DeepResearch.scripts.run_literature_review_pipeline",
    "--question",
    run.question,
    "--source-mode",
    run.sourceMode ?? "pubmed",
    "--max-sources",
    String(run.maxSourcesLit ?? 12),
    "--max-queries",
    String(run.maxQueriesLit ?? 3),
    "--min-relevance",
    String(run.minRelevanceLit ?? 0.35),
    "--output-jsonl",
    "-",
  ];
  if (run.liveRetrieval) {
    flags.push("--live-retrieval");
  } else {
    flags.push("--no-live-retrieval");
  }
  if (run.fixturePath) {
    flags.push("--fixture-path", run.fixturePath);
  }
  if (run.yearMinLit != null && run.yearMinLit !== undefined) {
    flags.push("--year-min", String(run.yearMinLit));
  }
  if (run.strictScreeningLit) {
    flags.push("--strict-screening");
  } else {
    flags.push("--no-strict-screening");
  }
  if (run.excludeIrrelevantPhrasesLit) {
    flags.push("--exclude-irrelevant-phrases");
  } else {
    flags.push("--no-exclude-irrelevant-phrases");
  }
  if (run.llmSynthesisLit) {
    flags.push("--llm-synthesis");
    flags.push("--temperature", String(run.llmTemperatureLit ?? 0.35));
    flags.push("--max-evidence-chars", String(run.maxEvidenceCharsLit ?? 12000));
    if (run.llmFallbackOnErrorLit === false) {
      flags.push("--no-llm-fallback-on-error");
    }
    const model = run.llmModelLit?.trim() || endpoint?.model;
    if (model) {
      flags.push("--model", model);
    }
    const base = run.llmBaseUrlLit?.trim() || endpoint?.baseUrl;
    if (base) {
      flags.push("--base-url", base);
    }
    if (endpoint?.apiKey) {
      flags.push("--api-key", endpoint.apiKey);
    }
  } else {
    flags.push("--no-llm-synthesis");
  }
  return flags;
}

/** Hypothesis LLM → literature review per hypothesis (combined CLI). */
export function buildHypothesisLiteratureCliFlags(
  endpoint: import("./types").EndpointConfig,
  run: import("./types").RunConfig,
): string[] {
  const flags = buildCliFlags(endpoint, run);
  const idx = flags.indexOf("-m");
  if (idx >= 0 && flags[idx + 1]) {
    flags[idx + 1] = "DeepResearch.scripts.run_hypothesis_literature_pipeline";
  }
  const litTail = [
    "--",
    "--lit-max-lit-reviews",
    String(run.maxLitReviewsChain ?? 5),
    "--lit-source-mode",
    run.sourceMode ?? "pubmed",
    "--lit-max-sources",
    String(run.maxSourcesLit ?? 12),
    "--lit-max-queries",
    String(run.maxQueriesLit ?? 3),
    "--lit-min-relevance",
    String(run.minRelevanceLit ?? 0.35),
  ];
  if (run.liveRetrieval) {
    litTail.push("--lit-live-retrieval");
  } else {
    litTail.push("--no-lit-live-retrieval");
  }
  if (run.fixturePath) {
    litTail.push("--lit-fixture-path", run.fixturePath);
  }
  if (run.yearMinLit != null && run.yearMinLit !== undefined) {
    litTail.push("--lit-year-min", String(run.yearMinLit));
  }
  if (run.strictScreeningLit) {
    litTail.push("--lit-strict-screening");
  } else {
    litTail.push("--no-lit-strict-screening");
  }
  if (run.excludeIrrelevantPhrasesLit) {
    litTail.push("--lit-exclude-irrelevant-phrases");
  } else {
    litTail.push("--no-lit-exclude-irrelevant-phrases");
  }
  if (run.llmSynthesisLit) {
    litTail.push("--lit-llm-synthesis");
    litTail.push("--lit-llm-temperature", String(run.llmTemperatureLit ?? 0.35));
    litTail.push("--lit-max-evidence-chars", String(run.maxEvidenceCharsLit ?? 12000));
    if (run.llmFallbackOnErrorLit === false) {
      litTail.push("--no-lit-llm-fallback-on-error");
    }
    const model = run.llmModelLit?.trim() || endpoint.model;
    if (model) {
      litTail.push("--lit-llm-model", model);
    }
    const base = run.llmBaseUrlLit?.trim() || endpoint.baseUrl;
    if (base) {
      litTail.push("--lit-llm-base-url", base);
    }
    if (endpoint.apiKey) {
      litTail.push("--lit-llm-api-key", endpoint.apiKey);
    }
  } else {
    litTail.push("--no-lit-llm-synthesis");
  }
  return [...flags, ...litTail];
}

export function buildCliFlagsForPipeline(
  mode: import("./types").PipelineMode,
  endpoint: import("./types").EndpointConfig,
  run: import("./types").RunConfig,
): string[] {
  if (mode === "literature") {
    return buildLiteratureCliFlags(run, endpoint);
  }
  if (mode === "hypothesis-literature") {
    return buildHypothesisLiteratureCliFlags(endpoint, run);
  }
  return buildCliFlags(endpoint, run);
}
