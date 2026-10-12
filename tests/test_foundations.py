"""
Tests for the shared foundations: the ontology, the twelve rules, identifiers,
the provenance log, and the fetch command's front door.
"""

from __future__ import annotations

import pytest

from microbegraph import fetch, provenance
from microbegraph.ontology import (
    EDGE_TYPES,
    EVIDENCE_LEVELS,
    NODE_TYPES,
    SUBTYPE_OF,
    is_a,
    is_valid_curie,
)
from microbegraph.sources.base import slugify, write_files_together, write_table
from microbegraph.validate import check_tables


# --- the ontology ---------------------------------------------------------------
def test_every_edge_type_connects_known_node_types():
    for edge_type, (start, end) in EDGE_TYPES.items():
        assert start in NODE_TYPES and end in NODE_TYPES, edge_type


def test_a_pathogen_is_a_kind_of_organism_and_not_the_other_way_round():
    assert is_a("Pathogen", "Organism") and is_a("Pathogen", "Pathogen")
    assert not is_a("Organism", "Pathogen")
    assert not is_a("Compound", "Organism")
    for kind, parent in SUBTYPE_OF.items():
        assert kind in NODE_TYPES and parent in NODE_TYPES


def test_nine_nouns_ten_verbs_four_levels():
    assert (len(NODE_TYPES), len(EDGE_TYPES), len(EVIDENCE_LEVELS)) == (9, 10, 4)
    assert EVIDENCE_LEVELS[0] == "curated_experimental"
    assert EVIDENCE_LEVELS[-1] == "inferred"


@pytest.mark.parametrize("curie, ok", [
    ("ncbitaxon:326423", True), ("mibig:BGC0000433", True), ("mg.compound:surfactin", True),
    ("326423", False), ("madeup:1", False), ("ncbitaxon:", False),
])
def test_curie_check(curie, ok):
    assert is_valid_curie(curie) is ok


# --- identifiers from names -------------------------------------------------------
@pytest.mark.parametrize("name, slug", [
    ("surfactin", "surfactin"),
    ("Bacillomycin D", "bacillomycin-d"),
    ("δ-cadinene", "delta-cadinene"),
    ("(-)-menthol", "minus-menthol"),
    ("(+)-menthol", "plus-menthol"),
    ("  Iturin  A ", "iturin-a"),
    ("2,4-diacetylphloroglucinol", "2-4-diacetylphloroglucinol"),
])
def test_slugify(name, slug):
    assert slugify(name) == slug


def test_mirror_image_molecules_stay_apart():
    assert slugify("(+)-menthol") != slugify("(-)-menthol")


# --- the twelve rules -------------------------------------------------------------
def good_tables():
    nodes = [
        {"node_id": "ncbitaxon:1", "node_type": "Organism", "name": "a microbe",
         "source": "test", "retrieved_at": "2026-10-10"},
        {"node_id": "mibig:BGC0000001", "node_type": "GeneCluster", "name": "a cluster",
         "source": "test", "retrieved_at": "2026-10-10"},
    ]
    edges = [
        {"source_id": "ncbitaxon:1", "target_id": "mibig:BGC0000001", "edge_type": "HARBORS",
         "evidence_level": "curated_experimental", "source": "test", "citation": "",
         "confidence": "0.5"},
    ]
    return nodes, edges


def test_good_tables_pass():
    assert check_tables(*good_tables()) == []


def test_a_pathogen_may_harbour_a_cluster_but_an_organism_may_not_infect():
    nodes, edges = good_tables()
    nodes[0]["node_type"] = "Pathogen"              # Fusarium graminearum, say
    assert check_tables(nodes, edges) == []

    nodes, edges = good_tables()
    nodes.append({"node_id": "mg.crop:wheat", "node_type": "Crop", "name": "wheat",
                  "source": "test", "retrieved_at": "2026-10-10"})
    edges[0].update(target_id="mg.crop:wheat", edge_type="INFECTS")
    problems = check_tables(nodes, edges)
    assert any(p.startswith("rule 8:") for p in problems), problems


@pytest.mark.parametrize("break_it, rule", [
    (lambda n, e: n.append(dict(n[0])), "rule 1"),
    (lambda n, e: n[0].update(node_id="nonsense"), "rule 2"),
    (lambda n, e: n[0].update(node_type="Vegetable"), "rule 3"),
    (lambda n, e: n[0].update(name=" "), "rule 4"),
    (lambda n, e: n[0].update(retrieved_at=""), "rule 5"),
    (lambda n, e: e[0].update(target_id="mibig:BGC9999999"), "rule 6"),
    (lambda n, e: e[0].update(edge_type="LIKES"), "rule 7"),
    (lambda n, e: e[0].update(edge_type="PRODUCES"), "rule 8"),
    (lambda n, e: e[0].update(evidence_level="a hunch"), "rule 9"),
    (lambda n, e: e[0].update(evidence_level="curated_literature"), "rule 10"),
    (lambda n, e: e[0].update(confidence="1.7"), "rule 11"),
    (lambda n, e: e.append(dict(e[0])), "rule 12"),
])
def test_each_rule_catches_its_mistake(break_it, rule):
    nodes, edges = good_tables()
    break_it(nodes, edges)
    problems = check_tables(nodes, edges)
    assert any(p.startswith(rule + ":") for p in problems), problems


# --- the provenance log ---------------------------------------------------------
def test_provenance_appends_and_never_rewrites(tmp_path):
    log = tmp_path / "provenance.csv"
    for outcome in ("downloaded", "already_present"):
        row = {c: "x" for c in provenance.COLUMNS}
        row.update(source="mibig", local_path="f.tar.gz", outcome=outcome)
        provenance.append(row, log_path=log)
    rows = provenance.read(log)
    assert [r["outcome"] for r in rows] == ["downloaded", "already_present"]
    assert log.read_text(encoding="utf-8").count("retrieved_at") == 1     # header once
    assert provenance.latest("mibig", "f.tar.gz", log)["outcome"] == "downloaded"


def test_provenance_refuses_half_filled_rows(tmp_path):
    with pytest.raises(ValueError, match="Missing"):
        provenance.append({"source": "mibig"}, log_path=tmp_path / "p.csv")


def test_tables_are_written_whole_or_not_at_all(tmp_path):
    path = tmp_path / "t.csv"
    assert write_table(path, ["a", "b"], [{"a": 1, "b": 2}]) == 1
    assert path.read_text(encoding="utf-8").splitlines() == ["a,b", "1,2"]
    assert not list(tmp_path.glob("*.tmp"))


def test_files_change_together_or_not_at_all(tmp_path):
    keep = tmp_path / "a.csv"
    keep.write_text("old", encoding="utf-8")
    blocked = tmp_path / "missing_folder_is_a_file"
    blocked.write_text("", encoding="utf-8")       # a FILE where a folder is needed
    with pytest.raises(OSError):
        write_files_together({keep: "new", blocked / "b.csv": "new"})
    assert keep.read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob("*.tmp"))


# --- the command's front door ---------------------------------------------------
def test_cli_lists_sources(capsys):
    assert fetch.main(["--list"]) == 0
    assert "mibig" in capsys.readouterr().out


def test_cli_asks_which_sources(capsys):
    assert fetch.main([]) == 2
    assert "--all" in capsys.readouterr().out


def test_cli_tidy_only_runs_offline(monkeypatch, make_adapter, archive_in_locker, capsys):
    adapter = make_adapter()
    monkeypatch.setattr(fetch, "get_source", lambda name: adapter)
    assert fetch.main(["--tidy-only", "--source", "mibig"]) == 0
    out = capsys.readouterr().out
    assert "mibig_nodes.csv" in out and "entries_active" in out


def test_cli_turns_errors_into_messages(monkeypatch, make_adapter, capsys):
    adapter = make_adapter()                       # empty locker: tidy must fail politely
    monkeypatch.setattr(fetch, "get_source", lambda name: adapter)
    assert fetch.main(["--tidy-only", "--all"]) == 1
    assert "FAILED" in capsys.readouterr().out
