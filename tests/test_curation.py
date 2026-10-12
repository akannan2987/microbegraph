"""
Tests for the curated bridge (curation/compound_pathogen_crop.csv).

Two kinds of test: the REAL bridge file in the repository must pass every
check against real NCBI answers, and each check must catch the mistake it
exists to catch.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from conftest import fixture_bytes, make_snapshot, write_mibig_staging

from microbegraph.paths import BRIDGE_FILE
from microbegraph.sources.base import SourceError
from microbegraph.sources.curation import (
    BRIDGE_COLUMNS,
    CurationSource,
    check_rows,
    read_bridge,
)
from microbegraph.sources.ncbi_taxonomy import NcbiTaxonomySource
from microbegraph.validate import check_tables

BRIDGE_COMPOUNDS = {f"mg.compound:{slug}": None for slug in (
    "iturin", "fengycin", "bacillomycin-d", "2-4-diacetylphloroglucinol", "pyrrolnitrin",
    "pyoluteorin", "surfactin")}
GOOD_ROW = {
    "compound_name": "surfactin", "compound_curie": "mg.compound:surfactin",
    "pathogen_name": "Botrytis cinerea", "pathogen_curie": "ncbitaxon:40559",
    "pathogen_type": "fungus", "disease": "grey mould", "crop_name": "jujube",
    "crop_curie": "mg.crop:jujube", "crop_scientific_name": "Ziziphus jujuba",
    "crop_category": "fruit", "relationship": "INHIBITS",
    "citation": "doi:10.1186/s13568-023-01543-w", "confidence": "0.90",
    "added_on": "2026-10-12", "notes": "",
}
NCBI = {"ncbitaxon:40559": {"name": "Botrytis cinerea", "group": "Fungi"}}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _ncbi_staging(make_source, tmp_path: Path) -> None:
    """Real NCBI answers for the six bridge pathogens, tidied into staging."""
    source = make_source(NcbiTaxonomySource, bridge_file=tmp_path / "none.csv")
    make_snapshot(source.locker,
                  {"efetch_001.xml": fixture_bytes("ncbi_taxonomy", "efetch_pathogens.xml")},
                  asked_for={"organism_taxids": [],
                             "pathogen_taxids": ["40559", "5518", "36779", "456999",
                                                 "62727", "2052682"]})
    source.tidy()


# --------------------------------------------------------------------------- the real file
def test_the_real_bridge_passes_every_check_against_real_ncbi_answers(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=BRIDGE_COMPOUNDS)
    _ncbi_staging(make_source, tmp_path)

    result = make_source(CurationSource, bridge_file=BRIDGE_FILE).tidy()

    assert result.counts["rows_checked_against_ncbi"] == result.counts["rows_read"]
    nodes, edges = _rows(result.nodes_path), _rows(result.edges_path)
    external = {cid: "Compound" for cid in BRIDGE_COMPOUNDS}
    assert check_tables(nodes, edges, external) == []
    for edge in edges:
        assert edge["evidence_level"] == "curated_literature"
        assert edge["citation"].startswith(("doi:", "pmid:"))


def test_the_worked_example_is_in_the_bridge(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=BRIDGE_COMPOUNDS)
    result = make_source(CurationSource, bridge_file=BRIDGE_FILE).tidy()

    edges = {(e["source_id"], e["target_id"], e["edge_type"]): e
             for e in _rows(result.edges_path)}
    inhibits = edges[("mg.compound:surfactin", "ncbitaxon:40559", "INHIBITS")]
    assert inhibits["citation"] == "doi:10.1186/s13568-023-01543-w"
    assert ("ncbitaxon:40559", "mg.crop:jujube", "INFECTS") in edges
    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert json.loads(nodes["mg.crop:jujube"]["properties"]) == {
        "category": "fruit", "scientific_name": "Ziziphus jujuba"}
    assert nodes["ncbitaxon:40559"]["node_type"] == "Pathogen"


def test_rows_sharing_an_arrow_become_one_arrow(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=BRIDGE_COMPOUNDS)
    result = make_source(CurationSource, bridge_file=BRIDGE_FILE).tidy()

    edges = [e for e in _rows(result.edges_path)
             if e["source_id"] == "mg.compound:bacillomycin-d"]
    # Two rows (wheat and maize) for one compound and one pathogen: one INHIBITS arrow,
    # keeping the higher of the two confidences.
    assert len(edges) == 1 and edges[0]["confidence"] == "0.90"
    pathogen = next(r for r in _rows(result.nodes_path) if r["node_id"] == "ncbitaxon:5518")
    assert json.loads(pathogen["properties"])["diseases"] == (
        "Fusarium head blight (wheat)|Gibberella ear rot (maize)")


def test_fetch_downloads_nothing(make_source):
    assert make_source(CurationSource, bridge_file=BRIDGE_FILE).fetch() == []


def test_the_real_bridge_has_exactly_the_documented_columns():
    header, rows = read_bridge(BRIDGE_FILE)
    assert tuple(header) == BRIDGE_COLUMNS
    assert len(rows) >= 8


# --------------------------------------------------------------------------- each check
@pytest.mark.parametrize(("change", "check"), [
    ({"disease": ""}, "check 2"),
    ({"relationship": "PROMOTES"}, "check 3"),
    ({"compound_curie": "mg.compound:not-in-mibig"}, "check 4"),
    ({"pathogen_curie": "ncbitaxon:Botrytis"}, "check 5"),
    ({"pathogen_type": "mould"}, "check 6"),
    ({"crop_curie": "mg.crop:Jujube"}, "check 7"),
    ({"crop_category": "tree"}, "check 8"),
    ({"citation": "Xiao 2023"}, "check 9"),
    ({"confidence": "high"}, "check 10"),
    ({"confidence": "1.5"}, "check 10"),
    ({"added_on": "12/10/2026"}, "check 11"),
    ({"added_on": "20261012"}, "check 11"),
    ({"pathogen_name": "Botryotinia fuckeliana"}, "check 13"),
    ({"pathogen_type": "oomycete"}, "check 13"),
    ({"pathogen_curie": "ncbitaxon:5518"}, "check 13"),
])
def test_each_check_catches_its_mistake(change, check):
    row = {**GOOD_ROW, **change}
    problems = check_rows(list(BRIDGE_COLUMNS), [(2, row)], {"mg.compound:surfactin"}, NCBI)
    assert problems, f"{change} was not caught"
    assert all(p.startswith(check) for p in problems), problems
    assert "line 2" in problems[0]


def test_a_good_row_passes():
    assert check_rows(list(BRIDGE_COLUMNS), [(2, GOOD_ROW)], {"mg.compound:surfactin"},
                      NCBI) == []


def test_wrong_columns_are_caught_first():
    problems = check_rows(["compound_name", "citation"], [], set(), None)
    assert len(problems) == 1 and problems[0].startswith("check 1")


def test_a_repeated_row_is_caught():
    problems = check_rows(list(BRIDGE_COLUMNS), [(2, GOOD_ROW), (3, dict(GOOD_ROW))],
                          {"mg.compound:surfactin"}, NCBI)
    assert problems == ["check 12: line 3 repeats line 2 (same compound, pathogen and crop)"]


def test_without_ncbi_the_name_check_is_skipped():
    row = {**GOOD_ROW, "pathogen_name": "Botryotinia fuckeliana"}
    assert check_rows(list(BRIDGE_COLUMNS), [(2, row)], {"mg.compound:surfactin"}, None) == []


def test_tidy_refuses_and_writes_nothing_when_a_row_is_wrong(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds={"mg.compound:surfactin": None})
    bridge = tmp_path / "bridge.csv"
    with bridge.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRIDGE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerow({**GOOD_ROW, "citation": "see the paper"})

    with pytest.raises(SourceError, match="line 2"):
        make_source(CurationSource, bridge_file=bridge).tidy()

    assert not (tmp_path / "staging" / "curation_nodes.csv").exists()
