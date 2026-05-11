import type { PersistedTuiConfig } from "../config";

export function formatSetupSummary(cfg: PersistedTuiConfig): string {
  const e = cfg.endpoint;
  const pipe = cfg.run.pipeline ?? "hypothesis";
  const lines = [
    "DeepCritical · OpenTUI — setup",
    `pipeline: ${pipe}${pipe === "hypothesis-literature" ? " (hypothesis → literature)" : ""}`,
    `baseUrl: ${e.baseUrl}`,
    `model: ${e.model}`,
    `modelRef: ${e.modelRef || "(none)"}`,
    `temperature: ${e.temperature}`,
    `apiKey: ${e.apiKey ? "(set)" : "(empty — set LLM_API_KEY or save config)"}`,
    "",
    "Run parameters:",
  ];
  if (pipe === "literature" || pipe === "hypothesis-literature") {
    lines.push(
      `sourceMode: ${cfg.run.sourceMode ?? "fixture"}`,
      `liveRetrieval: ${cfg.run.liveRetrieval ?? false}`,
      `maxSources: ${cfg.run.maxSourcesLit ?? 12}`,
      `maxQueries: ${cfg.run.maxQueriesLit ?? 3}`,
      `fixturePath: ${cfg.run.fixturePath ?? "(none)"}`,
      `llmSynthesis: ${cfg.run.llmSynthesisLit ?? false}`,
      `llmModel: ${cfg.run.llmModelLit ?? "(use endpoint.model)"}`,
      `llmTemperature: ${cfg.run.llmTemperatureLit ?? 0.35}`,
    );
    if (pipe === "hypothesis-literature") {
      lines.push(`maxLitReviews (chain): ${cfg.run.maxLitReviewsChain ?? 5}`);
    }
  } else {
    lines.push(
      `maxHypotheses: ${cfg.run.maxHypotheses}`,
      `enableCriticPass: ${cfg.run.enableCriticPass}`,
      `enableEvidenceSynthesis: ${cfg.run.enableEvidenceSynthesis}`,
    );
  }
  return lines.join("\n");
}
