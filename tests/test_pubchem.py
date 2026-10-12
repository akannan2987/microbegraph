"""
Tests for the PubChem adapter and the snapshot machinery it shares with
NCBI Taxonomy and KEGG (src/microbegraph/sources/api.py).

Every answer the fake server gives is a real one, captured from PubChem on
2026-10-12 (tests/fixtures/README.md), except where a test says otherwise.
From Phase 4b the fetch has three rounds: the numbers MIBiG gives, a name
search, and the numbers the name search found.
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import pytest
import requests
from conftest import FakeResponse, FakeSession, fixture_bytes, make_snapshot, write_mibig_staging

from microbegraph import provenance
from microbegraph.sources.api import MANIFEST
from microbegraph.sources.base import NODE_COLUMNS, SourceError, write_table
from microbegraph.sources.pubchem import (
    BULK_FILE,
    BULK_URL,
    NAME_SEARCH_URL,
    PROPERTIES_URL,
    SYNONYMS_URL,
    PubchemSource,
    worst_light,
)

# The five real CIDs in the captured answers, and the MIBiG compounds that "recorded" them.
CIDS = {"mg.compound:itaconic-acid": "811", "mg.compound:c-1027": "5281917",
        "mg.compound:subtilosin-a": "16132390", "mg.compound:spiroindimicin": "102196435",
        "mg.compound:not-in-pubchem": "406870990", "mg.compound:no-cid": None}


@pytest.fixture(autouse=True)
def no_review_file(tmp_path, monkeypatch):
    """The fetch also asks about numbers in the review file; these tests use none."""
    from microbegraph.sources import pubchem
    monkeypatch.setattr(pubchem, "REVIEW_FILE", tmp_path / "no_such_file.csv")


NOT_FOUND = FakeResponse(status=404, body=fixture_bytes("pubchem", "name_search_not_found.json"))


def _server() -> FakeSession:
    green = {"X-Throttling-Control": "Request Count status: Green (0%), Request Time "
                                     "status: Green (0%), Service status: Green (20%)"}
    return FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json"),
                                      headers=green)],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"),
                                    headers=green)],
        NAME_SEARCH_URL: [NOT_FOUND],          # Phase 4b: every name searched is unknown here
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
        MANIFEST, "names_001.json", "properties_001.json", "synonyms_001.json"]
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
    assert [r["outcome"] for r in rows] == ["downloaded"] * 3
    assert rows[0]["url"] == PROPERTIES_URL
    assert rows[2]["url"] == NAME_SEARCH_URL
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
        NAME_SEARCH_URL: [NOT_FOUND],
    })
    source = make_source(PubchemSource, session=session)
    factors: list[float] = []
    monkeypatch.setattr(source, "pause", lambda factor=1.0: factors.append(factor))

    source.fetch()

    # Round 1 slows down after the yellow light; each name search waits four
    # pauses (one a second at the real pace), and three names are searched.
    assert factors == [4.0, 1.0, 4.0, 4.0, 4.0]


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


# --------------------------------------------------------------- Phase 4b: the name search
def _mibig_compounds(staging: Path, rows: list[tuple[str, str, dict]]) -> None:
    """A small mibig_nodes.csv: (compound id, name, properties) for each compound."""
    write_table(staging / "mibig_nodes.csv", NODE_COLUMNS, [
        {"node_id": node_id, "node_type": "Compound", "name": name,
         "properties": json.dumps(props), "source": "mibig", "retrieved_at": "2026-10-12"}
        for node_id, name, props in rows])


def _found(cid: int) -> FakeResponse:
    """A name-search hit, shaped like the real one in name_search_found.json."""
    return FakeResponse(json_body={"IdentifierList": {"CID": [cid]}})


def test_round_two_asks_only_names_that_can_change_a_decision(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        # its number lists its name (Itaconic acid), so there's nothing to search
        ("mg.compound:itaconic-acid", "itaconic acid", {"pubchem_cid": 811}),
        # its number doesn't list its name: searched
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917, "formula": "C1"}),
        # no number, but a formula a name match could be checked against: searched
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
        # no number and no formula: a name match could never be confirmed, so skipped
        ("mg.compound:mystery", "mystery", {}),
    ])
    session = _server()
    make_source(PubchemSource, session=session).fetch()

    asked = [body["name"] for method, url, body in session.sent if url == NAME_SEARCH_URL]
    assert asked == ["C-1027 X", "itaconate"]


def test_a_number_the_name_search_finds_is_described_in_round_three(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
    ])
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json"))],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
        NAME_SEARCH_URL: [NOT_FOUND, _found(811)],      # C-1027 X: no; itaconate: 811
    })
    source = make_source(PubchemSource, session=session)
    [result] = source.fetch()

    cids_sent = [body["cid"] for method, url, body in session.sent if url == PROPERTIES_URL]
    assert cids_sent == ["5281917", "811"]               # round 1, then round 3
    tidied = source.tidy()
    nodes = {r["node_id"]: json.loads(r["properties"]) for r in _rows(tidied.nodes_path)}
    itaconic = nodes["pubchem.compound:811"]
    assert itaconic["found_by_name"] == "mg.compound:itaconate"
    assert "mibig_compound_ids" not in itaconic           # no MIBiG entry gives 811 here
    assert itaconic["names_matching_mibig"] == "itaconate"     # name 2 of the 95
    assert itaconic["synonym_count"] == 95                # the full list, though synonyms keeps 20
    assert tidied.counts["names_searched"] == 2
    assert tidied.counts["names_found_one_number"] == 1
    assert tidied.counts["names_not_found"] == 1
    assert tidied.counts["cids_found_by_name"] == 1


def test_a_busy_pubchem_stops_the_search_cleanly_and_the_next_run_carries_on(
        make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:a-one", "a one", {"formula": "C1"}),
        ("mg.compound:b-two", "b two", {"formula": "C2"}),
        ("mg.compound:c-three", "c three", {"formula": "C3"}),
    ])
    busy = FakeResponse(status=429, body=b"<html>429 Too Many Requests</html>")
    session = FakeSession({NAME_SEARCH_URL: [NOT_FOUND, busy]})
    source = make_source(PubchemSource, session=session, max_attempts=2)

    with pytest.raises(SourceError, match="after 1 of 3 names"):
        source.fetch()
    [partial] = source.snapshots()                        # finished, so tidy can read it
    manifest = json.loads((partial / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["complete"] is False
    assert manifest["notes"]["names_not_asked"] == ["mg.compound:b-two", "mg.compound:c-three"]

    session = FakeSession({NAME_SEARCH_URL: [NOT_FOUND]})
    source = make_source(PubchemSource, session=session)
    [result] = source.fetch()

    asked = [body["name"] for method, url, body in session.sent if url == NAME_SEARCH_URL]
    assert asked == ["b two", "c three"]                   # "a one" was carried over
    assert (result.local_path / "names_carried_over.json").exists()
    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert [r["outcome"] for r in rows if "carried" in r["local_path"]] == ["already_present"]
    assert source.tidy().counts["names_searched"] == 3


def test_a_refusal_in_round_three_keeps_the_name_search_for_the_next_run(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
    ])
    busy = FakeResponse(status=429, body=b"<html>429 Too Many Requests</html>")
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json")), busy],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
        NAME_SEARCH_URL: [NOT_FOUND, _found(811)],      # itaconate is found under 811
    })
    source = make_source(PubchemSource, session=session, max_attempts=2)
    with pytest.raises(SourceError, match="in round 3"):
        source.fetch()
    [partial] = source.snapshots()
    manifest = json.loads((partial / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["complete"] is False
    assert manifest["notes"]["names_not_asked"] == ["mg.compound:itaconate"]
    # tidy never uses half an answer: 811 wasn't described, so nothing points at it
    assert source.tidy().counts["cids_found_by_name"] == 0

    session = _server()
    source = make_source(PubchemSource, session=session)
    source.fetch()
    assert [b for m, u, b in session.sent if u == NAME_SEARCH_URL] == []    # all carried over
    cids_sent = [b["cid"] for m, u, b in session.sent if u == PROPERTIES_URL]
    assert cids_sent == ["811"]               # round 1 carried over too; round 3 asked again
    assert source.tidy().counts["cids_found_by_name"] == 1


def test_after_a_stop_in_round_two_round_three_is_left_for_the_next_run(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
        ("mg.compound:zzz", "zzz", {"formula": "C1"}),
    ])
    busy = FakeResponse(status=429, body=b"<html>429 Too Many Requests</html>")
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json"))],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
        NAME_SEARCH_URL: [_found(811), busy],           # itaconate: 811; then PubChem refuses
    })
    source = make_source(PubchemSource, session=session, max_attempts=2)
    with pytest.raises(SourceError, match="after 1 of 2 names"):
        source.fetch()
    # no round 3: asking a server that is refusing only prolongs the block
    assert [u for m, u, b in session.sent if u == PROPERTIES_URL] == []
    [partial] = source.snapshots()
    manifest = json.loads((partial / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["notes"]["names_not_asked"] == ["mg.compound:zzz", "mg.compound:itaconate"]


def test_a_dropped_line_in_round_three_also_keeps_the_name_search(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
    ])
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json")),
                         requests.ConnectionError("the line dropped")],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
        NAME_SEARCH_URL: [NOT_FOUND, _found(811)],
    })
    source = make_source(PubchemSource, session=session, max_attempts=2)
    with pytest.raises(SourceError, match="in round 3"):
        source.fetch()
    [partial] = source.snapshots()
    manifest = json.loads((partial / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["complete"] is False


def test_numbers_in_the_review_file_are_asked_about(make_source, tmp_path, monkeypatch):
    from microbegraph.sources import pubchem
    review = tmp_path / "resolution_decisions.csv"
    review.write_text("identifier,other_identifier,decision,reason,citation,decided_on\n"
                      "mg.compound:x,pubchem.compound:16132390,join,r,doi:10.1/x,2026-10-12\n",
                      encoding="utf-8")
    monkeypatch.setattr(pubchem, "REVIEW_FILE", review)
    _mibig_compounds(tmp_path / "staging", [("mg.compound:x", "x", {"pubchem_cid": 811})])
    session = _server()
    make_source(PubchemSource, session=session).fetch()
    assert session.sent[0][2] == {"cid": "811,16132390"}


def test_every_number_an_entry_gives_is_asked_about(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [(
        "mg.compound:2-methylisoborneol", "2-methylisoborneol",
        {"pubchem_cid": "9237955",
         "pubchem_cid_by_entry": "BGC0000657: 9237955|BGC0000658: 16913|BGC0000659: 16913"})])
    session = _server()
    make_source(PubchemSource, session=session).fetch()
    assert session.sent[0][2] == {"cid": "16913,9237955"}


def test_a_refusal_in_round_one_says_so_in_plain_words(make_source, tmp_path):
    """What happened on 2026-10-12: PubChem answered 429 to every request for hours."""
    _mibig_compounds(tmp_path / "staging", [("mg.compound:x", "x", {"pubchem_cid": 811})])
    busy = FakeResponse(status=429, body=b"<html>429 Too Many Requests</html>")
    source = make_source(PubchemSource, session=FakeSession({PROPERTIES_URL: [busy]}),
                         max_attempts=2)
    with pytest.raises(SourceError, match="refusing requests from this computer for now"):
        source.fetch()
    assert source.snapshots() == []              # nothing half-done for tidy to trip over


# ---------------------------------------------- the name search in PubChem's file of every name
def _names_file(lines: list[str]) -> bytes:
    """A tiny made-up CID-Synonym-filtered.gz: CID, a tab, a name, one per line."""
    return gzip.compress(("".join(f"{line}\n" for line in lines)).encode("utf-8"))


SYNONYM_LINES = ["811\tItaconic acid", "811\tITACONATE", "811\t97-65-4",
                 "5281917\tC-1027", "16132390\tSubtilosin A"]


def test_with_pubchems_names_file_in_the_locker_no_name_is_asked_on_the_web(make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),   # ITACONATE: any case
    ])
    (tmp_path / "raw" / "pubchem").mkdir(parents=True)
    (tmp_path / "raw" / "pubchem" / BULK_FILE).write_bytes(_names_file(SYNONYM_LINES))
    session = _server()
    source = make_source(PubchemSource, session=session)
    [result] = source.fetch()

    assert [u for m, u, b in session.sent if u == NAME_SEARCH_URL] == []
    cids_sent = [b["cid"] for m, u, b in session.sent if u == PROPERTIES_URL]
    assert cids_sent == ["5281917", "811"]                 # round 1, then round 3
    saved = json.loads((result.local_path / "names_from_file_001.json").read_text("utf-8"))
    assert {a["name"]: a["cids"] for a in saved} == {"C-1027 X": [], "itaconate": ["811"]}
    assert all(a["via"].startswith(BULK_FILE) for a in saved)
    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert {r["outcome"] for r in rows if "names_from_file" in r["local_path"]} == {"derived"}
    tidied = source.tidy()
    assert tidied.counts["names_found_one_number"] == 1 and tidied.counts["names_not_found"] == 1


def test_a_long_name_list_downloads_pubchems_names_file_once(make_source, tmp_path, monkeypatch):
    from microbegraph.sources import pubchem
    monkeypatch.setattr(pubchem, "NAMES_FROM_FILE_ABOVE", 1)   # two names count as many here
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:a-one", "a one", {"formula": "C1"}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
    ])
    session = _server()
    session.script[BULK_URL] = [FakeResponse(body=_names_file(SYNONYM_LINES))]
    source = make_source(PubchemSource, session=session)
    source.fetch()
    assert (tmp_path / "raw" / "pubchem" / BULK_FILE).exists()
    assert [u for m, u, b in session.sent if u == NAME_SEARCH_URL] == []
    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    [row] = [r for r in rows if r["url"] == BULK_URL and r["outcome"] == "downloaded"]
    assert len(row["sha256"]) == 64


def test_a_names_file_in_another_layout_is_refused_with_its_first_line(make_source, tmp_path):
    from microbegraph.sources.pubchem_names import search_synonym_file
    path = tmp_path / BULK_FILE
    path.write_bytes(_names_file(["CID,Synonym", "811,Itaconic acid"]))
    with pytest.raises(SourceError, match="isn't a number, a tab and a name"):
        search_synonym_file(path, ["itaconic acid"])


def test_a_fetch_stopped_in_round_three_after_the_file_search_is_not_searched_again(
        make_source, tmp_path):
    _mibig_compounds(tmp_path / "staging", [
        ("mg.compound:c-1027-x", "C-1027 X", {"pubchem_cid": 5281917}),
        ("mg.compound:itaconate", "itaconate", {"formula": "C5H6O4"}),
    ])
    (tmp_path / "raw" / "pubchem").mkdir(parents=True)
    (tmp_path / "raw" / "pubchem" / BULK_FILE).write_bytes(_names_file(SYNONYM_LINES))
    busy = FakeResponse(status=429, body=b"<html>429 Too Many Requests</html>")
    session = FakeSession({
        PROPERTIES_URL: [FakeResponse(body=fixture_bytes("pubchem", "properties_001.json")), busy],
        SYNONYMS_URL: [FakeResponse(body=fixture_bytes("pubchem", "synonyms_001.json"))],
    })
    source = make_source(PubchemSource, session=session, max_attempts=2)
    with pytest.raises(SourceError, match="in round 3"):
        source.fetch()

    session = _server()
    source = make_source(PubchemSource, session=session)
    [result] = source.fetch()
    assert (result.local_path / "names_carried_over.json").exists()
    assert [b["cid"] for m, u, b in session.sent if u == PROPERTIES_URL] == ["811"]
    assert source.tidy().counts["cids_found_by_name"] == 1


def test_probe_reports_pubchems_names_file_and_whether_the_locker_has_it(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", compounds=CIDS)
    session = _server()
    session.script[BULK_URL] = [FakeResponse(headers={
        "Content-Length": str(1_300 * 1_048_576), "Last-Modified": "Sat, 10 Oct 2026 07:01:00 GMT"})]
    source = make_source(PubchemSource, session=session)

    report = source.probe()
    assert any("1,300 MB" in f and "Sat, 10 Oct 2026" in f for f in report.facts)
    assert any(f.startswith("downloaded     : not yet") for f in report.facts)

    source.locker.mkdir(parents=True)
    (source.locker / BULK_FILE).write_bytes(_names_file(SYNONYM_LINES))
    report = source.probe()
    assert any(f.startswith("downloaded     : yes") for f in report.facts)


def test_the_gap_survey_looks_names_up_in_pubchems_names_file(tmp_path):
    """tests/fixtures/capture_gap_samples.py sends no name search when the file is there."""
    import importlib.util
    script = Path(__file__).parent / "fixtures" / "capture_gap_samples.py"
    spec = importlib.util.spec_from_file_location("capture_gap_samples", script)
    survey = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(survey)

    path = tmp_path / BULK_FILE
    path.write_bytes(_names_file(SYNONYM_LINES))
    answers = survey.names_from_file(path, [
        {"compound": "mg.compound:itaconate", "name": "ITACONIC ACID"},
        {"compound": "mg.compound:unknown", "name": "no such name"}])

    assert survey.cids_in(answers["mg.compound:itaconate"]) == [811]
    assert survey.answered(answers["mg.compound:unknown"])          # "not found" is an answer
    assert survey.cids_in(answers["mg.compound:unknown"]) == []
