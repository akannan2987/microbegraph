"""
MicrobeGraph, a look at the shape of the graph (Phase 5, Step 2).

USAGE (from the repository root, with .venv active)

    python tests/fixtures/survey_graph_shape.py

    Offline. It reads two things your computer already has:
        data/processed/microbegraph.duckdb          the graph (read-only)
        data/raw/mibig/mibig_gbk_4.0.tar.gz          MIBiG's GenBank file
    and prints what docs/07-graph-analytics.md, Step 2, reports. It takes
    about two minutes; Part 4 is the slow one. Nothing is written anywhere.

WHAT IT LOOKS AT, AND WHAT EACH PART DECIDED
    1. The shape: how many separate pieces the graph has, and its busiest
       nodes. (One giant piece, held together by a few general nodes.)
    2. The shortcut problem: the shortest route from jujube to a microbe,
       ignoring which way the arrows point. (It runs through a label, so the
       paths must follow a typed route.)
    3. The typed route: how many paths it finds, and how strong they are.
       (Every weakest link is the same, so the ranking needs tie-breaks.)
    4. Which arrows betweenness should count: the whole graph (estimated
       from 300 starting nodes) against the production layer. (The whole
       graph crowns general labels, so the production layer is used.)
    5. Communities with and without the labels, and in one randomly rewired
       copy where every node keeps its number of arrows. (Without proteins,
       with labels: groups that read as themes. The rewired copy scores
       almost as high, so the groups need Phase 6's test.)
    6. Protein names: how many are only a product, and how many the GenBank
       file can give a gene name. (A field of its own, genbank_gene.)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import networkx as nx  # noqa: E402

from microbegraph.analytics import centrality as cen  # noqa: E402
from microbegraph.analytics import communities as com  # noqa: E402
from microbegraph.analytics import evidence_paths as ep  # noqa: E402
from microbegraph.build_graph import load_graph  # noqa: E402
from microbegraph.sources.mibig_genbank import read_genbank_file  # noqa: E402

DATABASE = ROOT / "data" / "processed" / "microbegraph.duckdb"
GENBANK = ROOT / "data" / "raw" / "mibig" / "mibig_gbk_4.0.tar.gz"
FAR_MICROBE = "ncbitaxon:100226"         # Streptomyces coelicolor A3(2)
VAGUE = ("hypothetical protein", "conserved hypothetical protein", "unknown")


def line(key: str, value: object) -> None:
    print(f"    {key:<44} {value:>8}")


def name(graph: nx.DiGraph, node: str) -> str:
    return str(graph.nodes[node].get("name") or node)


def main() -> int:
    if not DATABASE.exists():
        print("data/processed/microbegraph.duckdb isn't there yet. Run python -m "
              "microbegraph.resolve and python -m microbegraph.build_graph first.")
        return 1
    graph = load_graph(DATABASE)
    whole = cen.undirected(graph)

    print("Part 1: the shape of the graph")
    pieces = sorted(nx.connected_components(whole), key=len, reverse=True)
    line("nodes", graph.number_of_nodes())
    line("arrows", graph.number_of_edges())
    line("separate pieces (ignoring arrow directions)", len(pieces))
    line("nodes in the biggest piece", len(pieces[0]))
    print("    the busiest nodes (arrows in and out):")
    for node, degree in sorted(graph.degree, key=lambda nd: (-nd[1], nd[0]))[:6]:
        print(f"      {degree:>5}  {name(graph, node)} ({graph.nodes[node]['node_type']})")

    print("Part 2: the shortest route from jujube to a microbe, ignoring directions")
    route = nx.shortest_path(whole, "mg.crop:jujube", FAR_MICROBE)
    print("    " + " - ".join(name(graph, n) for n in route))
    steps = nx.single_source_shortest_path_length(whole, "mg.crop:jujube", cutoff=6)
    producers = {n for n in steps if graph.nodes[n]["node_type"] in ("Organism", "Pathogen")
                 and any(graph.edges[n, s]["edge_type"] == "HARBORS"
                         for s in graph.successors(n))}
    line("microbes with a cluster, six steps or fewer", len(producers))

    print("Part 3: the typed route, microbe -> cluster -> compound -> pathogen -> crop")
    by_crop = ep.all_crop_paths(graph)
    paths = [p for ps in by_crop.values() for p in ps]
    line("paths", len(paths))
    line("leads (microbe, compound, pathogen, crop)",
         sum(len(ep.group_leads(graph, ps)) for ps in by_crop.values()))
    line("microbes on them", len({p.organism for p in paths}))
    for level, count in sorted(Counter(p.weakest for p in paths).items()):
        line(f"weakest link {level}", count)
    crops_per_microbe = Counter()
    for organism in {p.organism for p in paths}:
        crops_per_microbe[organism] = len({p.crop for p in paths if p.organism == organism})
    top, crops = sorted(crops_per_microbe.items(), key=lambda oc: (-oc[1], oc[0]))[0]
    print(f"    the microbe on most crops: {name(graph, top)}, {crops} of {len(by_crop)}")

    print("Part 4: betweenness, two ways")
    picked = cen.layer(graph)
    facts = cen.layer_facts(picked)
    print(f"    the production layer: {facts['nodes']:,} nodes, {facts['arrows']:,} arrows, "
          f"{facts['pieces']:,} pieces; exact:")
    for node, value in cen.top_nodes(cen.betweenness(picked), 5):
        print(f"      {value:.5f}  {name(graph, node)} ({graph.nodes[node]['node_type']})")
    print(f"    the whole graph, estimated from {cen.WHOLE_GRAPH_SAMPLE} starting nodes:")
    for node, value in cen.top_nodes(cen.whole_graph_betweenness(graph), 5):
        print(f"      {value:.5f}  {name(graph, node)} ({graph.nodes[node]['node_type']})")

    print("Part 5: communities (Louvain, seed 42)")
    without = com.without_proteins(graph)
    found = com.find_communities(without)
    line("without proteins: communities", len(found))
    line("without proteins: modularity", f"{com.modularity(without, found):.3f}")
    labels = ("Activity", "CompoundClass", "Pathway")
    bare = without.subgraph([n for n in without if graph.nodes[n]["node_type"] not in labels])
    bare_found = com.find_communities(nx.Graph(bare))
    line("without proteins or labels: communities", len(bare_found))
    line("without proteins or labels: modularity", f"{com.modularity(bare, bare_found):.3f}")
    # The same graph with its arrows shuffled: every node keeps its number of
    # arrows, but who links to whom is random (5 swaps per arrow, seed 1).
    rewired = without.copy()
    nx.double_edge_swap(rewired, nswap=5 * rewired.number_of_edges(),
                        max_tries=100 * rewired.number_of_edges(), seed=1)
    line("a rewired copy: modularity", f"{com.modularity(rewired, com.find_communities(rewired)):.3f}")

    print("Part 6: what the proteins are called")
    proteins = [d for _, d in graph.nodes(data=True) if d["node_type"] == "Protein"]
    by_product = sum(1 for d in proteins if d["name"] == d["properties"].get("product")
                     and d["name"] != d["properties"].get("gene_name"))
    line("proteins", len(proteins))
    line("named after their product", by_product)
    line("named 'hypothetical protein' or alike",
         sum(1 for d in proteins if d["name"] in VAGUE))
    with_gene = [d for d in proteins if d["properties"].get("genbank_gene")]
    if with_gene:
        line("given a GenBank gene name (genbank_gene)", len(with_gene))
        line("  of them with no MIBiG gene name",
             sum(1 for d in with_gene if not d["properties"].get("gene_name")))
    else:
        print("    given a GenBank gene name (genbank_gene)     none yet (Step 3 adds them)")
    if GENBANK.exists():
        cds = [c for entry in read_genbank_file(GENBANK).values() for c in entry]
        line("GenBank file: CDS", len(cds))
        line("  with a /gene", sum(1 for c in cds if c.gene))
        line("  with a /gene and a protein number", sum(1 for c in cds if c.gene and c.protein_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
