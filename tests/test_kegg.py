"""
Tests for the KEGG adapter.

The answers are real, captured from KEGG on 2026-10-12. The compound-to-map
list is an exact excerpt of the real one (tests/fixtures/README.md).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from conftest import FakeResponse, FakeSession, fixture_bytes, make_snapshot

from microbegraph.sources.base import NODE_COLUMNS, SourceError, write_table
from microbegraph.sources.kegg import (
    QUESTIONS,
    KeggSource,
    parse_categories,
    parse_links,
    parse_pathway_list,
    release_dates,
    version_text,
)
from microbegraph.validate import check_tables

FILES = ("info_kegg.txt", "list_pathway.txt", "link_pathway_compound.txt",
         "pathway_categories.txt")


def _text(name: str) -> str:
    return fixture_bytes("kegg", name).decode("utf-8")


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _pubchem_staging(staging_dir: Path) -> None:
    """Two compounds with KEGG numbers (itaconic acid, caffeine) and one without."""
    rows = [
        {"node_id": "pubchem.compound:811", "node_type": "Compound", "name": "Itaconic acid",
         "properties": json.dumps({"kegg_compound_ids": "C00490"}),
         "source": "pubchem", "retrieved_at": "2026-10-12"},
        {"node_id": "pubchem.compound:2519", "node_type": "Compound", "name": "Caffeine",
         "properties": json.dumps({"kegg_compound_ids": "C07481"}),
         "source": "pubchem", "retrieved_at": "2026-10-12"},
        {"node_id": "pubchem.compound:5281917", "node_type": "Compound",
         "name": "C-1027 Chromophore", "properties": "{}",
         "source": "pubchem", "retrieved_at": "2026-10-12"},
    ]
    write_table(staging_dir / "pubchem_nodes.csv", NODE_COLUMNS, rows)


# --------------------------------------------------------------------------- parsing
def test_release_dates_from_a_real_answer():
    assert release_dates(_text("info_kegg.txt")) == {"pathway": "2026/10/09",
                                                     "compound": "2026/10/09"}
    assert version_text(_text("info_kegg.txt")) == "pathway 2026/10/09, compound 2026/10/09"


def test_pathway_list_and_links():
    names = parse_pathway_list(_text("list_pathway.txt"))
    assert len(names) == 587
    assert names["map00660"] == "C5-Branched dibasic acid metabolism"
    links = parse_links(_text("link_pathway_compound.txt"))
    assert links["C00490"] == {"map00660", "map01100"}


def test_categories_follow_the_outline():
    categories = parse_categories(_text("pathway_categories.txt"))
    assert categories["map00660"] == ("Metabolism", "Carbohydrate metabolism")
    assert categories["map01100"] == ("Metabolism", "Global and overview maps")
    assert categories["map00232"][1] == "Biosynthesis of other secondary metabolites"


# --------------------------------------------------------------------------- fetch
def test_fetch_asks_four_questions_and_keeps_every_answer(make_source):
    session = FakeSession({url: [FakeResponse(body=fixture_bytes("kegg", name))]
                           for name, url in QUESTIONS.items()})
    source = make_source(KeggSource, session=session)

    [result] = source.fetch()

    assert session.calls == list(QUESTIONS.values())
    assert sorted(p.name for p in result.local_path.iterdir()) == sorted(
        [*FILES, "manifest.json"])
    manifest = json.loads((result.local_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_version"] == "pathway 2026/10/09, compound 2026/10/09"
    assert manifest["notes"]["terms_of_use"].endswith("legal.html")


def test_probe_states_the_terms_of_use(make_source):
    session = FakeSession({QUESTIONS["info_kegg.txt"]: [
        FakeResponse(body=fixture_bytes("kegg", "info_kegg.txt"))]})
    report = make_source(KeggSource, session=session).probe()
    text = "\n".join(report.facts)
    assert "academic use only" in text
    assert "release        : pathway 2026/10/09, compound 2026/10/09" in text


# --------------------------------------------------------------------------- tidy
def _tidied(make_source, tmp_path):
    source = make_source(KeggSource)
    make_snapshot(source.locker, {name: fixture_bytes("kegg", name) for name in FILES},
                  asked_for={"questions": list(QUESTIONS.values())})
    _pubchem_staging(tmp_path / "staging")
    return source.tidy()


def test_tidy_links_compounds_to_pathways(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    edges = {(e["source_id"], e["target_id"]): e for e in _rows(result.edges_path)}
    itaconic = edges[("pubchem.compound:811", "kegg.pathway:map00660")]
    assert itaconic["edge_type"] == "PARTICIPATES_IN"
    assert itaconic["evidence_level"] == "database_assertion"
    assert itaconic["source_record_id"] == "C00490"
    assert ("pubchem.compound:2519", "kegg.pathway:map00232") in edges     # caffeine metabolism
    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert nodes["kegg.pathway:map00660"]["name"] == "C5-Branched dibasic acid metabolism"
    assert json.loads(nodes["kegg.pathway:map00660"]["properties"]) == {
        "category": "Metabolism", "subcategory": "Carbohydrate metabolism"}


def test_tidy_leaves_out_maps_of_maps(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    targets = {e["target_id"] for e in _rows(result.edges_path)}
    assert "kegg.pathway:map01100" not in targets          # "Metabolic pathways"
    assert "kegg.pathway:map01060" not in targets          # a structure transformation map
    # 811: map01100. 2519: map01060, map01065, map01100, map01110, map01120.
    assert result.counts["links_to_overview_maps_skipped"] == 6
    assert result.counts["participates_in_edges"] == 2
    assert result.counts["our_compounds_with_kegg_id"] == 2


def test_tidy_output_passes_the_rules_with_pubchem_compounds_as_outside_nodes(
        make_source, tmp_path):
    result = _tidied(make_source, tmp_path)
    external = {"pubchem.compound:811": "Compound", "pubchem.compound:2519": "Compound"}
    assert check_tables(_rows(result.nodes_path), _rows(result.edges_path), external) == []


def test_tidy_needs_pubchem_first(make_source):
    source = make_source(KeggSource)
    make_snapshot(source.locker, {name: fixture_bytes("kegg", name) for name in FILES},
                  asked_for={"questions": list(QUESTIONS.values())})
    with pytest.raises(SourceError, match="--source pubchem"):
        source.tidy()


def test_tidy_refuses_an_answer_that_is_not_kegg(make_source, tmp_path):
    source = make_source(KeggSource)
    files = {name: fixture_bytes("kegg", name) for name in FILES}
    files["link_pathway_compound.txt"] = b"<html>Service unavailable</html>"
    make_snapshot(source.locker, files, asked_for={"questions": list(QUESTIONS.values())})
    _pubchem_staging(tmp_path / "staging")

    with pytest.raises(SourceError, match="link_pathway_compound.txt"):
        source.tidy()
