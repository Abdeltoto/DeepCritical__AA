import type { PipelineEvent } from "../types";
import { formatEventLine } from "./event_log";

export type LiteratureProgress = {
  stage?: string;
  nUnique?: number;
  nIncluded?: number;
  nExcluded?: number;
  llmMode?: string;
};

export function deriveLiteratureProgress(events: PipelineEvent[]): LiteratureProgress {
  const out: LiteratureProgress = {};
  for (const ev of events) {
    if (ev.event_type === "literature_review_stage") {
      out.stage = ev.stage;
    }
    if (ev.event_type === "literature_review_stage_completed") {
      out.stage = ev.stage;
      if (ev.n_unique != null) out.nUnique = ev.n_unique;
      if (ev.n_included != null) out.nIncluded = ev.n_included;
      if (ev.n_excluded != null) out.nExcluded = ev.n_excluded;
    }
    if (ev.event_type === "literature_review_llm_completed") {
      out.llmMode = ev.synthesis_mode;
    }
  }
  return out;
}

export function tailEventLines(events: PipelineEvent[], n: number): string[] {
  return events.slice(-n).map(formatEventLine);
}
