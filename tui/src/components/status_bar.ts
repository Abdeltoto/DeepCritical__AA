import type { EndpointConfig } from "../types";

export function formatStatusBar(
  endpoint: EndpointConfig,
  question: string,
  elapsedSec: number,
): string {
  const url = endpoint.baseUrl.replace(/^https?:\/\//, "").slice(0, 48);
  return `model=${endpoint.model}  endpoint=${url}  t=${elapsedSec.toFixed(1)}s  Q=${question.slice(0, 60)}`;
}
