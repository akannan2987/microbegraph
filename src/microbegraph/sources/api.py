"""
MicrobeGraph, what the web-API sources have in common (Phase 2).

TWO KINDS OF SOURCE
    MIBiG publishes one file per release. You download it once, compare its
    checksum with the one the publisher lists, and you're done.

    PubChem, NCBI Taxonomy and KEGG work differently. There's no single file
    to download. Instead you send questions to a web address and get answers
    back, which is what an API (application programming interface) is: a
    service desk for programs. The answers can change any day, there is no
    release number, and nobody publishes a checksum for them.

    It's the difference between buying a printed encyclopedia and phoning a
    library's enquiry desk. The book never changes once printed; the desk
    gives today's answer.

HOW AN API ANSWER IS KEPT AS EVIDENCE: SNAPSHOTS
    Every fetch from an API source makes one new folder in the evidence
    locker, named after the moment the fetch started (UTC, without colons,
    because Windows doesn't allow colons in folder names):

        data/raw/pubchem/2026-10-12T055202Z/
            properties_001.json      answers, saved exactly as they arrived
            synonyms_001.json
            ...
            manifest.json            what was asked, written LAST

    * Every answer gets its own row in data/raw/provenance.csv, with its size
      and fingerprints. The publisher doesn't list a checksum, so these are
      ours: they prove the file in the locker is the answer that arrived.
    * manifest.json is written only after every answer is safely saved. A
      folder without one is an unfinished fetch (the connection dropped
      halfway, say). tidy() ignores it and probe() points it out. It's the
      packing slip that goes into a parcel only once everything is packed.
    * tidy() reads the newest finished snapshot. Older ones stay where they
      are, so you can compare two of them and see what changed at the source.

ASKING THE SAME QUESTIONS TWICE IN ONE DAY
    If a finished snapshot from today (UTC) asked exactly the same questions,
    fetch() uses it again instead of asking the server a second time, and
    logs one "already_present" row. A new day, or a different set of
    questions (a new pathogen in the bridge, say), makes a new snapshot.

PACING
    Each service publishes a limit on how fast you may ask. Every adapter
    pauses between requests to stay well inside its limit (PubChem 5 a
    second, NCBI 3 a second without a key and 10 with one, KEGG 3 a second).
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from microbegraph import provenance
from microbegraph.paths import relative_to_repo
from microbegraph.sources.base import FetchResult, Source, SourceError, file_digests

MANIFEST = "manifest.json"

# 2026-10-12T055202Z, with "-2", "-3"... added in the rare case of two fetches
# starting in the same second.
_SNAPSHOT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6}Z(-\d+)?$")


def folder_name(moment: str) -> str:
    """'2026-10-12T05:52:02Z' -> '2026-10-12T055202Z' (no colons, so Windows accepts it)."""
    return moment.replace(":", "")


def chunks(items: list[str], size: int) -> list[list[str]]:
    """Split a list into batches of at most `size` items, keeping the order."""
    return [items[start:start + size] for start in range(0, len(items), size)]


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def batches_text(n: int) -> str:
    """'1 batch', '12 batches'."""
    return f"{n} batch" if n == 1 else f"{n} batches"


def size_text(n_bytes: int) -> str:
    """A size people can read: '4.3 KB' below a megabyte, '2.6 MB' above."""
    if n_bytes < 1_048_576:
        return f"{n_bytes / 1024:.1f} KB"
    return f"{n_bytes / 1_048_576:.1f} MB"


class Snapshot:
    """
    One fetch's folder in the locker, being filled.

    save() files each answer and logs it; finish() writes the manifest.
    Until finish() runs, the folder counts as unfinished.
    """

    def __init__(self, source: ApiSource, asked_for: dict[str, Any],
                 context: dict[str, Any] | None = None) -> None:
        self.source = source
        self.asked_for = asked_for
        self.context = context or {}
        self.started_at = provenance.utc_now()
        base = folder_name(self.started_at)
        folder, n = source.locker / base, 2
        while folder.exists():
            folder, n = source.locker / f"{base}-{n}", n + 1
        # The folder is made when the first answer arrives, so a fetch that
        # fails on its very first request (no internet, say) leaves no
        # empty folder behind.
        self.folder = folder
        self.answers: list[dict[str, Any]] = []

    def save(self, filename: str, body: bytes, *, url: str, method: str,
             sent: dict[str, Any], n_records: int | str, source_version: str) -> Path:
        """
        File one answer exactly as it arrived and log it.

        `url` is the address WITHOUT anything secret, and `sent` describes
        what went with the request, with any key shown only as "set" or
        "not set". Neither ever holds a key itself.
        """
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / filename
        part = path.with_name(path.name + ".part")
        part.write_bytes(body)
        part.replace(path)                      # all-or-nothing, like every download here
        n_bytes, md5, sha256 = file_digests(path)
        provenance.append(
            {
                "retrieved_at": provenance.utc_now(),
                "source": self.source.name,
                "source_version": source_version,
                "url": url,
                "local_path": relative_to_repo(path),
                "n_bytes": n_bytes,
                "md5": md5,
                "sha256": sha256,
                "n_records": n_records,
                "licence": self.source.licence,
                "outcome": "downloaded",
            },
            log_path=self.source.provenance_log,
        )
        self.answers.append({"file": filename, "method": method, "url": url, "sent": sent,
                             "n_bytes": n_bytes, "sha256": sha256, "n_records": n_records})
        return path

    def finish(self, source_version: str, notes: dict[str, Any] | None = None) -> list[FetchResult]:
        """Write manifest.json, which marks the snapshot as complete."""
        manifest = {
            "source": self.source.name,
            "started_at": self.started_at,
            "finished_at": provenance.utc_now(),
            "source_version": source_version,
            "licence": self.source.licence,
            "asked_for": self.asked_for,
            "context": self.context,
            "answers": self.answers,
            "notes": notes or {},
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / MANIFEST
        part = path.with_name(path.name + ".part")
        part.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        part.replace(path)
        n_bytes = sum(int(a["n_bytes"]) for a in self.answers)
        n_records = sum(int(a["n_records"] or 0) for a in self.answers)
        self.source.say(f"  [{self.source.name}] downloaded: {relative_to_repo(self.folder)}/ "
                        f"({len(self.answers)} answers, {size_text(n_bytes)}), "
                        f"provenance logged")
        return [FetchResult(self.source.name, self.folder, "downloaded", n_bytes, n_records)]


class ApiSource(Source):
    """
    The shared machinery for sources that answer questions over the web.

    A subclass still writes probe(), fetch() and tidy() itself; this class
    gives it snapshots, pacing and reuse, so the three adapters don't each
    reinvent them.
    """

    pause_seconds: float = 0.5      # between requests; each adapter sets its own

    def __init__(self, *args: Any, pause_seconds: float | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if pause_seconds is not None:            # tests pass 0, so they never wait
            self.pause_seconds = pause_seconds

    # ---------------------------------------------------------------- pacing
    def pause(self, factor: float = 1.0) -> None:
        """Wait between two requests, to stay inside the service's speed limit."""
        if self.pause_seconds > 0:
            time.sleep(self.pause_seconds * factor)

    # ---------------------------------------------------------------- snapshots
    def _snapshot_folders(self) -> list[Path]:
        if not self.locker.exists():
            return []
        return sorted(p for p in self.locker.iterdir()
                      if p.is_dir() and _SNAPSHOT_NAME.match(p.name))

    def snapshots(self) -> list[Path]:
        """Finished snapshots (those with a manifest), oldest first."""
        return [p for p in self._snapshot_folders() if (p / MANIFEST).exists()]

    def unfinished_snapshots(self) -> list[Path]:
        """Snapshot folders with no manifest: fetches that stopped halfway."""
        return [p for p in self._snapshot_folders() if not (p / MANIFEST).exists()]

    def read_manifest(self, folder: Path) -> dict[str, Any]:
        return json.loads((folder / MANIFEST).read_text(encoding="utf-8"))

    def latest_snapshot(self) -> tuple[Path, dict[str, Any]]:
        """The newest finished snapshot and its manifest, or a clear error if there is none."""
        finished = self.snapshots()
        if not finished:
            raise SourceError(
                f"{relative_to_repo(self.locker)}/ holds no finished fetch yet.\n"
                f"  Run:  python -m microbegraph.fetch --source {self.name}"
            )
        return finished[-1], self.read_manifest(finished[-1])

    def start_snapshot(self, asked_for: dict[str, Any],
                       context: dict[str, Any] | None = None) -> Snapshot:
        return Snapshot(self, asked_for, context)

    def reuse_today(self, asked_for: dict[str, Any]) -> list[FetchResult] | None:
        """
        If a finished snapshot from today asked exactly these questions, log
        it as already present and return it. Otherwise return None.
        """
        wanted = json.loads(json.dumps(asked_for))       # same shape as a manifest holds
        for folder in reversed(self.snapshots()):
            manifest = self.read_manifest(folder)
            if not str(manifest.get("started_at", "")).startswith(utc_today()):
                return None                              # the newest is older than today
            if manifest.get("asked_for") != wanted:
                continue
            path = folder / MANIFEST
            n_bytes, md5, sha256 = file_digests(path)
            n_records = sum(int(a.get("n_records") or 0) for a in manifest.get("answers", []))
            provenance.append(
                {
                    "retrieved_at": provenance.utc_now(),
                    "source": self.name,
                    "source_version": manifest.get("source_version", ""),
                    "url": "",
                    "local_path": relative_to_repo(path),
                    "n_bytes": n_bytes,
                    "md5": md5,
                    "sha256": sha256,
                    "n_records": n_records,
                    "licence": self.licence,
                    "outcome": "already_present",
                },
                log_path=self.provenance_log,
            )
            self.say(f"  [{self.name}] today's fetch {relative_to_repo(folder)}/ already asked "
                     f"these questions; using it again (nothing downloaded)")
            return [FetchResult(self.name, folder, "already_present", n_bytes, n_records)]
        return None

    def locker_facts(self) -> tuple[list[str], list[str]]:
        """What probe() says about the locker: (facts, warnings)."""
        facts: list[str] = []
        warnings: list[str] = []
        finished = self.snapshots()
        if finished:
            newest = self.read_manifest(finished[-1])
            facts.append(f"in your locker : {len(finished)} finished fetch(es), newest "
                         f"{finished[-1].name} ({newest.get('source_version', '?')})")
        else:
            facts.append("in your locker : nothing yet (run the fetch)")
        unfinished = self.unfinished_snapshots()
        if unfinished:
            names = ", ".join(p.name for p in unfinished)
            warnings.append(
                f"{len(unfinished)} unfinished fetch folder(s) in {relative_to_repo(self.locker)}/: "
                f"{names}. tidy ignores them. You can delete them, or keep them as a record."
            )
        return facts, warnings
