"""
Tests for the graph analytics (Phase 5): labels, evidence paths, hubs and
bridges, communities, the pages and the analyze command.

Most tests use the real slice in tests/fixtures/resolve/, resolved and built
once for this file (it holds three crops: jujube, maize and wheat). The
ranking rules and a few awkward cases need paths the slice doesn't have, so
those tests build a tiny graph by hand with make_graph().
"""

from __future__ import annotations

import csv
import io
import re
import shutil
from contextlib import redirect_stdout
from pathlib import Path

import duckdb
import networkx as nx
import pytest
from conftest import RESOLVE_FIXTURES, read_rows

from microbegraph.analytics import centrality as cen
from microbegraph.analytics import communities as com
from microbegraph.analytics import evidence_paths as ep
from microbegraph.analytics import pictures
from microbegraph.analytics.labels import label, protein_gene, shorten
from microbegraph.analyze import main
from microbegraph.build_graph import build, load_graph
from microbegraph.resolve import resolve
from microbegraph.sources.mibig_genbank import read_cds

FZB42 = "ncbitaxon:326423"
JUJUBE = "mg.crop:jujube"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The slice, resolved and built once: returns the database file."""
    root = tmp_path_factory.mktemp("analytics")
    staging = root / "staging"
    shutil.copytree(RESOLVE_FIXTURES, staging)
    with redirect_stdout(io.StringIO()):
        resolve(staging, root / "processed", staging / "curation")
        out = root / "processed"
        build(out / "nodes.csv", out / "edges.csv", out / "resolution_ledger.csv",
              out / "resolve_summary.json", out / "microbegraph.duckdb")
    return out / "microbegraph.duckdb"


@pytest.fixture(scope="module")
def graph(built: Path) -> nx.DiGraph:
    return load_graph(built)


def make_graph(nodes: dict[str, tuple[str, dict]], arrows: list[tuple]) -> nx.DiGraph:
    """
    A small graph by hand. nodes: {id: (type, properties)}, the name is the id
    after the colon. arrows: (start, end, type, evidence level, confidence, citation).
    """
    g = nx.DiGraph()
    for node, (kind, props) in nodes.items():
        g.add_node(node, node_type=kind, name=props.pop("name", node.split(":", 1)[-1]),
                   properties=props)
    for start, end, kind, level, confidence, citation in arrows:
        g.add_edge(start, end, edge_type=kind, evidence_level=level, source="test",
                   citation=citation, confidence=confidence)
    return g


EXP, DB, LIT = "curated_experimental", "database_assertion", "curated_literature"


def chain(org: str, bgc: str, cpd: str, pat: str, crop: str, levels: tuple[str, str] = (DB, DB),
          conf: tuple[float, float] = (0.8, 0.8), paper: str = "doi:x") -> list[tuple]:
    """The four arrows of one route, with chosen evidence for the two MIBiG arrows."""
    return [(org, bgc, "HARBORS", levels[0], 0.5, "pubmed:1"),
            (bgc, cpd, "PRODUCES", levels[1], 0.5, "pubmed:1"),
            (cpd, pat, "INHIBITS", LIT, conf[0], paper),
            (pat, crop, "INFECTS", LIT, conf[1], paper)]


def typed(**ids: str) -> dict[str, tuple[str, dict]]:
    kinds = {"o": "Organism", "b": "GeneCluster", "c": "Compound", "p": "Pathogen",
             "k": "Crop", "a": "Activity"}
    return {node: (kinds[key[0]], {}) for key, node in ids.items()}


# =============================================================================
# Labels, and the GenBank gene name behind them
# =============================================================================
def test_a_protein_label_puts_the_gene_first_and_the_product_after():
    g = make_graph({"uniprot:Q1": ("Protein", {"name": "surfactin synthetase A",
                                               "gene_name": "srfAA",
                                               "product": "surfactin synthetase A"})}, [])
    assert label(g, "uniprot:Q1") == "srfAA (surfactin synthetase A)"


def test_the_gene_comes_from_mibig_then_genbank_then_uniprot():
    assert protein_gene({"gene_name": "a", "genbank_gene": "b", "gene_names": "c|d"}) == "a"
    assert protein_gene({"genbank_gene": "b", "gene_names": "c|d"}) == "b"
    assert protein_gene({"gene_names": "c|d"}) == "c"
    assert protein_gene({}) == ""


def test_merged_names_show_only_the_first():
    assert protein_gene({"genbank_gene": "inkH|nokH"}) == "inkH"
    assert protein_gene({"gene_name": "|", "genbank_gene": "tylG"}) == "tylG"


def test_a_protein_without_any_gene_name_keeps_its_name():
    g = make_graph({"mg.protein:x": ("Protein", {"name": "hypothetical protein",
                                                 "product": "hypothetical protein"})}, [])
    assert label(g, "mg.protein:x") == "hypothetical protein"


def test_a_cluster_label_starts_with_its_accession_and_long_labels_are_cut():
    g = make_graph({"mibig:BGC0000433": ("GeneCluster", {"name": "surfactin BGC"})}, [])
    assert label(g, "mibig:BGC0000433") == "BGC0000433 surfactin BGC"
    assert shorten("a" * 60, 10) == "aaaaaaa..."
    cut = shorten("word " * 30)
    assert len(cut) <= 48 and cut.endswith("...")


def test_read_cds_keeps_the_first_gene_name_on_its_own():
    sample = RESOLVE_FIXTURES.parent / "mibig" / "genbank" / "BGC0000433.gbk"
    cds = read_cds(sample.read_text(encoding="utf-8"), "BGC0000433")
    by_number = {c.protein_id: c for c in cds}
    assert by_number["CAE02630.1"].gene == "srfAA"
    assert by_number["CAE02619.1"].gene == "yciC"


def test_genbank_genes_reach_the_database_but_never_gene_name(built, graph):
    con = duckdb.connect(str(built), read_only=True)
    try:
        given = con.execute("SELECT count(*) FROM proteins WHERE genbank_gene IS NOT NULL"
                            ).fetchone()[0]
        # A protein only the protein file knows has no gene record, so no gene_name:
        # the GenBank name must not have been copied there.
        copied = con.execute(
            "SELECT count(*) FROM nodes WHERE node_type = 'Protein' "
            "AND (properties->>'found_in') = 'protein_file' "
            "AND (properties->>'genbank_gene') IS NOT NULL "
            "AND (properties->>'gene_name') IS NOT NULL").fetchone()[0]
    finally:
        con.close()
    assert given > 0 and copied == 0
    # A protein named after its product, labelled with its GenBank gene instead.
    named_by_product = [n for n, d in graph.nodes(data=True)
                        if d["node_type"] == "Protein" and not d["properties"].get("gene_name")
                        and d["properties"].get("genbank_gene")]
    assert named_by_product
    node = named_by_product[0]
    assert label(graph, node).startswith(graph.nodes[node]["properties"]["genbank_gene"])


def test_the_resolver_ignores_genbank_genes(tmp_path):
    """Adding the new property changes no merge: the same ledger and arrows with or without it."""
    with_it, without = tmp_path / "with", tmp_path / "without"
    shutil.copytree(RESOLVE_FIXTURES, with_it / "staging")
    shutil.copytree(RESOLVE_FIXTURES, without / "staging")
    nodes = without / "staging" / "mibig_nodes.csv"
    text = re.sub(r', ""genbank_gene"": ""[^"]*""', "", nodes.read_text(encoding="utf-8"))
    text = re.sub(r'""genbank_gene"": ""[^"]*"", ', "", text)
    nodes.write_text(text, encoding="utf-8", newline="")
    assert "genbank_gene" not in text
    with redirect_stdout(io.StringIO()):
        for root in (with_it, without):
            resolve(root / "staging", root / "out", root / "staging" / "curation")
    for name in ("resolution_ledger.csv", "edges.csv"):
        assert read_rows(with_it / "out" / name) == read_rows(without / "out" / name)


# =============================================================================
# Evidence paths
# =============================================================================
def test_the_jujube_path_on_the_real_slice(graph):
    paths = ep.paths_to_crop(graph, JUJUBE)
    assert len(paths) == 1
    path = paths[0]
    assert path.organism == FZB42
    assert path.cluster == "mibig:BGC0000433"
    assert path.compound == "mg.compound:surfactin"
    assert [a.edge_type for a in path.arrows] == ["HARBORS", "PRODUCES", "INHIBITS", "INFECTS"]
    assert path.weakest == LIT
    assert path.experiments == 2
    assert path.weakest_confidence == pytest.approx(0.9)
    assert path.papers == ("doi:10.1186/s13568-023-01543-w",)


def test_every_crop_in_the_slice_has_its_paths(graph):
    by_crop = ep.all_crop_paths(graph)
    assert list(by_crop) == [JUJUBE, "mg.crop:maize", "mg.crop:wheat"]
    assert {c: len(p) for c, p in by_crop.items()} == {JUJUBE: 1, "mg.crop:maize": 1,
                                                       "mg.crop:wheat": 1}
    assert ep.crop_summary(by_crop["mg.crop:wheat"]) == {
        "leads": 1, "paths": 1, "microbes": 1, "compounds": 1, "pathogens": 1, "papers": 1}


def test_the_walk_follows_the_typed_route_only():
    """A microbe linked to the crop only through a shared activity label is no lead."""
    nodes = typed(o1="o:good", b1="b:1", c1="c:1", p1="p:1", k1="k:crop",
                  o2="o:other", b2="b:2", c2="c:2", a1="a:antifungal")
    arrows = chain("o:good", "b:1", "c:1", "p:1", "k:crop") + [
        ("o:other", "b:2", "HARBORS", DB, 0.5, ""), ("b:2", "c:2", "PRODUCES", DB, 0.5, ""),
        ("c:1", "a:antifungal", "HAS_ACTIVITY", DB, 0.5, ""),
        ("c:2", "a:antifungal", "HAS_ACTIVITY", DB, 0.5, "")]
    g = make_graph(nodes, arrows)
    assert [p.organism for p in ep.paths_to_crop(g, "k:crop")] == ["o:good"]
    # ...although, ignoring directions, the other microbe is only six steps away.
    assert nx.shortest_path_length(g.to_undirected(), "k:crop", "o:other") == 6


def test_a_pathogen_that_harbours_a_cluster_counts_as_a_microbe():
    nodes = typed(p0="p:fungus", b1="b:1", c1="c:1", p1="p:1", k1="k:crop")
    g = make_graph(nodes, chain("p:fungus", "b:1", "c:1", "p:1", "k:crop"))
    assert [p.organism for p in ep.paths_to_crop(g, "k:crop")] == ["p:fungus"]


def test_paths_rank_by_weakest_link_then_experiments_then_confidence_then_names():
    """And a path through an inferred arrow appears only when asked for."""
    nodes = typed(oa="o:a", ob="o:b", oc="o:c", od="o:d", ba="b:a", bb="b:b", bc="b:c", bd="b:d",
                  c1="c:1", p1="p:1", k1="k:crop")
    nodes["c:weak"] = ("Compound", {})
    arrows = (chain("o:d", "b:d", "c:1", "p:1", "k:crop", (EXP, EXP), (0.8, 0.8))   # 2 exp, 0.8
              + chain("o:c", "b:c", "c:1", "p:1", "k:crop", (EXP, DB), (0.8, 0.8))  # 1 exp
              + chain("o:b", "b:b", "c:1", "p:1", "k:crop", (EXP, EXP), (0.8, 0.8))  # ties o:d
              + [("o:a", "b:a", "HARBORS", EXP, 0.5, ""), ("b:a", "c:weak", "PRODUCES", EXP, 0.5, ""),
                 ("c:weak", "p:1", "INHIBITS", "inferred", 0.99, "")])
    g = make_graph(nodes, arrows)
    order = [p.organism for p in ep.paths_to_crop(g, "k:crop", include_inferred=True)]
    # o:b and o:d tie on everything but the name; o:c has one experiment fewer;
    # o:a has an inferred arrow, the weakest level, so it comes last.
    assert order == ["o:b", "o:d", "o:c", "o:a"]
    # Without asking, the inferred arrow is no evidence, and o:a's path isn't there.
    assert [p.organism for p in ep.paths_to_crop(g, "k:crop")] == ["o:b", "o:d", "o:c"]


def test_higher_confidence_on_the_weakest_arrows_ranks_first():
    nodes = typed(oa="o:a", ob="o:b", ba="b:a", bb="b:b", c1="c:1", c2="c:2", p1="p:1",
                  k1="k:crop")
    arrows = (chain("o:a", "b:a", "c:1", "p:1", "k:crop", conf=(0.8, 0.9))
              + [("o:b", "b:b", "HARBORS", DB, 0.5, ""), ("b:b", "c:2", "PRODUCES", DB, 0.5, ""),
                 ("c:2", "p:1", "INHIBITS", LIT, 0.9, "doi:y")])
    g = make_graph(nodes, arrows)
    paths = ep.paths_to_crop(g, "k:crop")
    assert [p.organism for p in paths] == ["o:b", "o:a"]
    assert [p.weakest_confidence for p in paths] == [pytest.approx(0.9), pytest.approx(0.8)]


def test_two_clusters_for_the_same_compound_make_one_lead():
    nodes = typed(o1="o:1", b1="b:1", b2="b:2", c1="c:1", p1="p:1", k1="k:crop")
    arrows = (chain("o:1", "b:1", "c:1", "p:1", "k:crop", (EXP, EXP))
              + [("o:1", "b:2", "HARBORS", DB, 0.5, ""), ("b:2", "c:1", "PRODUCES", DB, 0.5, "")])
    g = make_graph(nodes, arrows)
    leads = ep.group_leads(g, ep.paths_to_crop(g, "k:crop"))
    assert len(leads) == 1
    assert [p.cluster for p in leads[0].paths] == ["b:1", "b:2"]   # the stronger one first


def test_what_if_wrong_counts_a_lead_lost_only_when_every_path_uses_the_fact():
    nodes = typed(o1="o:1", o2="o:2", b1="b:1", b2="b:2", b3="b:3", c1="c:1", c2="c:2",
                  p1="p:1", p2="p:2", k1="k:one", k2="k:two")
    arrows = (chain("o:1", "b:1", "c:1", "p:1", "k:one", paper="doi:a")
              + [("o:1", "b:2", "HARBORS", DB, 0.5, ""), ("b:2", "c:1", "PRODUCES", DB, 0.5, "")]
              + chain("o:2", "b:3", "c:2", "p:2", "k:two", paper="doi:b"))
    g = make_graph(nodes, arrows)
    rows = {r["id"]: r for r in ep.what_if_wrong(g, ep.all_crop_paths(g))}
    assert "b:1" not in rows                       # o:1's lead still has b:2
    assert rows["o:1"]["leads_lost"] == 1
    assert rows["o:1"]["crops_left_with_none"] == ["one"]
    assert rows["doi:a"]["kind"] == "paper"
    assert rows["doi:b"]["crops_left_with_none"] == ["two"]


def test_a_claim_with_two_papers_survives_losing_one():
    nodes = typed(o1="o:1", b1="b:1", c1="c:1", p1="p:1", k1="k:crop")
    arrows = chain("o:1", "b:1", "c:1", "p:1", "k:crop", paper="doi:a")
    arrows[2] = ("c:1", "p:1", "INHIBITS", LIT, 0.8, "doi:a|doi:b")    # two papers
    g = make_graph(nodes, arrows)
    path = ep.paths_to_crop(g, "k:crop")[0]
    assert path.papers == ("doi:a", "doi:b")
    assert path.sole_papers == ("doi:a",)          # INFECTS still rests on doi:a alone
    rows = {r["id"]: r for r in ep.what_if_wrong(g, ep.all_crop_paths(g))}
    assert "doi:b" not in rows
    assert rows["doi:a"]["leads_lost"] == 1


def test_a_node_playing_two_parts_is_still_a_single_point():
    """A pathogen that also makes the compound against itself: one fact, counted once."""
    nodes = typed(b1="b:1", c1="c:1", k1="k:crop")
    nodes["p:x"] = ("Pathogen", {})
    g = make_graph(nodes, chain("p:x", "b:1", "c:1", "p:x", "k:crop"))
    rows = {r["id"]: r for r in ep.what_if_wrong(g, ep.all_crop_paths(g))}
    assert rows["p:x"]["leads_lost"] == 1


def test_find_node_by_identifier_or_name_and_helpful_errors(graph):
    assert ep.find_node(graph, "jujube", "Crop") == JUJUBE
    assert ep.find_node(graph, "JUJUBE", "Crop") == JUJUBE
    assert ep.find_node(graph, "mg.crop:jujube", "Crop") == JUJUBE
    assert ep.find_node(graph, "surfactin") == "mg.compound:surfactin"
    with pytest.raises(LookupError, match="jujube, maize, wheat"):
        ep.find_node(graph, "rice", "Crop")
    with pytest.raises(LookupError, match="identifier or name"):
        ep.find_node(graph, "no such thing")
    twins = make_graph({"c:1": ("Compound", {"name": "x"}), "c:2": ("Compound", {"name": "x"})}, [])
    with pytest.raises(LookupError, match="2 nodes are called"):
        ep.find_node(twins, "x")


# =============================================================================
# Hubs and bridges
# =============================================================================
def test_the_production_layer_keeps_four_arrow_types_without_directions(graph):
    picked = cen.layer(graph)
    assert not picked.is_directed()
    kinds = {graph.edges[a, b]["edge_type"] if graph.has_edge(a, b)
             else graph.edges[b, a]["edge_type"] for a, b in picked.edges}
    assert kinds == {"HARBORS", "PRODUCES", "INHIBITS", "INFECTS"}
    assert not any(graph.nodes[n]["node_type"] in ("Protein", "Activity") for n in picked)


def test_betweenness_finds_the_node_in_the_middle():
    line = nx.Graph([("a", "b"), ("b", "c")])
    assert cen.betweenness(line) == {"a": 0.0, "b": 1.0, "c": 0.0}
    star = nx.Graph([("hub", x) for x in "wxyz"] + [("z", "far")])
    assert cen.top_nodes(cen.betweenness(star), 1)[0][0] == "hub"


def test_hubs_are_listed_per_type_with_ties_by_identifier():
    g = make_graph(typed(o1="o:b", o2="o:a", b1="b:1", b2="b:2"),
                   [("o:a", "b:1", "HARBORS", DB, 0.5, ""), ("o:b", "b:2", "HARBORS", DB, 0.5, "")])
    hubs = cen.hubs_by_type(g, top=2)
    assert hubs["Organism"] == [("o:a", 1), ("o:b", 1)]
    assert list(hubs) == ["GeneCluster", "Organism"]


def test_the_whole_graph_estimate_is_the_same_every_time(graph):
    first = cen.whole_graph_betweenness(graph, k=20)
    assert first == cen.whole_graph_betweenness(graph, k=20)
    assert set(first) == set(graph.nodes)


# =============================================================================
# Communities
# =============================================================================
def two_cliques() -> nx.Graph:
    g = nx.complete_graph(["a1", "a2", "a3", "a4", "a5"])
    g.add_edges_from(nx.complete_graph(["b1", "b2", "b3", "b4"]).edges)
    g.add_edge("a1", "b1")
    return g


def test_louvain_finds_two_cliques_biggest_first():
    found = com.find_communities(two_cliques())
    assert found == [{"a1", "a2", "a3", "a4", "a5"}, {"b1", "b2", "b3", "b4"}]
    assert com.modularity(two_cliques(), found) > 0.3
    assert com.membership(found)["b3"] == 2


def test_communities_leave_out_proteins_and_repeat_exactly(graph):
    without = com.without_proteins(graph)
    assert not any(graph.nodes[n]["node_type"] == "Protein" for n in without)
    first = com.find_communities(without)
    assert first == com.find_communities(without)
    assert sum(len(c) for c in first) == without.number_of_nodes()
    rows = com.describe(graph, without, first)
    homes = {c: r["community"] for r in rows for c in r["crops"]}
    assert set(homes) == {JUJUBE, "mg.crop:maize", "mg.crop:wheat"}


# =============================================================================
# The pages and the command
# =============================================================================
def run(argv: list[str], built: Path, out: Path) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(argv, db_path=built, out_dir=out)
    return code, buffer.getvalue()


def test_the_full_run_writes_every_file(built, tmp_path):
    code, printed = run([], built, tmp_path)
    assert code == 0
    for name in ("crop_paths.csv", "single_points.csv", "node_measures.csv", "communities.csv",
                 "analytics_summary.json", "crop_paths.html", "communities.html",
                 "hubs_and_bridges.html", "plotly.min.js"):
        assert (tmp_path / name).stat().st_size > 0, name
    assert "evidence paths: 3 paths, 3 leads, 3 crops" in printed
    rows = list(csv.DictReader((tmp_path / "crop_paths.csv").open(encoding="utf-8")))
    assert [(r["crop"], r["rank"], r["compound"]) for r in rows] == [
        ("jujube", "1", "surfactin"), ("maize", "1", "bacillomycin D"),
        ("wheat", "1", "bacillomycin D")]
    measures = list(csv.DictReader((tmp_path / "node_measures.csv").open(encoding="utf-8")))
    assert len(measures) == load_graph(built).number_of_nodes()


def test_two_runs_give_the_same_results(built, tmp_path):
    run([], built, tmp_path / "one")
    run([], built, tmp_path / "two")
    for name in ("crop_paths.csv", "single_points.csv", "node_measures.csv", "communities.csv"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()


def test_the_pages_ask_no_website_for_anything(built, tmp_path):
    run([], built, tmp_path)
    run(["--around", "surfactin"], built, tmp_path)
    for page in tmp_path.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "bootstrap" not in html, page.name
        assert not re.search(r"<script[^>]+src=[\"']https?:", html), page.name
        assert not re.search(r"<link[^>]+href=[\"']https?:", html), page.name


def test_paths_for_one_crop_and_an_unknown_crop(built, tmp_path):
    code, printed = run(["--paths", "jujube"], built, tmp_path)
    assert code == 0
    assert "1. Bacillus velezensis FZB42 -> surfactin -> Botrytis cinerea -> jujube" in printed
    assert "doi:10.1186/s13568-023-01543-w" in printed
    code, printed = run(["--paths", "rice"], built, tmp_path)
    assert code == 2
    assert "The crops in the graph: jujube, maize, wheat." in printed


def test_the_detail_views_run(built, tmp_path):
    for option, heading in (("--hubs", "hubs:"), ("--bridges", "bridges:"),
                            ("--communities", "communities in the graph without proteins")):
        code, printed = run([option], built, tmp_path)
        assert code == 0 and heading in printed, option
    code, printed = run(["--around", "surfactin"], built, tmp_path)
    assert code == 0
    assert (tmp_path / "around_surfactin.html").exists()


def test_an_around_page_of_a_shared_name_gets_the_identifier_too():
    from microbegraph.analyze import around_file_name
    g = make_graph({"c:1": ("Compound", {"name": "x"}), "c:2": ("Compound", {"name": "X"}),
                    "c:3": ("Compound", {"name": "surfactin"})}, [])
    assert around_file_name(g, "c:3") == "around_surfactin.html"
    assert around_file_name(g, "c:1") == "around_x_c_1.html"
    assert around_file_name(g, "c:2") == "around_x_c_2.html"


def test_slug_makes_safe_file_names():
    assert pictures.slug("Botrytis cinerea") == "botrytis_cinerea"
    assert pictures.slug("2,4-diacetylphloroglucinol") == "2_4_diacetylphloroglucinol"
    assert pictures.slug("///") == "node"
