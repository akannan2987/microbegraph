"""
MicrobeGraph, decisions made by a person (Phase 4b).

WHY THE RESOLVER NEEDS A PLACE FOR THEM
    The rules in this package only join two records when the evidence is
    clear, and list everything else. Some of what they list can only be
    settled by someone who reads the papers: MIBiG's record says one thing,
    PubChem's another, and only the original article says which is right.
    That judgement needs a home that is as visible as the rules themselves,
    so a reader can always tell a rule's decision from a person's.

    A referee's call in a match works the same way. Most of the game runs on
    the rules, but some calls need a person, and the call is written into
    the match report with the referee's reason, not slipped in quietly.

THE FILE
    curation/resolution_decisions.csv, one decision per row:

        identifier        one record, e.g. mg.compound:2-methylisoborneol
        other_identifier  the other record, e.g. pubchem.compound:16913
        decision          join (they are the same thing) or keep_apart
        reason            why, in a sentence or two a reader can check
        citation          where to check it: doi:..., pubmed:..., or a
                          database record (pubchem.compound:16913, uniprot:P0CU77)
        decided_on        the date (YYYY-MM-DD)

    curation/README.md explains how to add a row.

WHAT THE RESOLVER DOES WITH IT
    Every decision is applied BEFORE the rules that join compounds and
    proteins run (only the organism number moves and the activity synonyms
    come first), and those rules leave a pair a person has settled alone:

        join        the two records become one group at once, and the
                    ledger gets a row (rule reviewed_by_hand, decision
                    merged) with the reason and the citation
        keep_apart  the two may never end up in one group, by any rule or
                    any chain of joins, and the ledger gets a row (decision
                    kept_apart) saying so

    A decision wins over a rule, and says so in the ledger. That is the
    whole point of it, and also why every row needs a citation: an
    override nobody can check would be worse than the gap it closes.

WHAT STOPS THE RUN
    A row with an empty cell or an unknown decision, the same pair twice, an
    identifier no source has (a typo, or a record not fetched yet), or a join
    the graph can't hold (two PubChem compounds, which PubChem itself says
    are different molecules). Each message names the line.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from microbegraph.paths import CURATION_DIR, relative_to_repo
from microbegraph.resolution.groups import Groups, rank_key
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.pool import Pool
from microbegraph.tables import SourceError

DECISIONS_FILE = CURATION_DIR / "resolution_decisions.csv"
COLUMNS = ("identifier", "other_identifier", "decision", "reason", "citation", "decided_on")
CHOICES = ("join", "keep_apart")
_CURIE = re.compile(r"^[a-z][a-z0-9.]*:\S+$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Decision:
    """One row of the review file."""

    identifier: str
    other_identifier: str
    decision: str
    reason: str
    citation: str
    decided_on: str
    line: int

    @property
    def pair(self) -> frozenset[str]:
        return frozenset((self.identifier, self.other_identifier))

    def grounds(self) -> str:
        """The ledger's sentence for this decision."""
        verb = "the same thing" if self.decision == "join" else "different things"
        return (f"Decided by hand on {self.decided_on}: {self.identifier} and "
                f"{self.other_identifier} are {verb}. {self.reason} Source: {self.citation} "
                f"(curation/resolution_decisions.csv, line {self.line}).")


def read_decisions(path: Path = DECISIONS_FILE) -> list[Decision]:
    """Every row of the review file, checked (see WHAT STOPS THE RUN). No file, no decisions."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise SourceError(f"{relative_to_repo(path)} must have exactly these columns, in "
                              f"this order: {', '.join(COLUMNS)}")
        rows = [Decision(**{k: (row.get(k) or "").strip() for k in COLUMNS}, line=number)
                for number, row in enumerate(reader, start=2)]
    problems: list[str] = []
    seen: dict[frozenset[str], int] = {}
    for row in rows:
        blank = [k for k in COLUMNS if not getattr(row, k)]
        if blank:
            problems.append(f"line {row.line}: {', '.join(blank)} is empty")
            continue
        if row.decision not in CHOICES:
            problems.append(f"line {row.line}: decision is '{row.decision}', but it must be "
                            f"join or keep_apart")
        for identifier in (row.identifier, row.other_identifier):
            if not _CURIE.match(identifier):
                problems.append(f"line {row.line}: '{identifier}' isn't an identifier "
                                f"(prefix:local, e.g. pubchem.compound:16913)")
        if row.identifier == row.other_identifier:
            problems.append(f"line {row.line}: a record can't be compared with itself")
        if not _DATE.match(row.decided_on):
            problems.append(f"line {row.line}: decided_on must be a date written YYYY-MM-DD")
        if row.pair in seen:
            problems.append(f"line {row.line}: the same pair is already decided on line "
                            f"{seen[row.pair]}")
        seen.setdefault(row.pair, row.line)
    if problems:
        raise SourceError(f"{relative_to_repo(path)} has {len(problems)} problem(s):\n    "
                          + "\n    ".join(problems))
    return rows


class Reviewed:
    """The decisions, ready for the rules to ask: has a person settled this pair?"""

    def __init__(self, decisions: list[Decision]) -> None:
        self._by_pair = {d.pair: d for d in decisions}
        self._touched = {i for d in decisions for i in d.pair}

    def settled(self, a: str, b: str) -> Decision | None:
        """The decision about a and b, if a person made one."""
        return self._by_pair.get(frozenset((a, b)))

    def kept_apart(self, a: str, b: str) -> bool:
        decision = self.settled(a, b)
        return decision is not None and decision.decision == "keep_apart"

    def mentions(self, identifier: str) -> bool:
        """Does any decision name this identifier?"""
        return identifier in self._touched


def apply_decisions(pool: Pool, groups: Groups, ledger: Ledger,
                    decisions: list[Decision] | None = None) -> Reviewed:
    """Apply every decision before the matching rules run (see WHAT THE RESOLVER DOES)."""
    decisions = read_decisions() if decisions is None else decisions
    problems: list[str] = []
    for row in decisions:
        missing = [i for i in (row.identifier, row.other_identifier) if i not in pool.rows]
        if missing:
            problems.append(f"line {row.line}: no source has {', '.join(missing)}")
    if problems:
        raise SourceError(
            f"{relative_to_repo(DECISIONS_FILE)} names records the graph doesn't have:\n    "
            + "\n    ".join(problems)
            + "\n  Check the spelling. A PubChem compound named here is fetched by the next "
              "`python -m microbegraph.fetch --source pubchem`.")

    for row in decisions:
        a, b = row.identifier, row.other_identifier
        node_type = sorted(pool.types(a))[0]
        sources = "|".join(dict.fromkeys(pool.sources(a) + pool.sources(b)))
        if row.decision == "keep_apart":
            if groups.leader(a) == groups.leader(b):
                raise SourceError(
                    f"{relative_to_repo(DECISIONS_FILE)}, line {row.line}: {a} and {b} are "
                    f"already one group, joined by a row above, so they can't be kept apart. "
                    f"Remove one of the two rows.")
            groups.forbid(a, b)
            ledger.add("reviewed_by_hand", "kept_apart", a, node_type, row.grounds(),
                       compared_with=b, sources=sources)
            continue
        if not groups.can_join(a, b):
            raise SourceError(
                f"{relative_to_repo(DECISIONS_FILE)}, line {row.line}: {a} and {b} can't be "
                f"joined: the group would hold two PubChem compounds or two UniProt entries "
                f"(which their own databases say are different), or a decision above keeps "
                f"them apart.")
        stays, goes = sorted((groups.leader(a), groups.leader(b)), key=rank_key)
        groups.join(a, b)
        ledger.add("reviewed_by_hand", "merged", goes, node_type, row.grounds(),
                   compared_with=stays, sources=sources)
    return Reviewed(decisions)
