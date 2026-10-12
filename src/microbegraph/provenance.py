"""
MicrobeGraph, the provenance log.

WHAT PROVENANCE MEANS
    Provenance is the documented history of where something came from.
    In art, it is the chain of owners that proves a painting is genuine.
    Here it's one line per download, and it answers the question a careful
    reader gets to sooner or later: "where did this number come from, and
    when?"

WHAT GETS WRITTEN
    data/raw/provenance.csv, never edited, only added to. One row for every
    file a fetch saves: one per fetch for MIBiG's archive (and, from Phase
    3b, one for its protein file), and one per answer for the web APIs from
    Phase 2 on (PubChem, NCBI Taxonomy, KEGG, UniProt).

    | column         | example (the first real MIBiG fetch)          |
    |----------------|-----------------------------------------------|
    | retrieved_at   | 2026-10-10T16:44:39Z  (UTC, to the second)    |
    | source         | mibig                                         |
    | source_version | 4.0                                           |
    | url            | https://zenodo.org/records/14169073/files/... |
    | local_path     | data/raw/mibig/mibig_json_4.0.tar.gz          |
    | n_bytes        | 10004480                                      |
    | md5            | ce1736f4fac7168d85dae3b37c77d3d2              |
    | sha256         | d02a387c...  (64 hex characters)              |
    | n_records      | 3013  (blank if the file could not be opened) |
    | licence        | CC-BY-4.0                                     |
    | outcome        | downloaded / already_present / derived        |

    "derived" (from Phase 4b) marks a file worked out on this computer from
    one that was downloaded, rather than received from a server: PubChem's
    name search done in its names file is the first example. Its url column
    says where the downloaded file came from.

WHY "ONLY ADDED TO"
    If a log can be rewritten, nobody can fully trust it. The functions below
    append a row and read rows back, and I left out any function that changes
    or deletes one.

    A bank statement works the same way. Last month's lines are never edited;
    a correction arrives as a new line that refers to the old one.

WHY UTC
    "10:00" means different moments in Zurich, Bangalore and New York. A log
    that gets read on three continents needs a single clock, so every
    timestamp is UTC and ends in "Z" (the international marker for UTC).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from microbegraph.paths import PROVENANCE_LOG

# The column order is part of the format. Adding a column later means
# appending it at the END, so older logs stay readable.
COLUMNS: tuple[str, ...] = (
    "retrieved_at",
    "source",
    "source_version",
    "url",
    "local_path",
    "n_bytes",
    "md5",
    "sha256",
    "n_records",
    "licence",
    "outcome",
)


def utc_now() -> str:
    """The current moment in UTC, as text like 2026-10-10T09:41:07Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(row: dict[str, object], log_path: Path = PROVENANCE_LOG) -> None:
    """
    Add one row to the provenance log, creating the file (with its header) if needed.

    Refuses a row with missing or unexpected columns. A half-filled provenance
    row looks like an answer when it isn't one, which makes it worse than no
    row at all.
    """
    missing = [c for c in COLUMNS if c not in row]
    extra = [c for c in row if c not in COLUMNS]
    if missing or extra:
        raise ValueError(
            f"provenance row does not match the log format. "
            f"Missing: {missing or 'none'}. Unexpected: {extra or 'none'}."
        )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()

    # newline="" is the csv module's own requirement: it writes the correct
    # line endings itself, identically on Windows, macOS and Linux.
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def read(log_path: Path = PROVENANCE_LOG) -> list[dict[str, str]]:
    """Every row of the log, oldest first. An empty list if nothing was fetched yet."""
    if not log_path.exists():
        return []
    # "utf-8-sig" also reads a file that a spreadsheet program re-saved with an
    # invisible marker (a "byte-order mark") at the start. Better still, open
    # the log in VS Code rather than a spreadsheet program, so it never gets
    # re-saved in the first place.
    with log_path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def latest(
    source: str,
    local_path: str,
    log_path: Path = PROVENANCE_LOG,
    outcome: str | None = "downloaded",
) -> dict[str, str] | None:
    """
    The most recent row for one file of one source, or None.

    tidy() uses this to stamp every row it produces with the date the raw
    file was actually downloaded. That is neither the date tidy() happened to
    run nor the date a later fetch merely confirmed the file was still there.
    The "as of" date describes the data, so it has to come from the download.

    Pass outcome=None to get the latest row of any kind.
    """
    matches = [
        row for row in read(log_path)
        if row["source"] == source
        and row["local_path"] == local_path
        and (outcome is None or row["outcome"] == outcome)
    ]
    return matches[-1] if matches else None
