import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import { config as dotenvConfig } from "dotenv";

import type { EndpointConfig, PipelineMode, RunConfig } from "./types.ts";

const CONFIG_DIR = join(homedir(), ".config", "deepresearch-tui");
const CONFIG_FILE = "tui-config.json";

export interface PersistedTuiConfig {
  endpoint: EndpointConfig;
  run: Partial<RunConfig> & {
    pipeline?: PipelineMode;
    maxHypotheses: number;
    numResults: number;
    enableCriticPass: boolean;
    enableEvidenceSynthesis: boolean;
    proposeRetries: number;
    failOnEmptyOutput: boolean;
    failOnCriticDropAll: boolean;
    sourceMode?: string;
    fixturePath?: string;
    liveRetrieval?: boolean;
    maxSourcesLit?: number;
    maxQueriesLit?: number;
    minRelevanceLit?: number;
    yearMinLit?: number | null;
    strictScreeningLit?: boolean;
    excludeIrrelevantPhrasesLit?: boolean;
    llmSynthesisLit?: boolean;
    llmModelLit?: string;
    llmBaseUrlLit?: string;
    llmTemperatureLit?: number;
    maxEvidenceCharsLit?: number;
    llmFallbackOnErrorLit?: boolean;
    /** Hypothesis → literature chain (`pipeline: hypothesis-literature`) */
    maxLitReviewsChain?: number;
  };
}

function defaults(): PersistedTuiConfig {
  return {
    endpoint: {
      baseUrl: process.env.LLM_BASE_URL || "https://api.openai.com/v1",
      apiKey: process.env.LLM_API_KEY || "",
      model: process.env.LLM_MODEL || "gpt-4o-mini",
      modelRef: process.env.LLM_MODEL_REF || undefined,
      temperature: Number(process.env.LLM_TEMPERATURE || 0.4),
    },
    run: {
      pipeline: "hypothesis",
      question: "",
      maxHypotheses: 6,
      numResults: 4,
      enableCriticPass: false,
      enableEvidenceSynthesis: true,
      proposeRetries: 0,
      failOnEmptyOutput: false,
      failOnCriticDropAll: false,
      extraDocumentTextPath: undefined,
      sourceMode: "pubmed",
      fixturePath: undefined,
      liveRetrieval: true,
      maxSourcesLit: 12,
      maxQueriesLit: 3,
      minRelevanceLit: 0.35,
      yearMinLit: undefined,
      strictScreeningLit: false,
      excludeIrrelevantPhrasesLit: false,
      llmSynthesisLit: false,
      llmTemperatureLit: 0.35,
      maxEvidenceCharsLit: 12000,
      llmFallbackOnErrorLit: true,
      maxLitReviewsChain: 5,
    },
  };
}

function loadJsonFile(): Partial<PersistedTuiConfig> | null {
  const path = join(CONFIG_DIR, CONFIG_FILE);
  if (!existsSync(path)) {
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf-8")) as Partial<PersistedTuiConfig>;
  } catch {
    return null;
  }
}

export function loadConfig(): PersistedTuiConfig {
  dotenvConfig();
  const d = defaults();
  const fromFile = loadJsonFile();
  if (fromFile?.endpoint) {
    d.endpoint = { ...d.endpoint, ...fromFile.endpoint };
  }
  if (fromFile?.run) {
    d.run = { ...d.run, ...fromFile.run };
  }
  return d;
}

export function saveConfig(
  data: PersistedTuiConfig,
  opts: { includeApiKey: boolean },
): void {
  mkdirSync(CONFIG_DIR, { recursive: true });
  const toWrite: PersistedTuiConfig = {
    ...data,
    endpoint: { ...data.endpoint },
  };
  if (!opts.includeApiKey) {
    toWrite.endpoint.apiKey = "";
  }
  writeFileSync(
    join(CONFIG_DIR, CONFIG_FILE),
    JSON.stringify(toWrite, null, 2),
    "utf-8",
  );
}

export const defaultQuestion =
  "What testable mechanisms could explain the observed effect?";
