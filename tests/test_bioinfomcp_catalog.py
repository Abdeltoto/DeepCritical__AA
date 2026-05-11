from pathlib import Path

from omegaconf import OmegaConf

from DeepResearch.src.tools.base import registry
from DeepResearch.src.tools.bioinfomcp_catalog import (
    ISSUE_130_NUMBER,
    ISSUE_130_PUBLIC_TOOL_NAMES,
    get_issue_130_bioinfomcp_tool,
    issue_130_bioinfomcp_catalog_by_name,
    list_issue_130_bioinfomcp_tools,
    validate_issue_130_bioinfomcp_catalog,
)


def test_issue_130_catalog_contains_expected_tools():
    catalog = list_issue_130_bioinfomcp_tools()

    assert len(catalog) == 12
    assert tuple(tool.public_name for tool in catalog) == ISSUE_130_PUBLIC_TOOL_NAMES
    assert [tool.issue_number for tool in catalog] == list(range(131, 143))


def test_issue_130_catalog_validates_internal_consistency():
    is_valid, errors = validate_issue_130_bioinfomcp_catalog()

    assert is_valid, errors
    assert errors == []


def test_issue_130_catalog_supports_public_name_and_alias_lookup():
    assert get_issue_130_bioinfomcp_tool("bamCoverage").tool_method == (
        "deeptools_bam_coverage"
    )
    assert get_issue_130_bioinfomcp_tool("deeptools_bam_coverage").public_name == (
        "bamCoverage"
    )
    assert get_issue_130_bioinfomcp_tool("ApplyBQSR").public_name == ("gatk_ApplyBQSR")


def test_issue_130_catalog_matches_bioinformatics_config():
    cfg_path = Path("configs/bioinformatics/tools.yaml")
    cfg = OmegaConf.load(cfg_path)
    configured = cfg.bioinformatics_mcp_servers
    catalog = issue_130_bioinfomcp_catalog_by_name()

    assert configured.issue_number == ISSUE_130_NUMBER
    assert tuple(configured.enabled_tools) == ISSUE_130_PUBLIC_TOOL_NAMES
    assert set(configured.tools.keys()) == set(ISSUE_130_PUBLIC_TOOL_NAMES)

    for name, spec in catalog.items():
        config_entry = configured.tools[name]
        assert config_entry.issue_number == spec.issue_number
        assert config_entry.server == spec.server_key
        assert config_entry.tool == spec.tool_method
        assert config_entry.category == spec.category
        assert config_entry.implementation_phase == spec.implementation_phase
        assert config_entry.container_hint == spec.container_hint
        assert tuple(config_entry.aliases) == spec.aliases


def test_bioinfomcp_catalog_tool_is_registered_and_runnable():
    tool = registry.make("bioinfomcp_tool_catalog")
    result = tool.run({})

    assert result.success
    assert result.data["issue_number"] == ISSUE_130_NUMBER
    assert result.data["tool_count"] == 12
    assert result.data["tools"][0]["public_name"] == "bamCoverage"

    gatk_result = tool.run({"implementation_phase": "gatk_suite"})
    assert gatk_result.success
    assert gatk_result.data["tool_count"] == 3
    assert {entry["public_name"] for entry in gatk_result.data["tools"]} == {
        "gatk_ApplyBQSR",
        "gatk_BaseRecalibrator",
        "gatk_SelectVariants",
    }
