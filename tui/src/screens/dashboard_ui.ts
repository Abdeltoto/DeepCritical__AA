import type { EndpointConfig, PipelineEvent, PipelineMode } from "../types";
import { evidenceLinesFromEvents } from "../components/evidence_panel";
import { formatEventLine } from "../components/event_log";
import { hypothesisLinesFromEvents } from "../components/hypotheses_list";
import { formatStatusBar } from "../components/status_bar";
import { theme } from "../ui/theme";
import type { FocusId } from "../ui/state";

type Otui = typeof import("@opentui/core");

function panel(
  otui: Otui,
  title: string,
  body: string,
  opts?: {
    width?: number | `${number}%` | "auto";
    height?: number | `${number}%` | "auto";
    focused?: boolean;
  },
) {
  const { Box, Text } = otui;
  return Box(
    {
      borderStyle: theme.borderStyle,
      borderColor: opts?.focused ? theme.fg.accent : theme.fg.muted,
      flexDirection: "column",
      padding: 1,
      gap: 1,
      width: opts?.width,
      height: opts?.height,
    },
    Text({ content: title, fg: theme.fg.accent }),
    Text({ content: body || "(empty)", fg: theme.fg.text }),
  );
}

function tailLines(events: PipelineEvent[], n: number): string {
  return events
    .slice(-n)
    .map(formatEventLine)
    .join("\n");
}

function sliceFromBottom(text: string, maxLines: number, offsetLines: number): string {
  const lines = (text || "").split("\n");
  const end = Math.max(0, lines.length - Math.max(0, offsetLines));
  const start = Math.max(0, end - Math.max(1, maxLines));
  return lines.slice(start, end).join("\n");
}

function chainLines(events: PipelineEvent[]): string {
  return events
    .filter(
      (e) =>
        typeof e.event_type === "string" &&
        e.event_type.startsWith("hypothesis_literature_"),
    )
    .slice(-30)
    .map(formatEventLine)
    .join("\n");
}

function literatureStageLines(events: PipelineEvent[]): string {
  return events
    .filter((e) =>
      [
        "literature_review_started",
        "literature_review_stage",
        "literature_review_stage_completed",
        "literature_review_llm_started",
        "literature_review_llm_completed",
        "literature_review_completed",
        "literature_review_error",
      ].includes(e.event_type),
    )
    .slice(-40)
    .map(formatEventLine)
    .join("\n");
}

export async function renderDashboardUi(args: {
  endpoint: EndpointConfig;
  question: string;
  events: PipelineEvent[];
  startedAtMs: number;
  errorMessage?: string;
  pipeline: PipelineMode;
  focus: FocusId;
  scroll: {
    evidence: number;
    hypotheses: number;
    literature: number;
    chain: number;
    log: number;
  };
}) {
  const otui = await import("@opentui/core");
  const { Box, Text } = otui;
  const elapsed = (Date.now() - args.startedAtMs) / 1000;
  const header = formatStatusBar(args.endpoint, args.question, elapsed);

  const evi = evidenceLinesFromEvents(args.events).join("\n");
  const hyps = hypothesisLinesFromEvents(args.events).join("\n");
  const log = tailLines(args.events, 18);
  const litStages = literatureStageLines(args.events);
  const chain = args.pipeline === "hypothesis-literature" ? chainLines(args.events) : "";
  const err = args.errorMessage ? `\n\nERROR: ${args.errorMessage}` : "";

  const leftTop = panel(
    otui,
    "Evidence",
    sliceFromBottom(evi || "(no evidence yet)", 12, args.scroll.evidence),
    { focused: args.focus === "evidence" },
  );
  const leftMid = panel(
    otui,
    "Hypotheses",
    sliceFromBottom(hyps || "(waiting)", 14, args.scroll.hypotheses),
    { focused: args.focus === "hypotheses" },
  );
  const leftBottom =
    args.pipeline === "hypothesis-literature"
      ? panel(
          otui,
          "Hypothesis → literature",
          sliceFromBottom(chain || "(starting)", 12, args.scroll.chain),
          { focused: args.focus === "chain" },
        )
      : panel(otui, "Notes", "Press x to stop, q to quit.");

  const rightTop = panel(
    otui,
    "Literature",
    sliceFromBottom(litStages || "(not started)", 18, args.scroll.literature),
    { focused: args.focus === "literature" },
  );
  const rightBottom = panel(
    otui,
    "Log",
    sliceFromBottom((log || "(no events)") + err, 14, args.scroll.log),
    { focused: args.focus === "log" },
  );

  return Box(
    { flexDirection: "column", gap: 1, padding: 1 },
    Text({ content: header, fg: theme.fg.text }),
    Box(
      { flexDirection: "row", gap: 1 },
      Box(
        { flexDirection: "column", gap: 1, width: "60%" },
        leftTop,
        leftMid,
        leftBottom,
      ),
      Box(
        { flexDirection: "column", gap: 1, width: "40%" },
        rightTop,
        rightBottom,
      ),
    ),
  );
}
