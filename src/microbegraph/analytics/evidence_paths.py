"""
MicrobeGraph, evidence paths from a crop back to candidate microbes (Phase 5).

THE QUESTION
    "Which microbes might help protect this crop, and how sure are we?"
    Cookbook recipe R9 answers it for every crop as one SQL query. This module
    turns it into a tool: start at any crop, walk the arrows backwards, collect
    every route that ends at a microbe, rank the routes, and keep each arrow's
    evidence so a person can check every step.

WHY NOT JUST "THE SHORTEST PATH"
    The graph is one big connected piece (48,215 of its 48,234 nodes), held
    together by a few very busy nodes. Ignoring which way the arrows point,
    the shortest path from jujube to most microbes runs through one of them:

        jujube <- Botrytis cinerea <- surfactin -> antibacterial
               <- coelimycin P1 <- its cluster <- Streptomyces coelicolor A3(2)

    Six steps, all real arrows, and it means nothing: "this microbe makes
    something that is also antibacterial" says nothing about Botrytis. So the
    walk follows one TYPED ROUTE, the chain the project was built for:

        Organism -HARBORS-> GeneCluster -PRODUCES-> Compound
                 -INHIBITS-> Pathogen -INFECTS-> Crop

    Walking backwards from the crop, each step may only take an arrow of the
    next type in that chain. A route like this is called a metapath: a path
    pattern written in types rather than in particular nodes.

    (The longer route through a protein, cluster -ENCODES-> protein
    -CATALYZES-> compound, finds no cluster on this data that PRODUCES
    doesn't already find, so it is left out.)

HOW THE PATHS ARE RANKED
    A path is only as strong as its weakest arrow, so that comes first. On the
    current data every crop path has two arrows from this project's own reading
    of a paper (curated_literature), so the weakest link alone ties them all.
    The ranking then looks further, in this order:

        1. the weakest evidence level (stronger first)
        2. how many arrows are backed by an experiment (curated_experimental),
           more first
        3. how sure the weakest arrows are: the lowest confidence among the
           arrows at the weakest level, higher first. On this data those are
           the INHIBITS and INFECTS arrows, which the curated bridge file
           grades by hand (0.8 to 0.9). MIBiG's own arrows all carry 0.5
           (docs/02-ontology-and-data-model.md), so comparing those would
           tell the paths nothing.
        4. names (microbe, compound, pathogen, cluster), only so that ties
           always come out in the same order

ARROWS THAT ARE ONLY HYPOTHESES
    An `inferred` arrow is a guess made by this project (Phase 7 makes the
    first ones), never evidence. The ontology says such arrows stay out of
    evidence chains unless someone asks for them (NOT_EVIDENCE in
    ontology.py), so the walk skips them unless include_inferred=True
    (python -m microbegraph.analyze --include-inferred). When they are let in,
    the ranking puts their paths last, because inferred is the weakest level.

LEADS AND PATHS
    Pseudomonas fluorescens has two clusters that both make
    2,4-diacetylphloroglucinol, so there are two paths from it to wheat. They
    are one LEAD (one microbe, one compound, one pathogen, one crop) with two
    paths. The lead keeps both and is ranked by its better one.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from microbegraph.analytics.labels import label
from microbegraph.ontology import NOT_EVIDENCE, evidence_rank, is_a

# The typed route, walked backwards from the crop: (arrow type, type of node it starts at).
ROUTE: tuple[tuple[str, str], ...] = (
    ("INFECTS", "Pathogen"),       # crop     <- pathogen
    ("INHIBITS", "Compound"),      # pathogen <- compound
    ("PRODUCES", "GeneCluster"),   # compound <- cluster
    ("HARBORS", "Organism"),       # cluster  <- organism
)

EXPERIMENT = "curated_experimental"
FROM_A_PAPER = "curated_literature"     # this project's own cited reading of a paper


@dataclass(frozen=True)
class Arrow:
    """One arrow of a path, with everything needed to check it."""

    start: str
    end: str
    edge_type: str
    evidence_level: str
    source: str
    citation: str
    confidence: float | None


@dataclass(frozen=True)
class EvidencePath:
    """One route: organism -> cluster -> compound -> pathogen -> crop, and its four arrows."""

    nodes: tuple[str, ...]        # organism, cluster, compound, pathogen, crop
    arrows: tuple[Arrow, ...]     # the four arrows, in the same direction

    @property
    def organism(self) -> str:
        return self.nodes[0]

    @property
    def cluster(self) -> str:
        return self.nodes[1]

    @property
    def compound(self) -> str:
        return self.nodes[2]

    @property
    def pathogen(self) -> str:
        return self.nodes[3]

    @property
    def crop(self) -> str:
        return self.nodes[4]

    @property
    def weakest(self) -> str:
        """The weakest evidence level on the path (the path is only as strong as this)."""
        return max((a.evidence_level for a in self.arrows), key=evidence_rank)

    @property
    def experiments(self) -> int:
        """How many arrows a published experiment backs."""
        return sum(1 for a in self.arrows if a.evidence_level == EXPERIMENT)

    @property
    def weakest_confidence(self) -> float:
        """The lowest confidence among the arrows at the weakest level (0 if none is given)."""
        return min((a.confidence or 0.0) for a in self.arrows
                   if a.evidence_level == self.weakest)

    @property
    def papers(self) -> tuple[str, ...]:
        """Every paper cited by the arrows that come from this project's reading of a paper."""
        return tuple(sorted({c for a in self.arrows if a.evidence_level == FROM_A_PAPER
                             for c in citations(a)}))

    @property
    def sole_papers(self) -> tuple[str, ...]:
        """
        The papers some arrow of this path rests on alone. An arrow citing two
        papers survives either one turning out wrong, so neither counts here.
        """
        return tuple(sorted({next(iter(citations(a))) for a in self.arrows
                             if a.evidence_level == FROM_A_PAPER and len(citations(a)) == 1}))


@dataclass
class Lead:
    """One microbe, one compound, one pathogen, one crop, and every path between them."""

    organism: str
    compound: str
    pathogen: str
    crop: str
    paths: list[EvidencePath] = field(default_factory=list)

    @property
    def best(self) -> EvidencePath:
        return self.paths[0]


def citations(arrow: Arrow) -> set[str]:
    """An arrow's citations: the curated bridge joins several with "|"."""
    return {c.strip() for c in arrow.citation.split("|") if c.strip()}


def rank_key(graph: nx.DiGraph, path: EvidencePath) -> tuple[Any, ...]:
    """The sort key for a path (smaller sorts first). See HOW THE PATHS ARE RANKED."""
    def name(node: str) -> str:
        return str(graph.nodes[node].get("name") or node).casefold()
    return (evidence_rank(path.weakest), -path.experiments, -path.weakest_confidence,
            name(path.organism), name(path.compound), name(path.pathogen), path.cluster)


# =============================================================================
# Finding nodes by what a person types
# =============================================================================
def crops(graph: nx.DiGraph) -> list[str]:
    """Every crop in the graph, sorted by name."""
    return sorted((n for n, d in graph.nodes(data=True) if d.get("node_type") == "Crop"),
                  key=lambda n: (str(graph.nodes[n].get("name")).casefold(), n))


def find_node(graph: nx.DiGraph, text: str, node_type: str | None = None) -> str:
    """
    The node a person means: its identifier ("mg.crop:jujube") or its name
    ("jujube", any capitals). Raises LookupError, with what to try instead,
    when nothing or more than one node matches.
    """
    wanted = text.strip()
    if wanted in graph and (node_type is None or graph.nodes[wanted].get("node_type") == node_type):
        return wanted
    folded = wanted.casefold()
    found = sorted(n for n, d in graph.nodes(data=True)
                   if str(d.get("name") or "").casefold() == folded
                   and (node_type is None or d.get("node_type") == node_type))
    if len(found) == 1:
        return found[0]
    if not found:
        if node_type == "Crop":
            names = ", ".join(str(graph.nodes[c]["name"]) for c in crops(graph))
            raise LookupError(f"There's no crop called {text!r}. The crops in the graph: {names}.")
        raise LookupError(f"Nothing in the graph has the identifier or name {text!r}. "
                          f"Try its identifier, as the cookbook's recipes show it "
                          f"(for example mg.compound:surfactin).")
    shown = ", ".join(f"{n} ({graph.nodes[n]['node_type']})" for n in found[:10])
    raise LookupError(f"{len(found)} nodes are called {text!r}: {shown}. "
                      f"Give the identifier instead.")


# =============================================================================
# Walking backwards along the typed route
# =============================================================================
def _arrow(graph: nx.DiGraph, start: str, end: str) -> Arrow:
    data = graph.edges[start, end]
    return Arrow(start, end, data["edge_type"], data["evidence_level"], data.get("source", ""),
                 data.get("citation") or "", data.get("confidence"))


def _steps_back(graph: nx.DiGraph, node: str, edge_type: str, start_type: str,
                include_inferred: bool = False) -> list[str]:
    """
    The nodes with an arrow of this type INTO `node`, sorted (a Pathogen counts
    as an Organism). Arrows that are only hypotheses are skipped unless asked for.
    """
    return sorted(p for p in graph.predecessors(node)
                  if graph.edges[p, node]["edge_type"] == edge_type
                  and is_a(str(graph.nodes[p].get("node_type")), start_type)
                  and (include_inferred
                       or graph.edges[p, node]["evidence_level"] not in NOT_EVIDENCE))


def paths_to_crop(graph: nx.DiGraph, crop: str, include_inferred: bool = False
                  ) -> list[EvidencePath]:
    """Every path along the typed route that ends at this crop, best first."""
    # Each partial route is a list of nodes from the crop backwards.
    routes: list[list[str]] = [[crop]]
    for edge_type, start_type in ROUTE:
        routes = [route + [step] for route in routes
                  for step in _steps_back(graph, route[-1], edge_type, start_type,
                                          include_inferred)]
    found = []
    for route in routes:
        forward = tuple(reversed(route))       # organism, cluster, compound, pathogen, crop
        arrows = tuple(_arrow(graph, a, b) for a, b in zip(forward, forward[1:], strict=False))
        found.append(EvidencePath(forward, arrows))
    return sorted(found, key=lambda p: rank_key(graph, p))


def all_crop_paths(graph: nx.DiGraph, include_inferred: bool = False
                   ) -> dict[str, list[EvidencePath]]:
    """{crop: its paths, best first}, for every crop, crops sorted by name."""
    return {crop: paths_to_crop(graph, crop, include_inferred) for crop in crops(graph)}


def group_leads(graph: nx.DiGraph, paths: list[EvidencePath]) -> list[Lead]:
    """Paths grouped into leads (one per microbe, compound, pathogen and crop), best lead first."""
    grouped: dict[tuple[str, str, str, str], list[EvidencePath]] = defaultdict(list)
    for path in paths:
        grouped[(path.organism, path.compound, path.pathogen, path.crop)].append(path)
    leads = []
    for (organism, compound, pathogen, crop), its_paths in grouped.items():
        leads.append(Lead(organism, compound, pathogen, crop,
                          sorted(its_paths, key=lambda p: rank_key(graph, p))))
    return sorted(leads, key=lambda lead: rank_key(graph, lead.best))


# =============================================================================
# How much each crop's leads rest on
# =============================================================================
def crop_summary(paths: list[EvidencePath]) -> dict[str, int]:
    """For one crop's paths: how many leads, paths, microbes, compounds, pathogens and papers."""
    return {
        "leads": len({(p.organism, p.compound, p.pathogen) for p in paths}),
        "paths": len(paths),
        "microbes": len({p.organism for p in paths}),
        "compounds": len({p.compound for p in paths}),
        "pathogens": len({p.pathogen for p in paths}),
        "papers": len({c for p in paths for c in p.papers}),
    }


def what_if_wrong(graph: nx.DiGraph,
                  by_crop: dict[str, list[EvidencePath]]) -> list[dict[str, Any]]:
    """
    Every fact (a node, or a paper) that some lead rests on entirely: if that
    one fact were wrong (the node shouldn't be there, or the paper didn't show
    what we read in it), how many leads would be lost, and which crops would be
    left with none. A lead is lost only when every one of its paths uses the
    fact, and a paper only counts where an arrow rests on it alone: a bridge row
    citing two papers keeps its arrows if one of them turns out wrong. A fact
    no lead rests on entirely (one of two clusters, say) isn't listed.

    This is the disease side's version of a bridge: a single point of failure.
    Sorted by leads lost, then crops left with nothing, then label.
    """
    leads = [lead for paths in by_crop.values() for lead in group_leads(graph, paths)]
    facts: dict[tuple[str, str], set[int]] = defaultdict(set)   # (kind, what) -> lead numbers
    for number, lead in enumerate(leads):
        uses: dict[tuple[str, str], int] = defaultdict(int)
        for path in lead.paths:
            # Each fact once per path, even when a node plays two parts (a
            # pathogen that is also the producer).
            facts_here = ({("node", node) for node in path.nodes[:-1]}   # all but the crop
                          | {("paper", paper) for paper in path.sole_papers})
            for fact in facts_here:
                uses[fact] += 1
        for fact, count in uses.items():
            if count == len(lead.paths):                   # every path uses it
                facts[fact].add(number)
    rows = []
    for (kind, what), lost in facts.items():
        crops_hit = sorted({leads[i].crop for i in lost})
        left_with_none = [c for c in crops_hit
                          if all(i in lost for i, lead in enumerate(leads) if lead.crop == c)]
        rows.append({
            "kind": kind,
            "id": what,
            "label": what if kind == "paper" else label(graph, what),
            "node_type": "" if kind == "paper" else str(graph.nodes[what]["node_type"]),
            "leads_lost": len(lost),
            "crops_hit": [str(graph.nodes[c]["name"]) for c in crops_hit],
            "crops_left_with_none": [str(graph.nodes[c]["name"]) for c in left_with_none],
        })
    return sorted(rows, key=lambda r: (-r["leads_lost"], -len(r["crops_left_with_none"]),
                                       r["label"].casefold(), r["id"]))
