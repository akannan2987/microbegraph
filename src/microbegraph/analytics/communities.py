"""
MicrobeGraph, communities: groups of nodes that link mostly to each other (Phase 5).

WHAT A COMMUNITY IS
    A group of nodes with many arrows inside the group and few to the rest of
    the graph. In a school, the friendship network splits into groups without
    anyone drawing the lines: the chess club, the football team, one class.
    Community detection draws those lines from the links alone.

HOW THE GROUPS ARE FOUND: THE LOUVAIN METHOD
    Louvain (named after the Belgian university where it was written, 2008)
    starts with every node in a group of its own. It then moves each node into
    the neighbouring group that improves a score called MODULARITY the most,
    until no move helps. Then it treats each group as a single node and does
    the same again, and so on, until nothing changes.

    Modularity compares the arrows inside the groups with how many you would
    expect if every node kept its number of arrows but they were wired up at
    random. It runs from below 0 to just under 1: around 0 means "no better
    than chance", and networks with clear groups typically score 0.3 to 0.7.
    It is one score, though, not a proof: Louvain finds high modularity even
    in graphs wired at random (Guimera, Sales-Pardo and Amaral, Physical
    Review E 70, 025101, 2004), so Phase 6 compares the real score with
    rewired copies.

    NetworkX has Louvain built in (nx.community.louvain_communities), so
    nothing new needs installing.

WHY THE SAME SEED EVERY TIME
    Louvain visits the nodes in a random order, and a different order can give
    slightly different groups. A fixed seed (42) makes the order the same on
    every run, so the groups are the same on every machine with the same
    NetworkX version. With another NetworkX version the groups may differ a
    little; the summary file records the version used.

WHICH GRAPH (the survey that shaped this, 2026-10-15)
    The proteins are left out. 36,910 of the 39,354 have exactly one arrow
    (from their cluster), so they would only follow their cluster into its
    group and make the groups about five times bigger on average. Without
    them the real graph has 8,880 nodes and splits into 63 groups with
    modularity 0.778, in under two seconds. The groups read as themes: a
    Streptomyces group, a siderophore group, an antiviral group, a
    Pseudomonas group that holds cotton. Leaving out the labels as well
    (activities, classes, pathways) gives 156 smaller groups that mostly
    follow the family tree instead. A copy of the graph without proteins,
    rewired at random so that every node keeps its number of arrows, still
    scores 0.700.
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from microbegraph.analytics.centrality import SEED


def without_proteins(graph: nx.DiGraph) -> nx.Graph:
    """The graph without Protein nodes, directions set aside, in sorted order."""
    kept = sorted(n for n, d in graph.nodes(data=True) if d.get("node_type") != "Protein")
    keep = set(kept)
    picked = nx.Graph()
    picked.add_nodes_from(kept)
    picked.add_edges_from(sorted((a, b) for a, b in graph.edges if a in keep and b in keep))
    return picked


def find_communities(picked: nx.Graph, seed: int = SEED) -> list[set[str]]:
    """
    Louvain communities of `picked`, numbered by size: the biggest first, and
    ties by the identifier that sorts first.
    """
    found = nx.community.louvain_communities(picked, seed=seed)
    return sorted(found, key=lambda c: (-len(c), min(c)))


def modularity(picked: nx.Graph, communities: list[set[str]]) -> float:
    """How much more the groups link inside than chance would give (see the notes above)."""
    return nx.community.modularity(picked, communities)


def describe(graph: nx.DiGraph, picked: nx.Graph, communities: list[set[str]],
             top: int = 3) -> list[dict[str, object]]:
    """
    One row per community, in order: its number (from 1), size, node types,
    the `top` members with the most arrows inside the group, and any crops in it.
    """
    rows = []
    for number, members in enumerate(communities, start=1):
        inside = picked.subgraph(members)
        busiest = sorted(members, key=lambda n: (-inside.degree(n), n))[:top]
        rows.append({
            "community": number,
            "size": len(members),
            "types": dict(sorted(Counter(str(graph.nodes[n]["node_type"]) for n in members).items())),
            "top": busiest,
            "crops": sorted(n for n in members if graph.nodes[n]["node_type"] == "Crop"),
        })
    return rows


def membership(communities: list[set[str]]) -> dict[str, int]:
    """{node: the number of its community}, numbers as in find_communities (from 1)."""
    return {node: number for number, members in enumerate(communities, start=1)
            for node in members}
