"""
Tests for the UniProt adapter (Phase 3).

The answers the fake server gives are real ones, captured from UniProt on
2026-10-12 (tests/fixtures/README.md), with their real status codes and
headers (tests/fixtures/uniprot/headers.json). The only made-up answers are
the "still running" and "error" job states, which the capture never saw
because both real jobs had finished by the first check. "Still running"
follows the example in UniProt's documentation; "error" has the same shape
with a different state. Each test that uses one says so.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from conftest import FakeResponse, FakeSession, fixture_bytes, make_snapshot, write_mibig_staging

from microbegraph import provenance
from microbegraph.sources import uniprot
from microbegraph.sources.api import MANIFEST
from microbegraph.sources.base import SourceError
from microbegraph.sources.uniprot import (
    FIELDS_URL,
    RESULTS_URL,
    RETURN_FIELDS,
    RUN_URL,
    STATUS_URL,
    UniprotSource,
    count_rows,
    entry_properties,
    job_state,
    offered_from_names,
    short_name,
)

HEADERS = json.loads(fixture_bytes("uniprot", "headers.json"))

# The ids the captured jobs asked about: surfactin's nine genes, twenty spread
# through MIBiG's other INSDC ids, one made up on purpose, and five RefSeq ids.
INSDC = ["CAE02630.1", "CAE02631.1", "CAE02632.1", "CAE02633.1", "CAE02634.1", "CAE02636.1",
         "CAE02637.1", "CAE02638.1", "CAE02639.1", "AAA16191.1", "AAL06661.1", "AAS98775.1",
         "ABP54653.1", "ACJ24844.1", "ACZ57547.1", "ADP94222.1", "AEE88289.1", "AFY23043.1",
         "AGY30679.1", "AHZ61875.1", "ALI92658.1", "BAI44337.1", "CAD91226.1", "CAO98879.1",
         "CCQ18699.1", "MBA5221208.1", "PLB34718.1", "QLD23475.1", "UUQ67960.1", "XYZ99999.99"]
REFSEQ = ["NP_199072.1", "WP_019032753.1", "WP_030890472.1", "WP_164841441.1", "XP_028481820.1"]
INSDC_JOB, REFSEQ_JOB = "8Pr33gbOw8", "sufWW4pG1o"


def captured(name: str) -> FakeResponse:
    """A captured answer with the status code and headers it really arrived with."""
    real = HEADERS[name]
    return FakeResponse(status=real["status"], body=fixture_bytes("uniprot", name),
                        headers=real["headers"])


# Made up, in the shape UniProt documents for a job that is still working.
STILL_RUNNING = FakeResponse(json_body={"jobStatus": "RUNNING"})


def _server(insdc_status: list[FakeResponse] | None = None) -> FakeSession:
    return FakeSession({
        FIELDS_URL: [captured("idmapping_fields.json")],
        RUN_URL: [captured("insdc_001_job.json"), captured("refseq_001_job.json")],
        STATUS_URL.format(job=INSDC_JOB): insdc_status or [captured("insdc_001_status.json")],
        STATUS_URL.format(job=REFSEQ_JOB): [captured("refseq_001_status.json")],
        RESULTS_URL.format(job=INSDC_JOB): [captured("insdc_001_results.tsv")],
        RESULTS_URL.format(job=REFSEQ_JOB): [captured("refseq_001_results.tsv")],
    })


def _staging(tmp_path: Path) -> None:
    proteins = {i: "insdc" for i in INSDC} | {i: "refseq" for i in REFSEQ}
    proteins["TSTA_117750"] = "other"            # a locus tag: never sent to UniProt
    write_mibig_staging(tmp_path / "staging", proteins=proteins)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- probe
def test_probe_reports_the_release_and_the_identifier_types(make_source, tmp_path):
    _staging(tmp_path)
    report = make_source(UniprotSource, session=_server()).probe()

    assert report.reachable is True
    assert "release        : 2026_03 (published 02-September-2026)" in report.facts
    assert any("offers both identifier types" in fact for fact in report.facts)
    assert any("30 INSDC and 5 RefSeq protein ids from MIBiG, 2 jobs" in fact
               for fact in report.facts)
    assert report.warnings == []


def test_probe_warns_when_an_identifier_type_disappears(make_source, tmp_path):
    fields = fixture_bytes("uniprot", "idmapping_fields.json").replace(
        b'"name":"RefSeq_Protein"', b'"name":"Renamed_Protein"')
    session = FakeSession({FIELDS_URL: [FakeResponse(body=fields)]})

    report = make_source(UniprotSource, session=session).probe()

    assert any("no longer lists RefSeq_Protein" in w for w in report.warnings)


def test_probe_without_mibig_proteins_says_what_to_run(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", organisms=["326423"])   # a Phase 2 table
    report = make_source(UniprotSource, session=_server()).probe()
    assert any("unknown yet" in fact and "Phase 3" in fact for fact in report.facts)


def test_the_captured_list_offers_both_identifier_types():
    offered = offered_from_names(fixture_bytes("uniprot", "idmapping_fields.json"))
    assert {"EMBL-GenBank-DDBJ_CDS", "RefSeq_Protein"} <= offered
    assert "UniProtKB" not in offered            # a "to" type only, never a "from"


# --------------------------------------------------------------------------- fetch
def test_fetch_runs_one_job_per_identifier_type_and_keeps_its_answers(make_source, tmp_path):
    _staging(tmp_path)
    session = _server()
    [result] = make_source(UniprotSource, session=session).fetch()

    folder = result.local_path
    assert sorted(p.name for p in folder.iterdir()) == [
        "insdc_001_job.json", "insdc_001_results.tsv", MANIFEST,
        "refseq_001_job.json", "refseq_001_results.tsv"]
    assert (folder / "insdc_001_results.tsv").read_bytes() == fixture_bytes(
        "uniprot", "insdc_001_results.tsv")

    # The ids went in the POST body, sorted, with UniProt's own names for their type.
    posts = [sent for sent in session.sent if sent[0] == "POST"]
    assert posts[0][2] == {"from": "EMBL-GenBank-DDBJ_CDS", "to": "UniProtKB",
                           "ids": ",".join(sorted(INSDC))}
    assert posts[1][2]["from"] == "RefSeq_Protein"
    assert "TSTA_117750" not in posts[0][2]["ids"] + posts[1][2]["ids"]

    manifest = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    assert manifest["source_version"] == "2026_03"
    assert manifest["notes"]["release_date"] == "02-September-2026"
    assert manifest["asked_for"] == {"fields": RETURN_FIELDS, "insdc": sorted(INSDC),
                                     "refseq": sorted(REFSEQ)}


def test_fetch_asks_about_a_job_without_following_the_redirect(make_source, tmp_path):
    """The 303 'finished' answer has to be seen as it is, so redirects stay off."""
    _staging(tmp_path)
    session = _server()
    make_source(UniprotSource, session=session).fetch()
    assert session.not_followed == [STATUS_URL.format(job=INSDC_JOB),
                                    STATUS_URL.format(job=REFSEQ_JOB)]


def test_fetch_waits_while_a_job_is_running(make_source, tmp_path, monkeypatch):
    _staging(tmp_path)
    session = _server(insdc_status=[STILL_RUNNING, STILL_RUNNING,
                                    captured("insdc_001_status.json")])
    source = make_source(UniprotSource, session=session)
    waits: list[float] = []
    monkeypatch.setattr(source, "pause", lambda factor=1.0: waits.append(factor))

    [result] = source.fetch()

    manifest = json.loads((result.local_path / MANIFEST).read_text(encoding="utf-8"))
    assert [job["status_checks"] for job in manifest["notes"]["jobs"]] == [3, 1]
    assert waits.count(uniprot.POLL_FACTOR) == 2        # one longer wait per "still running"


def test_fetch_logs_the_job_answers_and_the_results(make_source, tmp_path):
    _staging(tmp_path)
    make_source(UniprotSource, session=_server()).fetch()

    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert [Path(r["local_path"]).name for r in rows] == [
        "insdc_001_job.json", "insdc_001_results.tsv",
        "refseq_001_job.json", "refseq_001_results.tsv"]
    assert [r["n_records"] for r in rows] == ["1", "18", "1", "2"]
    assert {r["source_version"] for r in rows} == {"2026_03"}
    assert {r["licence"] for r in rows} == {"CC-BY-4.0"}


def test_second_fetch_on_the_same_day_asks_nothing(make_source, tmp_path):
    _staging(tmp_path)
    session = _server()
    source = make_source(UniprotSource, session=session)
    source.fetch()
    calls = len(session.calls)

    [again] = source.fetch()

    assert again.outcome == "already_present"
    assert len(session.calls) == calls


def test_a_job_that_fails_stops_the_fetch(make_source, tmp_path):
    _staging(tmp_path)
    # Made up: the real status answer's shape, with a state other than new,
    # running or finished.
    failed = FakeResponse(json_body={"jobStatus": "ERROR"})
    source = make_source(UniprotSource, session=_server(insdc_status=[failed]))

    with pytest.raises(SourceError, match=f"stopped job {INSDC_JOB} \\(ERROR\\)"):
        source.fetch()
    assert source.snapshots() == []                      # unfinished, so tidy ignores it


def test_a_job_that_never_finishes_stops_the_fetch(make_source, tmp_path, monkeypatch):
    _staging(tmp_path)
    monkeypatch.setattr(uniprot, "MAX_POLLS", 3)
    source = make_source(UniprotSource, session=_server(insdc_status=[STILL_RUNNING]))

    with pytest.raises(SourceError, match="still running after 3 checks"):
        source.fetch()


def test_an_answer_that_is_not_a_table_is_logged_then_stops_the_fetch(make_source, tmp_path):
    _staging(tmp_path)
    session = _server()
    session.script[RESULTS_URL.format(job=INSDC_JOB)] = [
        FakeResponse(json_body={"messages": ["Something went wrong"]})]
    source = make_source(UniprotSource, session=session)

    with pytest.raises(SourceError, match="isn't the results table expected"):
        source.fetch()
    rows = provenance.read(tmp_path / "raw" / "provenance.csv")
    assert rows[-1]["n_records"] == ""
    assert source.snapshots() == []


def test_a_job_answer_without_a_ticket_number_stops_the_fetch(make_source, tmp_path):
    _staging(tmp_path)
    session = _server()
    session.script[RUN_URL] = [FakeResponse(json_body={"messages": ["Invalid from"]})]

    with pytest.raises(SourceError, match="no job number"):
        make_source(UniprotSource, session=session).fetch()


def test_fetch_asks_for_a_mibig_re_tidy_when_there_are_no_proteins(make_source, tmp_path):
    write_mibig_staging(tmp_path / "staging", organisms=["326423"])
    with pytest.raises(SourceError, match="--tidy-only --source mibig"):
        make_source(UniprotSource, session=_server()).fetch()


# --------------------------------------------------------------------------- tidy
def _tidied(make_source, tmp_path, insdc_results: bytes | None = None):
    source = make_source(UniprotSource)
    make_snapshot(source.locker,
                  {"insdc_001_job.json": fixture_bytes("uniprot", "insdc_001_job.json"),
                   "insdc_001_results.tsv": insdc_results or fixture_bytes(
                       "uniprot", "insdc_001_results.tsv"),
                   "refseq_001_job.json": fixture_bytes("uniprot", "refseq_001_job.json"),
                   "refseq_001_results.tsv": fixture_bytes("uniprot", "refseq_001_results.tsv")},
                  asked_for={"fields": RETURN_FIELDS, "insdc": sorted(INSDC),
                             "refseq": sorted(REFSEQ)},
                  source_version="2026_03")
    return source.tidy()


def test_tidy_counts_what_mapped_and_what_did_not(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)

    assert result.counts == {
        "results_files_read": 2, "ids_asked": 35, "ids_asked_insdc": 30,
        "ids_asked_refseq": 5, "ids_mapped": 20, "ids_not_mapped": 15,
        "ids_with_several_entries": 0, "uniprot_entries": 20, "entries_from_several_ids": 0,
        "entries_reviewed": 5, "entries_with_ec_number": 6, "entries_with_function": 6,
    }
    summary = json.loads((tmp_path / "staging" / "uniprot_summary.json").read_text("utf-8"))
    assert "XYZ99999.99" in summary["ids_not_mapped"]["insdc"]      # the made-up one
    assert summary["ids_not_mapped"]["refseq"] == ["WP_019032753.1", "WP_164841441.1",
                                                   "XP_028481820.1"]
    assert summary["source_version"] == "2026_03"


def test_tidy_turns_the_srfaa_row_into_a_protein_node(make_source, tmp_path):
    """The worked example in docs/05: CAE02630.1 (srfAA) maps to Q70KJ7."""
    result = _tidied(make_source, tmp_path)
    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}

    srfaa = nodes["uniprot:Q70KJ7"]
    assert srfaa["node_type"] == "Protein"
    assert srfaa["name"] == "Surfactin synthetase A"
    props = json.loads(srfaa["properties"])
    assert props["mibig_protein_ids"] == "ncbiprotein:CAE02630.1"
    assert props["reviewed"] is False                     # made from the sequence record
    assert props["organism_taxid"] == 1390
    assert props["length"] == 3584
    assert props["gene_names"] == "srfAA"
    assert props["annotation_score"] == 2.0
    assert "ec_numbers" not in props                      # UniProt gives none for it


def test_tidy_keeps_ec_numbers_function_and_several_gene_names(make_source, tmp_path):
    result = _tidied(make_source, tmp_path)
    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}

    rmla = json.loads(nodes["uniprot:B0RVK9"]["properties"])
    assert nodes["uniprot:B0RVK9"]["name"] == "Glucose-1-phosphate thymidylyltransferase"
    assert rmla["reviewed"] is True
    assert rmla["ec_numbers"] == "2.7.7.24"
    assert rmla["gene_names"] == "rmlA|xcc-b100_3733"
    assert rmla["function"].startswith("Catalyzes the formation of dTDP-glucose")
    assert json.loads(nodes["uniprot:Q9FH67"]["properties"])["mibig_protein_ids"] == (
        "ncbiprotein:NP_199072.1")                        # a RefSeq id maps the same way


def test_tidy_records_an_id_with_several_entries(make_source, tmp_path):
    """
    Made up from two real rows: CAE02630.1 is given a second entry, and that
    entry is also reached from a second id. Both cases are counted and listed.
    """
    real = fixture_bytes("uniprot", "insdc_001_results.tsv").decode("utf-8")
    srfab = next(line for line in real.splitlines() if line.startswith("CAE02631.1"))
    extra = srfab.replace("CAE02631.1", "CAE02630.1", 1) + "\n"
    result = _tidied(make_source, tmp_path, (real + extra).encode("utf-8"))

    assert result.counts["ids_with_several_entries"] == 1
    assert result.counts["entries_from_several_ids"] == 1
    summary = json.loads((tmp_path / "staging" / "uniprot_summary.json").read_text("utf-8"))
    assert summary["ids_with_several_entries"] == {"CAE02630.1": ["Q70KJ6", "Q70KJ7"]}
    nodes = {r["node_id"]: r for r in _rows(result.nodes_path)}
    assert json.loads(nodes["uniprot:Q70KJ6"]["properties"])["mibig_protein_ids"] == (
        "ncbiprotein:CAE02630.1|ncbiprotein:CAE02631.1")


def test_tidy_without_a_finished_snapshot_says_what_to_run(make_source):
    with pytest.raises(SourceError, match="--source uniprot"):
        make_source(UniprotSource).tidy()


# --------------------------------------------------------------------------- helpers
def test_job_state_reads_both_ways_of_saying_finished():
    finished = fixture_bytes("uniprot", "insdc_001_status.json")
    assert job_state(303, finished) == "FINISHED"
    assert job_state(200, finished) == "FINISHED"
    assert job_state(200, b'{"jobStatus":"RUNNING"}') == "RUNNING"
    assert job_state(200, b'{"results":[]}') == "FINISHED"
    assert job_state(200, b"<html>busy</html>") == "UNREADABLE"


def test_count_rows():
    assert count_rows(fixture_bytes("uniprot", "refseq_001_results.tsv")) == 2
    assert count_rows(b"") == 0                            # nothing mapped is still an answer
    assert count_rows(b'{"messages":["no"]}') == ""


def test_short_name_and_properties_from_one_row():
    row = {"Entry": "E5KJ95", "Entry Name": "E5KJ95_STRCX", "Reviewed": "unreviewed",
           "Protein names": "Radical SAM domain protein (Tun2) (TunB)",
           "Gene Names": "tunB tun2", "EC number": "1.1.1.1; 2.2.2.2", "Length": "338",
           "Organism (ID)": "1969", "Annotation": "1.0", "Function [CC]": ""}
    assert short_name(row) == "Radical SAM domain protein"
    assert short_name({"Entry": "X1", "Protein names": ""}) == "X1"
    props = entry_properties(row, {"ADP94222.1"})
    assert props["gene_names"] == "tunB|tun2"
    assert props["ec_numbers"] == "1.1.1.1|2.2.2.2"
    assert props["length"] == 338 and props["organism_taxid"] == 1969
