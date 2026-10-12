"""
Shared test helpers ("fixtures", in pytest's vocabulary).

WHAT A PYTEST FIXTURE IS
    A function that prepares something a test needs (a temporary folder, a
    fake archive, a fake server) and hands it over. A test asks for one just
    by naming it as a parameter, and pytest finds it here in conftest.py
    without being told.

    Cooks call this mise en place: every station gets the same chopped
    onions, prepared the same way, before cooking starts.

WHY THE TESTS NEVER TOUCH THE INTERNET
    A test that downloads things is slow and fails whenever the Wi-Fi does,
    and it bothers a public server every time anyone runs it. So these helpers build
    a small archive from the four records in tests/fixtures/mibig/ (with,
    from Phase 3b, a small sample of MIBiG's protein file beside it) and stand
    in a fake server that answers from memory. The real download is checked
    by hand, once, on your machine (docs/03-ingestion-mibig.md, Step 8).

    From Phase 2 the fake server answers with REAL answers, captured once
    from PubChem, NCBI, KEGG and (from Phase 3) UniProt, and kept in
    tests/fixtures/<source>/. tests/fixtures/README.md says where each one
    came from.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import requests

from microbegraph.sources.mibig import FILENAME, PROTEIN_FILE, MibigSource

FIXTURES = Path(__file__).parent / "fixtures" / "mibig"

# Phase 3b: surfactin's 23 real proteins, copied unchanged from MIBiG's protein
# file, followed by made-up ones for the made-up entries (tests/fixtures/README.md).
PROTEIN_SAMPLE = FIXTURES / "mibig_prot_seqs_sample.fasta"


def protein_file_bytes() -> bytes:
    """The sample of MIBiG's protein file, exactly as stored."""
    return PROTEIN_SAMPLE.read_bytes()


@pytest.fixture(autouse=True)
def never_read_your_real_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Every test runs without reading your real .env file, so a key you keep
    there can never end up inside a test run (or its output). "autouse" means
    pytest applies this to every test without being asked. Tests about
    settings pass their own temporary .env file instead.
    """
    import microbegraph.fetch

    monkeypatch.setattr(microbegraph.fetch, "load_settings", lambda *args, **kwargs: False)


def build_archive(target: Path, extra: dict[str, bytes] | None = None,
                  reverse: bool = False, compression: str = "gz",
                  proteins: bool = True) -> bytes:
    """
    Pack the fixture records into a tar archive shaped like a MIBiG release
    (one JSON file per entry inside one folder) and return its bytes.
    `extra` adds more members by name, e.g. a file that is broken on purpose.
    `reverse` stores them in reverse order, to check that the output does not
    depend on the order inside the archive.
    `compression` is "gz", "bz2", "xz", or "" for none at all. The real
    MIBiG 4.0 file is named .tar.gz but is not gzip-compressed, so the tests
    try every kind under that same name.
    `proteins` also puts the protein file sample next to the archive, under
    the name the adapter expects (Phase 3b): the tidy reads both.
    """
    members = {f"mibig_json_4.0/{p.name}": p.read_bytes() for p in sorted(FIXTURES.glob("*.json"))}
    members.update(extra or {})
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=f"w:{compression}") as tar:
        for name, data in sorted(members.items(), reverse=reverse):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0                      # fixed, so the bytes are identical every run
            tar.addfile(info, io.BytesIO(data))
    payload = buffer.getvalue()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    if proteins:
        (target.parent / PROTEIN_FILE).write_bytes(protein_file_bytes())
    return payload


@pytest.fixture
def make_adapter(tmp_path: Path) -> Callable[..., MibigSource]:
    """A factory for MIBiG adapters that live entirely inside a temporary folder."""

    def _make(session: Any = None, **kwargs: Any) -> MibigSource:
        return MibigSource(
            raw_dir=tmp_path / "raw",
            staging_dir=tmp_path / "staging",
            provenance_log=tmp_path / "raw" / "provenance.csv",
            session=session,
            retry_wait_seconds=0,      # no real waiting between retries in tests
            quiet=True,
            **kwargs,
        )

    return _make


@pytest.fixture
def archive_in_locker(tmp_path: Path) -> Path:
    """The fixture archive, already sitting in a temporary evidence locker."""
    target = tmp_path / "raw" / "mibig" / FILENAME
    build_archive(target)
    return target


# --- A fake web server ------------------------------------------------------------
class FakeResponse:
    """Just enough of requests.Response for our code: status, headers, body.
    `break_after` makes the body stop with an error after that many bytes,
    like a connection dropping halfway through a download."""

    def __init__(self, status: int = 200, body: bytes = b"", json_body: Any = None,
                 break_after: int | None = None, headers: dict[str, str] | None = None) -> None:
        self.status_code = status
        self._body = json.dumps(json_body).encode() if json_body is not None else body
        self.headers = {"Content-Length": str(len(self._body)), **(headers or {})}
        self.closed = False
        self.break_after = break_after

    @property
    def content(self) -> bytes:
        return self._body

    def json(self) -> Any:
        return json.loads(self._body)

    def iter_content(self, chunk_size: int = 1024):
        body = self._body if self.break_after is None else self._body[:self.break_after]
        for start in range(0, len(body), chunk_size):
            yield body[start:start + chunk_size]
        if self.break_after is not None:
            raise requests.exceptions.ChunkedEncodingError("connection broken halfway")

    def close(self) -> None:
        self.closed = True


class FakeSession:
    """
    Answers requests from a script instead of the internet.

    `script` maps a URL to a list of answers, used in order. An answer is a
    FakeResponse, or an exception to raise (to imitate a dropped connection).
    Every call is recorded in `calls`, so a test can check how many requests
    were made, which is how we prove "no download happened". What each
    request carried (its query or its POST body) is kept in `sent`, so a
    test can check, for example, that a key never travels in the address.
    """

    def __init__(self, script: dict[str, list[Any]]) -> None:
        self.script = {url: list(answers) for url, answers in script.items()}
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []
        self.sent: list[tuple[str, str, dict[str, str]]] = []
        self.not_followed: list[str] = []      # GETs asked NOT to follow a redirect
        self.streamed: list[str] = []          # GETs asked to stream (read the headers first)

    def get(self, url: str, params: dict[str, str] | None = None, stream: bool = False,
            allow_redirects: bool = True, timeout: Any = None) -> FakeResponse:
        self.sent.append(("GET", url, dict(params or {})))
        if not allow_redirects:
            self.not_followed.append(url)
        if stream:
            self.streamed.append(url)
        return self._answer(url)

    def post(self, url: str, data: dict[str, str] | None = None,
             timeout: Any = None) -> FakeResponse:
        self.sent.append(("POST", url, dict(data or {})))
        return self._answer(url)

    def _answer(self, url: str) -> FakeResponse:
        self.calls.append(url)
        answers = self.script.get(url)
        if not answers:
            raise requests.ConnectionError(f"fake server has no answer for {url}")
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, BaseException):
            raise answer
        return answer


def md5_of(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# --- Phase 2 helpers: the API sources -----------------------------------------------
PHASE2_FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(source: str, name: str) -> bytes:
    """A real captured answer from tests/fixtures/<source>/ (see the README there)."""
    return (PHASE2_FIXTURES / source / name).read_bytes()


def write_mibig_staging(staging_dir: Path, compounds: dict[str, str | None] | None = None,
                        organisms: list[str] | None = None,
                        proteins: dict[str, str] | None = None) -> Path:
    """
    A small mibig_nodes.csv, standing in for the MIBiG output that later
    sources build on. `compounds` maps a compound id to its PubChem CID (or
    None); `organisms` lists NCBI taxids; `proteins` maps a gene record's
    protein id to its id_type ("insdc", "refseq" or "other").
    """
    from microbegraph.sources.base import NODE_COLUMNS, write_table

    rows = []
    for node_id, cid in (compounds or {}).items():
        props = {"pubchem_cid": int(cid)} if cid else {}
        rows.append({"node_id": node_id, "node_type": "Compound",
                     "name": node_id.split(":", 1)[1], "properties": json.dumps(props),
                     "source": "mibig", "retrieved_at": "2026-10-10"})
    for taxid in organisms or []:
        rows.append({"node_id": f"ncbitaxon:{taxid}", "node_type": "Organism",
                     "name": f"organism {taxid}", "properties": "{}",
                     "source": "mibig", "retrieved_at": "2026-10-10"})
    for protein_id, id_type in (proteins or {}).items():
        prefix = "mg.protein:bgc9999901-" if id_type == "other" else "ncbiprotein:"
        rows.append({"node_id": prefix + protein_id, "node_type": "Protein",
                     "name": protein_id,
                     "properties": json.dumps({"protein_id": protein_id, "id_type": id_type}),
                     "source": "mibig", "retrieved_at": "2026-10-10"})
    path = staging_dir / "mibig_nodes.csv"
    write_table(path, NODE_COLUMNS, rows)
    return path


def make_snapshot(locker: Path, files: dict[str, bytes], asked_for: dict[str, Any],
                  context: dict[str, Any] | None = None,
                  started_at: str = "2026-10-12T05:52:02Z",
                  source_version: str = "test") -> Path:
    """
    A finished snapshot folder built straight from captured answers, the way
    fetch() would have left it, so tidy() can be tested on its own.
    """
    folder = locker / started_at.replace(":", "")
    folder.mkdir(parents=True)
    answers = []
    for name, body in files.items():
        (folder / name).write_bytes(body)
        answers.append({"file": name, "method": "POST", "url": "https://example.org",
                        "sent": {}, "n_bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(), "n_records": ""})
    manifest = {"source": locker.name, "started_at": started_at, "finished_at": started_at,
                "source_version": source_version, "licence": "", "asked_for": asked_for,
                "context": context or {}, "answers": answers, "notes": {}}
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


@pytest.fixture
def make_source(tmp_path: Path) -> Callable[..., Any]:
    """A factory for any adapter class, living entirely inside a temporary folder."""

    def _make(cls: type, session: Any = None, **kwargs: Any) -> Any:
        from microbegraph.sources.api import ApiSource

        if issubclass(cls, ApiSource):
            kwargs.setdefault("pause_seconds", 0)     # never really wait in a test
        kwargs.setdefault("quiet", True)
        return cls(
            raw_dir=tmp_path / "raw",
            staging_dir=tmp_path / "staging",
            provenance_log=tmp_path / "raw" / "provenance.csv",
            session=session,
            retry_wait_seconds=0,
            **kwargs,
        )

    return _make


# --- Phase 4 helpers: the resolver and the graph build ------------------------------
# A real slice of all six sources' staging tables, cut around chosen clusters by
# tests/fixtures/capture_resolution_samples.py (tests/fixtures/README.md).
RESOLVE_FIXTURES = PHASE2_FIXTURES / "resolve"


def read_rows(path: Path) -> list[dict[str, str]]:
    """Every row of a CSV file, as dicts."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_rows(path: Path, rows: list[dict[str, str]]) -> None:
    """Append made-up rows to a copied staging table (for cases the slice lacks)."""
    with path.open(newline="", encoding="utf-8") as handle:
        columns = next(csv.reader(handle))
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


@pytest.fixture
def staging_copy(tmp_path: Path) -> Path:
    """A fresh copy of the resolver's slice, safe to change in one test."""
    target = tmp_path / "staging"
    shutil.copytree(RESOLVE_FIXTURES, target)
    return target
