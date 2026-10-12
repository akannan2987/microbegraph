"""
MicrobeGraph, activity names that mean the same thing (Phase 4b).

THE SITUATION
    MIBiG records what each compound has been seen to do with a short word:
    antibacterial, antifungal, cytotoxic. Most words are distinct, but a few
    say the same thing in two ways. MIBiG 4.0 has "anticancer" (12 entries),
    "antitumor" (11 entries) and "antineoplastic" (1 entry), and one entry
    even uses the label "antitumor (duplicate of anticancer)". Left alone,
    the graph has three dots for one activity, and a question such as "which
    compounds act against cancer?" finds only a third of them.

    A shop that files the same product under "trainers" and "sneakers" has
    the same problem: two shelves, one product, and a stock count that is
    wrong on both.

WHERE THE LIST LIVES
    curation/activity_synonyms.csv, one row per word to fold away:

        activity    the word MIBiG uses ("antitumor")
        same_as     the word it means the same as ("anticancer")
        reason      why, in a sentence
        citation    where the reason can be checked (doi:..., mesh:...)
        added_on    the date the row was added

    The list is short and written by hand on purpose. Words that sound alike
    but mean different things stay apart: "cytotoxic" (kills cells) is not
    "anticancer", and "antiplasmodial" (acts on the malaria parasite in a
    dish) is not "antimalarial" (treats the disease).

WHAT THE RESOLVER DOES WITH IT
    Each word's Activity node moves to the node of the word it means the same
    as, the way an old NCBI number moves to the current one: every arrow that
    pointed at mg.activity:antitumor now points at mg.activity:anticancer,
    the two arrows from one compound become one, and the old name is kept in
    the node's other_names. The ledger gets one row per word (rule
    activity_synonym), with the reason and the citation.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from microbegraph.paths import CURATION_DIR, relative_to_repo
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.pool import Pool
from microbegraph.tables import SourceError, slugify

ACTIVITY_SYNONYMS_FILE = CURATION_DIR / "activity_synonyms.csv"
COLUMNS = ("activity", "same_as", "reason", "citation", "added_on")


@dataclass(frozen=True)
class Synonym:
    """One row of the list: `activity` means the same as `same_as`."""

    activity: str
    same_as: str
    reason: str
    citation: str
    added_on: str
    line: int

    @property
    def old_id(self) -> str:
        return f"mg.activity:{slugify(self.activity)}"

    @property
    def new_id(self) -> str:
        return f"mg.activity:{slugify(self.same_as)}"


def read_synonyms(path: Path = ACTIVITY_SYNONYMS_FILE) -> list[Synonym]:
    """
    Every row of the list, checked. A missing file means an empty list (the
    resolver still runs). A row with a blank cell, a word mapped to itself,
    a word listed twice or a chain (a -> b and b -> c) stops the run with the
    line number, because a half-applied list would be harder to spot than no
    list at all.
    """
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise SourceError(f"{relative_to_repo(path)} must have exactly these columns, in "
                              f"this order: {', '.join(COLUMNS)}")
        rows = [Synonym(**{k: (row.get(k) or "").strip() for k in COLUMNS}, line=number)
                for number, row in enumerate(reader, start=2)]
    problems: list[str] = []
    seen: dict[str, int] = {}
    for row in rows:
        blank = [k for k in COLUMNS if not getattr(row, k)]
        if blank:
            problems.append(f"line {row.line}: {', '.join(blank)} is empty")
        if row.old_id == row.new_id:
            problems.append(f"line {row.line}: '{row.activity}' is mapped to itself")
        if row.old_id in seen:
            problems.append(f"line {row.line}: '{row.activity}' is already listed on line "
                            f"{seen[row.old_id]}")
        seen[row.old_id] = row.line
    targets = {row.new_id for row in rows}
    for row in rows:
        if row.old_id in targets:
            problems.append(f"line {row.line}: '{row.activity}' is folded away, but another "
                            f"row folds a word into it; point both at the same word")
    if problems:
        raise SourceError(f"{relative_to_repo(path)} has {len(problems)} problem(s):\n    "
                          + "\n    ".join(problems))
    return rows


def fold_activities(pool: Pool, ledger: Ledger,
                    synonyms: list[Synonym] | None = None) -> dict[str, str]:
    """
    Move each listed activity to the one it means the same as, and record
    each move. Returns {old identifier: new identifier}.

    A row is applied only when a source uses both words. Otherwise it waits
    (the list may be ahead of the data, or the tests may run on a slice of
    it), and the resolver's summary lists it under
    activity_synonyms_not_applied, so a misspelt word is easy to spot.
    """
    moves: dict[str, str] = {}
    for row in synonyms if synonyms is not None else read_synonyms():
        if row.old_id not in pool.rows or row.new_id not in pool.rows:
            continue
        moves[row.old_id] = row.new_id
        used = len(pool.starts(row.old_id, "HAS_ACTIVITY"))
        ledger.add("activity_synonym", "merged", row.old_id, "Activity",
                   f"'{row.activity}' means the same as '{row.same_as}': {row.reason} "
                   f"Source: {row.citation}. {used} {'arrow moves' if used == 1 else 'arrows move'} "
                   f"with it (curation/activity_synonyms.csv, line {row.line}).",
                   compared_with=row.new_id, sources="mibig")
    return moves
