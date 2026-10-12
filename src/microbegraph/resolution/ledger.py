"""
MicrobeGraph, the resolution ledger.

WHAT IT IS
    One row for every decision the resolver makes: two records joined into
    one node, a join refused, an old number moved to a new one, an entry
    left out of the graph. Each row says which rule decided it and on what
    grounds, in a sentence a person can check.

    A bank statement is the everyday version. The balance is the graph; the
    statement is the ledger. Nobody trusts a balance that can't be explained
    line by line, and nobody should trust a merged dot that can't either.

THE COLUMNS
    rule           which rule decided (the list is RULES, below)
    decision       merged, moved, combined, kept_apart or left_out
    identifier     the identifier this row is about
    node_id        the node it ended up in (empty when it was left out)
    compared_with  the other identifier the evidence involves, if any
    node_type      Organism, Compound, Protein...
    grounds        the evidence, in words
    sources        the sources whose records were involved

    Looking up any identifier in the identifier column tells you where it
    went. Looking up a node in node_id lists everything that became it.

WHERE IT GOES
    data/processed/resolution_ledger.csv, and the "ledger" table of the
    database. The ledger is one of the project's outputs, as much as the
    graph: it's how anyone can check the graph without redoing the work.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

LEDGER_COLUMNS: tuple[str, ...] = (
    "rule", "decision", "identifier", "node_id", "compared_with", "node_type",
    "grounds", "sources",
)

DECISIONS: tuple[str, ...] = ("combined", "moved", "merged", "kept_apart", "left_out")

# Every rule the resolver applies, in the order it applies them, with the
# one-line description the guide and the summary use.
RULES: dict[str, str] = {
    "same_identifier":
        "The same identifier from several sources becomes one node with every source's facts",
    "ncbi_merged_number":
        "NCBI has merged an organism's number into another: the old number moves to the new one",
    "organism_and_pathogen":
        "An identifier that is an Organism in one source and a Pathogen in another becomes "
        "one Pathogen node, a kind of Organism",
    "pubchem_number_confirmed":
        "MIBiG gives a PubChem number, and the name or the formula confirms it",
    "pubchem_number_shared":
        "Several MIBiG compounds give one PubChem number: each needs its own name confirmed",
    "pubchem_number_unknown":
        "MIBiG gives a PubChem number that PubChem doesn't have",
    "npatlas_and_formula":
        "Two MIBiG compounds with the same NPAtlas number and the same formula are one compound",
    "uniprot_cross_reference":
        "UniProt lists the protein number under one of its entries "
        "(organism, then length, then review status choose between several)",
    "identical_sequence":
        "The same sequence in the same organism is one protein",
    "gene_name_in_uniprot":
        "A gene record named only by a gene name joins the one protein of its cluster that "
        "UniProt gives that gene name",
    "not_used":
        "A PubChem or UniProt entry that no MIBiG compound or protein ended up joined to",
}


@dataclass
class Ledger:
    """The ledger rows, collected while the rules run."""

    rows: list[dict[str, str]] = field(default_factory=list)

    def add(self, rule: str, decision: str, identifier: str, node_type: str,
            grounds: str, compared_with: str = "", sources: str = "") -> None:
        """Record one decision. node_id is filled in at the end (see finish())."""
        if rule not in RULES:
            raise ValueError(f"unknown rule {rule!r}; add it to RULES with a description")
        if decision not in DECISIONS:
            raise ValueError(f"unknown decision {decision!r}")
        self.rows.append({
            "rule": rule, "decision": decision, "identifier": identifier, "node_id": "",
            "compared_with": compared_with, "node_type": node_type, "grounds": grounds,
            "sources": sources,
        })

    def finish(self, final_id: Callable[[str], str]) -> list[dict[str, str]]:
        """
        Fill in where each identifier ended up, and return the rows in a fixed
        order (by rule, then identifier), so the file is the same on every run.

        final_id(identifier) gives the node an identifier became, or "" when it
        was left out of the graph.
        """
        order = {rule: i for i, rule in enumerate(RULES)}
        for row in self.rows:
            row["node_id"] = "" if row["decision"] == "left_out" else final_id(row["identifier"])
        self.rows.sort(key=lambda r: (order[r["rule"]], r["identifier"], r["compared_with"],
                                      r["decision"]))
        return self.rows

    def counts(self) -> dict[str, dict[str, int]]:
        """How many rows each rule wrote, by decision: {rule: {decision: n}}."""
        tally: Counter[tuple[str, str]] = Counter((r["rule"], r["decision"]) for r in self.rows)
        result: dict[str, dict[str, int]] = {}
        for rule in RULES:
            by_decision = {d: tally[(rule, d)] for d in DECISIONS if tally[(rule, d)]}
            if by_decision:
                result[rule] = by_decision
        return result
