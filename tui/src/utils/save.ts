import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export function saveJsonRun(
  repoRoot: string,
  dataset: Record<string, unknown>,
): string {
  const dir = join(repoRoot, "hypothesis_runs", `${Date.now()}`);
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "dataset.json");
  writeFileSync(path, JSON.stringify(dataset, null, 2), "utf-8");
  return path;
}

export function saveMarkdownRun(
  repoRoot: string,
  dataset: Record<string, unknown>,
): string {
  const dir = join(repoRoot, "hypothesis_runs", `${Date.now()}`);
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "dataset.md");
  const hyps = Array.isArray(dataset.hypotheses)
    ? (dataset.hypotheses as Record<string, unknown>[])
    : [];
  const lines = hyps.map((h, i) => {
    const stmt = typeof h.statement === "string" ? h.statement : JSON.stringify(h);
    return `### ${i + 1}\n\n${stmt}\n`;
  });
  const md = `# ${dataset.name || "Hypotheses"}\n\n${dataset.description || ""}\n\n${lines.join("\n")}`;
  writeFileSync(path, md, "utf-8");
  return path;
}

export function ensureHypothesisRunsDir(repoRoot: string): void {
  const p = join(repoRoot, "hypothesis_runs");
  if (!existsSync(p)) {
    mkdirSync(p, { recursive: true });
  }
}
