from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Tuple

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

ISSUE_130_NUMBER = 130


@dataclass(frozen=True)
class BioinfoMCPToolSpec:
    """Catalog entry for a BioContainers-backed BioinfoMCP tool request."""

    public_name: str
    issue_number: int
    server_key: str
    tool_method: str
    category: str
    implementation_phase: str
    container_hint: str
    description: str
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["aliases"] = list(self.aliases)
        return data


ISSUE_130_PUBLIC_TOOL_NAMES: tuple[str, ...] = (
    "bamCoverage",
    "faToTwoBit",
    "gatk_ApplyBQSR",
    "gatk_BaseRecalibrator",
    "gatk_HaplotypeCaller",
    "gatk_SelectVariants",
    "gunzip",
    "mafft",
    "multiqc",
    "plotCorrelation",
    "quast",
    "trimmomatic",
)


_ISSUE_130_CATALOG: tuple[BioinfoMCPToolSpec, ...] = (
    BioinfoMCPToolSpec(
        public_name="bamCoverage",
        issue_number=131,
        server_key="deeptools",
        tool_method="deeptools_bam_coverage",
        category="coverage_analysis",
        implementation_phase="deeptools_reconciliation",
        container_hint="biocontainers/deeptools",
        description="Generate normalized genome-wide coverage tracks from BAM files.",
        aliases=("bam_coverage", "deeptools_bam_coverage"),
    ),
    BioinfoMCPToolSpec(
        public_name="faToTwoBit",
        issue_number=132,
        server_key="fatotwobit",
        tool_method="fatotwobit_convert",
        category="reference_conversion",
        implementation_phase="fatotwobit_server",
        container_hint="biocontainers/ucsc-fatotwobit",
        description="Convert FASTA reference genomes into UCSC 2bit format.",
        aliases=("fatotwobit", "fa_to_twobit"),
    ),
    BioinfoMCPToolSpec(
        public_name="gatk_ApplyBQSR",
        issue_number=133,
        server_key="gatk",
        tool_method="gatk_apply_bqsr",
        category="variant_calling",
        implementation_phase="gatk_suite",
        container_hint="biocontainers/gatk4",
        description="Apply GATK base quality score recalibration to BAM files.",
        aliases=("ApplyBQSR", "gatk_applybqsr"),
    ),
    BioinfoMCPToolSpec(
        public_name="gatk_BaseRecalibrator",
        issue_number=134,
        server_key="gatk",
        tool_method="gatk_base_recalibrator",
        category="variant_calling",
        implementation_phase="gatk_suite",
        container_hint="biocontainers/gatk4",
        description="Generate GATK BQSR recalibration tables from BAM files.",
        aliases=("BaseRecalibrator", "gatk_baserecalibrator"),
    ),
    BioinfoMCPToolSpec(
        public_name="gatk_HaplotypeCaller",
        issue_number=135,
        server_key="haplotypecaller",
        tool_method="call_variants",
        category="variant_calling",
        implementation_phase="haplotypecaller_reconciliation",
        container_hint="biocontainers/gatk4",
        description="Call SNPs and indels with GATK HaplotypeCaller.",
        aliases=("HaplotypeCaller", "gatk_haplotypecaller"),
    ),
    BioinfoMCPToolSpec(
        public_name="gatk_SelectVariants",
        issue_number=136,
        server_key="gatk",
        tool_method="gatk_select_variants",
        category="variant_filtering",
        implementation_phase="gatk_suite",
        container_hint="biocontainers/gatk4",
        description="Select samples, regions, and variant types from VCF files.",
        aliases=("SelectVariants", "gatk_selectvariants"),
    ),
    BioinfoMCPToolSpec(
        public_name="gunzip",
        issue_number=137,
        server_key="gunzip",
        tool_method="gunzip_decompress",
        category="compression",
        implementation_phase="gunzip_reconciliation",
        container_hint="biocontainers/gnu-coreutils",
        description="Decompress gzip-compressed bioinformatics input files.",
        aliases=("gzip_decompress", "decompress_gzip"),
    ),
    BioinfoMCPToolSpec(
        public_name="mafft",
        issue_number=138,
        server_key="mafft",
        tool_method="mafft_align",
        category="multiple_sequence_alignment",
        implementation_phase="mafft_reconciliation",
        container_hint="biocontainers/mafft",
        description="Run multiple sequence alignment for nucleotide or protein FASTA files.",
        aliases=("mafft_align",),
    ),
    BioinfoMCPToolSpec(
        public_name="multiqc",
        issue_number=139,
        server_key="multiqc",
        tool_method="multiqc_run",
        category="quality_control",
        implementation_phase="multiqc_reconciliation",
        container_hint="biocontainers/multiqc",
        description="Aggregate bioinformatics QC outputs into a MultiQC report.",
        aliases=("multiqc_run",),
    ),
    BioinfoMCPToolSpec(
        public_name="plotCorrelation",
        issue_number=140,
        server_key="deeptools",
        tool_method="deeptools_plot_correlation",
        category="quality_control",
        implementation_phase="deeptools_completion",
        container_hint="biocontainers/deeptools",
        description="Create deeptools sample-correlation plots from summary matrices.",
        aliases=("plot_correlation", "deeptools_plot_correlation"),
    ),
    BioinfoMCPToolSpec(
        public_name="quast",
        issue_number=141,
        server_key="quast",
        tool_method="quast_assess",
        category="assembly_quality",
        implementation_phase="quast_server",
        container_hint="biocontainers/quast",
        description="Assess genome assembly quality with QUAST metrics and reports.",
        aliases=("quast_assess",),
    ),
    BioinfoMCPToolSpec(
        public_name="trimmomatic",
        issue_number=142,
        server_key="trimmomatic",
        tool_method="trimmomatic_pe",
        category="read_preprocessing",
        implementation_phase="trimmomatic_server",
        container_hint="biocontainers/trimmomatic",
        description="Trim Illumina reads in paired-end or single-end mode.",
        aliases=("trimmomatic_pe", "trimmomatic_se"),
    ),
)


def list_issue_130_bioinfomcp_tools() -> tuple[BioinfoMCPToolSpec, ...]:
    """Return the canonical tool catalog for issue #130."""

    return _ISSUE_130_CATALOG


def issue_130_bioinfomcp_catalog_by_name() -> dict[str, BioinfoMCPToolSpec]:
    """Return issue #130 catalog entries keyed by public issue tool name."""

    return {tool.public_name: tool for tool in _ISSUE_130_CATALOG}


def iter_issue_130_names_and_aliases() -> Iterable[tuple[str, BioinfoMCPToolSpec]]:
    """Yield public names and aliases for lookup-table construction."""

    for tool in _ISSUE_130_CATALOG:
        yield tool.public_name, tool
        for alias in tool.aliases:
            yield alias, tool


def get_issue_130_bioinfomcp_tool(name: str) -> BioinfoMCPToolSpec:
    """Look up an issue #130 tool by public name or alias."""

    lookup = dict(iter_issue_130_names_and_aliases())
    try:
        return lookup[name]
    except KeyError as exc:
        available = ", ".join(sorted(lookup))
        raise KeyError(
            f"Unknown BioinfoMCP issue #130 tool {name!r}. Available: {available}"
        ) from exc


def validate_issue_130_bioinfomcp_catalog() -> tuple[bool, list[str]]:
    """Validate internal consistency of the issue #130 catalog."""

    errors: list[str] = []
    public_names = [tool.public_name for tool in _ISSUE_130_CATALOG]
    if tuple(public_names) != ISSUE_130_PUBLIC_TOOL_NAMES:
        errors.append(
            "Catalog public names must match ISSUE_130_PUBLIC_TOOL_NAMES order."
        )

    issue_numbers = [tool.issue_number for tool in _ISSUE_130_CATALOG]
    if issue_numbers != list(range(131, 143)):
        errors.append("Issue #130 child tools must map to issues #131 through #142.")

    seen_lookup_names: dict[str, str] = {}
    for lookup_name, tool in iter_issue_130_names_and_aliases():
        owner = seen_lookup_names.get(lookup_name)
        if owner is not None and owner != tool.public_name:
            errors.append(
                f"Lookup name {lookup_name!r} is used by both {owner!r} and {tool.public_name!r}."
            )
        seen_lookup_names[lookup_name] = tool.public_name

        if not tool.server_key:
            errors.append(f"{tool.public_name} is missing a server key.")
        if not tool.tool_method:
            errors.append(f"{tool.public_name} is missing a tool method.")
        if not tool.container_hint:
            errors.append(f"{tool.public_name} is missing a container hint.")

    return not errors, errors


class BioinfoMCPToolCatalogTool(ToolRunner):
    """Expose the issue #130 BioinfoMCP catalog through the tool registry."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="bioinfomcp_tool_catalog",
                description="List BioContainers-backed BioinfoMCP tool requests for issue #130.",
                inputs={},
                outputs={
                    "issue_number": "INTEGER",
                    "tools": "JSON",
                    "tool_count": "INTEGER",
                },
            )
        )

    def run(self, params: dict[str, object]) -> ExecutionResult:
        implementation_phase = str(params.get("implementation_phase", "")).strip()
        catalog = list_issue_130_bioinfomcp_tools()
        if implementation_phase:
            catalog = tuple(
                tool
                for tool in catalog
                if tool.implementation_phase == implementation_phase
            )

        return ExecutionResult(
            success=True,
            data={
                "issue_number": ISSUE_130_NUMBER,
                "tool_count": len(catalog),
                "tools": [tool.to_dict() for tool in catalog],
            },
        )


registry.register("bioinfomcp_tool_catalog", BioinfoMCPToolCatalogTool)
