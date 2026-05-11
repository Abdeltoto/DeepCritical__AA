import type { EndpointConfig, PipelineEvent, PipelineMode } from "../types";
import { theme } from "../ui/theme";
import { formatEventLine } from "../components/event_log";

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
    Text({ content: body || "(empty)", fg: theme.fg.text }),
  );
}

function tail(events: PipelineEvent[], n: number): string {
  return events
    .slice(-n)
    .map(formatEventLine)
    .join("\n");
}

export async function renderResultUi(args: {
  endpoint: EndpointConfig;
  question: string;
  pipeline: PipelineMode;
  events: PipelineEvent[];
  dataset: Record<string, unknown> | null;
  literatureMarkdown: string | null;
  chainSummary: string | null;
  savePath?: string | null;
}) {
  const otui = await import("@opentui/core");
  const { Box, Text } = otui;

  const header = Text({
    content: `DeepCritical · Result  pipeline=${args.pipeline}  Q=${args.question.slice(0, 80)}`,
    fg: theme.fg.text,
  });

  const leftBody = args.dataset
    ? JSON.stringify(args.dataset, null, 2).slice(0, 6000)
    : "(no dataset)";
  const rightBody =
    args.chainSummary || args.literatureMarkdown || "(no markdown output)";

  const left = panel(otui, "Dataset / Payload (preview)", leftBody);
  const right = panel(otui, "Report / Summary", rightBody);
  const log = panel(otui, "Log (tail)", tail(args.events, 30));

  const footer = Text({
    content:
      `Keys: q quit | s save-json (dataset only) | x stop\n` +
      (args.savePath ? `Saved: ${args.savePath}` : ""),
    fg: theme.fg.muted,
  });

  return Box(
    { flexDirection: "column", gap: 1, padding: 1 },
    header,
    Box({ flexDirection: "row", gap: 1 }, left, right),
    log,
    footer,
  );
}
