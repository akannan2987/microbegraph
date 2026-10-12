"""
MicrobeGraph, resolving organisms.

WHAT NEEDS DECIDING
    Organisms are the easy case, because every source names them by the same
    authority: NCBI Taxonomy numbers. MIBiG writes ncbitaxon:326423 for
    Bacillus velezensis FZB42, and so does NCBI Taxonomy's table, so the two
    records are already one node (rule same_identifier, in combine.py).

    Two things still need a rule:

    1. NUMBERS NCBI HAS MERGED (rule ncbi_merged_number, here)
       When NCBI decides two numbers were the same organism all along, it
       keeps one and retires the other. MIBiG 4.0 still uses seven retired
       numbers. Phase 2 asked NCBI about them and got the current number back
       (ncbi_taxonomy_summary.json, "merged_taxids"). The resolver moves
       MIBiG's organism to the current number, so its clusters hang from the
       same dot as everything else NCBI files under that number.

       A forwarding address works the same way: post sent to the old address
       still arrives, because the post office knows where you moved.

    2. AN ORGANISM THAT IS ALSO A CROP PATHOGEN (rule organism_and_pathogen,
       in combine.py)
       Fusarium graminearum harbours four MIBiG gene clusters and causes head
       blight on wheat. MIBiG and NCBI call it an Organism; the curated bridge
       calls it a Pathogen. Since Phase 4, a Pathogen is a kind of Organism
       (ontology.py, SUBTYPE_OF), so the one node becomes a Pathogen and keeps
       its clusters and its place in the family tree.
"""

from __future__ import annotations

from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.pool import Pool


def move_merged_numbers(pool: Pool, ledger: Ledger) -> dict[str, str]:
    """
    Map each retired organism number to NCBI's current one, and record each move.

    Returns {old identifier: new identifier}, e.g.
    {"ncbitaxon:182080": "ncbitaxon:46161"}.
    """
    merged = pool.summaries["ncbi_taxonomy"].get("merged_taxids", {})
    moves: dict[str, str] = {}
    for old, new in sorted(merged.items(), key=lambda item: int(item[0])):
        old_id, new_id = f"ncbitaxon:{old}", f"ncbitaxon:{new}"
        if old_id not in pool.rows:
            continue                    # nobody uses the old number: nothing to move
        if new_id not in pool.rows:
            continue                    # shouldn't happen: Phase 2 writes the new number
        moves[old_id] = new_id
        old_name = pool.name(old_id, "mibig") or old_id
        new_name = pool.name(new_id, "ncbi_taxonomy") or new_id
        also = (" MIBiG also uses the current number, so their clusters now share one node."
                if pool.row(new_id, "mibig") else "")
        ledger.add(
            "ncbi_merged_number", "moved", old_id, "Organism",
            f"NCBI Taxonomy has merged {old} into {new}. MIBiG names {old} "
            f"'{old_name}'; NCBI's current name for {new} is '{new_name}'.{also}",
            compared_with=new_id, sources="|".join(pool.sources(old_id) + ["ncbi_taxonomy"]),
        )
    return moves
