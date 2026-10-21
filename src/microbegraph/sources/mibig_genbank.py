"""
MicrobeGraph, reading MIBiG's GenBank file (Phase 4b).

WHAT THE FILE IS
    MIBiG's download server (https://dl.secondarymetabolites.org/mibig/)
    publishes every cluster of the release as a GenBank record, all packed
    into one archive, mibig_gbk_4.0.tar.gz (83,652,126 bytes, 331 MB once
    unpacked). GenBank is the text format NCBI has used for DNA records since
    the 1980s: a header, a FEATURES table listing what sits where on the DNA,
    and then the DNA itself.

    Every gene that codes for a protein is a "CDS" feature (CDS means coding
    sequence), followed by qualifiers, one per line, each starting with "/":

         CDS             complement(12046..13545)
                         /gene="baeI"
                         /locus_tag="..."
                         /protein_id="CAG23956.1"
                         /db_xref="GeneID:..."
                         /translation="MKK..."

    Think of a parts catalogue for each cluster: one entry per part, and
    each entry lists the part's name, its shelf code and its order number
    side by side. The protein file (Phase 3b) only gave the order number and
    one label; this catalogue gives every name a part goes by.

WHAT THE SURVEY FOUND (tests/fixtures/capture_gap_samples.py, 2026-10-12)
    2,636 files, one record each (the active and the pending entries), with
    46,987 CDS features: exactly the 46,987 proteins of the protein file.
    45,916 CDS carry a protein number. The files were written by antiSMASH,
    so they hold far more than NCBI's own records (domains, motifs, regions);
    none of that extra annotation is read here.

    The names Phase 3b couldn't place are all in it: the 21 gene records that
    give only a gene name (baeI, agqA, SCO6265...) each match the /gene of
    exactly one CDS, and the 4 maize genes MIBiG's curators removed from
    BGC0002390 (LOC100272490 and three more) each match a /gene and a
    /db_xref="GeneID:..." of one CDS. Every one of those CDS has a protein
    number that the protein file also lists.

WHAT IS KEPT OF EACH CDS
    Only the names it goes by and its protein number:
        /gene /locus_tag /old_locus_tag                every name, as written
        /gene_synonym="abcA; orf3"                     each name in the list
        /db_xref="GeneID:100272490"                    kept as GeneID:100272490
        /protein_id                                    the number ("" if none)
    The translation and the DNA are skipped (the protein file already has the
    sequences), which keeps reading the whole archive to a few seconds.

    From Phase 5 the first /gene is also kept on its own. The MIBiG adapter
    stores it on the protein as `genbank_gene`, a property of its own, so that
    paths and pictures can show "dauE (aklaviketone reductase)" instead of a
    product alone. It is never copied into `gene_name`: the resolver's
    gene_name_in_uniprot rule matches on that, and a new name there would
    change which proteins merge.

MATCHING A CURATOR'S NAME (used by the MIBiG adapter)
    find_in_genbank(name, cds) looks the name up within one entry, ignoring
    capitals, against every name of every CDS. An NCBI gene name of the form
    LOC<number> also matches the CDS whose GeneID is that number. It returns
    the protein numbers of every CDS that matched; the adapter then decides
    whether that is one protein (a gene record) or all of them (a removal),
    the same way mibig_proteins.py does for the protein file.
"""

from __future__ import annotations

import re
import tarfile
from dataclasses import dataclass
from pathlib import Path

from microbegraph.paths import relative_to_repo
from microbegraph.tables import SourceError

NAME_QUALIFIERS = ("gene", "locus_tag", "old_locus_tag", "gene_synonym")
_ACCESSION = re.compile(r"(BGC\d{7})")
_FEATURE = re.compile(r"^ {5}(\S+) +\S")          # "     CDS             complement(...)"
_QUALIFIER = re.compile(r"^ {21}/([A-Za-z_]+)(?:=(.*))?$")
WANTED = (*NAME_QUALIFIERS, "protein_id", "db_xref")
_LOC = re.compile(r"^LOC(\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class CodingSequence:
    """One CDS of one entry: the names it goes by and its protein number."""

    accession: str
    protein_id: str             # "" when the CDS has none
    names: tuple[str, ...]      # every /gene, /locus_tag... and GeneID:<n>, as written
    gene: str = ""              # Phase 5: the first /gene alone ("" if none), for labels


def read_cds(text: str, accession: str) -> list[CodingSequence]:
    """
    The CDS features of one GenBank record (or several, one after another),
    with only the qualifiers listed above. Lines between FEATURES and ORIGIN
    are read. A value in quotes can carry on over several lines; those lines
    are joined for the qualifiers kept, and skipped quickly for the rest (the
    /translation is most of the file).
    """
    found: list[CodingSequence] = []
    in_table = False
    current: dict[str, list[str]] | None = None
    open_key: str | None = None            # the qualifier whose quoted value is still open

    def close() -> None:
        if current is None:
            return
        names = [v.strip('"').strip() for key in NAME_QUALIFIERS for v in current.get(key, [])]
        names = [part.strip() for n in names for part in n.split(";")]
        names += [v.strip('"') for v in current.get("db_xref", [])
                  if v.strip('"').startswith("GeneID:")]
        number = (current.get("protein_id") or [""])[0].strip('"').strip()
        gene = (current.get("gene") or [""])[0].strip('"').strip()
        found.append(CodingSequence(accession, number, tuple(dict.fromkeys(n for n in names if n)),
                                    gene))

    for line in text.splitlines():
        if line.startswith("FEATURES"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith(" "):              # ORIGIN, CONTIG, "//" or a new header
            close()
            current, in_table = None, line.startswith("FEATURES")
            continue
        feature = _FEATURE.match(line)
        if feature:
            close()
            current = {} if feature.group(1) == "CDS" else None
            open_key = None
            continue
        if current is None:
            continue
        if open_key is not None:               # the rest of a value that wrapped
            if open_key in WANTED:
                current[open_key][-1] += " " + line.strip()
            if line.rstrip().endswith('"'):
                open_key = None
            continue
        qualifier = _QUALIFIER.match(line)
        if not qualifier:
            continue
        value = (qualifier.group(2) or "").strip()
        if qualifier.group(1) in WANTED:
            current.setdefault(qualifier.group(1), []).append(value)
        if value.startswith('"') and (len(value) == 1 or not value.endswith('"')):
            open_key = qualifier.group(1)      # a line inside it never starts a qualifier
    close()
    return found


def read_genbank_file(path: Path) -> dict[str, list[CodingSequence]]:
    """
    Every CDS in the archive, grouped by entry accession (BGC0000433), in
    file order. Raises SourceError if the archive holds no GenBank records
    at all, which would mean the pin points at the wrong file.
    """
    by_entry: dict[str, list[CodingSequence]] = {}
    with tarfile.open(path, mode="r|*") as tar:          # gzip or not, read by its contents
        for member in tar:
            name = Path(member.name).name
            match = _ACCESSION.match(name)
            if not member.isfile() or not match or not name.endswith((".gbk", ".gb")):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            text = handle.read().decode("utf-8", errors="replace")
            by_entry.setdefault(match.group(1), []).extend(read_cds(text, match.group(1)))
    if not by_entry:
        raise SourceError(
            f"{relative_to_repo(path)} holds no GenBank records (.gbk files named after an "
            f"entry), so nothing was written. The pinned file may have changed; see\n"
            f"  docs/06b-closing-the-gaps.md, section 18.")
    return by_entry


def count_entries(path: Path) -> int:
    """How many GenBank records the archive holds, without reading them."""
    with tarfile.open(path, mode="r|*") as tar:
        return sum(1 for m in tar if m.isfile() and m.name.endswith((".gbk", ".gb")))


def find_in_genbank(name: str, cds: list[CodingSequence]) -> list[str]:
    """
    The protein numbers of every CDS of one entry that goes by `name`
    (ignoring capitals; LOC<n> also matches GeneID:<n>). Empty if none does,
    or if the matching CDS have no protein number.
    """
    folded = name.strip().casefold()
    if not folded:
        return []
    loc = _LOC.match(name.strip())
    gene_id = f"geneid:{loc.group(1)}" if loc else ""
    numbers = [c.protein_id for c in cds if c.protein_id
               and any(n.casefold() in (folded, gene_id) for n in c.names)]
    return list(dict.fromkeys(numbers))
