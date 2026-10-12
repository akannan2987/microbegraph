"""
MicrobeGraph, resolving proteins.

THE SITUATION
    MIBiG names about 40,000 proteins, mostly by INSDC or RefSeq protein
    numbers (ncbiprotein:CAE02630.1). Phases 3 and 3b asked UniProt which of
    its entries carry each number, and UniProt answered with about 20,500
    entries, each listing the numbers it was found through
    (mibig_protein_ids). As with compounds, the graph has two records of one
    protein, and the job is to join them only where the evidence is clear.

    The evidence here is stronger than for compounds. UniProt's link from an
    entry to a protein number is UniProt's own cross-reference to that exact
    sequence record, kept by UniProt, not a number someone typed into MIBiG.

THE THREE RULES, IN THE ORDER THEY RUN

    rule uniprot_cross_reference
        A number with ONE UniProt entry joins it. Most numbers are like this.
        A number with SEVERAL entries (82 of them, mostly RefSeq "WP_" numbers
        that NCBI shares between strains with identical proteins) needs a way
        to pick one, tried in this order:
            1. the entry whose organism is the cluster's organism
            2. among those, the entry whose length matches MIBiG's sequence
            3. among those, the one entry a curator has reviewed (Swiss-Prot)
        If none of these leaves exactly one entry, the number stays on its own
        and the candidates are listed. Several numbers can join one entry (the
        same protein submitted twice), which makes one node encoded by more
        than one cluster. An entry no number ends up choosing is left out.

    rule identical_sequence
        Two protein records with the same sequence fingerprint (the MD5 from
        MIBiG's protein file, Phase 3b) in the SAME organism are one protein,
        for example a gene listed once by its locus tag and once by its number.
        Different organisms stay apart, however identical the sequences: two
        strains each make their own copy, and the graph keeps track of which
        strain makes what. If UniProt has two separate entries for the pair,
        UniProt's separation wins.

    rule gene_name_in_uniprot
        In Phase 4, 59 gene records named their protein only by a gene name
        that MIBiG's protein file doesn't use (baeB in the bacillaene
        cluster, for example). If UniProt gives that gene name to exactly ONE
        protein of the same cluster, the gene record joins that protein, and
        the gene record's facts (its job in the pathway, the experiment that
        showed it) move with it; 38 joined this way. From Phase 4b the MIBiG
        adapter finds all 59 in MIBiG's GenBank file before the resolver
        runs, so this rule is a fallback that the real data no longer needs.
"""

from __future__ import annotations

import re
from collections import defaultdict

from microbegraph.resolution.groups import Groups, rank_key
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.names import split_list
from microbegraph.resolution.pool import Pool
from microbegraph.resolution.reviewed import Reviewed


def gene_names(text: object) -> set[str]:
    """
    UniProt's gene names for one entry, lowercased. The UniProt adapter joins
    them with "|" ("baeI|PV946_13250"). Phase 4 split them on spaces and ";"
    only, so an entry with more than one gene name never matched; Phase 4b
    found that while checking baeI, whose entry Q1RS74 lists two names.
    """
    return {n.lower() for n in re.split(r"[|;\s]+", str(text or "")) if n}


def _taxid(node_id: str) -> str:
    return node_id.split(":", 1)[1] if node_id.startswith("ncbitaxon:") else ""


class ProteinFacts:
    """What the protein rules need to know about each MIBiG protein, worked out once."""

    def __init__(self, pool: Pool, moves: dict[str, str]) -> None:
        self.pool = pool
        self.organisms: dict[str, set[str]] = {}   # protein -> organism taxids (old and new)
        self.current: dict[str, frozenset[str]] = {}  # protein -> current organism ids only
        for protein in pool.ids("ncbiprotein") + pool.ids("mg.protein"):
            taxids: set[str] = set()
            current: set[str] = set()
            for cluster in pool.starts(protein, "ENCODES"):
                for organism in pool.starts(cluster, "HARBORS"):
                    moved = moves.get(organism, organism)
                    taxids |= {_taxid(organism), _taxid(moved)}
                    current.add(moved)
            self.organisms[protein] = taxids - {""}
            self.current[protein] = frozenset(current)

    def length(self, protein: str) -> str:
        return str(self.pool.props(protein, "mibig").get("sequence_length", ""))


def _entry(pool: Pool, entry: str) -> dict:
    return pool.props(entry, "uniprot")


def join_uniprot(pool: Pool, groups: Groups, ledger: Ledger, facts: ProteinFacts,
                 notes: dict[str, list[str]], reviewed: Reviewed | None = None) -> None:
    """Rule uniprot_cross_reference (see the module notes)."""
    reviewed = reviewed or Reviewed([])
    candidates: dict[str, list[str]] = defaultdict(list)
    for entry in pool.ids("uniprot"):
        for number in split_list(_entry(pool, entry).get("mibig_protein_ids")):
            if number in pool.rows:
                candidates[number].append(entry)

    for number in sorted(candidates):
        # Phase 4b: a pair a person settled is left to that decision.
        settled = [e for e in candidates[number] if reviewed.settled(number, e)]
        if any(reviewed.settled(number, e).decision == "join" for e in settled):
            continue
        entries = sorted(e for e in candidates[number] if e not in settled)
        if not entries:
            continue
        chosen, how = _choose(pool, facts, number, entries)
        if chosen and not groups.can_join(chosen, number):
            chosen, how = "", ", but it is already one with another UniProt entry"
        if chosen:
            groups.join(chosen, number)
            accession = chosen.split(":", 1)[1]
            ledger.add("uniprot_cross_reference", "merged", number, "Protein",
                       f"UniProt lists {number.split(':', 1)[1]} under entry {accession}"
                       f"{how}.", compared_with=chosen, sources="mibig|uniprot")
        else:
            listed = ", ".join(e.split(":", 1)[1] for e in entries)
            ledger.add("uniprot_cross_reference", "kept_apart", number, "Protein",
                       f"UniProt lists {number.split(':', 1)[1]} under {len(entries)} entries "
                       f"({listed}){how}, so the number stays on its own.",
                       compared_with="|".join(entries), sources="mibig|uniprot")
            notes[number].append(f"{number.split(':', 1)[1]}: UniProt candidates, none "
                                 f"chosen: {listed}")


def _choose(pool: Pool, facts: ProteinFacts, number: str,
            entries: list[str]) -> tuple[str, str]:
    """
    Pick the one entry a number joins, or ("", reason) when the evidence
    doesn't single one out. The reason text finishes the ledger sentence.
    """
    if len(entries) == 1:
        return entries[0], ""
    organisms = facts.organisms.get(number, set())
    same_organism = [e for e in entries
                     if str(_entry(pool, e).get("organism_taxid", "")) in organisms]
    if len(same_organism) == 1:
        return same_organism[0], (f", one of {len(entries)} entries, and the only one for the "
                                  f"cluster's organism (taxid {_entry(pool, same_organism[0])['organism_taxid']})")
    if not same_organism:
        return "", ", none of them for the cluster's organism"
    length = facts.length(number)
    same_length = [e for e in same_organism if str(_entry(pool, e).get("length", "")) == length]
    if len(same_length) == 1:
        return same_length[0], (f", one of {len(same_organism)} entries for the cluster's "
                                f"organism, and the only one {length} amino acids long, "
                                f"like MIBiG's sequence")
    shortlist = same_length or same_organism
    reviewed = [e for e in shortlist if str(_entry(pool, e).get("reviewed", "")).lower() == "true"]
    if len(reviewed) == 1:
        return reviewed[0], (f", one of {len(shortlist)} equally good entries for the "
                             f"cluster's organism, and the only one a curator has reviewed")
    if not length:
        sizes = "with no length from MIBiG to compare"
    elif same_length:
        sizes = f"all {length} amino acids long"
    else:
        sizes = f"none of them {length} amino acids long like MIBiG's sequence"
    checked = (f"{len(reviewed)} reviewed by a curator" if reviewed
               else "none reviewed by a curator")
    return "", f", {len(shortlist)} of them for the cluster's organism, {sizes}, and {checked}"


def join_identical_sequences(pool: Pool, groups: Groups, ledger: Ledger,
                             facts: ProteinFacts, reviewed: Reviewed | None = None) -> None:
    """Rule identical_sequence (see the module notes)."""
    reviewed = reviewed or Reviewed([])
    by_fingerprint: dict[tuple[str, frozenset[str]], list[str]] = defaultdict(list)
    for protein, organisms in facts.current.items():
        md5 = pool.props(protein, "mibig").get("sequence_md5", "")
        if md5 and organisms:
            by_fingerprint[(md5, organisms)].append(protein)

    for (md5, organisms), members in sorted(by_fingerprint.items()):
        if len(members) < 2:
            continue
        first, *rest = sorted(members, key=rank_key)
        where = ", ".join(sorted(organisms))
        for other in rest:
            if groups.same(first, other) or reviewed.settled(first, other):
                continue
            pair = f"{first.split(':', 1)[1]} and {other.split(':', 1)[1]}"
            if groups.can_join(first, other):
                # Either side may already belong to a bigger group (a number
                # that joined its UniProt entry under the rule before). The
                # row is about the group that loses its name, so every
                # identifier that disappears has a row of its own.
                stays, goes = sorted((groups.leader(first), groups.leader(other)), key=rank_key)
                member = first if groups.same(goes, first) else other
                already = ("" if goes == member else
                           f" {goes.split(':', 1)[1]} was already one with {member.split(':', 1)[1]}.")
                groups.join(first, other)
                ledger.add("identical_sequence", "merged", goes, "Protein",
                           f"{pair} have the same sequence (MD5 {md5}) in the same "
                           f"organism ({where}).{already}", compared_with=stays, sources="mibig")
            elif groups.kept_apart_by_hand(first, other):
                ledger.add("identical_sequence", "kept_apart", other, "Protein",
                           f"{pair} have the same sequence (MD5 {md5}) in the same organism, "
                           f"but a person decided they stay apart (see their reviewed_by_hand "
                           f"rows).", compared_with=first, sources="mibig")
            else:
                entries = sorted(groups.authorities(first) | groups.authorities(other))
                ledger.add("identical_sequence", "kept_apart", other, "Protein",
                           f"{pair} have the same sequence (MD5 {md5}) in the same organism, "
                           f"but UniProt keeps them as separate entries "
                           f"({', '.join(e.split(':', 1)[1] for e in entries)}).",
                           compared_with=first, sources="mibig|uniprot")


def join_gene_names(pool: Pool, groups: Groups, ledger: Ledger,
                    reviewed: Reviewed | None = None) -> list[str]:
    """
    Rule gene_name_in_uniprot (see the module notes).

    Returns the gene records that stayed on their own. From Phase 4b, the
    MIBiG adapter places these through MIBiG's GenBank file first, so on the
    real data this rule finds nothing left to do; it stays as the fallback
    for a gene name the GenBank file doesn't give.
    """
    reviewed = reviewed or Reviewed([])
    left: list[str] = []
    for protein in pool.ids("mg.protein"):
        props = pool.props(protein, "mibig")
        if props.get("found_in") != "gene_records":
            continue
        gene = str(props.get("gene_name") or "").strip()
        clusters = pool.starts(protein, "ENCODES")
        where = ", ".join(c.split(":", 1)[1] for c in clusters)
        if not gene:
            left.append(protein)
            ledger.add("gene_name_in_uniprot", "kept_apart", protein, "Protein",
                       f"The gene record in {where} gives no gene name to look for.",
                       sources="mibig")
            continue
        matches: dict[str, str] = {}          # group representative -> a member protein
        for cluster in clusters:
            for other in pool.targets(cluster, "ENCODES"):
                if other == protein:
                    continue
                for entry in groups.authorities(other):
                    if gene.lower() in gene_names(_entry(pool, entry).get("gene_names")):
                        matches[groups.find(other)] = other
        if len(matches) == 1 and not reviewed.settled(protein, next(iter(matches.values()))) \
                and groups.can_join(next(iter(matches.values())), protein):
            other = next(iter(matches.values()))
            entry = sorted(groups.authorities(other))[0]
            groups.join(other, protein)
            ledger.add("gene_name_in_uniprot", "merged", protein, "Protein",
                       f"The gene record in {where} names the gene '{gene}' only; UniProt "
                       f"gives that gene name to exactly one protein of the cluster, "
                       f"{other.split(':', 1)[1]} (entry {entry.split(':', 1)[1]}).",
                       compared_with=other, sources="mibig|uniprot")
        else:
            left.append(protein)
            found = ("no protein of the cluster" if not matches
                     else f"{len(matches)} proteins of the cluster")
            ledger.add("gene_name_in_uniprot", "kept_apart", protein, "Protein",
                       f"The gene record in {where} names the gene '{gene}' only, and UniProt "
                       f"gives that gene name to {found}, and MIBiG's GenBank file doesn't "
                       f"give it a protein number either.", sources="mibig|uniprot")
    return left
