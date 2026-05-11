"""
Prompts for optional LLM-backed literature synthesis (grounded in workflow evidence only).
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_LITERATURE_SYNTHESIS_LLM = """
You are an expert systematic reviewer producing a critical synthesis of literature.

Rules:
- Ground every substantive claim in the provided evidence JSON only. Do not invent studies,
  PMIDs, DOIs, titles, or results that are not present in the payload.
- If evidence is thin or conflicting, say so explicitly.
- Produce structured consensus findings, conflicting findings, themes, limitations, and gaps.
- The markdown_report must be a coherent critical literature review section (headings optional)
  that references sources by source_id where appropriate; do not fabricate citations.
""".strip()


def build_literature_synthesis_user_prompt(evidence_payload: dict[str, Any]) -> str:
    """Serialize the packed evidence payload as the user message for the synthesis agent."""

    body = json.dumps(evidence_payload, indent=2, default=str, ensure_ascii=False)
    return (
        "Synthesize the following literature review evidence. "
        "Respond with structured synthesis and markdown_report per your instructions.\n\n"
        f"{body}"
    )


__all__ = [
    "SYSTEM_LITERATURE_SYNTHESIS_LLM",
    "build_literature_synthesis_user_prompt",
]
