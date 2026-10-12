"""
MicrobeGraph, the ontology, in code.

WHY THIS FILE EXISTS:
    docs/02-ontology-and-data-model.md is the rulebook written for people,
    and this file is the same rulebook written for the loader. Every
    validation rule imports its definitions from here, so the two can never
    drift apart.

    If you change the ontology, change it HERE and in the doc, in the
    same commit.
"""

from typing import Final

# --- The nine node types (the nouns) ---------------------------------
NODE_TYPES: Final[frozenset[str]] = frozenset({
    "Organism",       # a helpful microbe, the factory
    "GeneCluster",    # a run of genes that builds one molecule, the production line
    "Protein",        # an enzyme encoded by the cluster, the machine on the line
    "Compound",       # the molecule produced, the product
    "CompoundClass",  # a family of related molecules, the product category
    "Activity",       # what a molecule does, what it is for
    "Pathogen",       # an organism that causes plant disease, the problem
    "Crop",           # a cultivated plant, who suffers
    "Pathway",        # a chain of biochemical reactions, the wider process
})

# --- Kinds of a type --------------------------------------------------
# A Pathogen is a kind of Organism (from Phase 4). Anything an Organism may do
# in the graph, a Pathogen may do too: harbour a gene cluster, or sit in the
# family tree with MEMBER_OF arrows. The reverse isn't true: INFECTS starts at
# a Pathogen, and an ordinary Organism can't be its starting point.
#
# Without this, an organism that is both a producer and a crop pathogen
# (MIBiG records four gene clusters in Fusarium graminearum, which also causes
# head blight on wheat) would need two dots with one identifier, which rule 1
# forbids. With it, the graph has one Pathogen dot that also harbours clusters.
SUBTYPE_OF: Final[dict[str, str]] = {
    "Pathogen": "Organism",
}

# --- The ten edge types (the verbs) ---------------------------------
# Each maps to the (from_type, to_type) pair it is allowed to connect, or a
# kind of either (see SUBTYPE_OF above). The loader uses this to reject nonsense
# like Compound --PRODUCES--> Compound.
EDGE_TYPES: Final[dict[str, tuple[str, str]]] = {
    "HARBORS":         ("Organism", "GeneCluster"),
    "ENCODES":         ("GeneCluster", "Protein"),    # genomics -> proteomics
    "CATALYZES":       ("Protein", "Compound"),       # proteomics -> metabolomics
    "PRODUCES":        ("GeneCluster", "Compound"),   # the direct shortcut (MIBiG)
    "BELONGS_TO":      ("Compound", "CompoundClass"),
    "HAS_ACTIVITY":    ("Compound", "Activity"),
    "INHIBITS":        ("Compound", "Pathogen"),
    "INFECTS":         ("Pathogen", "Crop"),
    "PARTICIPATES_IN": ("Compound", "Pathway"),
    "MEMBER_OF":       ("Organism", "Organism"),   # species -> genus -> family ...
}

# --- The four evidence levels, strongest first ------------------------
# Order matters: a path's strength is the WEAKEST link in it, so the
# analytics code needs to know which of two levels is weaker.
EVIDENCE_LEVELS: Final[tuple[str,...]] = (
    "curated_experimental",   # a curator recorded a published experiment
    "database_assertion",     # a public database states it
    "curated_literature",     # this project's own cited reading of a paper
    "inferred",               # produced by an algorithm here, a HYPOTHESIS
)

# Levels that must carry a citation, or the loader rejects the row.
REQUIRES_CITATION: Final[frozenset[str]] = frozenset({"curated_literature"})

# Levels excluded from evidence chains unless the user explicitly opts in.
NOT_EVIDENCE: Final[frozenset[str]] = frozenset({"inferred"})

# --- Identifier prefixes ----------------------------------------------
# "mg." marks identifiers this project minted because no public authority
# numbers the concept. I keep them visibly separate so a reader can tell at a
# glance how much outside authority stands behind an identifier.
KNOWN_PREFIXES: Final[frozenset[str]] = frozenset({
    "ncbitaxon",          # NCBI Taxonomy
    "mibig",              # MIBiG gene clusters
    "pubchem.compound",   # PubChem compounds
    "kegg.pathway",       # KEGG pathways
    "ncbiprotein",        # NCBI protein sequence records (GenBank, EMBL, DDBJ, RefSeq)
    "uniprot",            # UniProt proteins
    "mg.class",           # ours: compound classes
    "mg.activity",        # ours: biological activities
    "mg.crop",            # ours: crops
    "mg.organism",        # ours: strains with no NCBI entry
    "mg.compound",        # ours: compounds with no PubChem entry
    "mg.protein",         # ours: proteins MIBiG names only by a gene name or locus tag
})


def is_a(node_type: str, wanted: str) -> bool:
    """
    True if node_type is the wanted type, or a kind of it.

    is_a("Pathogen", "Organism") is True; is_a("Organism", "Pathogen") is False.
    Rule 8 uses it, so a Pathogen may start a HARBORS or MEMBER_OF arrow.
    """
    seen = set()
    while node_type and node_type not in seen:
        if node_type == wanted:
            return True
        seen.add(node_type)
        node_type = SUBTYPE_OF.get(node_type, "")
    return False


def evidence_rank(level: str) -> int:
    """
    Return a level's position in EVIDENCE_LEVELS (0 = strongest).

    Used to find the weakest link in a path: the highest rank wins,
    because a chain is only as strong as its weakest arrow.
    """
    return EVIDENCE_LEVELS.index(level)


def is_valid_curie(node_id: str) -> bool:
    """
    Check that an identifier looks like 'prefix:localid' with a known prefix.

    The check is strict by design. An unknown prefix means either a typo or a
    new source that hasn't been registered above, and either one should fail
    loudly.
    """
    if ":" not in node_id:
        return False
    prefix, _, local = node_id.partition(":")
    return prefix in KNOWN_PREFIXES and bool(local)
