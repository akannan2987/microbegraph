"""
MicrobeGraph, where every file lives.

WHY THIS FILE EXISTS
    Every part of the pipeline needs to know where the data folders are.
    If each module worked that out for itself, sooner or later one of them
    would get it slightly wrong, so the answer lives here once and everything
    else imports it.

WHY THE PATHS ARE COMPUTED, NOT TYPED
    A path like "C:/Users/<your-name>/microbegraph/data" works on exactly one
    machine. Instead, the code starts from where THIS file sits and walks up
    to the repository root. That works on Windows, macOS and RHEL 8 alike,
    and in whatever folder you cloned into.

    It's like giving directions as "two doors down from the bakery" instead
    of GPS coordinates: move the whole street and the directions still work.

THE LAYOUT
    data/
    ├── raw/                      the evidence locker: untouched downloads
    │   ├── provenance.csv        one row per fetch: what, from where, when
    │   └── mibig/                one folder per source
    └── processed/
        ├── staging/              per-source tidy tables (mibig_nodes.csv ...)
        ├── nodes.csv             the merged graph's dots (Phase 4)
        ├── edges.csv             the merged graph's arrows (Phase 4)
        ├── resolution_ledger.csv every merge and refusal, with its grounds
        ├── resolve_summary.json  the resolver's counts and lists
        └── microbegraph.duckdb   the database the graph is built from

    data/ is never committed to Git. The pipeline rebuilds it on demand,
    and that rebuild is also how you know the pipeline works.

    Sources answered by a web API (PubChem, NCBI Taxonomy, KEGG, from Phase 2)
    keep one folder per fetch inside their shelf, named by the moment it
    started, for example data/raw/pubchem/2026-10-12T055202Z/.
"""

from __future__ import annotations

from pathlib import Path

# src/microbegraph/paths.py -> parents[0] is src/microbegraph,
# parents[1] is src, parents[2] is the repository root.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

DATA_DIR: Path = REPO_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
STAGING_DIR: Path = PROCESSED_DIR / "staging"
PROVENANCE_LOG: Path = RAW_DIR / "provenance.csv"

# What the resolver writes (Phase 4), and the database built from it.
NODES_FILE: Path = PROCESSED_DIR / "nodes.csv"
EDGES_FILE: Path = PROCESSED_DIR / "edges.csv"
LEDGER_FILE: Path = PROCESSED_DIR / "resolution_ledger.csv"
RESOLVE_SUMMARY: Path = PROCESSED_DIR / "resolve_summary.json"
DATABASE_FILE: Path = PROCESSED_DIR / "microbegraph.duckdb"

# Things that ARE in the repository (unlike data/, which never is).
CURATION_DIR: Path = REPO_ROOT / "curation"
BRIDGE_FILE: Path = CURATION_DIR / "compound_pathogen_crop.csv"

# Your private settings, such as API keys. Never in the repository.
ENV_FILE: Path = REPO_ROOT / ".env"


def relative_to_repo(path: Path) -> str:
    """
    Return a path as text relative to the repository root, with forward slashes.

    Use it whenever a path gets written down, in the provenance log or in a
    printed message. A log that says "data/raw/mibig/..." is portable and safe
    to share. One that says "/Users/<your-name>/Documents/..." leaks your
    folder layout and is no use on anyone else's machine.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # The path is outside the repository (tests use temporary folders),
        # so keep only the file name.
        return path.name
