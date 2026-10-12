"""
Tests for the PubChem adapter and the snapshot machinery it shares with
NCBI Taxonomy and KEGG (src/microbegraph/sources/api.py).

Every answer the fake server gives is a real one, captured from PubChem on
2026-10-12 (tests/fixtures/README.md).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import requests
from conftest import FakeResponse, FakeSession, fixture_bytes, make_snapshot, write_mibig_staging

from microbegraph import provenance
from microbegraph.sources.api import MANIFEST
from microbegraph.sources.base import SourceError
from microbegraph.sources.pubchem import (
    PROPERTIES_URL,
    SYNONYMS_URL,
    PubchemSource,
    worst_light,
)

# The five real CIDs in the captured answers, and the MIBiG compounds that "recorded" them.
CIDS = {"mg.compound:itaconic-acid": "811", "mg.compound:c-1027": "5281917",
        "mg.compound:subtilosin-a": "16132390", "mg.compound:spiroindimicin": "102196435",
        "mg.compound:not-in-pubchem": "406870990", "mg.compound:no-cid": None}


def _server() -> FakeSession:
    green = {"X-Throttling-Control": "Request Count status: Green (0%), Request Time "
                                     "status: Green (0%), Service status: Green (20%)"}
    return FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json"),
                                      headers=green)],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"),
                                    headers=green)],
    })


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- fetch
def test_fetch_saves_each_answer_and_a_manifest(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    session = _server()
    source = make_source(PubchemSource, session=session)

    [result] = source.fetch()

    assert result.outcome == "downloaded"
    folder = result.local_path
    assert ":" not in folder.name                       # Windows-safe folder name
    assert sorted(p.name for p in folder.iterdir()) == [
        MANIFEST, "properties_001.json", "synonyms_001.json"]
    # Saved byte for byte, exactly as the server sent them.
    assert (folder / "properties_001.json").read_bytes() == fixture_bytes(
        "pubchem", "properties_001.json")
    # The CIDs went in the POST body, in number order, and nothing else did.
    assert session.sent[0] == ("POST", PROPERTIES_URL,
                               {"cid": "811,5281917,16132390,102196435,406870990"})
    manifest = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["asked_for"]["cids"] == ["811", "5281917", "16132390", "102196435",
                                             "406870990"]
    assert manifest["context"]["mibig_compounds_by_cid"]["811"] == ["mg.compound:itaconic-acid"]


def test_fetch_logs_one_provenance_row_per_answer(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    make_source(PubchemSource, session=_server()).fetch()

    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert [r["outcome"] for r in rows] == ["downloaded", "downloaded"]
    assert rows[0]["url"] == PROPERTIES_URL
    assert rows[0]["n_records"] == "4"                  # 406870990 came back empty
    assert rows[0]["local_path"].endswith("properties_001.json")
    assert len(rows[0]["sha256"]) == 64


def test_second_fetch_on_the_same_day_asks_nothing(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    session = _server()
    source = make_source(PubchemSource, session=session)
    source.fetch()
    calls_after_first = len(session.calls)

    [again] = source.fetch()

    assert again.outcome == "already_present"
    assert len(session.calls) == calls_after_first     # no request was made
    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert rows[-1]["outcome"] == "already_present"
    assert rows[-1]["local_path"].endswith(MANIFEST)


def test_a_different_question_makes_a_new_snapshot(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    source = make_source(PubchemSource, session=_server())
    source.fetch()
    write_mibig_staging(tmp_path / "staging", compounds={"mg.compound:itaconic-acid": "811"})

    [result] = source.fetch()

    assert result.outcome == "downloaded"
    assert len(source.snapshots()) == 2


def test_a_failed_first_request_leaves_no_empty_folder(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    source = make_source(PubchemSource, session=FakeSession({}), max_attempts=1)

    with pytest.raises(requests.ConnectionError):
        source.fetch()

    assert not (tmp_path / "raw" / "pubchem").exists()


def test_fetch_needs_the_mibig_tables_first(make_source):
    with pytest.raises(SourceError, match="--source mibig"):
        make_source(PubchemSource, session=_server()).fetch()


def test_traffic_light_reading():
    assert worst_light("Request Count status: Green (0%), Request Time status: "
                       "Yellow (60%), Service status: Green (20%)") == "Yellow"
    assert worst_light("") == "Green"
    assert worst_light("Request Count status: Red (90%), Service status: Black (100%)") == "Black"


def test_fetch_slows_down_when_the_light_is_not_green(make_source, tmp_path, monkeypatch):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    yellow = {"X-Throttling-Control": "Request Count status: Yellow (55%)"}
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json"),
                                      headers=yellow)],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
    })
    source = make_source(PubchemSource, session=session)
    factors: list[float] = []
    monkeypatch.setattr(source, "pause", lambda factor=1.0: factors.append(factor))

    source.fetch()

    assert factors == [4.0, 1.0]


# --------------------------------------------------------------------------- tidy
def _tidied(make_source, tmp_path):
    source = make_source(PubchemSource)
    make_snapshot(source.locker,
                  {"properties_001.json": fixture_bytes("pubchem", "properties_001.json"),
                   "synonyms_001.json": fixture_bytes("pubchem", "synonyms_001.json")},
                  asked_for={"cids": ["811", "5281917", "16132390", "102196435", "406870990"]},
                  context={"mibig_compounds_by_cid": {"811": ["mg.compound:itaconic-acid"]}},
                  source_version="live")
    return source.tidy()


def test_tidy_counts_what_pubchem_knows_and_what_it_does_not(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    assert result.counts == {
        "cids_requested": 5, "compounds_found": 4, "cids_not_in_pubchem": 1,
        "compounds_with_synonyms": 3, "compounds_with_kegg_id": 1, "compounds_with_chebi_id": 2,
    }
    summary = json.loads((tmp_path / "staging" / "pubchem_summary.json").read_text("utf-8"))
    assert summary["cids_not_in_pubchem"] == ["406870990"]


def test_tidy_turns_an_answer_into_a_compound_node(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert "pubchem.compound:406870990" not in nodes          # never an empty node
    itaconic = nodes["pubchem.compound:811"]
    assert itaconic["node_type"] == "Compound"
    assert itaconic["name"] == "Itaconic acid"
    assert itaconic["retrieved_at"] == "2026-10-12"
    props = json.loads(itaconic["properties"])
    assert props["formula"] == "C5H6O4"
    assert props["molecular_weight"] == pytest.approx(130.10)  # text in, number out
    assert props["inchikey"] == "LVHBHZANLOWSRM-UHFFFAOYSA-N"
    assert props["kegg_compound_ids"] == "C00490"
    assert props["chebi_ids"] == "CHEBI:30838"
    assert props["mibig_compound_ids"] == "mg.compound:itaconic-acid"
    assert props["synonyms"].split("|")[0] == "Itaconic acid"
    assert len(props["synonyms"].split("|")) == 20             # the first 20 of 95


def test_tidy_without_a_finished_snapshot_says_what_to_run(make_source, tmp_path):
    source = make_source(PubchemSource)
    (source.locker / "2026-10-12T055202Z").mkdir(parents=True)  # unfinished: no manifest

    with pytest.raises(SourceError, match="--source pubchem"):
        source.tidy()


def test_probe_points_out_an_unfinished_fetch(make_source, tmp_path):
    source = make_source(PubchemSource, session=FakeSession({}), max_attempts=1)
    (source.locker / "2026-10-12T055202Z").mkdir(parents=True)

    report = source.probe()

    assert report.reachable is False
    assert any("unfinished" in w for w in report.warnings)


def test_a_fault_instead_of_an_answer_stops_the_fetch_after_logging_it(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    fault = {"Fault": {"Code": "PUGREST.ServerError", "Message": "Unexpected error"}}
    session = FakeSession({PROPERTIES_URL: [FakeResponse(json_body=fault)]})
    source = make_source(PubchemSource, session=session)

    with pytest.raises(SourceError, match="PubChem says: Unexpected error"):
        source.fetch()

    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert len(rows) == 1 and rows[0]["n_records"] == ""      # logged, then stopped
    assert source.snapshots() == []                           # unfinished, so tidy ignores it
