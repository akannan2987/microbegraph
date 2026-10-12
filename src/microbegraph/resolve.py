"""
MicrobeGraph, the resolver (Phase 4).

USAGE (from the repository root, with .venv active)

    python -m microbegraph.resolve

    It reads data/processed/staging/ (all six sources, from Phases 1 to 4b)
    and two hand-written lists in curation/ (Phase 4b), decides which records
    are the same thing, and writes:

        data/processed/nodes.csv              one row per node of the graph
        data/processed/edges.csv              one row per arrow
        data/processed/resolution_ledger.csv  every decision, with its grounds
        data/processed/resolve_summary.json   the counts, and what is still open

    It needs no network: everything it reads is already on your disk. Run
    `python -m microbegraph.build_graph` next, to load the result into DuckDB
    and NetworkX.

WHAT HAPPENS, IN ORDER
    1. read every source's tables into one pool             resolution/pool.py
    2. move organisms whose NCBI number was merged          resolution/organisms.py
    3. fold activity words that mean the same thing         resolution/activities.py
       (curation/activity_synonyms.csv, Phase 4b)
    4. apply the decisions a person made                    resolution/reviewed.py
       (curation/resolution_decisions.csv, Phase 4b)
    5. join MIBiG's compounds to PubChem's, where confirmed resolution/compounds.py
    6. join protein numbers to UniProt, identical
       sequences, and gene records by gene name            resolution/proteins.py
    7. one node per group, arrows re-pointed               resolution/combine.py
    8. the twelve rules on the merged tables, and a check that every
       identifier that disappeared has a ledger row; if either fails,
       nothing is written
    9. write the four files together

WHY THE TWELVE RULES RUN AGAIN
    Each source passed them on its own, but merging can break them: two
    records joined into one node, or an arrow re-pointed to a node that was
    left out. Running the same rules (validate.py) on the merged tables means
    a mistake in the resolver is caught here, the day it's made.

WHY THE LEDGER IS CHECKED TOO
    The ledger is only useful if it's complete: anyone holding an old
    identifier must be able to look up where it went. So before writing, the
    resolver lists every identifier it read that is no longer a node, and
    stops if any of them has no merged, moved or left_out row. A rule that
    joins records and forgets to say so is caught on the first run, even on
    data the tests don't contain.

EXIT CODES
    0  the graph was written
    1  something failed; the message says what and what to do
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from microbegraph.paths import (
    CURATION_DIR,
    EDGES_FILE,
    LEDGER_FILE,
    NODES_FILE,
    PROCESSED_DIR,
    RESOLVE_SUMMARY,
    STAGING_DIR,
    relative_to_repo,
)
from microbegraph.provenance import utc_now
from microbegraph.resolution.activities import fold_activities, read_synonyms
from microbegraph.resolution.combine import ResolutionError, combine_edges, combine_nodes
from microbegraph.resolution.compounds import join_pubchem, join_same_npatlas
from microbegraph.resolution.groups import Groups
from microbegraph.resolution.ledger import LEDGER_COLUMNS, RULES, Ledger
from microbegraph.resolution.organisms import move_merged_numbers
from microbegraph.resolution.pool import SOURCE_ORDER, Pool
from microbegraph.resolution.proteins import (
    ProteinFacts,
    join_gene_names,
    join_identical_sequences,
    join_uniprot,
)
from microbegraph.resolution.reviewed import apply_decisions, read_decisions
from microbegraph.tables import (
    EDGE_COLUMNS,
    NODE_COLUMNS,
    SourceError,
    table_text,
    write_files_together,
)
from microbegraph.validate import check_tables


@dataclass
class ResolveResult:
    """What one run produced: where the files went, and the counts."""

    nodes_path: Path
    edges_path: Path
    ledger_path: Path
    summary_path: Path
    summary: dict[str, Any] = field(default_factory=dict)


def resolve(staging_dir: Path = STAGING_DIR, out_dir: Path = PROCESSED_DIR,
            curation_dir: Path = CURATION_DIR) -> ResolveResult:
    """
    Run every rule, check the result, and write the four files (see the notes
    above). curation_dir holds activity_synonyms.csv and
    resolution_decisions.csv; a missing file means an empty list.
    """
    pool = Pool.read(staging_dir)
    ledger = Ledger()
    groups = Groups()
    notes: dict[str, list[str]] = defaultdict(list)                # added to a node
    renames: dict[str, dict[str, str]] = defaultdict(dict)        # property renamed
    synonyms = read_synonyms(curation_dir / "activity_synonyms.csv")
    decisions = read_decisions(curation_dir / "resolution_decisions.csv")

    moves = move_merged_numbers(pool, ledger)
    folded = fold_activities(pool, ledger, synonyms)
    moves.update(folded)
    reviewed = apply_decisions(pool, groups, ledger, decisions)
    join_pubchem(pool, groups, ledger, notes, renames, reviewed)
    join_same_npatlas(pool, groups, ledger, reviewed)
    facts = ProteinFacts(pool, moves)
    join_uniprot(pool, groups, ledger, facts, notes, reviewed)
    join_identical_sequences(pool, groups, ledger, facts, reviewed)
    gene_records_left = join_gene_names(pool, groups, ledger, reviewed)
    groups.settle()

    def final_id(identifier: str) -> str:
        return groups.canonical(moves.get(identifier, identifier))

    nodes, left_out = combine_nodes(pool, final_id, ledger, notes, renames)
    edges, edge_counts = combine_edges(pool, final_id, left_out)
    nodes.sort(key=lambda r: (r["node_type"], r["node_id"]))
    edges.sort(key=lambda r: (r["edge_type"], r["source_id"], r["target_id"], r["source"]))

    problems = check_tables(nodes, edges)
    if problems:
        shown = "\n    ".join(problems[:10])
        raise ResolutionError(
            f"The merged tables break the rulebook ({len(problems)} problems), so nothing "
            f"was written. First ones:\n    {shown}"
        )

    ledger_rows = ledger.finish(lambda i: "" if i in left_out else final_id(i))
    unexplained = sorted(set(pool.rows) - {row["node_id"] for row in nodes}
                         - {row["identifier"] for row in ledger_rows
                            if row["decision"] in ("merged", "moved", "left_out")})
    if unexplained:
        raise ResolutionError(
            f"{len(unexplained)} identifiers disappeared without a ledger row, so nothing "
            f"was written. A rule joined records without recording it. First ones: "
            f"{', '.join(unexplained[:10])}"
        )
    summary = _summary(pool, nodes, edges, edge_counts, ledger, left_out, gene_records_left)
    summary["curation"] = {
        "activity_synonyms": len(synonyms),
        "activity_synonyms_applied": len(folded),
        "activity_synonyms_not_applied": [s.activity for s in synonyms
                                          if s.old_id not in folded],
        "decisions_by_hand": len(decisions),
    }

    paths = {name: out_dir / path.name for name, path in (
        ("nodes", NODES_FILE), ("edges", EDGES_FILE), ("ledger", LEDGER_FILE),
        ("summary", RESOLVE_SUMMARY))}
    write_files_together({
        paths["nodes"]: table_text(NODE_COLUMNS, nodes),
        paths["edges"]: table_text(EDGE_COLUMNS, edges),
        paths["ledger"]: table_text(LEDGER_COLUMNS, ledger_rows),
        paths["summary"]: json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    })
    return ResolveResult(paths["nodes"], paths["edges"], paths["ledger"], paths["summary"],
                         summary)


def _summary(pool: Pool, nodes: list[dict[str, Any]], edges: list[dict[str, Any]],
             edge_counts: dict[str, int], ledger: Ledger, left_out: set[str],
             gene_records_left: list[str]) -> dict[str, Any]:
    """The counts and lists written to resolve_summary.json."""
    sources = {}
    for source in SOURCE_ORDER:
        info = pool.summaries[source]
        sources[source] = {
            "version": info.get("source_version", ""),
            "retrieved_at": info.get("retrieved_at", ""),
            "snapshot": info.get("snapshot", info.get("archive", info.get("file", ""))),
            "nodes_read": pool.nodes_read[source],
        }
    by_type = Counter(row["node_type"] for row in nodes)
    by_edge = Counter(row["edge_type"] for row in edges)
    mibig = pool.summaries["mibig"]
    return {
        "resolved_at": utc_now(),
        "sources": sources,
        "counts": {
            "node_rows_read": sum(pool.nodes_read.values()),
            "identifiers_read": len(pool.rows),
            "nodes_written": len(nodes),
            "identifiers_left_out": len(left_out),
            "edges_read": edge_counts["edges_read"],
            "edges_written": len(edges),
            "edges_combined": edge_counts["edges_combined"],
            "edges_dropped_at_left_out_nodes": edge_counts["edges_dropped_at_left_out_nodes"],
            "edges_that_became_loops": edge_counts["edges_that_became_loops"],
        },
        "nodes_by_type": dict(sorted(by_type.items())),
        "edges_by_type": dict(sorted(by_edge.items())),
        "rules": ledger.counts(),
        # What the rules left for a person (Phase 4b: the review file is where
        # a decision about any of these goes; docs/06b-closing-the-gaps.md).
        "still_open": {
            "gene_records_without_a_protein_number": gene_records_left,
            "curators_removals_not_found": mibig.get("to_delete_not_found", []),
            "pubchem_joins_on_the_formula_alone": sum(
                1 for r in ledger.rows if r["decision"] == "merged"
                and r["grounds"].endswith("Confirmed by the formula alone.")),
            "compounds_kept_apart_from_pubchem": len({
                r["identifier"] for r in ledger.rows if r["decision"] == "kept_apart"
                and r["rule"].startswith("pubchem_")}),
            "protein_numbers_with_tied_uniprot_entries": sorted(
                r["identifier"] for r in ledger.rows if r["rule"] == "uniprot_cross_reference"
                and r["decision"] == "kept_apart"),
        },
    }


# ------------------------------------------------------------------------ the command
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m microbegraph.resolve",
        description="Merge every source's staging tables into one graph, with a ledger.",
    )
    parser.add_argument("--debug", action="store_true",
                        help="show the full Python error instead of the short message")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        print(f"[resolve] reading {relative_to_repo(STAGING_DIR)}/ (six sources) and "
              f"{relative_to_repo(CURATION_DIR)}/")
        result = resolve()
    except (SourceError, ResolutionError, OSError, ValueError, KeyError) as error:
        if args.debug:
            raise
        print(f"\n[resolve] FAILED: {error}\n  (add --debug to see the full error)")
        return 1
    print(report(result.summary))
    curation = result.summary["curation"]
    print(f"[resolve] curation/: {curation['activity_synonyms_applied']} of "
          f"{curation['activity_synonyms']} activity synonyms applied, "
          f"{curation['decisions_by_hand']} decisions by hand")
    for word in curation["activity_synonyms_not_applied"]:
        print(f"  note: no source uses the activity '{word}' yet, so its synonym row waits")
    written = ", ".join(p.name for p in (result.nodes_path, result.edges_path,
                                          result.ledger_path, result.summary_path))
    print("[resolve] the twelve rules pass on the merged tables")
    print("[resolve] every identifier that disappeared has a ledger row")
    print(f"[resolve] wrote {relative_to_repo(result.nodes_path.parent)}/: {written}")
    print("Next:  python -m microbegraph.build_graph")
    return 0


def report(summary: dict[str, Any]) -> str:
    """The summary as the aligned text the command prints."""
    out = io.StringIO()
    for source, info in summary["sources"].items():
        out.write(f"  {source:<14} {info['nodes_read']:>7,} nodes   version {info['version']}\n")
    out.write("[resolve] decisions, rule by rule (the ledger has one row for each)\n")
    width = max(len(rule) for rule in RULES)
    for rule, decisions in summary["rules"].items():
        text = "   ".join(f"{d} {n:,}" for d, n in decisions.items())
        out.write(f"  {rule:<{width}}  {text}\n")
    counts = summary["counts"]
    out.write("[resolve] the merged graph\n")
    out.write(f"  nodes {counts['nodes_written']:>7,}   from {counts['identifiers_read']:,} "
              f"identifiers ({counts['identifiers_left_out']:,} left out)\n")
    for node_type, n in summary["nodes_by_type"].items():
        out.write(f"    {node_type:<14}{n:>7,}\n")
    out.write(f"  edges {counts['edges_written']:>7,}   from {counts['edges_read']:,} "
              f"({counts['edges_combined']:,} combined, "
              f"{counts['edges_dropped_at_left_out_nodes']:,} dropped with left-out entries)\n")
    for edge_type, n in summary["edges_by_type"].items():
        out.write(f"    {edge_type:<14}{n:>7,}\n")
    return out.getvalue().rstrip("\n")


def read_ledger(path: Path = LEDGER_FILE) -> list[dict[str, str]]:
    """Every ledger row, for the build and the tests."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    sys.exit(main())
