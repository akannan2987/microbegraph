"""
MicrobeGraph, every source's tables in one pool.

WHAT IT HOLDS
    The resolver needs to see all six sources at once: MIBiG's compounds next
    to PubChem's, MIBiG's protein numbers next to UniProt's entries. The pool
    reads every staging table and arranges the rows so the rules can ask
    simple questions:

        pool.rows["ncbitaxon:5518"]     every source's record of one identifier
        pool.props("mibig:BGC0000433")  that node's properties, from one source
        pool.summaries["pubchem"]       a source's summary (counts and lists)
        pool.edges                      every arrow from every source

    It changes nothing. The rules read from it, write their decisions to the
    ledger, and combine.py builds the merged tables at the end.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from microbegraph.staging import properties_of, read_table, staging_path
from microbegraph.tables import SourceError

# The sources in the order they run (the same order as `fetch --all`).
SOURCE_ORDER: tuple[str, ...] = ("mibig", "pubchem", "ncbi_taxonomy", "kegg", "uniprot",
                                 "curation")


@dataclass
class Pool:
    """Every source's node rows (grouped by identifier), edge rows and summaries."""

    rows: dict[str, list[dict[str, str]]] = field(default_factory=lambda: defaultdict(list))
    edges: list[dict[str, str]] = field(default_factory=list)
    summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    nodes_read: dict[str, int] = field(default_factory=dict)
    _edge_index: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def read(cls, staging_dir: Path) -> Pool:
        """Read all six sources' tables. A missing table says which command makes it."""
        pool = cls()
        for source in SOURCE_ORDER:
            nodes = read_table(source, "nodes", staging_dir, needed_by="the resolver")
            edges = read_table(source, "edges", staging_dir, needed_by="the resolver")
            summary_path = staging_path(source, "summary", staging_dir)
            if not summary_path.exists():
                raise SourceError(
                    f"{summary_path.name} is missing, and the resolver reads it.\n"
                    f"  Run:  python -m microbegraph.fetch --tidy-only --source {source}"
                )
            pool.summaries[source] = json.loads(summary_path.read_text(encoding="utf-8"))
            for row in nodes:
                pool.rows[row["node_id"]].append(row)
            pool.edges.extend(edges)
            pool.nodes_read[source] = len(nodes)
        return pool

    # ------------------------------------------------------------------ lookups
    def row(self, node_id: str, source: str) -> dict[str, str] | None:
        """One source's record of an identifier, or None."""
        return next((r for r in self.rows.get(node_id, []) if r["source"] == source), None)

    def props(self, node_id: str, source: str = "mibig") -> dict[str, Any]:
        """One source's properties for an identifier ({} if that source doesn't have it)."""
        row = self.row(node_id, source)
        return properties_of(row) if row else {}

    def name(self, node_id: str, source: str = "mibig") -> str:
        """One source's name for an identifier ("" if that source doesn't have it)."""
        row = self.row(node_id, source)
        return row["name"] if row else ""

    def ids(self, prefix: str) -> list[str]:
        """Every identifier with a given prefix, sorted: pool.ids("pubchem.compound")."""
        return sorted(i for i in self.rows if i.startswith(prefix + ":"))

    def types(self, node_id: str) -> set[str]:
        """The node types the sources give an identifier (normally exactly one)."""
        return {r["node_type"] for r in self.rows.get(node_id, [])}

    def sources(self, node_id: str) -> list[str]:
        """The sources that have a record of an identifier, in pipeline order."""
        present = {r["source"] for r in self.rows.get(node_id, [])}
        return [s for s in SOURCE_ORDER if s in present]

    def targets(self, source_id: str, edge_type: str) -> list[str]:
        """Where one kind of arrow from a node points, e.g. a cluster's proteins."""
        return self._index(edge_type)[0].get(source_id, [])

    def starts(self, target_id: str, edge_type: str) -> list[str]:
        """Where one kind of arrow into a node comes from, e.g. a protein's clusters."""
        return self._index(edge_type)[1].get(target_id, [])

    def _index(self, edge_type: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        cache = self._edge_index           # built once per edge type, on first use
        if edge_type not in cache:
            forward: dict[str, list[str]] = defaultdict(list)
            backward: dict[str, list[str]] = defaultdict(list)
            for edge in self.edges:
                if edge["edge_type"] == edge_type:
                    forward[edge["source_id"]].append(edge["target_id"])
                    backward[edge["target_id"]].append(edge["source_id"])
            cache[edge_type] = (dict(forward), dict(backward))
        return cache[edge_type]
