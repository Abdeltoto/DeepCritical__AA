import type { PersistedTuiConfig } from "../config";
import type { PipelineMode } from "../types";
import { theme } from "../ui/theme";

type Otui = typeof import("@opentui/core");

function panel(otui: Otui, title: string, body: string) {
  const { Box, Text } = otui;
  return Box(
    {
      borderStyle: theme.borderStyle,
      borderColor: theme.fg.muted,
      flexDirection: "column",
      padding: 1,
      gap: 1,
    },
    Text({ content: title, fg: theme.fg.accent }),
    Text({ content: body, fg: theme.fg.text }),
  );
}

function buildWarnings(cfg: PersistedTuiConfig): string[] {
  const warnings: string[] = [];
  const pipe = cfg.run.pipeline ?? "hypothesis";
  if (!cfg.endpoint.apiKey && pipe !== "literature") {
    warnings.push("LLM_API_KEY is empty (hypothesis pipeline will likely fail).");
  }
  if (pipe === "literature" || pipe === "hypothesis-literature") {
    const mode = cfg.run.sourceMode ?? "pubmed";
    const live = cfg.run.liveRetrieval ?? true;
    if (!live && mode !== "fixture") {
      warnings.push("liveRetrieval=false requires sourceMode=fixture.");
    }
    if (mode === "fixture" && !cfg.run.fixturePath) {
      warnings.push("fixturePath is empty (fixture mode needs a JSON file).");
    }
    if (mode === "web" && !process.env.SERPER_API_KEY) {
      warnings.push("SERPER_API_KEY not set (web retrieval will fail).");
    }
  }
  return warnings;
}

function formatConfigSummary(cfg: PersistedTuiConfig): string {
  const e = cfg.endpoint;
  const pipe = cfg.run.pipeline ?? "hypothesis";
  const parts = [
    `pipeline: ${pipe}`,
    `endpoint: ${e.baseUrl}`,
    `model: ${e.model}`,
    `modelRef: ${e.modelRef || "(none)"}`,
    `temperature: ${e.temperature}`,
    `apiKey: ${e.apiKey ? "(set)" : "(empty)"}`,
  ];
  if (pipe === "literature" || pipe === "hypothesis-literature") {
    parts.push(
      "",
      "Literature params:",
      `sourceMode: ${cfg.run.sourceMode ?? "pubmed"}`,
      `liveRetrieval: ${cfg.run.liveRetrieval ?? true}`,
      `maxSources: ${cfg.run.maxSourcesLit ?? 12}`,
      `maxQueries: ${cfg.run.maxQueriesLit ?? 3}`,
      `llmSynthesis: ${cfg.run.llmSynthesisLit ?? false}`,
    );
  } else {
    parts.push(
      "",
      "Hypothesis params:",
      `maxHypotheses: ${cfg.run.maxHypotheses}`,
      `numResults: ${cfg.run.numResults}`,
      `enableCriticPass: ${cfg.run.enableCriticPass}`,
    );
  }
  return parts.join("\n");
}

export async function renderSetupUi(args: {
  cfg: PersistedTuiConfig;
  optsPipeline?: string;
}): Promise<{ node: any; pipeline: PipelineMode }> {
  const otui = await import("@opentui/core");
  const { Box, Text } = otui;

  // “Guided” mode fallback: we show a structured setup screen with warnings and
  // clear instructions. If @opentui/core exposes Input/Select, we can upgrade later.
  const pipeline = (args.cfg.run.pipeline ?? "hypothesis") as PipelineMode;
  const warnings = buildWarnings(args.cfg);

  const left = panel(
    otui,
    "Setup",
    [
      "Press Enter to start.",
      "Press q to quit.",
      "Press x to stop a running pipeline.",
      "",
      "To change settings, edit:",
      "~/.config/deepresearch-tui/tui-config.json",
      "or tui/.env",
    ].join("\n"),
  );

  const right = panel(otui, "Configuration", formatConfigSummary(args.cfg));

  const warnPanel = panel(
    otui,
    "Warnings",
    warnings.length ? warnings.map((w) => `- ${w}`).join("\n") : "(none)",
  );

  const header = Text({ content: "DeepCritical · OpenTUI", fg: theme.fg.text });

  const node = Box(
    { flexDirection: "column", gap: 1, padding: 1 },
    header,
    Box({ flexDirection: "row", gap: 1 }, left, right),
    warnPanel,
  );

  return { node, pipeline };
}
