"""
MicrobeGraph, hubs and bridges: two meanings of "important" (Phase 5).

CENTRALITY, IN PLAIN WORDS
    "Which nodes matter most?" has no single answer, because it depends on what
    you mean by matter. Network science calls each answer a centrality. This
    module computes two.

    DEGREE: how many arrows touch a node. A railway station served by many
    lines has a high degree. It finds HUBS, and it is quick (one count per
    node).

    BETWEENNESS: how often a node sits on the shortest route between two other
    nodes. A small station where two lines meet can have few platforms and
    still be the only place to change trains between two regions. It finds
    BRIDGES. For every pair of nodes it counts the shortest routes between
    them and the share of those that pass through each node, then adds the
    shares up. NetworkX scales the result to between 0 and 1 (normalized), so
    1 would mean "on every shortest route in the graph".

WHICH ARROWS COUNT (the survey that shaped this, 2026-10-15)
    On the whole graph both measures crown the same few nodes: the activity
    labels "antibacterial" (936 arrows) and "cytotoxic" (627), and the genus
    Streptomyces (399). They are popular because they are general, the way
    "the letter e" is the commonest letter without saying anything about a
    word. Their betweenness is high for the same reason: any two compounds that
    are both antibacterial are two steps apart through that label.

    A bridge worth finding links things that would otherwise be apart. So
    betweenness here runs on the PRODUCTION LAYER only, the arrows that say who
    makes what and what it does to a pathogen:

        HARBORS, PRODUCES, INHIBITS, INFECTS

    without the labels, the family tree or the proteins. On the real data that
    layer has 7,750 nodes, 6,733 arrows and 1,183 separate pieces (most are one
    microbe, one cluster and its compounds). Its bridges are microbes with
    many clusters and compounds made by several unrelated microbes, such as
    carotenoid (17 producers).

    Betweenness counts shortest routes between every pair of nodes, which
    makes it the slowest thing in this phase. On the production layer it takes
    about half a minute to a minute and a half. The whole graph would take
    hours, so whole_graph_betweenness() estimates it from a sample of 300
    starting nodes instead (k=300, seed 42), for the lesson above.

THE GRAPH IS TREATED AS UNDIRECTED HERE
    The arrows have a direction (a microbe HARBORS a cluster, never the other
    way round), but a bridge is about what is linked to what. Following
    arrows only forwards, nothing could ever be "between" a compound and the
    microbe that makes it. So both measures read the graph with directions
    set aside (nx.Graph), and degree counts arrows in and out.
"""

from __future__ import annotations

from collections import defaultdict

import networkx as nx

PRODUCTION_LAYER: tuple[str, ...] = ("HARBORS", "PRODUCES", "INHIBITS", "INFECTS")
WHOLE_GRAPH_SAMPLE = 300       # starting nodes for the whole-graph estimate
SEED = 42                      # the same sample every time


def layer(graph: nx.DiGraph, edge_types: tuple[str, ...] = PRODUCTION_LAYER) -> nx.Graph:
    """
    The undirected graph of only these arrow types, and only the nodes they touch.
    Nodes and arrows are added in sorted order, so the result never depends on
    the order the database returned them in.
    """
    keep = set(edge_types)
    picked = nx.Graph()
    picked.add_edges_from(sorted((a, b) for a, b, d in graph.edges(data=True)
                                 if d["edge_type"] in keep))
    return picked


def undirected(graph: nx.DiGraph) -> nx.Graph:
    """The whole graph with directions set aside."""
    whole = nx.Graph()
    whole.add_nodes_from(sorted(graph.nodes))
    whole.add_edges_from(sorted((a, b) for a, b in graph.edges))
    return whole


def degrees(graph: nx.DiGraph) -> dict[str, int]:
    """Every node's degree: the arrows that start or end at it."""
    return dict(graph.degree())


def hubs_by_type(graph: nx.DiGraph, top: int = 3) -> dict[str, list[tuple[str, int]]]:
    """
    {node type: its `top` nodes with the most arrows}, types sorted by name.
    Ties go to the identifier that sorts first, so the list never shuffles.
    """
    by_type: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for node, degree in graph.degree():
        by_type[str(graph.nodes[node]["node_type"])].append((node, degree))
    return {kind: sorted(nodes, key=lambda nd: (-nd[1], nd[0]))[:top]
            for kind, nodes in sorted(by_type.items())}


def betweenness(picked: nx.Graph) -> dict[str, float]:
    """Exact betweenness of every node in `picked` (normalized: 0 to 1)."""
    return nx.betweenness_centrality(picked, normalized=True)


def whole_graph_betweenness(graph: nx.DiGraph, k: int = WHOLE_GRAPH_SAMPLE,
                            seed: int = SEED) -> dict[str, float]:
    """
    An ESTIMATE of betweenness on the whole graph, from k starting nodes
    picked at random (the same ones every time, thanks to the seed). With
    k=300 it takes about a minute; the exact answer would take hours.
    """
    return nx.betweenness_centrality(undirected(graph), k=k, seed=seed, normalized=True)


def top_nodes(values: dict[str, float], top: int = 10) -> list[tuple[str, float]]:
    """The `top` nodes with the highest values, ties broken by identifier."""
    return sorted(values.items(), key=lambda nv: (-nv[1], nv[0]))[:top]


def layer_facts(picked: nx.Graph) -> dict[str, int]:
    """How big a layer is: nodes, arrows and separate pieces."""
    return {"nodes": picked.number_of_nodes(), "arrows": picked.number_of_edges(),
            "pieces": nx.number_connected_components(picked)}
