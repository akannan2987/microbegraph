"""
Tests for the NCBI Taxonomy adapter, and for keeping an API key secret.

The XML answers are real, captured from NCBI on 2026-10-12
(tests/fixtures/README.md). The key used here is made up.
"""

from __future__ import annotations

import csv
import json
from itertools import pairwise
from pathlib import Path

import pytest
from conftest import FakeResponse, FakeSession, fixture_bytes, make_snapshot, write_mibig_staging

from microbegraph.sources.base import SourceError
from microbegraph.sources.ncbi_taxonomy import (
    EFETCH_URL,
    EINFO_URL,
    PAUSE_WITH_KEY,
    PAUSE_WITHOUT_KEY,
    NcbiTaxonomySource,
    bridge_pathogen_taxids,
    group_of,
    parse_taxa,
)
from microbegraph.validate import check_tables

ORGANISMS = ["326423", "33", "109376", "746360", "2961896"]
PATHOGENS = ["40559", "5518", "36779", "456999", "62727", "2052682"]
FAKE_KEY = "0123456789abcdef0123456789abcdef0123"       # made up, the shape of a real one
FAKE_EMAIL = "someone@example.org"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _empty_bridge(tmp_path: Path) -> Path:
    path = tmp_path / "bridge.csv"
    path.write_text("compound_name,pathogen_curie\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- reading XML
def test_parse_taxa_reads_a_real_answer():
    records = {r["taxid"]: r for r in parse_taxa(fixture_bytes("ncbi_taxonomy",
                                                               "efetch_organisms.xml"))}
    assert sorted(records, key=int) == sorted(ORGANISMS, key=int)
    fzb42 = records["326423"]
    assert fzb42["name"] == "Bacillus velezensis FZB42"
    assert fzb42["rank"] == "strain"
    assert "Bacillus amyloliquefaciens FZB42" in fzb42["synonyms"]
    assert ("2", "Bacteria", "domain") in fzb42["lineage_ex"]         # the 2025 rank name
    assert ("1783272", "Bacillati", "kingdom") in fzb42["lineage_ex"]


def test_merged_number_comes_back_under_the_new_one():
    records = parse_taxa(fixture_bytes("ncbi_taxonomy", "efetch_retired.xml"))
    by_id = {r["taxid"]: r for r in records}
    assert "2056260" not in by_id and by_id["435890"]["aka"] == ["2056260"]
    assert "3897929" not in by_id                                     # deleted: nothing at all


@pytest.mark.parametrize(("taxid", "fixture", "group"), [
    ("326423", "efetch_organisms.xml", "Bacteria"),
    ("109376", "efetch_organisms.xml", "Plants"),
    ("40559", "efetch_pathogens.xml", "Fungi"),
    ("2052682", "efetch_pathogens.xml", "Oomycetes"),
    ("435890", "efetch_retired.xml", "Other"),                    # a ciliate
])
def test_group_from_real_lineages(taxid, fixture, group):
    record = next(r for r in parse_taxa(fixture_bytes("ncbi_taxonomy", fixture))
                  if r["taxid"] == taxid)
    assert group_of([name for _, name, _ in record["lineage_ex"]] + [record["name"]]) == group


def test_bridge_pathogens_are_read_from_the_bridge(tmp_path):
    bridge = tmp_path / "bridge.csv"
    bridge.write_text("pathogen_curie,x\nncbitaxon:5518,a\nncbitaxon:40559,b\n"
                      "ncbitaxon:5518,c\nmg.organism:x,d\n", encoding="utf-8")
    assert bridge_pathogen_taxids(bridge) == ["5518", "40559"]
    assert bridge_pathogen_taxids(tmp_path / "missing.csv") == []


# --------------------------------------------------------------------------- tidy
def _tidied(make_source, tmp_path, organisms=None, pathogens=None):
    source = make_source(NcbiTaxonomySource, bridge_file=_empty_bridge(tmp_path))
    make_snapshot(source.locker,
                  {"einfo.json": fixture_bytes("ncbi_taxonomy", "einfo.json"),
                   "efetch_001.xml": fixture_bytes("ncbi_taxonomy", "efetch_organisms.xml"),
                   "efetch_002.xml": fixture_bytes("ncbi_taxonomy", "efetch_pathogens.xml"),
                   "efetch_003.xml": fixture_bytes("ncbi_taxonomy", "efetch_retired.xml")},
                  asked_for={"organism_taxids": organisms or ORGANISMS + ["2056260", "3897929"],
                             "pathogen_taxids": pathogens or PATHOGENS},
                  source_version="Build261011-2030.1")
    return source.tidy()


def test_tidy_builds_the_family_tree(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    edges = {(e["source_id"], e["target_id"]) for e in _rows(result.edges_path)}
    # FZB42 -> its species -> genus -> ... -> domain, one step at a time.
    chain = ["326423", "492670", "1386", "186817", "1385", "91061", "1239", "1783272", "2"]
    for child, parent in pairwise(chain):
        assert (f"ncbitaxon:{child}", f"ncbitaxon:{parent}") in edges
    # Ranks in between ("species group", "clade") get no node of their own.
    assert "ncbitaxon:653685" not in nodes
    fzb42 = json.loads(nodes["ncbitaxon:326423"]["properties"])
    assert fzb42["group"] == "Bacteria" and fzb42["rank"] == "strain"
    assert fzb42["lineage"].startswith("cellular organisms; Bacteria; Bacillati")
    assert json.loads(nodes["ncbitaxon:1386"]["properties"]) == {"rank": "genus"}


def test_tidy_output_passes_the_twelve_rules(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)
    assert check_tables(_rows(result.nodes_path), _rows(result.edges_path)) == []
    for edge in _rows(result.edges_path):
        assert edge["edge_type"] == "MEMBER_OF"
        assert edge["evidence_level"] == "database_assertion"


def test_tidy_handles_merged_and_deleted_numbers(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert "ncbitaxon:2056260" not in nodes
    assert json.loads(nodes["ncbitaxon:435890"]["properties"])["merged_from"] == "2056260"
    summary = json.loads((tmp_path / "staging" / "ncbi_taxonomy_summary.json").read_text("utf-8"))
    assert summary["merged_taxids"] == {"2056260": "435890"}
    assert summary["taxids_not_found"] == ["3897929"]
    assert result.counts["taxids_merged"] == 1 and result.counts["taxids_not_found"] == 1


def test_pathogens_become_pathogen_nodes(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    botrytis = nodes["ncbitaxon:40559"]
    assert botrytis["node_type"] == "Pathogen" and botrytis["name"] == "Botrytis cinerea"
    assert json.loads(botrytis["properties"])["group"] == "Fungi"
    assert result.counts["pathogen_nodes"] == 6
    # Pathogens get no MEMBER_OF arrows: that edge joins Organism to Organism.
    assert not any(e["source_id"] == "ncbitaxon:40559" for e in _rows(result.edges_path))


def test_a_pathogen_that_is_also_an_organism_stays_an_organism(make_source, tmp_path):
    result = _tidied(make_source, tmp_path, organisms=ORGANISMS + ["40559"])

    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert nodes["ncbitaxon:40559"]["node_type"] == "Organism"
    assert result.counts["pathogens_also_organisms"] == 1


# --------------------------------------------------------------------------- the key
def _server() -> FakeSession:
    return FakeSession({
        EINFO_URL: [FakeResponse(body=fixture_bytes("ncbi_taxonomy", "einfo.json"))],
        EFETCH_URL: [FakeResponse(body=fixture_bytes("ncbi_taxonomy", "efetch_organisms.xml"))],
    })


def test_fetch_without_a_key_paces_for_three_a_second(make_source, tmp_path, monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    source = NcbiTaxonomySource(raw_dir=tmp_path, staging_dir=tmp_path, quiet=True)
    assert source.pause_seconds == PAUSE_WITHOUT_KEY
    monkeypatch.setenv("NCBI_API_KEY", FAKE_KEY)
    source = NcbiTaxonomySource(raw_dir=tmp_path, staging_dir=tmp_path, quiet=True)
    assert source.pause_seconds == PAUSE_WITH_KEY


def test_the_key_travels_only_in_the_post_body(make_source, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NCBI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("NCBI_EMAIL", FAKE_EMAIL)
    write_mibig_staging(tmp_path / "staging", organisms=ORGANISMS)
    session = _server()
    source = make_source(NcbiTaxonomySource, session=session,
                         bridge_file=_empty_bridge(tmp_path), quiet=False)

    [result] = source.fetch()

    method, url, sent = session.sent[-1]
    assert (method, url) == ("POST", EFETCH_URL)
    assert sent["api_key"] == FAKE_KEY and sent["email"] == FAKE_EMAIL
    assert sent["tool"] == "microbegraph"
    # Not in any web address, not in the GET's query, not on screen, not on disk.
    for _, called_url, params in session.sent:
        assert FAKE_KEY not in called_url
        if _ == "GET":
            assert "api_key" not in params and "email" not in params
    assert FAKE_KEY not in capsys.readouterr().out
    for path in [tmp_path / "raw" / "provenance.csv", *result.local_path.iterdir()]:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert FAKE_KEY not in text and FAKE_EMAIL not in text, path.name
    manifest = json.loads((result.local_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["answers"][-1]["sent"]["api_key"] == "set"
    assert manifest["source_version"] == "Build261011-2030.1"


def test_an_error_message_never_repeats_the_key(make_source, tmp_path, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", FAKE_KEY)
    write_mibig_staging(tmp_path / "staging", organisms=ORGANISMS)
    session = FakeSession({
        EINFO_URL: [FakeResponse(body=fixture_bytes("ncbi_taxonomy", "einfo.json"))],
        EFETCH_URL: [FakeResponse(status=400, body=b"bad request")],
    })
    source = make_source(NcbiTaxonomySource, session=session, bridge_file=_empty_bridge(tmp_path))

    with pytest.raises(SourceError) as caught:
        source.fetch()

    assert FAKE_KEY not in str(caught.value)
    assert "HTTP 400" in str(caught.value)


def test_probe_says_whether_a_key_is_set_never_what_it_is(make_source, tmp_path, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", FAKE_KEY)
    source = make_source(NcbiTaxonomySource, session=_server(),
                         bridge_file=_empty_bridge(tmp_path))

    report = source.probe()

    text = "\n".join(report.facts + report.warnings)
    assert report.reachable
    assert "API key        : set (10 requests a second)" in text
    assert FAKE_KEY not in text
    assert "Build261011-2030.1" in text
