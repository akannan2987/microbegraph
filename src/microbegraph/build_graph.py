"""
MicrobeGraph, the graph build (Phase 4).

USAGE (from the repository root, with .venv active)

    python -m microbegraph.build_graph

    Run it after `python -m microbegraph.resolve`. It reads the resolver's
    files in data/processed/ and builds the project's database:

        data/processed/microbegraph.duckdb

    then rebuilds the NetworkX graph from that database and checks that the
    two hold exactly the same nodes and arrows.

TWO SHAPES OF THE SAME FACTS
    DuckDB is a database in a single file, with no server to install. It
    answers table-shaped questions in SQL: how many, which ones, grouped by
    what. NetworkX is a Python library that holds the same facts as a graph:
    dots and arrows you can walk, to find paths and hubs. Phase 5 uses both.

    A library catalogue and the library's shelves are the everyday picture.
    The catalogue (DuckDB) answers "how many books by this author?"; the
    shelves (NetworkX) let you walk from one book to the next one beside it.
    Both describe the same books, and the catalogue is the record everyone
    trusts.

THE RULE THAT KEEPS THEM IN STEP
    DuckDB is the single source of truth. The NetworkX graph is always
    rebuilt from it (load_graph(), below) and never edited, so the two can't
    drift apart. This command proves it on every build: it counts nodes and
    arrows of every type in both, and stops if any number differs.

WHAT THE DATABASE HOLDS
    tables  nodes       one row per node (properties as JSON)
            edges       one row per arrow
            ledger      the resolution ledger: every merge and refusal
            sources     which version of each source the graph was built from
            build_info  when it was built, and the totals
    views   organisms (pathogens included, since a Pathogen is a kind of
            Organism), clusters, compounds, proteins, pathogens, crops and
            pathways, each with the properties used most often as ordinary
            columns ("promoted"), so queries don't have to dig into JSON; and
            aliases, every identifier that was folded into another node and
            the node it became. Activities and compound classes have no view
            of their own; they have only a name, so the nodes table is enough.

    The tables carry the ontology as database rules too: every node_id is
    unique (PRIMARY KEY), every arrow's ends must be real nodes (FOREIGN KEY),
    and node types, arrow types and evidence levels must be ones the ontology
    knows (CHECK). So even a hand-edited CSV can't sneak a broken row in.

WHY A TEMPORARY FILE
    The database is built in microbegraph.duckdb.building, checked against
    NetworkX, and only then renamed to microbegraph.duckdb. If anything fails
    on the way (a broken row, a value DuckDB refuses, a count that differs),
    the temporary file is deleted and the previous database is still there,
    untouched.

EXIT CODES
    0  built, and DuckDB and NetworkX agree
    1  something failed; the message says what and what to do
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import networkx as nx

from microbegraph import __version__
from microbegraph.ontology import EDGE_TYPES, EVIDENCE_LEVELS, NODE_TYPES
from microbegraph.paths import (
    DATABASE_FILE,
    EDGES_FILE,
    LEDGER_FILE,
    NODES_FILE,
    RESOLVE_SUMMARY,
    relative_to_repo,
)
from microbegraph.provenance import utc_now
from microbegraph.validate import check_tables


class BuildError(Exception):
    """The build couldn't finish; the message says why and what to do."""


def _quoted(values: Any) -> str:
    """('a', 'b') -> "'a', 'b'", for the CHECK rules below."""
    return ", ".join(f"'{v}'" for v in sorted(values))


# The tables, written as SQL. The CHECK lists come from ontology.py, so the
# database and the Python rules can never disagree about what's allowed.
SCHEMA = f"""
CREATE TABLE nodes (
    node_id      VARCHAR PRIMARY KEY,
    node_type    VARCHAR NOT NULL CHECK (node_type IN ({_quoted(NODE_TYPES)})),
    name         VARCHAR NOT NULL,
    properties   JSON,
    source       VARCHAR NOT NULL,
    retrieved_at DATE NOT NULL
);
CREATE TABLE edges (
    source_id        VARCHAR NOT NULL REFERENCES nodes (node_id),
    target_id        VARCHAR NOT NULL REFERENCES nodes (node_id),
    edge_type        VARCHAR NOT NULL CHECK (edge_type IN ({_quoted(EDGE_TYPES)})),
    evidence_level   VARCHAR NOT NULL CHECK (evidence_level IN ({_quoted(EVIDENCE_LEVELS)})),
    source           VARCHAR NOT NULL,
    source_record_id VARCHAR,
    citation         VARCHAR,
    confidence       DOUBLE CHECK (confidence BETWEEN 0 AND 1),
    retrieved_at     DATE NOT NULL
);
CREATE TABLE ledger (
    rule VARCHAR, decision VARCHAR, identifier VARCHAR, node_id VARCHAR,
    compared_with VARCHAR, node_type VARCHAR, grounds VARCHAR, sources VARCHAR
);
CREATE TABLE sources (
    source VARCHAR PRIMARY KEY, version VARCHAR, retrieved_at VARCHAR, snapshot VARCHAR,
    nodes_read INTEGER
);
CREATE TABLE build_info (key VARCHAR PRIMARY KEY, value VARCHAR);
"""

# One view per node type, with the most-used properties as plain columns.
# p->>'x' reads property x from the JSON as text.
VIEWS = """
CREATE VIEW organisms AS
    SELECT node_id, name, node_type, properties->>'rank' AS rank,
           properties->>'group' AS group_name, properties->>'lineage' AS lineage,
           properties->>'other_names' AS other_names, source
    FROM nodes WHERE node_type IN ('Organism', 'Pathogen');
CREATE VIEW clusters AS
    SELECT node_id, name, properties->>'bgc_class' AS bgc_class,
           properties->>'completeness' AS completeness, properties->>'quality' AS quality
    FROM nodes WHERE node_type = 'GeneCluster';
CREATE VIEW compounds AS
    SELECT node_id, name, properties->>'formula' AS formula,
           properties->>'pubchem_cid' AS pubchem_cid, properties->>'inchikey' AS inchikey,
           properties->>'other_names' AS other_names, source
    FROM nodes WHERE node_type = 'Compound';
CREATE VIEW proteins AS
    SELECT node_id, name, properties->>'gene_name' AS gene_name,
           properties->>'product' AS product,
           properties->>'uniprot_accession' AS uniprot_accession,
           properties->>'protein_names' AS uniprot_name,
           properties->>'reviewed' AS reviewed, properties->>'ec_numbers' AS ec_numbers,
           properties->>'sequence_length' AS sequence_length, source
    FROM nodes WHERE node_type = 'Protein';
CREATE VIEW pathogens AS
    SELECT node_id, name, properties->>'pathogen_type' AS pathogen_type,
           properties->>'diseases' AS diseases
    FROM nodes WHERE node_type = 'Pathogen';
CREATE VIEW crops AS
    SELECT node_id, name, properties->>'scientific_name' AS scientific_name,
           properties->>'category' AS category
    FROM nodes WHERE node_type = 'Crop';
CREATE VIEW pathways AS
    SELECT node_id, name, properties->>'category' AS category,
           properties->>'subcategory' AS subcategory
    FROM nodes WHERE node_type = 'Pathway';
CREATE VIEW aliases AS
    SELECT identifier AS alias, node_id, rule
    FROM ledger WHERE decision IN ('merged', 'moved');
"""


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Every row of a CSV file, as a dict of column name -> text."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build(nodes_path: Path = NODES_FILE, edges_path: Path = EDGES_FILE,
          ledger_path: Path = LEDGER_FILE, summary_path: Path = RESOLVE_SUMMARY,
          db_path: Path = DATABASE_FILE) -> dict[str, Any]:
    """Check, load into DuckDB, rebuild in NetworkX, compare. Returns the counts."""
    for path in (nodes_path, edges_path, ledger_path, summary_path):
        if not path.exists():
            raise BuildError(f"{relative_to_repo(path)} is missing.\n"
                             f"  Run:  python -m microbegraph.resolve")
    nodes = read_csv_rows(nodes_path)
    edges = read_csv_rows(edges_path)
    problems = check_tables(nodes, edges)
    if problems:
        shown = "\n    ".join(problems[:10])
        raise BuildError(f"{relative_to_repo(nodes_path)} and {edges_path.name} break the "
                         f"rulebook ({len(problems)} problems), so nothing was built. "
                         f"Run the resolver again rather than editing them by hand. "
                         f"First ones:\n    {shown}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    building = db_path.with_name(db_path.name + ".building")
    for leftover in (building, building.with_name(building.name + ".wal")):
        leftover.unlink(missing_ok=True)
    con = duckdb.connect(str(building))
    try:
        con.execute(SCHEMA)
        con.execute("INSERT INTO nodes SELECT node_id, node_type, name, properties::JSON, "
                    "source, retrieved_at::DATE FROM read_csv(?, header = true, "
                    "all_varchar = true)", [str(nodes_path)])
        con.execute("INSERT INTO edges SELECT source_id, target_id, edge_type, evidence_level, "
                    "source, source_record_id, citation, NULLIF(confidence, '')::DOUBLE, "
                    "retrieved_at::DATE FROM read_csv(?, header = true, all_varchar = true)",
                    [str(edges_path)])
        con.execute("INSERT INTO ledger SELECT * FROM read_csv(?, header = true, "
                    "all_varchar = true)", [str(ledger_path)])
        for source, info in summary.get("sources", {}).items():
            con.execute("INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
                        [source, info.get("version", ""), info.get("retrieved_at", ""),
                         info.get("snapshot", ""), info.get("nodes_read", 0)])
        info_rows = {"built_at": utc_now(), "resolved_at": summary.get("resolved_at", ""),
                     "microbegraph_version": __version__, "nodes": str(len(nodes)),
                     "edges": str(len(edges))}
        con.executemany("INSERT INTO build_info VALUES (?, ?)", list(info_rows.items()))
        con.execute(VIEWS)
        counts = _database_counts(con)
    except duckdb.Error as error:
        con.close()
        building.unlink(missing_ok=True)
        raise BuildError(f"DuckDB refused the data ({error}). Nothing was replaced.") from error
    con.close()

    # Rebuild the graph in NetworkX from the new file and compare, BEFORE the
    # swap, so a disagreement leaves the previous database exactly as it was.
    counts["networkx"] = graph_counts(load_graph(building))
    differences = [key for key in ("nodes", "edges", "node_types", "edge_types")
                   if counts["duckdb"][key] != counts["networkx"][key]]
    if differences:
        building.unlink(missing_ok=True)
        raise BuildError(
            f"DuckDB and NetworkX disagree about {', '.join(differences)}. The most likely "
            f"cause is two arrows between the same pair of nodes, which a NetworkX DiGraph "
            f"can hold only once. Nothing was replaced. The counts were: "
            f"{json.dumps(counts)}"
        )

    # On macOS and Linux the swap works even while another program has the old
    # file open (that program keeps reading the old copy until it reconnects).
    # Windows refuses to replace an open file, which arrives as PermissionError.
    try:
        os.replace(building, db_path)
    except PermissionError as error:
        building.unlink(missing_ok=True)
        raise BuildError(
            f"{relative_to_repo(db_path)} is open in another program (an R session, a "
            f"notebook, the app or a database viewer), and Windows won't replace a file "
            f"that's in use. The old database is still there, unchanged. Close that "
            f"program's connection and run the build again."
        ) from error
    return counts


def _database_counts(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    def by(sql: str) -> dict[str, int]:
        return {key: int(n) for key, n in con.execute(sql).fetchall()}
    tables = {name: int(con.execute(f"SELECT count(*) FROM {name}").fetchone()[0])
              for name in ("nodes", "edges", "ledger", "sources")}
    return {
        "tables": tables,
        "duckdb": {
            "nodes": tables["nodes"],
            "edges": tables["edges"],
            "node_types": by("SELECT node_type, count(*) FROM nodes GROUP BY 1 ORDER BY 1"),
            "edge_types": by("SELECT edge_type, count(*) FROM edges GROUP BY 1 ORDER BY 1"),
        },
    }


def load_graph(db_path: Path | str | None = None) -> nx.DiGraph:
    """
    The NetworkX graph, rebuilt from the database (never edited, see the notes above).

    Each node carries node_type, name and its properties (as a dict); each
    arrow carries edge_type, evidence_level, source, citation and confidence.
    The connection is read-only, so loading never changes the database.
    """
    db_path = Path(db_path or DATABASE_FILE)
    if not db_path.exists():
        raise BuildError(f"{relative_to_repo(db_path)} doesn't exist yet.\n"
                         f"  Run:  python -m microbegraph.resolve\n"
                         f"        python -m microbegraph.build_graph")
    graph = nx.DiGraph()
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        for node_id, node_type, name, props in con.execute(
                "SELECT node_id, node_type, name, properties FROM nodes ORDER BY node_id"
        ).fetchall():
            graph.add_node(node_id, node_type=node_type, name=name,
                           properties=json.loads(props) if props else {})
        for row in con.execute(
                "SELECT source_id, target_id, edge_type, evidence_level, source, citation, "
                "confidence FROM edges ORDER BY source_id, target_id, edge_type"
        ).fetchall():
            start, end, edge_type, level, source, citation, confidence = row
            graph.add_edge(start, end, edge_type=edge_type, evidence_level=level,
                           source=source, citation=citation or "", confidence=confidence)
    finally:
        con.close()
    return graph


def graph_counts(graph: nx.DiGraph) -> dict[str, Any]:
    """Nodes and arrows of every type in a NetworkX graph, to compare with DuckDB."""
    node_types = Counter(data["node_type"] for _, data in graph.nodes(data=True))
    edge_types = Counter(data["edge_type"] for _, _, data in graph.edges(data=True))
    return {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
            "node_types": dict(sorted(node_types.items())),
            "edge_types": dict(sorted(edge_types.items()))}


def report(counts: dict[str, Any]) -> str:
    """The side-by-side table the command prints."""
    db, g = counts["duckdb"], counts["networkx"]
    lines = [f"  {'':<18}{'DuckDB':>9}{'NetworkX':>10}",
             f"  {'nodes':<18}{db['nodes']:>9,}{g['nodes']:>10,}"]
    lines += [f"    {k:<16}{v:>9,}{g['node_types'].get(k, 0):>10,}"
              for k, v in db["node_types"].items()]
    lines.append(f"  {'edges':<18}{db['edges']:>9,}{g['edges']:>10,}")
    lines += [f"    {k:<16}{v:>9,}{g['edge_types'].get(k, 0):>10,}"
              for k, v in db["edge_types"].items()]
    return "\n".join(lines)


# ------------------------------------------------------------------------ the command
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microbegraph.build_graph",
        description="Load the resolved graph into DuckDB, rebuild it in NetworkX, compare.",
    )
    parser.add_argument("--debug", action="store_true",
                        help="show the full Python error instead of the short message")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        print(f"[build_graph] checking {relative_to_repo(NODES_FILE)} and "
              f"{EDGES_FILE.name} against the twelve rules")
        counts = build()
    except (BuildError, OSError, ValueError, duckdb.Error) as error:
        if args.debug:
            raise
        print(f"\n[build_graph] FAILED: {error}\n  (add --debug to see the full error)")
        return 1
    tables = counts["tables"]
    print(f"[build_graph] wrote {relative_to_repo(DATABASE_FILE)}")
    print(f"  tables  nodes {tables['nodes']:,}   edges {tables['edges']:,}   "
          f"ledger {tables['ledger']:,}   sources {tables['sources']}   build_info")
    print("  views   organisms, clusters, compounds, proteins, pathogens, crops, pathways, "
          "aliases")
    print("[build_graph] rebuilt the NetworkX graph from the database and compared")
    print(report(counts))
    print(f"[build_graph] every count matches. Done in {time.perf_counter() - started:.1f} s.")
    print("Next:  try the recipes in docs/QUERY_COOKBOOK.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
