import type { PipelineEvent } from "../types";

export function hypothesisLiteratureSummaryFromEvents(
  events: PipelineEvent[],
): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i]!;
    if (ev.event_type !== "hypothesis_literature_chain_completed") {
      continue;
    }
    const rec = ev as {
      status?: string;
      literature_review_dataset?: { entries?: unknown[] };
      hypothesis_dataset?: { hypotheses?: unknown[] };
      metadata?: Record<string, unknown>;
    };
    const he = Array.isArray(rec.hypothesis_dataset?.hypotheses)
      ? rec.hypothesis_dataset!.hypotheses!.length
      : 0;
    const le = Array.isArray(rec.literature_review_dataset?.entries)
      ? rec.literature_review_dataset!.entries!.length
      : 0;
    const meta = rec.metadata ?? {};
    const elapsed =
      typeof meta.elapsed_seconds === "number"
        ? `\nElapsed: ${meta.elapsed_seconds.toFixed(1)}s`
        : "";
    return `# Hypothesis → literature chain\n\nstatus: ${rec.status ?? "?"}\nhypotheses: ${he}\nliterature runs: ${le}${elapsed}`;
  }
  return null;
}

export function literatureMarkdownFromEvents(events: PipelineEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i]!;
    if (ev.event_type === "literature_review_completed") {
      const prev = typeof ev.markdown_preview === "string" ? ev.markdown_preview : "";
      const suf =
        ev.markdown_truncated && ev.markdown_total_chars
          ? `\n\n… (${ev.markdown_total_chars} chars total; preview truncated in JSONL)`
          : "";
      return prev ? `${prev}${suf}` : null;
    }
  }
  return null;
}

export function formatResultScreen(dataset: Record<string, unknown>): string {
  const hyps = Array.isArray(dataset.hypotheses)
    ? (dataset.hypotheses as Record<string, unknown>[])
    : [];
  const blocks = hyps.map((h, i) => {
    const st = typeof h.statement === "string" ? h.statement : JSON.stringify(h);
    const conf = typeof h.confidence === "number" ? h.confidence.toFixed(2) : "?";
    const typ = typeof h.hypothesis_type === "string" ? h.hypothesis_type : "";
    return `${i + 1}. [${typ}] (c=${conf})\n${st}`;
  });
  return [`# ${dataset.name || "Dataset"}`, "", ...blocks].join("\n");
}

export function datasetFromCompletedEvent(ev: PipelineEvent): Record<string, unknown> | null {
  if (ev.event_type !== "pipeline_completed") {
    return null;
  }
  const ds = (ev as { dataset?: unknown }).dataset;
  return typeof ds === "object" && ds !== null ? (ds as Record<string, unknown>) : null;
}
