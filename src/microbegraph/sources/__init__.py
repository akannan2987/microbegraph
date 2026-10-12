"""
MicrobeGraph, the list of plugged-in sources.

Every adapter is registered here by its short name. The fetch command
(src/microbegraph/fetch.py) reads this list, so a new source becomes usable
as soon as it's added below, without touching any other file.

    Phase 1   mibig           gene clusters, organisms, compounds, activities
                              (from Phase 3, the proteins in its gene records;
                              from Phase 3b, every cluster's proteins, read
                              from MIBiG's protein file)
    Phase 2   pubchem         compound identity, structure and other names
              ncbi_taxonomy   the family tree above organisms and pathogens
              kegg            which pathway maps compounds appear on
              curation        the cited bridge: compound -> pathogen -> crop
    Phase 3   uniprot         what each MIBiG protein is, through ID mapping
                              (about 39,000 protein numbers from Phase 3b)

THE ORDER MATTERS
    Later sources build on earlier ones: PubChem asks about MIBiG's compound
    numbers, KEGG reads PubChem's KEGG numbers, UniProt maps MIBiG's protein
    ids, the bridge is checked against MIBiG and NCBI. `--all` runs them in
    the order written below.
"""

from __future__ import annotations

from microbegraph.sources.base import Source
from microbegraph.sources.curation import CurationSource
from microbegraph.sources.kegg import KeggSource
from microbegraph.sources.mibig import MibigSource
from microbegraph.sources.ncbi_taxonomy import NcbiTaxonomySource
from microbegraph.sources.pubchem import PubchemSource
from microbegraph.sources.uniprot import UniprotSource

# name -> adapter class. Order is the order sources run in.
SOURCES: dict[str, type[Source]] = {
    MibigSource.name: MibigSource,
    PubchemSource.name: PubchemSource,
    NcbiTaxonomySource.name: NcbiTaxonomySource,
    KeggSource.name: KeggSource,
    UniprotSource.name: UniprotSource,
    CurationSource.name: CurationSource,
}


def get_source(name: str, **kwargs: object) -> Source:
    """Build the adapter called `name`, or explain which names exist."""
    try:
        return SOURCES[name](**kwargs)  # type: ignore[arg-type]
    except KeyError:
        known = ", ".join(SOURCES) or "none yet"
        raise KeyError(f"unknown source {name!r}. Known sources: {known}") from None
