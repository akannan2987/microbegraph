"""
MicrobeGraph, entity resolution (Phase 4).

WHAT ENTITY RESOLUTION MEANS
    Deciding when two records describe the same real thing. MIBiG calls a
    molecule "erythromycin A", PubChem calls compound 12560 "Erythromycin",
    and both mean the same molecule. A graph that keeps them as two dots
    counts one antibiotic twice and splits its facts across two places.

    It's the problem a school has when one pupil is enrolled as "Sam Lee" by
    the office and "Samantha Lee" by the sports club: before anyone can count
    pupils, someone has to decide which records are the same child, and write
    down why.

THE STEPS, IN THE ORDER THEY RUN
    pool.py         read every source's staging tables into one pool
    organisms.py    move organisms whose NCBI number was merged
    compounds.py    join MIBiG's compounds to PubChem's, where confirmed
                    (stereo.py compares two records' 3D detail, Phase 4c)
    proteins.py     join protein numbers to UniProt entries, identical
                    sequences, and gene records named only by a gene name
    combine.py      turn each group of records into one node, re-point every
                    arrow, and combine arrows that became the same arrow

    Every decision, a merge or a refusal, goes into the ledger (ledger.py)
    with its grounds. src/microbegraph/resolve.py runs the steps and writes
    the results; docs/06-entity-resolution-graph-build.md explains each rule.

THE PRINCIPLE BEHIND EVERY RULE
    A wrong merge does more harm than a missed one. Two records that stay
    apart are a small gap anyone can see. Two different molecules joined
    into one dot quietly attach facts to the wrong thing, and every answer
    that passes through that dot inherits the mistake. So each rule needs
    evidence beyond a single shared number or name, and when the evidence
    isn't there, the records stay apart and the ledger says why.
"""
