"""Literature retrieval fails clearly when PubMed adapter raises."""

from __future__ import annotations

from unittest.mock import patch

from DeepResearch.src.tools.bioinformatics_tools import pubmed_paper_retriever
from DeepResearch.src.tools.literature_review_tools import LiteratureRetrievalTool


def test_pubmed_outcome_reports_transport_error():
    with patch(
        "DeepResearch.src.tools.bioinformatics_tools.requests.get",
        side_effect=OSError("network down"),
    ):
        out = pubmed_paper_retriever("x", max_results=5)
        assert out.error is not None
        assert not out.papers


def test_literature_retrieval_pubmed_mode_fails_on_adapter_error():
    tool = LiteratureRetrievalTool()
    with patch(
        "DeepResearch.src.tools.literature_review_tools.PubMedLiteratureAdapter.retrieve",
        side_effect=RuntimeError("PubMed adapter failed"),
    ):
        res = tool.run(
            {
                "question": "test query",
                "source_mode": "pubmed",
                "live_retrieval_enabled": True,
                "max_sources": 5,
                "search_plan": {"queries": ["test query"], "source_mode": "pubmed"},
            }
        )
    assert res.success is False
    assert res.error is not None
    assert "PubMedLiteratureAdapter" in res.error
