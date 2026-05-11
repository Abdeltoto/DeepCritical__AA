/**
 * JSONL events from hypothesis pipeline and literature review pipeline CLIs.
 */

import { z } from "zod";

const base = z.object({ event_type: z.string() });

export const pipelineEventSchema = z.discriminatedUnion("event_type", [
  base.extend({
    event_type: z.literal("pipeline_started"),
    question_preview: z.string().optional(),
    max_hypotheses: z.number().optional(),
  }),
  base.extend({ event_type: z.literal("evidence_fetch_started") }),
  base.extend({
    event_type: z.literal("evidence_fetched"),
    evidence_degraded: z.boolean().optional(),
    chunk_count: z.number().optional(),
    characters: z.number().optional(),
  }),
  base.extend({ event_type: z.literal("proposer_started") }),
  base.extend({
    event_type: z.literal("proposer_completed"),
    n_candidates: z.number().optional(),
    statements: z.array(z.string()).optional(),
  }),
  base.extend({ event_type: z.literal("critic_started") }),
  base.extend({
    event_type: z.literal("critic_completed"),
    kept_count: z.number().optional(),
    dropped_indices: z.array(z.number()).optional(),
    invalid_indices: z.array(z.number()).optional(),
    critic_dropped_all: z.boolean().optional(),
  }),
  base.extend({
    event_type: z.literal("dedupe_applied"),
    hypotheses_truncated: z.boolean().optional(),
  }),
  base.extend({
    event_type: z.literal("dataset_built"),
    dataset_name: z.string().optional(),
    n_hypotheses: z.number().optional(),
  }),
  base.extend({
    event_type: z.literal("pipeline_completed"),
    dataset: z.unknown().optional(),
    metadata: z.unknown().optional(),
  }).passthrough(),
  base.extend({
    event_type: z.literal("pipeline_error"),
    stage: z.string(),
    message: z.string(),
    detail: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_started"),
    question_preview: z.string().optional(),
    source_mode: z.string().optional(),
    live_retrieval_enabled: z.boolean().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_stage"),
    stage: z.string(),
  }),
  base.extend({
    event_type: z.literal("literature_review_stage_completed"),
    stage: z.string(),
    n_candidates: z.number().optional(),
    n_unique: z.number().optional(),
    n_included: z.number().optional(),
    n_excluded: z.number().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_completed"),
    status: z.string(),
    markdown_preview: z.string().optional(),
    markdown_total_chars: z.number().optional(),
    markdown_truncated: z.boolean().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_error"),
    stage: z.string(),
    message: z.string(),
    detail: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_llm_started"),
    model_preview: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("literature_review_llm_completed"),
    ok: z.boolean().optional(),
    synthesis_mode: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("hypothesis_literature_chain_started"),
    parent_question_preview: z.string().optional(),
    max_lit_reviews: z.number().optional(),
  }),
  base.extend({
    event_type: z.literal("hypothesis_literature_hypothesis_phase_completed"),
    hypothesis_count: z.number().optional(),
    dataset_name: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("hypothesis_literature_review_started"),
    hypothesis_index: z.number().optional(),
    review_question_preview: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("hypothesis_literature_review_completed"),
    hypothesis_index: z.number().optional(),
    status: z.string().optional(),
  }),
  base.extend({
    event_type: z.literal("hypothesis_literature_chain_completed"),
    status: z.string().optional(),
    literature_review_dataset: z.unknown().optional(),
    hypothesis_dataset: z.unknown().optional(),
    metadata: z.unknown().optional(),
  }).passthrough(),
]);

export type PipelineEvent = z.infer<typeof pipelineEventSchema>;

export type PipelineMode = "hypothesis" | "literature" | "hypothesis-literature";

export interface EndpointConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
  modelRef?: string;
  temperature: number;
}

export interface RunConfig {
  pipeline: PipelineMode;
  question: string;
  maxHypotheses: number;
  numResults: number;
  enableCriticPass: boolean;
  enableEvidenceSynthesis: boolean;
  proposeRetries: number;
  failOnEmptyOutput: boolean;
  failOnCriticDropAll: boolean;
  extraDocumentTextPath?: string;
  /** Literature pipeline (when pipeline === "literature") */
  sourceMode?: string;
  fixturePath?: string;
  liveRetrieval?: boolean;
  maxSourcesLit?: number;
  maxQueriesLit?: number;
  minRelevanceLit?: number;
  yearMinLit?: number | null;
  strictScreeningLit?: boolean;
  excludeIrrelevantPhrasesLit?: boolean;
  /** Optional LLM synthesis for literature pipeline */
  llmSynthesisLit?: boolean;
  llmModelLit?: string;
  llmBaseUrlLit?: string;
  llmTemperatureLit?: number;
  maxEvidenceCharsLit?: number;
  llmFallbackOnErrorLit?: boolean;
  /** Cap literature reviews in hypothesis-literature pipeline */
  maxLitReviewsChain?: number;
}
