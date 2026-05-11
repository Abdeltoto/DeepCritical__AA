import type { PersistedTuiConfig } from "../config";
import type { PipelineEvent, PipelineMode } from "../types";

export type ScreenId = "setup" | "running" | "result" | "error";

export type FocusId =
  | "setup"
  | "evidence"
  | "hypotheses"
  | "literature"
  | "chain"
  | "log"
  | "result";

export type AppState = {
  screen: ScreenId;
  pipeline: PipelineMode;
  question: string;
  cfg: PersistedTuiConfig;
  focus: FocusId;
  events: PipelineEvent[];
  startedAtMs: number;
  errorMessage?: string;
  exitCode?: number | null;
  derived: {
    completedDataset?: Record<string, unknown> | null;
    literatureMarkdown?: string | null;
    chainSummary?: string | null;
  };
};

export function buildInitialState(cfg: PersistedTuiConfig): AppState {
  const pipeline = cfg.run.pipeline ?? "hypothesis";
  return {
    screen: "setup",
    pipeline,
    question: cfg.run.question ?? "",
    cfg,
    focus: "setup",
    events: [],
    startedAtMs: Date.now(),
    derived: {},
  };
}
