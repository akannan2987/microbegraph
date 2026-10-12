"""
MicrobeGraph, the table shapes and the safe way to write them.

WHAT LIVES HERE
    The two table shapes every step of the pipeline reads and writes (the
    columns of nodes.csv and edges.csv), the error a person can act on, and
    the helpers that write tables without ever leaving half a file behind:

        NODE_COLUMNS, EDGE_COLUMNS   the columns, in order
        SourceError                  "something went wrong, and here's what to do"
        TidyResult                   what one tidy wrote, with its counts
        table_text, write_table      rows as CSV text, or straight to a file
        write_files_together         several files that change together or not at all
        slugify                      a name turned into the local part of an identifier

WHY THIS IS ITS OWN FILE (Phase 4b)
    Until Phase 4b these lived in src/microbegraph/sources/base.py, inside the
    adapters' package. That made one import order fail: `import
    microbegraph.staging` on its own loaded the package, the package loaded
    every adapter, and the adapters asked for staging while it was still
    half loaded. Python calls this a circular import. Every command happened
    to load the adapters first, so nothing broke in practice, but a new
    script or a notebook could have tripped over it.

    A household version: two people each waiting at the door for the other
    to come through first. Moving the shared pieces into a room of their
    own, which needs nothing from either of them, lets both go through.

    sources/base.py still offers every name below (it imports them from
    here), so code written for the earlier layout keeps working.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# The columns of nodes.csv and edges.csv in docs/02-ontology-and-data-model.md,
# section 7. Same names, same order.
NODE_COLUMNS: tuple[str, ...] = (
    "node_id", "node_type", "name", "properties", "source", "retrieved_at",
)
EDGE_COLUMNS: tuple[str, ...] = (
    "source_id", "target_id", "edge_type", "evidence_level", "source",
    "source_record_id", "citation", "confidence", "retrieved_at",
)


class SourceError(Exception):
    """Something went wrong in a way the person running the command can fix.
    The message always says what happened AND what to do next."""


@dataclass
class TidyResult:
    """What one tidy wrote to the staging folder, and the counts behind it."""

    source: str
    nodes_path: Path
    edges_path: Path
    counts: dict[str, int]


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
