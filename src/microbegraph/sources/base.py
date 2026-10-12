"""
MicrobeGraph, the contract every data source follows.

THE BIG IDEA: ONE SOCKET, MANY PLUGS
    MicrobeGraph reads from several public databases (MIBiG, PubChem, NCBI
    Taxonomy, KEGG and UniProt), plus our own curated file. Each one has its
    own website, file format and rules.

    Instead of writing a separate, tangled script for each, this file defines
    ONE shape that every source must fit, and each source becomes a small
    "adapter" that fills in its own details. The rest of the project only ever
    talks to the shape, so adding a source never changes anything downstream.

    The picture I keep in mind is a wall socket. A kettle, a laptop charger
    and a lamp are completely different machines, but each one ends in the
    same plug, and the socket doesn't need to know anything about kettles.

THE CONTRACT: THREE VERBS
    probe()  "What is out there?"  Asks the source about its data WITHOUT
             downloading it: which version, how big, has it changed. It's
             cheap and safe, so it's the first thing you run (measure twice,
             cut once).

    fetch()  "Bring it home, untouched."  Downloads the raw data into the
             EVIDENCE LOCKER (data/raw/<source>/), checks it arrived intact,
             and writes a row to the PROVENANCE LOG for every file it saves.
             It never edits anything.

    tidy()   "Make it fit our rulebook."  Reads ONLY what is already on your
             machine (the locker, plus the staging tables of any source it
             builds on), never the internet, and writes rows shaped exactly
             like docs/02-ontology-and-data-model.md describes, into
             data/processed/staging/<source>_nodes.csv and _edges.csv.

    Keeping fetch() and tidy() apart is more useful than it might look.
    Because tidy() never touches the network, you can re-run it a hundred
    times while fixing a parsing bug, offline, without bothering anyone's
    server.

POLITENESS: HOW TO BE A GOOD GUEST ON SOMEONE ELSE'S SERVER
    Public scientific databases are free to use and shared by everyone, and
    they run on modest budgets. Every request this project makes:
      * says who is asking (a "User-Agent" naming the project and its address),
      * gives up waiting after a sensible time (a timeout) instead of hanging,
      * retries a failed request only for problems that might be temporary,
        and waits longer between each try ("exponential backoff"),
      * never retries a request the server REFUSED for a clear reason
        (404 "not found" will be just as not-found in four seconds).

    It's the same courtesy you'd show phoning a busy office. If the line is
    engaged you try again in a minute, then in five, then in fifteen, but if
    they tell you the person you want has never worked there, you stop
    ringing.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import tarfile
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import requests
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from microbegraph import __version__
from microbegraph.paths import PROVENANCE_LOG, RAW_DIR, STAGING_DIR

# --- How we introduce ourselves to every server -----------------------------
USER_AGENT = f"MicrobeGraph/{__version__} (+https://github.com/akannan2987/microbegraph)"

# (seconds to wait for the connection, seconds to wait between bytes)
# A big download is fine; a download that goes silent for a minute is not.
TIMEOUT = (15, 60)

# --- The two table shapes every adapter writes -------------------------------
# These are the columns of nodes.csv and edges.csv in
# docs/02-ontology-and-data-model.md, section 7. Same names, same order.
NODE_COLUMNS: tuple[str, ...] = (
    "node_id", "node_type", "name", "properties", "source", "retrieved_at",
)
EDGE_COLUMNS: tuple[str, ...] = (
    "source_id", "target_id", "edge_type", "evidence_level", "source",
    "source_record_id", "citation", "confidence", "retrieved_at",
)


# --- Errors with a message a person can act on ----------------------------------
class SourceError(Exception):
    """Something went wrong in a way the person running the command can fix.
    The message always says what happened AND what to do next."""


class TransientHTTPError(SourceError):
    """The server said 'busy' (429) or 'broken right now' (5xx), so trying again may help."""


class ChecksumMismatch(SourceError):
    """The file arrived, but it is not the file the publisher published."""


class LockerConflict(SourceError):
    """A file is already in the evidence locker and it is not the expected one."""


# Only these are retried. Everything else fails at once, with its message.
RETRYABLE_ERRORS = (
    requests.ConnectionError,                  # the line dropped or never connected
    requests.Timeout,                          # the server went silent
    requests.exceptions.ChunkedEncodingError,  # a download broke off halfway
    TransientHTTPError,                        # 429 or 5xx
)
# ...except these two, which look like connection errors but are permanent on a
# given network (a proxy refusing us, a certificate the network has replaced).
# Retrying them only wastes half a minute before the same message.
NOT_RETRYABLE = (requests.exceptions.SSLError, requests.exceptions.ProxyError)


def is_retryable(error: BaseException) -> bool:
    """True for trouble that might be gone in a few seconds."""
    return isinstance(error, RETRYABLE_ERRORS) and not isinstance(error, NOT_RETRYABLE)


# --- What each verb hands back ---------------------------------------------------
@dataclass
class ProbeReport:
    """The answer to 'what is out there?', as short facts ready to print."""

    source: str
    reachable: bool
    facts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FetchResult:
    """What one fetch put in the evidence locker."""

    source: str
    local_path: Path
    outcome: str          # "downloaded" or "already_present"
    n_bytes: int
    n_records: int


@dataclass
class TidyResult:
    """What one tidy wrote to the staging folder, and the counts behind it."""

    source: str
    nodes_path: Path
    edges_path: Path
    counts: dict[str, int]


# --- The socket itself -------------------------------------------------------------
class Source(ABC):
    """
    The shape every adapter fits. A subclass sets three facts about itself
    and writes the three verbs; it inherits the polite downloading, the
    checksum checking and the table writing from here.
    """

    name: str = "base"      # short id, also the locker folder: data/raw/<name>/
    licence: str = ""       # e.g. "CC-BY-4.0"; written into every provenance row
    homepage: str = ""      # where a human can read about the source

    def __init__(
        self,
        raw_dir: Path = RAW_DIR,
        staging_dir: Path = STAGING_DIR,
        provenance_log: Path = PROVENANCE_LOG,
        session: requests.Session | None = None,
        retry_wait_seconds: float = 2.0,
        max_attempts: int = 5,
        quiet: bool = False,
    ) -> None:
        # Every location is a parameter so tests can point the adapter at a
        # temporary folder and never touch your real data/ directory.
        self.raw_dir = Path(raw_dir)
        self.staging_dir = Path(staging_dir)
        self.provenance_log = Path(provenance_log)
        self.retry_wait_seconds = retry_wait_seconds
        self.max_attempts = max_attempts
        self.quiet = quiet

        # A Session reuses one connection for several requests and carries
        # our User-Agent on every one of them.
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    # ---------------------------------------------------------------- the verbs
    @abstractmethod
    def probe(self) -> ProbeReport:
        """Ask the source what it has, without downloading it."""

    @abstractmethod
    def fetch(self) -> list[FetchResult]:
        """Download the raw data into the evidence locker and log it."""

    @abstractmethod
    def tidy(self) -> TidyResult:
        """Turn what is in the locker into staging tables. Never uses the network."""

    # ---------------------------------------------------------------- helpers
    @property
    def locker(self) -> Path:
        """This source's shelf in the evidence locker: data/raw/<name>/."""
        return self.raw_dir / self.name

    def say(self, message: str) -> None:
        """Print a progress message, unless the adapter was told to be quiet."""
        if not self.quiet:
            print(message, flush=True)

    def _before_retry(self, state: RetryCallState) -> None:
        """Called by tenacity just before it waits and tries again."""
        error = state.outcome.exception() if state.outcome else None
        wait = state.next_action.sleep if state.next_action else 0
        self.say(
            f"  [{self.name}] attempt {state.attempt_number} of {self.max_attempts} "
            f"failed ({error}); trying again in {wait:.0f} s"
        )

    def _retrying(self) -> Retrying:
        """The retry policy every request uses: same rules, one place."""
        return Retrying(
            retry=retry_if_exception(is_retryable),
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=self.retry_wait_seconds, max=60),
            before_sleep=self._before_retry,
            reraise=True,
        )

    def http_get(self, url: str, *, params: dict[str, str] | None = None,
                 stream: bool = False, allow_redirects: bool = True) -> requests.Response:
        """
        One polite GET request, retried only when retrying could help.

        429 (too many requests) and 5xx (server trouble) are temporary by
        nature, so we wait and try again: 2 s, 4 s, 8 s, 16 s by default.
        Any other refusal (404 not found, 403 forbidden...) is a clear answer,
        so it is reported immediately instead of being repeated.

        allow_redirects=False keeps a "look over there" answer (HTTP 303, say)
        as it is, instead of following it. UniProt answers "your job is
        finished" that way (Phase 3), and the adapter wants to see that answer.
        """
        for attempt in self._retrying():
            with attempt:
                return self._get_once(url, params=params, stream=stream,
                                      allow_redirects=allow_redirects)
        raise AssertionError("unreachable: tenacity either returns or re-raises")

    def http_post(self, url: str, data: dict[str, str]) -> requests.Response:
        """
        One polite POST request, with the same retry rules as http_get().

        A POST carries its details in the request BODY instead of the web
        address. That matters twice over here: a list of 200 identifiers is
        too long for an address, and a key in the body never appears in an
        error message, a log or a browser history, while a key in an address
        can turn up in all three.
        """
        for attempt in self._retrying():
            with attempt:
                return self._check(url, self.session.post(url, data=data, timeout=TIMEOUT))
        raise AssertionError("unreachable: tenacity either returns or re-raises")

    def _get_once(self, url: str, *, params: dict[str, str] | None = None,
                  stream: bool = False, allow_redirects: bool = True) -> requests.Response:
        """A single GET, turning HTTP refusals into clear errors. No retrying here."""
        return self._check(url, self.session.get(url, params=params, stream=stream,
                                                 allow_redirects=allow_redirects,
                                                 timeout=TIMEOUT))

    def _check(self, url: str, response: requests.Response) -> requests.Response:
        """
        Turn an HTTP refusal into an error a person can act on.

        The message names the address WITHOUT its query or body, so nothing
        sent along with the request (an identifier list, a key) is repeated.
        """
        if response.status_code == 429 or response.status_code >= 500:
            response.close()
            raise TransientHTTPError(
                f"{url} answered HTTP {response.status_code} (busy or temporarily broken)"
            )
        if response.status_code >= 400:
            response.close()
            raise SourceError(
                f"{url} answered HTTP {response.status_code}. This is not a temporary "
                f"problem, so it was not retried. Check the address in "
                f"src/microbegraph/sources/{self.name}.py."
            )
        return response

    def download_to_locker(
        self, url: str, filename: str, expected_md5: str | None,
        expected_sha256: str | None = None,
    ) -> tuple[Path, str, int, str, str]:
        """
        Download one file into the evidence locker, safely.

        Returns (path, outcome, n_bytes, md5, sha256).

        THE SAFETY RULES, AND WHY EACH EXISTS
          1. If the file is already there AND matches the expected checksum,
             do nothing. (Re-running a fetch should never cost a download.)
          2. If the file is already there and does NOT match, stop and say so.
             Never overwrite evidence: it may be the only copy of something.
          3. Download into "<name>.part" first and rename only at the end, so a
             dropped connection can never leave a half-file that looks complete.
          4. Verify the checksum before the rename. A file that arrived but is
             not the one the publisher published is thrown away, not filed.

        WHAT A CHECKSUM IS
          A short fingerprint computed from every byte of a file. Change one
          byte anywhere and the fingerprint changes completely. Publishers list
          the fingerprint next to the download; if ours matches theirs, we have
          exactly the file they published. (Rather like counting the items in
          a parcel against the packing slip before you sign for it.)

        TWO KINDS OF EXPECTED FINGERPRINT (from Phase 3b)
          expected_md5 is the one a publisher lists (Zenodo lists an MD5 for
          MIBiG's archive). expected_sha256 is one this project recorded
          itself, for a file whose publisher lists none (MIBiG's protein
          file): the first download was looked at, its SHA-256 written into
          the code, and every later download must match it. Either, both or
          neither can be given.
        """
        self.locker.mkdir(parents=True, exist_ok=True)
        target = self.locker / filename

        # Rules 1 and 2: something is already on the shelf.
        if target.exists():
            n_bytes, md5, sha256 = file_digests(target)
            mismatch = _fingerprint_mismatch(md5, sha256, expected_md5, expected_sha256)
            if not mismatch:
                self.say(f"  [{self.name}] {filename} is already in the locker and verified, "
                         f"nothing to download")
                return target, "already_present", n_bytes, md5, sha256
            raise LockerConflict(
                f"{target} exists but its {mismatch}.\n"
                f"  The locker never overwrites a file. If you are sure this copy is damaged,\n"
                f"  move it somewhere else yourself and run the fetch again."
            )

        # Rules 3 and 4, inside the retry policy: a download that breaks off
        # halfway is discarded and started again, like a dropped phone call.
        for attempt in self._retrying():
            with attempt:
                n_bytes, md5, sha256 = self._download_once(url, target, expected_md5,
                                                           expected_sha256)
        return target, "downloaded", n_bytes, md5, sha256

    def _download_once(self, url: str, target: Path, expected_md5: str | None,
                       expected_sha256: str | None = None) -> tuple[int, str, str]:
        """One attempt: stream into '<name>.part', verify, then rename. Cleans up after itself."""
        part = target.with_name(target.name + ".part")
        md5_hash, sha_hash, n_bytes = hashlib.md5(), hashlib.sha256(), 0
        self.say(f"  [{self.name}] downloading {target.name}")
        response = self._get_once(url, stream=True)   # the retrying happens one level up
        try:
            total = int(response.headers.get("Content-Length", 0)) or None
            with part.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    md5_hash.update(chunk)
                    sha_hash.update(chunk)
                    n_bytes += len(chunk)
                    self._show_progress(n_bytes, total)
            if not self.quiet:
                print(flush=True)              # end the progress line

            # Rule 4: verify before filing.
            md5, sha256 = md5_hash.hexdigest(), sha_hash.hexdigest()
            if expected_md5 is not None and md5 != expected_md5:
                raise ChecksumMismatch(
                    f"{target.name} arrived with MD5 {md5}, but the publisher lists "
                    f"{expected_md5}.\n"
                    f"  The download was discarded. Run the fetch again; if it keeps happening,\n"
                    f"  the network is altering the file (some corporate proxies do) or the\n"
                    f"  publisher changed the file, which `--probe` will show."
                )
            if expected_sha256 is not None and sha256 != expected_sha256:
                raise ChecksumMismatch(
                    f"{target.name} arrived with SHA-256 {sha256}, but this project pinned "
                    f"{expected_sha256}.\n"
                    f"  The download was discarded. Run the fetch again; if it keeps happening,\n"
                    f"  the network is altering the file or the publisher replaced it, which\n"
                    f"  `--probe` will show (the size it reports will differ from the pinned one)."
                )
            part.replace(target)               # the rename: instant and all-or-nothing
        except BaseException:
            part.unlink(missing_ok=True)       # never leave a half-file behind
            raise
        finally:
            response.close()
        return n_bytes, md5, sha256

    def _show_progress(self, done: int, total: int | None) -> None:
        if self.quiet:
            return
        mb = done / 1_048_576
        if total:
            sys.stdout.write(f"\r    {mb:6.1f} MB of {total / 1_048_576:.1f} MB "
                             f"({100 * done / total:3.0f}%)")
        else:
            sys.stdout.write(f"\r    {mb:6.1f} MB")
        sys.stdout.flush()


# --- Small tools every adapter uses --------------------------------------------------
def _fingerprint_mismatch(md5: str, sha256: str, expected_md5: str | None,
                          expected_sha256: str | None) -> str:
    """'' when the file matches every fingerprint expected, else what didn't match."""
    if expected_md5 is not None and md5 != expected_md5:
        return f"MD5 is {md5}, not the expected {expected_md5}"
    if expected_sha256 is not None and sha256 != expected_sha256:
        return f"SHA-256 is {sha256}, not the pinned {expected_sha256}"
    return ""


def file_digests(path: Path) -> tuple[int, str, str]:
    """Size in bytes, MD5 and SHA-256 of a file, read in 1 MB pieces."""
    md5, sha256, n_bytes = hashlib.md5(), hashlib.sha256(), 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
            n_bytes += len(chunk)
    return n_bytes, md5.hexdigest(), sha256.hexdigest()


# How every archive is opened. "r" = read, "|" = one pass from front to back,
# "*" = work out the compression from the file's first bytes (gzip, bzip2,
# xz, or none at all) instead of trusting the file name.
#
# Why not trust the name? MIBiG 4.0 taught me not to. Its archive is called
# mibig_json_4.0.tar.gz, its MD5 matches the one Zenodo publishes, and yet it
# is a plain tar archive with no compression at all. The first real run
# stopped with "not a gzip file". The tests only ever used archives I'd packed
# myself, so they couldn't catch it. A file name is a label someone typed; the
# first bytes are the contents.
_ARCHIVE_MODE = "r|*"


def iter_tar_json(archive: Path) -> Iterator[tuple[str, bytes]]:
    """
    Yield (member name, raw bytes) for every .json file inside a tar archive,
    compressed or not, in the order they are stored, WITHOUT unpacking the
    archive to disk.

    Reading straight from the archive keeps the evidence locker as one
    pristine file. Reading in STORED order matters for speed: a compressed
    archive can only be read front to back, so jumping around inside it means
    starting the decompression again from the beginning each time. Callers
    that need a fixed order (for identical output on every machine) sort
    afterwards, in memory, which is fast.
    """
    with tarfile.open(archive, mode=_ARCHIVE_MODE) as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".json"):
                handle = tar.extractfile(member)
                if handle is not None:
                    yield member.name, handle.read()


def count_tar_json(archive: Path) -> int:
    """How many .json records an archive holds, without unpacking it."""
    with tarfile.open(archive, mode=_ARCHIVE_MODE) as tar:
        return sum(1 for m in tar if m.isfile() and m.name.endswith(".json"))


# Greek letters appear in compound names (delta-cadinene, beta-lactam...).
# Spelling them out keeps identifiers readable and plain ASCII.
_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi",
    "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}


def slugify(text: str) -> str:
    """
    Turn a name into the local part of an identifier: lowercase, plain
    letters and digits, words joined by single hyphens.

        "surfactin"          -> "surfactin"
        "Bacillomycin D"     -> "bacillomycin-d"
        "δ-cadinene"         -> "delta-cadinene"
        "(-)-menthol"        -> "minus-menthol"
        "(+)-menthol"        -> "plus-menthol"

    Why spell out (+) and (-)? They mark mirror-image molecules, which can
    behave very differently. Dropping the sign would quietly merge two
    different chemicals into one node.
    """
    s = unicodedata.normalize("NFKC", text).strip().lower()
    s = s.replace("−", "-")                       # the true minus sign
    for sign, word in (("(+/-)", " rac "), ("(±)", " rac "),
                       ("(+)", " plus "), ("(-)", " minus ")):
        s = s.replace(sign, word)
    s = "".join(_GREEK.get(ch, ch) for ch in s)
    # Accented letters become their plain form (e.g. an accented e becomes e).
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def write_files_together(contents: dict[Path, str]) -> None:
    """
    Write several text files so that they change together: every file is first
    written to "<name>.tmp", and only when ALL of them are written are they
    renamed into place. If anything fails while writing, the .tmp files are
    removed and the old files are left exactly as they were.

    The reason: a nodes table from today sitting next to an edges table from
    yesterday is the kind of mismatch nobody would spot by eye.
    """
    tmps: list[tuple[Path, Path]] = []
    try:
        for path, text in contents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8", newline="")
            tmps.append((tmp, path))
        for tmp, path in tmps:
            tmp.replace(path)
    except BaseException:
        for tmp, _ in tmps:
            tmp.unlink(missing_ok=True)
        raise


def table_text(columns: Iterable[str], rows: Iterable[dict[str, object]]) -> str:
    """Rows as CSV text with a fixed column order (the csv module handles quoting)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_table(path: Path, columns: Iterable[str], rows: Iterable[dict[str, object]]) -> int:
    """
    Write rows to a CSV file with a fixed column order. Returns the row count.

    Written to "<name>.tmp" first and renamed at the end, for the same reason
    downloads are: a crash halfway must never leave a half-written table that
    a later step would trust.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    n = 0
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            n += 1
    tmp.replace(path)
    return n
