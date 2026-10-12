"""
Tests for the graph build (Phase 4): DuckDB, NetworkX, and the checks between them.

Each test resolves the real slice in tests/fixtures/resolve/ into a temporary
folder, builds the database from it, and looks at the result.
"""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import networkx as nx
import pytest
from conftest import add_rows, read_rows

from microbegraph.build_graph import BuildError, build, graph_counts, load_graph
from microbegraph.resolve import resolve


def _build(staging: Path, out: Path) -> tuple[dict, Path]:
    resolve(staging, out, staging / "curation")
    db = out / "microbegraph.duckdb"
    counts = build(out / "nodes.csv", out / "edges.csv", out / "resolution_ledger.csv",
                   out / "resolve_summary.json", db)
    return counts, db


@pytest.fixture
def built(staging_copy, tmp_path):
    return _build(staging_copy, tmp_path / "processed")


def test_duckdb_and_networkx_hold_the_same_graph(built, tmp_path):
    counts, db = built
    assert counts["duckdb"] == counts["networkx"]
    assert counts["duckdb"]["nodes"] == len(read_rows(tmp_path / "processed" / "nodes.csv"))
    assert counts["tables"]["ledger"] == len(
        read_rows(tmp_path / "processed" / "resolution_ledger.csv"))
    assert counts["tables"]["sources"] == 6


def test_the_views_promote_properties_to_columns(built):
    _, db = built
    con = duckdb.connect(str(db), read_only=True)
    try:
        assert con.execute("SELECT rank, group_name FROM organisms "
                           "WHERE node_id = 'ncbitaxon:326423'").fetchone() == (
            "strain", "Bacteria")
        assert con.execute("SELECT name, uniprot_accession FROM proteins "
                           "WHERE node_id = 'uniprot:Q70KJ7'").fetchone() == ("srfAA", "Q70KJ7")
        assert con.execute("SELECT node_id FROM aliases "
                           "WHERE alias = 'mg.compound:erythromycin-a'").fetchone() == (
            "pubchem.compound:12560",)
        # A Pathogen is a kind of Organism, so it's in both views.
        assert con.execute("SELECT count(*) FROM organisms WHERE node_type = 'Pathogen'"
                           ).fetchone()[0] == con.execute("SELECT count(*) FROM pathogens"
                                                          ).fetchone()[0]
    finally:
        con.close()


def test_the_database_itself_refuses_an_arrow_to_nowhere(built, tmp_path):
    _, db = built
    copy = tmp_path / "copy.duckdb"
    copy.write_bytes(db.read_bytes())
    con = duckdb.connect(str(copy))
    try:
        with pytest.raises(duckdb.ConstraintException):
            con.execute("INSERT INTO edges VALUES ('mibig:BGC0000433', 'mg.compound:nothing', "
                        "'PRODUCES', 'database_assertion', 'test', '', '', NULL, '2026-10-12')")
        with pytest.raises(duckdb.ConstraintException):
            con.execute("INSERT INTO edges VALUES ('mibig:BGC0000433', 'mg.compound:surfactin', "
                        "'PRODUCES', 'a hunch', 'test', '', '', NULL, '2026-10-12')")
    finally:
        con.close()


def test_the_graph_carries_names_properties_and_evidence(built):
    _, db = built
    graph = load_graph(db)
    assert graph.nodes["uniprot:Q70KJ7"]["name"] == "srfAA"
    assert graph.nodes["uniprot:Q70KJ7"]["properties"]["reviewed"] is False
    path = nx.shortest_path(graph, "ncbitaxon:326423", "mg.crop:jujube")
    assert path == ["ncbitaxon:326423", "mibig:BGC0000433", "mg.compound:surfactin",
                    "ncbitaxon:40559", "mg.crop:jujube"]
    assert graph.edges["mg.compound:surfactin", "ncbitaxon:40559"]["citation"].startswith("doi:")


def test_a_broken_csv_is_refused_and_the_old_database_stays(built, tmp_path):
    _, db = built
    before = db.read_bytes()
    out = tmp_path / "processed"
    rows = read_rows(out / "nodes.csv")
    add_rows(out / "nodes.csv", [rows[0]])                 # made up: a node twice (rule 1)
    with pytest.raises(BuildError, match="rule 1"):
        build(out / "nodes.csv", out / "edges.csv", out / "resolution_ledger.csv",
              out / "resolve_summary.json", db)
    assert db.read_bytes() == before
    assert not db.with_name(db.name + ".building").exists()


def test_a_value_duckdb_refuses_leaves_the_old_database(built, tmp_path):
    _, db = built
    before = db.read_bytes()
    out = tmp_path / "processed"
    rows = read_rows(out / "nodes.csv")
    rows[0]["retrieved_at"] = "last Tuesday"               # made up: not a date
    with (out / "nodes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(BuildError, match="DuckDB refused"):
        build(out / "nodes.csv", out / "edges.csv", out / "resolution_ledger.csv",
              out / "resolve_summary.json", db)
    assert db.read_bytes() == before


def test_two_arrows_between_one_pair_are_caught(staging_copy, tmp_path):
    # Made up: a second source stating an arrow MIBiG already states. The rules
    # allow it (rule 12 counts per source), but a DiGraph holds one arrow per
    # pair, so the counts would differ, and the build must say so and leave
    # the database from the run before untouched.
    _, db = _build(staging_copy, tmp_path / "processed")
    before = db.read_bytes()
    add_rows(staging_copy / "curation_edges.csv", [{
        "source_id": "mibig:BGC0000433", "target_id": "mg.compound:surfactin",
        "edge_type": "PRODUCES", "evidence_level": "curated_literature",
        "source": "curation", "source_record_id": "made-up",
        "citation": "doi:10.0000/made-up", "retrieved_at": "2026-10-12"}])
    with pytest.raises(BuildError, match="disagree"):
        _build(staging_copy, tmp_path / "processed")
    assert db.read_bytes() == before
    assert not db.with_name(db.name + ".building").exists()


def test_missing_inputs_say_which_command_makes_them(tmp_path):
    with pytest.raises(BuildError, match="microbegraph.resolve"):
        build(tmp_path / "nodes.csv", tmp_path / "edges.csv", tmp_path / "ledger.csv",
              tmp_path / "summary.json", tmp_path / "db.duckdb")
    with pytest.raises(BuildError, match="build_graph"):
        load_graph(tmp_path / "db.duckdb")


def test_graph_counts_count_by_type():
    graph = nx.DiGraph()
    graph.add_node("a", node_type="Organism")
    graph.add_node("b", node_type="GeneCluster")
    graph.add_edge("a", "b", edge_type="HARBORS")
    assert graph_counts(graph) == {"nodes": 2, "edges": 1,
                                   "node_types": {"GeneCluster": 1, "Organism": 1},
                                   "edge_types": {"HARBORS": 1}}
