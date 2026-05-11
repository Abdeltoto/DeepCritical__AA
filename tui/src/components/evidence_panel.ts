import type { PipelineEvent } from "../types";

export function evidenceLinesFromEvents(events: PipelineEvent[]): string[] {
  const lines: string[] = [];
  for (const ev of events) {
    if (ev.event_type === "evidence_fetched") {
      lines.push(
        `chunks=${ev.chunk_count ?? "?"} degraded=${ev.evidence_degraded ?? false} chars=${ev.characters ?? "?"}`,
      );
    }
  }
  return lines.slice(-12);
}
