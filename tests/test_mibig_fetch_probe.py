"""
Tests for MIBiG fetch and probe, against a fake server.

The promises checked here are the evidence-locker rules:
  * a download is verified before it is filed,
  * nothing in the locker is ever overwritten,
  * re-running a fetch costs no download,
  * every fetch leaves a provenance row, even when the file then can't be read,
  * temporary trouble is retried, clear refusals are not.

From Phase 3b a fetch brings two files: the JSON archive from Zenodo (checked
against the MD5 Zenodo publishes) and the protein file from MIBiG's download
server (checked against the SHA-256 this project pinned). Both follow the
same rules.
"""

from __future__ import annotations

import hashlib

import pytest
import requests
from conftest import (
    FakeResponse,
    FakeSession,
    build_archive,
    genbank_file_bytes,
    md5_of,
    protein_file_bytes,
)

from microbegraph import provenance
from microbegraph.sources import mibig
from microbegraph.sources.base import ChecksumMismatch, LockerConflict, SourceError

PROTEINS = protein_file_bytes()
GENBANK = genbank_file_bytes()                    # Phase 4b: three records, packed as MIBiG packs them


@pytest.fixture
def served(tmp_path, monkeypatch):
    """
    Archive bytes on a fake server, with the pinned MD5 set to match them,
    and the protein file and GenBank samples with the pinned SHA-256s set to
    match them.
    """
    payload = build_archive(tmp_path / "server" / mibig.FILENAME)
    monkeypatch.setattr(mibig, "EXPECTED_MD5", md5_of(payload))
    monkeypatch.setattr(mibig, "PROTEIN_FILE_SHA256", hashlib.sha256(PROTEINS).hexdigest())
    monkeypatch.setattr(mibig, "GENBANK_FILE_SHA256", hashlib.sha256(GENBANK).hexdigest())
    return payload


def with_proteins(archive_answers: list, protein_answers: list | None = None,
                  genbank_answers: list | None = None) -> dict:
    """A fake server script: the archive answers given; the protein and GenBank files served once."""
    return {mibig.DOWNLOAD_URL: archive_answers,
            mibig.PROTEIN_FILE_URL: protein_answers or [FakeResponse(body=PROTEINS)],
            mibig.GENBANK_FILE_URL: genbank_answers or [FakeResponse(body=GENBANK)]}


def test_fetch_downloads_verifies_files_and_logs(make_adapter, served):
    session = FakeSession(with_proteins([FakeResponse(body=served)]))
    adapter = make_adapter(session=session)

    archive, proteins, genbank = adapter.fetch()

    assert archive.outcome == "downloaded"
    assert archive.local_path.read_bytes() == served
    assert archive.n_records == 4
    assert proteins.outcome == "downloaded"
    assert proteins.local_path.name == mibig.PROTEIN_FILE
    assert proteins.local_path.read_bytes() == PROTEINS
    assert proteins.n_records == 43                         # proteins in the sample
    assert genbank.outcome == "downloaded"
    assert genbank.local_path.name == mibig.GENBANK_FILE
    assert genbank.n_records == 3                           # GenBank records in the sample
    assert not list(adapter.locker.glob("*.part"))          # no half-files left behind
    archive_row, protein_row, genbank_row = provenance.read(adapter.provenance_log)
    assert archive_row["outcome"] == "downloaded"
    assert archive_row["md5"] == md5_of(served)
    assert archive_row["licence"] == "CC-BY-4.0"
    assert archive_row["source_version"] == "4.0"
    assert protein_row["url"] == mibig.PROTEIN_FILE_URL
    assert protein_row["sha256"] == hashlib.sha256(PROTEINS).hexdigest()
    assert protein_row["n_records"] == "43"
    assert protein_row["licence"] == "CC-BY-4.0"
    assert genbank_row["url"] == mibig.GENBANK_FILE_URL
    assert genbank_row["sha256"] == hashlib.sha256(GENBANK).hexdigest()
    assert genbank_row["n_records"] == "3"


def test_second_fetch_costs_no_download(make_adapter, served):
    session = FakeSession(with_proteins([FakeResponse(body=served)]))
    adapter = make_adapter(session=session)
    adapter.fetch()
    again = adapter.fetch()
    assert [result.outcome for result in again] == ["already_present"] * 3
    assert session.calls.count(mibig.DOWNLOAD_URL) == 1
    assert session.calls.count(mibig.PROTEIN_FILE_URL) == 1
    assert session.calls.count(mibig.GENBANK_FILE_URL) == 1
    assert [r["outcome"] for r in provenance.read(adapter.provenance_log)] == [
        "downloaded"] * 3 + ["already_present"] * 3


def test_a_protein_file_that_is_not_the_pinned_one_is_thrown_away(make_adapter, served):
    """The server lists no checksum, so the SHA-256 this project recorded is the check."""
    changed = PROTEINS.replace(b"MYIMMKKGQ", b"MYIMMKKGA", 1)
    session = FakeSession(with_proteins([FakeResponse(body=served)],
                                        [FakeResponse(body=changed)]))
    adapter = make_adapter(session=session)
    with pytest.raises(ChecksumMismatch, match="this project pinned"):
        adapter.fetch()
    assert not (adapter.locker / mibig.PROTEIN_FILE).exists()
    assert not list(adapter.locker.glob("*.part"))
    [row] = provenance.read(adapter.provenance_log)         # only the archive was filed
    assert row["local_path"].endswith(mibig.FILENAME)


def test_a_different_protein_file_in_the_locker_is_never_overwritten(make_adapter, served):
    adapter = make_adapter(session=FakeSession(with_proteins([FakeResponse(body=served)])))
    adapter.locker.mkdir(parents=True)
    existing = adapter.locker / mibig.PROTEIN_FILE
    existing.write_bytes(b">BGC0000001.1|c1|1-3|+|X|y|X\nM\n")
    with pytest.raises(LockerConflict, match="SHA-256"):
        adapter.fetch()
    assert existing.read_bytes() == b">BGC0000001.1|c1|1-3|+|X|y|X\nM\n"


def test_a_corrupted_download_is_thrown_away(make_adapter, served):
    damaged = served[:-10] + b"0123456789"
    session = FakeSession({mibig.DOWNLOAD_URL: [FakeResponse(body=damaged)]})
    adapter = make_adapter(session=session)
    with pytest.raises(ChecksumMismatch):
        adapter.fetch()
    assert not (adapter.locker / mibig.FILENAME).exists()
    assert not list(adapter.locker.glob("*.part"))
    assert provenance.read(adapter.provenance_log) == []    # nothing filed, nothing logged


def test_the_locker_never_overwrites(make_adapter, served):
    adapter = make_adapter(session=FakeSession({}))
    adapter.locker.mkdir(parents=True)
    existing = adapter.locker / mibig.FILENAME
    existing.write_bytes(b"something else entirely")
    with pytest.raises(LockerConflict):
        adapter.fetch()
    assert existing.read_bytes() == b"something else entirely"


def test_an_uncompressed_archive_is_counted(make_adapter, tmp_path, monkeypatch):
    """The real MIBiG 4.0 file: named .tar.gz, not gzip inside. It must still be counted."""
    payload = build_archive(tmp_path / "server" / mibig.FILENAME, compression="")
    monkeypatch.setattr(mibig, "EXPECTED_MD5", md5_of(payload))
    monkeypatch.setattr(mibig, "PROTEIN_FILE_SHA256", hashlib.sha256(PROTEINS).hexdigest())
    monkeypatch.setattr(mibig, "GENBANK_FILE_SHA256", hashlib.sha256(GENBANK).hexdigest())
    adapter = make_adapter(session=FakeSession(with_proteins([FakeResponse(body=payload)])))
    archive, _, _ = adapter.fetch()
    assert archive.n_records == 4


def test_a_file_that_cannot_be_opened_is_still_logged(make_adapter, monkeypatch):
    """
    The first real run found this gap: the download was verified and filed,
    then reading it failed, and the locker held a file the log had no row for.
    Now the row is written first (record count blank) and the fetch stops after.
    """
    payload = b"intact, published, and not a tar archive of any kind. " * 20
    monkeypatch.setattr(mibig, "EXPECTED_MD5", md5_of(payload))
    adapter = make_adapter(session=FakeSession({mibig.DOWNLOAD_URL: [FakeResponse(body=payload)]}))
    with pytest.raises(SourceError, match="can't be read as an archive"):
        adapter.fetch()
    assert (adapter.locker / mibig.FILENAME).read_bytes() == payload
    [row] = provenance.read(adapter.provenance_log)
    assert row["outcome"] == "downloaded"
    assert row["md5"] == md5_of(payload)
    assert row["n_records"] == ""


def test_temporary_trouble_is_retried(make_adapter, served):
    session = FakeSession(with_proteins([
        FakeResponse(status=503), requests.ConnectionError("Wi-Fi blinked"),
        FakeResponse(body=served),
    ]))
    archive, _, _ = make_adapter(session=session).fetch()
    assert archive.outcome == "downloaded"
    assert session.calls.count(mibig.DOWNLOAD_URL) == 3


def test_a_download_that_breaks_halfway_starts_again(make_adapter, served):
    session = FakeSession(with_proteins(
        [FakeResponse(body=served)],
        [FakeResponse(body=PROTEINS, break_after=len(PROTEINS) // 2), FakeResponse(body=PROTEINS)],
    ))
    adapter = make_adapter(session=session)
    _, proteins, _ = adapter.fetch()
    assert proteins.outcome == "downloaded"
    assert session.calls.count(mibig.PROTEIN_FILE_URL) == 2
    assert not list(adapter.locker.glob("*.part"))


def test_a_certificate_problem_is_not_retried(make_adapter, served):
    """Certificate and proxy refusals are permanent on a given network."""
    session = FakeSession({mibig.DOWNLOAD_URL: [requests.exceptions.SSLError("certificate replaced")]})
    with pytest.raises(requests.exceptions.SSLError):
        make_adapter(session=session).fetch()
    assert len(session.calls) == 1


def test_a_clear_refusal_is_not_retried(make_adapter, served):
    session = FakeSession({mibig.DOWNLOAD_URL: [FakeResponse(status=404)]})
    with pytest.raises(SourceError, match="HTTP 404"):
        make_adapter(session=session).fetch()
    assert len(session.calls) == 1


def test_retrying_gives_up_eventually(make_adapter, served):
    session = FakeSession({mibig.DOWNLOAD_URL: [requests.ConnectionError("offline")]})
    with pytest.raises(requests.ConnectionError):
        make_adapter(session=session, max_attempts=3).fetch()
    assert len(session.calls) == 3


# --- probe ---------------------------------------------------------------------
def zenodo_record(is_last: bool = True, last_id: str = mibig.ZENODO_RECORD) -> dict:
    """A trimmed record in the shape Zenodo's records API returns."""
    return {
        "id": int(mibig.ZENODO_RECORD),
        "metadata": {
            "title": "MIBiG 4.0 JSON",
            "version": "4.0",
            "publication_date": "2024-11-15",
            "license": {"id": "cc-by-4.0"},
            "relations": {"version": [{"is_last": is_last, "last": {"pid_value": last_id}}]},
        },
        "files": [{"key": mibig.FILENAME, "size": 10_498_325,
                   "checksum": f"md5:{mibig.EXPECTED_MD5}"}],
        "links": {},
    }


def test_probe_reports_without_downloading(make_adapter):
    session = FakeSession({mibig.RECORD_API_URL: [FakeResponse(json_body=zenodo_record())]})
    report = make_adapter(session=session).probe()
    text = "\n".join(report.facts)
    assert report.reachable
    assert "matches the pinned MD5" in text
    assert "none, this is the newest version" in text
    assert "not yet" in text
    assert mibig.DOWNLOAD_URL not in session.calls


def test_probe_flags_a_newer_release(make_adapter):
    record = zenodo_record(is_last=False, last_id="99999999")
    session = FakeSession({mibig.RECORD_API_URL: [FakeResponse(json_body=record)]})
    report = make_adapter(session=session).probe()
    assert any("newer MIBiG release" in w and "99999999" in w for w in report.warnings)


def test_probe_follows_the_latest_link_when_needed(make_adapter):
    record = zenodo_record()
    record["metadata"].pop("relations")
    record["links"]["latest"] = "https://zenodo.org/api/records/14169073/versions/latest"
    newer = {"id": 88888888, "metadata": {"version": "4.1"}}
    session = FakeSession({
        mibig.RECORD_API_URL: [FakeResponse(json_body=record)],
        record["links"]["latest"]: [FakeResponse(json_body=newer)],
    })
    report = make_adapter(session=session).probe()
    assert any("version 4.1" in w for w in report.warnings)


def test_probe_when_offline_reports_instead_of_crashing(make_adapter):
    report = make_adapter(session=FakeSession({}), max_attempts=1).probe()
    assert not report.reachable
    assert report.warnings and "Check your connection" in report.warnings[0]


LISTING = (b'<a href="mibig_json_4.0.tar.gz">mibig_json_4.0.tar.gz</a>'
           b'<a href="mibig_prot_seqs_3.1.fasta">mibig_prot_seqs_3.1.fasta</a>'
           b'<a href="mibig_prot_seqs_4.0.fasta">mibig_prot_seqs_4.0.fasta</a>'
           b'<a href="mibig_json_5.0rc1.tar.bz2">mibig_json_5.0rc1.tar.bz2</a>')


GENBANK_SIZE = {"Content-Length": str(mibig.GENBANK_FILE_BYTES),
                "Last-Modified": "Fri, 15 Nov 2024 08:50:00 GMT"}


def test_probe_checks_the_protein_file_without_downloading_it(make_adapter):
    size = {"Content-Length": str(mibig.PROTEIN_FILE_BYTES),
            "Last-Modified": "Fri, 15 Nov 2024 12:35:03 GMT"}
    session = FakeSession({
        mibig.RECORD_API_URL: [FakeResponse(json_body=zenodo_record())],
        mibig.PROTEIN_FILE_URL: [FakeResponse(body=b">BGC", headers=size)],
        mibig.GENBANK_FILE_URL: [FakeResponse(body=b"\x1f\x8b", headers=GENBANK_SIZE)],
        mibig.DOWNLOAD_SERVER: [FakeResponse(body=LISTING)],
    })
    report = make_adapter(session=session).probe()
    text = "\n".join(report.facts)
    assert f"{mibig.PROTEIN_FILE_BYTES:,} bytes, the pinned size" in text
    assert f"{mibig.GENBANK_FILE_BYTES:,} bytes, the pinned size" in text     # Phase 4b
    assert "also offers mibig_json_5.0rc1.tar.bz2" in text
    assert "mibig_prot_seqs_3.1" not in text                 # older releases aren't news
    # headers only, then hang up, for both files
    assert session.streamed == [mibig.PROTEIN_FILE_URL, mibig.GENBANK_FILE_URL]
    assert not report.warnings


def test_probe_warns_if_the_protein_file_changed_size(make_adapter):
    session = FakeSession({
        mibig.RECORD_API_URL: [FakeResponse(json_body=zenodo_record())],
        mibig.PROTEIN_FILE_URL: [FakeResponse(headers={"Content-Length": "12345"})],
        mibig.GENBANK_FILE_URL: [FakeResponse(headers=GENBANK_SIZE)],
        mibig.DOWNLOAD_SERVER: [FakeResponse(body=LISTING)],
    })
    report = make_adapter(session=session).probe()
    assert any("12,345 bytes" in w and "Do not fetch" in w for w in report.warnings)


def test_probe_warns_if_the_genbank_file_changed_size(make_adapter):
    session = FakeSession({
        mibig.RECORD_API_URL: [FakeResponse(json_body=zenodo_record())],
        mibig.PROTEIN_FILE_URL: [FakeResponse(headers={
            "Content-Length": str(mibig.PROTEIN_FILE_BYTES)})],
        mibig.GENBANK_FILE_URL: [FakeResponse(headers={"Content-Length": "999"})],
        mibig.DOWNLOAD_SERVER: [FakeResponse(body=LISTING)],
    })
    report = make_adapter(session=session).probe()
    [warning] = report.warnings
    assert mibig.GENBANK_FILE in warning and "999 bytes" in warning and "Do not fetch" in warning


def test_a_genbank_file_that_is_not_the_pinned_one_is_thrown_away(make_adapter, served):
    changed = genbank_file_bytes({"BGC9999903.gbk": b"LOCUS       BGC9999903\n//\n"})
    session = FakeSession(with_proteins([FakeResponse(body=served)],
                                        genbank_answers=[FakeResponse(body=changed)]))
    adapter = make_adapter(session=session, max_attempts=1)
    with pytest.raises(ChecksumMismatch, match="pinned"):
        adapter.fetch()
    assert not (adapter.locker / mibig.GENBANK_FILE).exists()
    assert (adapter.locker / mibig.PROTEIN_FILE).exists()     # the files before it are kept


def test_newer_release_files_reads_the_server_listing():
    names = mibig.newer_release_files(LISTING.decode() + "mibig_gbk_4.1.tar.gz", "4.0")
    assert names == ["mibig_gbk_4.1.tar.gz", "mibig_json_5.0rc1.tar.bz2"]
    assert mibig.newer_release_files("mibig_json_4.0.tar.gz", "4.0") == []


def test_probe_warns_if_the_publisher_changed_the_file(make_adapter):
    record = zenodo_record()
    record["files"][0]["checksum"] = "md5:" + "0" * 32
    session = FakeSession({mibig.RECORD_API_URL: [FakeResponse(json_body=record)]})
    report = make_adapter(session=session).probe()
    assert any("Do not fetch until you know why" in w for w in report.warnings)
