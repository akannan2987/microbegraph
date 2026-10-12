"""
MicrobeGraph, reading and writing the staging tables.

WHAT THE STAGING FOLDER IS
    data/processed/staging/ holds one small set of tables per source:

        <source>_nodes.csv      the dots this source knows about
        <source>_edges.csv      the arrows between them
        <source>_summary.json   counts, the version used, and the snapshot read

    Phase 4 merges every source's tables into one graph. Until then each set
    stands on its own and is checked against the twelve rules on its own.

WHY SOME SOURCES READ ANOTHER SOURCE'S TABLES
    From Phase 2 on, sources build on each other, the way a second coat of
    paint goes on top of the first:

        pubchem         asks about the compound numbers MIBiG recorded
        ncbi_taxonomy   asks about MIBiG's organisms and the bridge's pathogens
        kegg            links the KEGG numbers PubChem found to pathways
        curation        checks every bridge row against MIBiG and NCBI

    So the order sources run in matters, and `--all` follows it. If a table a
    source needs is missing, the message below says which command makes it.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from microbegraph.paths import relative_to_repo
from microbegraph.sources.base import (
    EDGE_COLUMNS,
    NODE_COLUMNS,
    SourceError,
    TidyResult,
    table_text,
    write_files_together,
)
from microbegraph.validate import check_tables


def staging_path(source: str, kind: str, staging_dir: Path) -> Path:
    """Where one table lives, e.g. ("mibig", "nodes") -> .../staging/mibig_nodes.csv."""
    suffix = "json" if kind == "summary" else "csv"
    return staging_dir / f"{source}_{kind}.{suffix}"


def read_table(source: str, kind: str, staging_dir: Path, needed_by: str) -> list[dict[str, str]]:
    """
    Every row of another source's nodes or edges table.

    `needed_by` names the source asking, so a missing table produces a
    message that says who needs it and how to make it.
    """
    path = staging_path(source, kind, staging_dir)
    if not path.exists():
        raise SourceError(
            f"{relative_to_repo(path)} is missing, and {needed_by} builds on it.\n"
            f"  Run:  python -m microbegraph.fetch --source {source}"
        )
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def properties_of(row: dict[str, str]) -> dict[str, Any]:
    """The properties column of a node row, turned back from JSON text into a dict."""
    return json.loads(row.get("properties") or "{}")


def node_row(node_id: str, node_type: str, name: str, props: dict[str, Any],
             source: str, retrieved_at: str) -> dict[str, Any]:
    """One node row in the shared format. Empty properties are left out."""
    clean = {k: v for k, v in props.items() if v not in (None, "", [])}
    return {
        "node_id": node_id,
        "node_type": node_type,
        "name": name,
        "properties": json.dumps(clean, sort_keys=True, ensure_ascii=False),
        "source": source,
        "retrieved_at": retrieved_at,
    }


def edge_row(source_id: str, target_id: str, edge_type: str, evidence_level: str,
             source: str, source_record_id: str, retrieved_at: str,
             citation: str = "", confidence: str = "") -> dict[str, Any]:
    """One edge row in the shared format."""
    return {
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "evidence_level": evidence_level,
        "source": source,
        "source_record_id": source_record_id,
        "citation": citation,
        "confidence": confidence,
        "retrieved_at": retrieved_at,
    }


def write_tables(source: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]],
                 summary: dict[str, Any], staging_dir: Path,
                 external_node_types: dict[str, str] | None = None) -> TidyResult:
    """
    Check one source's tables against the twelve rules, then write all three
    files together. If any rule fails, nothing is written and the message
    lists the first problems.

    external_node_types names the nodes this source points at but does not
    own (KEGG's arrows start at PubChem's compounds, for example), so the
    check knows they exist.
    """
    nodes = sorted(nodes, key=lambda r: (r["node_type"], r["node_id"]))
    edges = sorted(edges, key=lambda r: (r["edge_type"], r["source_id"], r["target_id"]))
    problems = check_tables(nodes, edges, external_node_types)
    if problems:
        shown = "\n    ".join(problems[:10])
        raise SourceError(
            f"The {source} tidy produced rows that break the rulebook "
            f"({len(problems)} problems). Nothing was written. First ones:\n    {shown}"
        )
    nodes_path = staging_path(source, "nodes", staging_dir)
    edges_path = staging_path(source, "edges", staging_dir)
    summary_path = staging_path(source, "summary", staging_dir)
    write_files_together({
        nodes_path: table_text(NODE_COLUMNS, nodes),
        edges_path: table_text(EDGE_COLUMNS, edges),
        summary_path: json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    })
    return TidyResult(source, nodes_path, edges_path, dict(summary.get("counts", {})))
