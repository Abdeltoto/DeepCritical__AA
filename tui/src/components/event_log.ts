import type { PipelineEvent } from "../types";

export function formatEventLine(ev: PipelineEvent): string {
  switch (ev.event_type) {
    case "evidence_fetched": {
      return `${ev.event_type}: chunks=${ev.chunk_count ?? "?"} degraded=${ev.evidence_degraded ?? false} chars=${ev.characters ?? "?"}`;
    }
    case "proposer_completed": {
      return `${ev.event_type}: n=${ev.n_candidates ?? (ev.statements?.length ?? "?")}`;
    }
    case "critic_completed": {
      const kept = ev.kept_count ?? "?";
      const dropped = ev.dropped_indices?.length ?? 0;
      const invalid = ev.invalid_indices?.length ?? 0;
      const all = ev.critic_dropped_all ? " all_dropped" : "";
      return `${ev.event_type}: kept=${kept} dropped=${dropped} invalid=${invalid}${all}`;
    }
    case "literature_review_stage_completed": {
      const parts = [ev.stage];
      if (ev.n_candidates != null) parts.push(`n=${ev.n_candidates}`);
      if (ev.n_unique != null) parts.push(`uniq=${ev.n_unique}`);
      if (ev.n_included != null) parts.push(`in=${ev.n_included}`);
      if (ev.n_excluded != null) parts.push(`out=${ev.n_excluded}`);
      return `${ev.event_type}: ${parts.join(" ")}`;
    }
    case "literature_review_llm_started":
      return `${ev.event_type}: ${ev.model_preview ?? ""}`.trim();
    case "literature_review_llm_completed":
      return `${ev.event_type}: ok=${ev.ok ?? "?"} mode=${ev.synthesis_mode ?? "?"}`;
    case "literature_review_completed": {
      const tr = ev.markdown_truncated ? "truncated" : "full";
      return `${ev.event_type}: ${ev.status} (${tr}, ${ev.markdown_total_chars ?? 0} chars)`;
    }
    case "literature_review_error":
      return `${ev.event_type}: [${ev.stage}] ${ev.message}`;
    case "hypothesis_literature_chain_started":
      return `${ev.event_type}: max_lit_reviews=${ev.max_lit_reviews ?? "?"}`;
    case "hypothesis_literature_hypothesis_phase_completed":
      return `${ev.event_type}: hypotheses=${ev.hypothesis_count ?? "?"}`;
    case "hypothesis_literature_review_started":
      return `${ev.event_type}: idx=${ev.hypothesis_index ?? "?"}`;
    case "hypothesis_literature_review_completed":
      return `${ev.event_type}: idx=${ev.hypothesis_index ?? "?"} status=${ev.status ?? "?"}`;
    case "hypothesis_literature_chain_completed":
      return `${ev.event_type}: status=${ev.status ?? "?"}`;
    default:
      return `${ev.event_type}`;
  }
}
