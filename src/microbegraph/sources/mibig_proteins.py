"""
MicrobeGraph, reading MIBiG's protein file (Phase 3b).

WHAT THE FILE IS
    MIBiG's download server (https://dl.secondarymetabolites.org/mibig/)
    publishes every protein of every cluster in one text file,
    mibig_prot_seqs_4.0.fasta. It's written in the FASTA format, a very
    plain and widely used way of storing sequences: each protein takes two
    parts, a header line starting with ">" and then its sequence, one letter
    per amino acid.

        >BGC0000433.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A|CAE02630.1
        MEITFYPLTNAQKRIWYTEKFYPNTSISNLAGFGKLISEDGVQAHYVEKAIQEFVRRYESMRIRLRLDD...

    A shelf of labelled jars works as a comparison: the header is the label,
    the sequence is what's in the jar, and the file is the whole shelf.

THE HEADER, PART BY PART
    MIBiG writes seven parts separated by "|". Before any code was written, a
    survey of the real file (tests/fixtures/capture_mibig_protein_samples.py)
    found all 46,987 headers in this one shape:

        0  BGC0000433.5            the entry and its version
        1  c1                      which sequence record of the entry (always c1 in 4.0)
        2  8558-19312              where the gene sits in that record
        3  +                       which DNA strand it is read from (+ or -)
        4  CAE02630.1              the gene's label: a locus tag such as TSTA_117750
                                   when the record gives one, else the same as part 6
        5  surfactin_synthetase_A  the product, with spaces written as "_" (can be empty)
        6  CAE02630.1              the protein's number: INSDC or RefSeq when there is
                                   one, otherwise a gene name or MIBiG's own label

    read_protein_file() refuses a file in which any header has another shape,
    rather than guessing what the parts mean. The file is pinned by its
    SHA-256 (src/microbegraph/sources/mibig.py), so this can only happen if
    someone moves the pin to a different file.

WHAT IS KEPT OF EACH PROTEIN
    Everything in the header, plus the sequence's length and its MD5
    fingerprint. The sequence itself stays in the file in the evidence
    locker: 40,000 sequences would make the staging tables enormous, and no
    phase so far needs the letters. The fingerprint is enough to tell whether
    two proteins have exactly the same sequence, which Phase 4 can use. MD5
    is fine for that because it's only used to compare sequences; the file
    as a whole is guarded by its SHA-256.

MATCHING A CURATOR'S NAME TO A PROTEIN IN THE FILE
    MIBiG's JSON entries name genes in two places, and neither always uses
    the protein's number:

      * gene records ("annotations", read since Phase 3) use the protein's
        number, a locus tag, or a gene name such as nisA;
      * the list of genes the curators removed from the cluster ("to_delete")
        uses numbers, gene names such as CrmK, or NCBI gene numbers such as
        LOC100273419.

    So a name is looked up within its own entry, in this order:

      1. exactly, against the protein number (part 6) or the label (part 4);
      2. exactly but ignoring capitals, against the product (nisA = NisA);
      3. for removals only: as a whole word inside the product, which is how
         NCBI names a protein nobody has characterised
         ("uncharacterized protein LOC100273419 isoform X5").

    A gene record is one protein, so rule 2 counts only when exactly one
    protein in the entry has that product; two or more is ambiguous and the
    gene record stays unmatched (and listed). A removal can match several
    proteins at once: removing a gene removes every version (isoform) of its
    protein. Rule 3 isn't used for gene records, because a gene name found
    inside a longer product could belong to a neighbouring gene.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from microbegraph.paths import relative_to_repo
from microbegraph.sources.base import SourceError

_ACCESSION = re.compile(r"^BGC\d{7}$")
_PARTS = 7


@dataclass(frozen=True)
class ProteinRecord:
    """One protein from the file: its header's parts, and a fingerprint of its sequence."""

    accession: str          # BGC0000433
    entry_version: str      # "5"
    location: str           # "8558-19312"
    strand: str             # "+" or "-"
    label: str              # part 4: a locus tag, or the protein number again
    product: str            # part 5, with "_" turned back into spaces; "" if none
    protein_id: str         # part 6
    length: int             # amino acids
    md5: str                # fingerprint of the sequence


def parse_header(header: str) -> tuple[str, ...] | None:
    """
    The seven parts of one header (without its ">"), or None if it has
    another shape: a different number of parts, no BGC accession, or no
    protein id.
    """
    parts = tuple(part.strip() for part in header.split("|"))
    if len(parts) != _PARTS:
        return None
    accession = parts[0].partition(".")[0]
    if not _ACCESSION.match(accession) or not parts[6]:
        return None
    return parts


def _record(parts: tuple[str, ...], sequence: str) -> ProteinRecord:
    accession, _, version = parts[0].partition(".")
    return ProteinRecord(
        accession=accession, entry_version=version, location=parts[2], strand=parts[3],
        label=parts[4], product=parts[5].replace("_", " ").strip(), protein_id=parts[6],
        length=len(sequence), md5=hashlib.md5(sequence.encode("utf-8")).hexdigest(),
    )


def read_protein_file(path: Path) -> dict[str, list[ProteinRecord]]:
    """
    Every protein in the file, grouped by entry accession, in file order.

    Raises SourceError, naming the first few, if any header isn't in the
    shape described at the top of this module. Nothing half-read is returned.
    """
    by_entry: dict[str, list[ProteinRecord]] = {}
    unreadable: list[str] = []
    header: str | None = None
    pieces: list[str] = []

    def close() -> None:
        if header is None:
            return
        parts = parse_header(header)
        if parts is None:
            unreadable.append(header)
            return
        record = _record(parts, "".join(pieces))
        by_entry.setdefault(record.accession, []).append(record)

    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith(">"):
                close()
                header, pieces = line[1:], []
            elif line and header is not None:
                pieces.append(line)
    close()

    if unreadable:
        shown = "\n    ".join(h[:120] for h in unreadable[:5])
        raise SourceError(
            f"{relative_to_repo(path)} has {len(unreadable)} header(s) that aren't in the "
            f"seven-part shape this adapter reads, so nothing was written. First ones:\n"
            f"    {shown}\n"
            f"  The file's format may have changed. Look at it before changing the code\n"
            f"  (docs/05b-all-cluster-proteins.md, section 3)."
        )
    return by_entry


def count_records(path: Path) -> int:
    """How many proteins the file holds: the number of lines that start with '>'."""
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.startswith(b">"))


def _same_word(name: str, text: str) -> bool:
    """True if `name` appears in `text` as a whole word, ignoring capitals."""
    pattern = r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def find_gene(name: str, records: list[ProteinRecord]) -> tuple[int | None, str]:
    """
    The position of the protein a gene record means, and how it was found:
    (index, "id"), (index, "product"), or (None, "") when there's no single match.
    """
    for index, record in enumerate(records):
        if name in (record.protein_id, record.label):
            return index, "id"
    folded = name.casefold()
    same_product = [i for i, r in enumerate(records) if r.product and r.product.casefold() == folded]
    if len(same_product) == 1:
        return same_product[0], "product"
    return None, ""


def find_removed(name: str, records: list[ProteinRecord]) -> tuple[list[int], str]:
    """
    The positions of the protein(s) a "to_delete" item means, and how they
    were found ("id", "product" or "word in product"), or ([], "").
    """
    by_id = [i for i, r in enumerate(records) if name in (r.protein_id, r.label)]
    if by_id:
        return by_id, "id"
    folded = name.casefold()
    by_product = [i for i, r in enumerate(records) if r.product and r.product.casefold() == folded]
    if by_product:
        return by_product, "product"
    by_word = [i for i, r in enumerate(records) if r.product and _same_word(name, r.product)]
    if by_word:
        return by_word, "word in product"
    return [], ""
