"""
MicrobeGraph, PubChem's name search done on your own computer (Phase 4b).

WHY THIS EXISTS
    PubChem's web name search answers one name per request, and PubChem
    allows one computer only so many of those. On 2026-10-12 it refused
    with "429 Too Many Requests" twice, both times after about 400 names,
    once at four names a second and once at one a second. MicrobeGraph
    has 1,655 names to look up, so asking one by one can't finish in a day.

    PubChem also publishes every name it files under every compound as one
    big download, CID-Synonym-filtered.gz, in its "Extras" folder:

        https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/Extras/CID-Synonym-filtered.gz

    Downloading that file once and searching it here asks PubChem for one
    file instead of 1,655 answers, and has no speed limit at all. It works
    like borrowing the library's whole card catalogue for the afternoon
    instead of asking the librarian about each book in turn.

THE FILE
    gzip-compressed text, one name per line: the compound's number (CID), a
    tab, then the name. A compound with many names has many lines:

        2244<TAB>aspirin
        2244<TAB>ACETYLSALICYLIC ACID
        2244<TAB>50-78-2

    "filtered" is PubChem's own selection of the names it trusts. The web
    name search can know a few names this file leaves out, so a name the
    file doesn't have isn't proof that PubChem has never heard of it. On
    the 673 names both had answered by 2026-10-12, the two agreed every
    time (docs/06b-closing-the-gaps.md, Step 5).

HOW A NAME MATCHES
    Exactly, but ignoring the capitals A to Z and spaces at either end, much
    as the web search does ("2-methylisoborneol" finds "2-Methylisoborneol").
    Other capitals (accented or Greek letters) must match as written.
    Only the names asked for are kept, so the search needs little memory
    however big the file is. Reading it takes a few minutes; a progress line
    appears every tenth of the way.
"""

from __future__ import annotations

import gzip
from collections.abc import Callable, Iterable
from pathlib import Path

from microbegraph.paths import relative_to_repo
from microbegraph.tables import SourceError

BULK_FILE = "CID-Synonym-filtered.gz"
BULK_URL = f"https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/Extras/{BULK_FILE}"

LINES_CHECKED = 1_000       # the first lines must all look like "CID<TAB>name"


def name_key_bytes(name: str) -> bytes:
    """How a name is compared: UTF-8, without spaces at the ends, capitals made small."""
    return name.strip().encode("utf-8").lower()


def search_synonym_file(path: Path, names: Iterable[str],
                        say: Callable[[str], None] | None = None) -> dict[str, list[str]]:
    """
    {name: [CIDs that list it]} for every name asked, in number order. A name
    no compound lists gets an empty list. Stops with a clear message if the
    file isn't in the expected shape, rather than quietly finding nothing.
    """
    wanted: dict[bytes, list[str]] = {}
    for name in names:
        wanted.setdefault(name_key_bytes(name), []).append(name)
    found: dict[bytes, set[int]] = {key: set() for key in wanted}

    total = path.stat().st_size
    next_report = 0.1
    with path.open("rb") as raw, gzip.GzipFile(fileobj=raw) as text:
        for number, line in enumerate(text, start=1):
            tab = line.find(b"\t")
            if number <= LINES_CHECKED and (tab < 1 or not line[:tab].isdigit()):
                shown = line[:80].decode("utf-8", errors="replace").rstrip()
                raise SourceError(
                    f"{relative_to_repo(path)}, line {number}, isn't a number, a tab and a "
                    f"name ({shown!r}). PubChem may have changed the file's layout; open "
                    f"it to see what arrived before running the fetch again.")
            if tab < 1:
                continue
            key = line[tab + 1:].rstrip(b"\r\n").strip().lower()
            if key in found:
                found[key].add(int(line[:tab]))
            if say and number % 65_536 == 0 and raw.tell() >= next_report * total:
                say(f"    searched {next_report:.0%} of {path.name}")
                next_report += 0.1
    if say and next_report <= 1.0:
        say(f"    searched 100% of {path.name}")

    result: dict[str, list[str]] = {}
    for key, originals in wanted.items():
        cids = [str(c) for c in sorted(found[key])]
        for name in originals:
            result[name] = cids
    return result
