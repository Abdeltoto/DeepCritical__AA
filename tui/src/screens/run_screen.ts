import type { EndpointConfig, PipelineEvent, PipelineMode } from "../types";
import { evidenceLinesFromEvents } from "../components/evidence_panel";
import { formatEventLine } from "../components/event_log";
import { hypothesisLinesFromEvents } from "../components/hypotheses_list";
import { formatStatusBar } from "../components/status_bar";

export interface RunUiState {
  events: PipelineEvent[];
  startedAt: number;
  errorMessage?: string;
}

function literatureStageLines(events: PipelineEvent[]): string {
  return events
    .filter((e) =>
      [
        "literature_review_started",
        "literature_review_stage",
        "literature_review_stage_completed",
        "literature_review_completed",
        "literature_review_error",
      ].includes(e.event_type),
    )
    .map(formatEventLine)
    .join("\n");
}

export function composeRunScreenText(
  endpoint: EndpointConfig,
  question: string,
  state: RunUiState,
  pipeline: PipelineMode = "hypothesis",
): string {
  const elapsed = (Date.now() - state.startedAt) / 1000;
  const header = formatStatusBar(endpoint, question, elapsed);

  const chainSteps =
    pipeline === "hypothesis-literature"
      ? state.events
          .filter(
            (e) =>
              typeof e.event_type === "string" &&
              e.event_type.startsWith("hypothesis_literature_"),
          )
          .map(formatEventLine)
          .join("\n")
      : "";

  if (pipeline === "literature") {
    const stages = literatureStageLines(state.events);
    const tail = state.events.slice(-10).map(formatEventLine).join("\n");
    const err = state.errorMessage ? `\n\nERROR: ${state.errorMessage}` : "";
    return [
      header,
      "",
      "— Literature review —",
      stages || "(starting)",
      "",
      "— Log —",
      tail + err,
    ].join("\n");
  }

  const evi =
    evidenceLinesFromEvents(state.events).join("\n") || "(no evidence metadata yet)";
  const hyps =
    hypothesisLinesFromEvents(state.events).join("\n") || "(waiting for proposer)";
  const critic = state.events
    .filter(
      (e) =>
        e.event_type === "critic_started" || e.event_type === "critic_completed",
    )
    .map(formatEventLine)
    .join("\n");
  const tail = state.events.slice(-8).map(formatEventLine).join("\n");
  const err = state.errorMessage ? `\n\nERROR: ${state.errorMessage}` : "";
  const chainBlock =
    pipeline === "hypothesis-literature"
      ? ["", "— Hypothesis → literature —", chainSteps || "(starting)"]
      : [];
  return [
    header,
    "",
    "— Evidence —",
    evi,
    "",
    "— Hypotheses —",
    hyps,
    "",
    "— Critic —",
    critic || "(none)",
    ...chainBlock,
    "",
    "— Log —",
    tail + err,
  ].join("\n");
}
