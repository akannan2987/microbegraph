"""
MicrobeGraph, the list of plugged-in sources.

Every adapter is registered here by its short name. The fetch command
(src/microbegraph/fetch.py) reads this list, so a new source becomes usable
as soon as it's added below, without touching any other file.

    Phase 1   mibig       gene clusters, organisms, compounds, activities
    Phase 2   pubchem, ncbi_taxonomy, kegg, curation       (planned)
    Phase 3   uniprot                                       (planned)
"""

from __future__ import annotations

from microbegraph.sources.base import Source
from microbegraph.sources.mibig import MibigSource

# name -> adapter class. Order is the order sources run in.
SOURCES: dict[str, type[Source]] = {
    MibigSource.name: MibigSource,
}


def get_source(name: str, **kwargs: object) -> Source:
    """Build the adapter called `name`, or explain which names exist."""
    try:
        return SOURCES[name](**kwargs)  # type: ignore[arg-type]
    except KeyError:
        known = ", ".join(SOURCES) or "none yet"
        raise KeyError(f"unknown source {name!r}. Known sources: {known}") from None
