"""
MicrobeGraph, readable labels for nodes (Phase 5).

WHY LABELS NEED THEIR OWN CODE
    A node's `name` is whatever its source called it. For most nodes that
    reads well ("surfactin", "Botrytis cinerea"). For proteins it often
    doesn't: 33,984 of the 39,354 are named after their product, and 4,295
    of those are called "hypothetical protein". A picture with three dots
    all saying "hypothetical protein" tells you nothing.

    Gene names fix most of that. They come from three places, tried in this
    order:

        gene_name      MIBiG's curators, in the cluster's gene records
        genbank_gene   MIBiG's GenBank file, the /gene of the same protein
                       (from Phase 5; read in sources/mibig_genbank.py)
        gene_names     UniProt, the first of the names it lists

    and the label puts the gene first and the product after it in brackets:
    "srfAA (surfactin synthetase A)", or, for a protein only the GenBank file
    names, "dauE (aklaviketone reductase)". A protein with no gene name
    anywhere keeps its name.

    When the resolver merges proteins that were named differently, a property
    holds every name, joined with "|" (inkH|nokH). The label shows the first.

    Labels are only for showing. They never decide anything: no rule in the
    resolver or the analytics compares labels.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

WIDEST_LABEL = 48           # longer labels are cut, with "..." at the end


def shorten(text: str, widest: int = WIDEST_LABEL) -> str:
    """Cut text to `widest` characters, ending in "..." when something was cut."""
    text = " ".join(str(text).split())
    return text if len(text) <= widest else text[:widest - 3].rstrip() + "..."


def protein_gene(properties: dict[str, Any]) -> str:
    """The protein's gene name: MIBiG's curators first, then GenBank, then UniProt ("" if none)."""
    # Each can hold several names joined with "|" (UniProt lists every gene
    # name it knows; the resolver joins the names of merged proteins). The
    # first is the one shown.
    for key in ("gene_name", "genbank_gene", "gene_names"):
        value = str(properties.get(key) or "").split("|")[0].strip()
        if value:
            return value
    return ""


def protein_product(properties: dict[str, Any]) -> str:
    """What the protein does, in words: MIBiG's product, else UniProt's name ("" if neither)."""
    for key in ("product", "protein_names"):
        value = str(properties.get(key) or "").split("|")[0].strip()
        if value:
            return value
    return ""


def label(graph: nx.DiGraph, node_id: str, widest: int = WIDEST_LABEL) -> str:
    """
    A short, readable name for one node.

        Protein       "srfAA (surfactin synthetase A)", or its name if it has no gene
        GeneCluster   "BGC0000433 surfactin BGC" (the accession first, so it survives a cut)
        anything else its name
    """
    data = graph.nodes[node_id]
    name = str(data.get("name") or node_id)
    props = data.get("properties") or {}
    if data.get("node_type") == "Protein":
        gene, product = protein_gene(props), protein_product(props)
        if gene and product and product.casefold() != gene.casefold():
            return shorten(f"{gene} ({product})", widest)
        return shorten(gene or name, widest)
    if data.get("node_type") == "GeneCluster":
        accession = node_id.split(":", 1)[-1]
        return shorten(f"{accession} {name}", widest)
    return shorten(name, widest)
