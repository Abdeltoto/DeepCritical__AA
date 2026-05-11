import type { PipelineEvent } from "../types";

export function hypothesisLinesFromEvents(events: PipelineEvent[]): string[] {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i]!;
    if (ev.event_type === "proposer_completed" && ev.statements?.length) {
      return ev.statements.map((s, j) => `${j + 1}. ${s}`);
    }
  }
  return [];
}
