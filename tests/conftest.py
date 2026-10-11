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
    a small archive from the four records in tests/fixtures/mibig/ and stand
    in a fake server that answers from memory. The real download is checked
    by hand, once, on your machine (docs/03-ingestion-mibig.md, Step 8).
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import requests

from microbegraph.sources.mibig import FILENAME, MibigSource

FIXTURES = Path(__file__).parent / "fixtures" / "mibig"


def build_archive(target: Path, extra: dict[str, bytes] | None = None,
                  reverse: bool = False, compression: str = "gz") -> bytes:
    """
    Pack the fixture records into a tar archive shaped like a MIBiG release
    (one JSON file per entry inside one folder) and return its bytes.
    `extra` adds more members by name, e.g. a file that is broken on purpose.
    `reverse` stores them in reverse order, to check that the output does not
    depend on the order inside the archive.
    `compression` is "gz", "bz2", "xz", or "" for none at all. The real
    MIBiG 4.0 file is named .tar.gz but is not gzip-compressed, so the tests
    try every kind under that same name.
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
                 break_after: int | None = None) -> None:
        self.status_code = status
        self._body = json.dumps(json_body).encode() if json_body is not None else body
        self.headers = {"Content-Length": str(len(self._body))}
        self.closed = False
        self.break_after = break_after

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
    were made, which is how we prove "no download happened".
    """

    def __init__(self, script: dict[str, list[Any]]) -> None:
        self.script = {url: list(answers) for url, answers in script.items()}
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def get(self, url: str, stream: bool = False, timeout: Any = None) -> FakeResponse:
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
