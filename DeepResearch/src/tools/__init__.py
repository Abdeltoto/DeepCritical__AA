"""DeepResearch tool package.

This package historically imported all tool modules eagerly to auto-register them.
That caused heavy import-time side effects (e.g. initializing MCP servers) and made
the package fragile in environments where optional dependencies aren't available.

Use `register_all_tools()` to register the full tool suite explicitly.
"""

from __future__ import annotations

from .base import registry


def register_all_tools() -> None:
    """Explicitly import tool modules to trigger registration.

    Keep this list in dependency order (lightweight first).
    """

    from . import (
        analytics_tools,
        deepsearch_tools,
        deepsearch_workflow_tool,
        docker_sandbox,
        hypothesis_generation_tool,
        integrated_search_tools,
        mock_tools,
        pyd_ai_tools,
        rag_tools,
        websearch_cleaned,
        websearch_tools,
        workflow_tools,
    )

    # NOTE: bioinformatics tool registration pulls in large vendored MCP server
    # implementations. Import it only when specifically needed.
    # from . import bioinformatics_tools


def register_bioinformatics_tools() -> None:
    """Register bioinformatics tools (heavy import)."""

    from . import bioinformatics_tools


# Optional re-exports for documentation/introspection; keep them lazy to avoid
# import-time failures when optional deps are missing.
def __getattr__(name: str):
    if name in {"ChunkedSearchTool", "WebSearchTool"}:
        from .websearch_tools import (
            ChunkedSearchTool,
            WebSearchTool,
        )

        return {"ChunkedSearchTool": ChunkedSearchTool, "WebSearchTool": WebSearchTool}[
            name
        ]
    if name in {"DeepSearchTool"}:
        from .deepsearch_tools import DeepSearchTool

        return DeepSearchTool
    if name in {"RAGSearchTool"}:
        from .integrated_search_tools import RAGSearchTool

        return RAGSearchTool
    if name in {"GOAnnotationTool", "PubMedRetrievalTool"}:
        from .bioinformatics_tools import (
            GOAnnotationTool,
            PubMedRetrievalTool,
        )

        return {
            "GOAnnotationTool": GOAnnotationTool,
            "PubMedRetrievalTool": PubMedRetrievalTool,
        }[name]
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)


__all__ = [
    # Tool classes
    "ChunkedSearchTool",
    "DeepSearchTool",
    "GOAnnotationTool",
    "PubMedRetrievalTool",
    "RAGSearchTool",
    "WebSearchTool",
    # Registration helpers
    "register_all_tools",
    "register_bioinformatics_tools",
    "registry",
]
