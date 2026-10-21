"""
MicrobeGraph, ask the graph questions (Phase 5).

USAGE (from the repository root, with .venv active)

    python -m microbegraph.analyze                     all of it: a summary on screen, and
                                                       every result in data/processed/analytics/
    python -m microbegraph.analyze --paths             every crop's leads, each arrow's evidence
    python -m microbegraph.analyze --paths jujube      one crop
    python -m microbegraph.analyze --hubs              the nodes with the most arrows, by type
    python -m microbegraph.analyze --bridges           bridges, and the facts each crop rests on
    python -m microbegraph.analyze --bridges --whole-graph     also the whole-graph estimate
    python -m microbegraph.analyze --communities       the groups Louvain finds
    python -m microbegraph.analyze --around surfactin  a page of one node and its neighbours

    Arrows that are only hypotheses (evidence level `inferred`, none yet; Phase 7
    makes the first) stay out of the paths unless you add --include-inferred.

    A name with spaces goes in double quotes: --around "Botrytis cinerea".
    docs/07-graph-analytics.md explains every part from the start.

WHAT THE FULL RUN WRITES (data/processed/analytics/, never committed, like all of data/)

    crop_paths.csv          one row per evidence path, ranked within its crop
    single_points.csv       every fact some lead rests on entirely, and the leads lost
                            without it
    node_measures.csv       every node: arrows (degree), betweenness on the production
                            layer, and its community
    communities.csv         one row per community: size, types, busiest members, crops
    analytics_summary.json  the counts, the settings (seed, sample) and the versions used
    crop_paths.html, communities.html, hubs_and_bridges.html, plotly.min.js
                            the pages (pictures.py says what each one shows)

    The CSV files are the results. The pages only show them. Phase 6 reads
    node_measures.csv to check the same numbers from R.

IT ONLY READS THE DATABASE
    The graph comes from build_graph.load_graph(), which opens the database
    read-only. Nothing this command does can change a node or an arrow.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import plotly
import pyvis

from microbegraph.analytics import centrality as cen
from microbegraph.analytics import communities as com
from microbegraph.analytics import evidence_paths as ep
from microbegraph.analytics import pictures
from microbegraph.analytics.labels import label, shorten
from microbegraph.build_graph import BuildError, load_graph
from microbegraph.ontology import evidence_rank
from microbegraph.paths import ANALYTICS_DIR, DATABASE_FILE, relative_to_repo

SHOWN = 10          # rows shown on screen for the long lists (the CSV files have all of them)


def say(text: str = "") -> None:
    print(text)


def _csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """CSV text with Unix line ends, so the file is the same on every system."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buffer.getvalue()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _name(graph: nx.DiGraph, node: str) -> str:
    return str(graph.nodes[node].get("name") or node)


# =============================================================================
# Evidence paths
# =============================================================================
def around_file_name(graph: nx.DiGraph, centre: str) -> str:
    """
    The --around page's file name, after the node's name. A node that shares
    its name with another gets its identifier too, so two pages never
    overwrite each other.
    """
    name = _name(graph, centre)
    twins = sum(1 for _, d in graph.nodes(data=True)
                if str(d.get("name") or "").casefold() == name.casefold())
    part = name if twins == 1 else f"{name} {centre}"
    return f"around_{pictures.slug(part)}.html"


def lead_line(graph: nx.DiGraph, lead: ep.Lead) -> str:
    return " -> ".join(_name(graph, n) for n in (lead.organism, lead.compound, lead.pathogen,
                                                 lead.crop))


def show_lead(graph: nx.DiGraph, number: int, lead: ep.Lead) -> None:
    """One lead: its route, how strong its best path is, and every arrow's evidence."""
    best = lead.best
    say(f"  {number}. {lead_line(graph, lead)}")
    say(f"     weakest link {best.weakest}; {best.experiments} of {len(best.arrows)} arrows "
        f"from an experiment; weakest arrows' confidence {best.weakest_confidence:.2f}")
    for arrow in best.arrows:
        say(f"       {arrow.edge_type:<9} {label(graph, arrow.start)} -> {label(graph, arrow.end)}")
        cited = shorten(arrow.citation, 60) if arrow.citation else "no citation"
        conf = "" if arrow.confidence is None else f", confidence {arrow.confidence:.2f}"
        say(f"       {'':<9} {arrow.evidence_level}, from {arrow.source}, {cited}{conf}")
    for other in lead.paths[1:]:
        say(f"     also through {label(graph, other.cluster)} "
            f"(weakest link {other.weakest}; {other.experiments} of {len(other.arrows)} "
            f"from an experiment)")


def show_paths(graph: nx.DiGraph, crop_text: str | None, include_inferred: bool = False) -> None:
    chosen = [ep.find_node(graph, crop_text, "Crop")] if crop_text else ep.crops(graph)
    for crop in chosen:
        paths = ep.paths_to_crop(graph, crop, include_inferred)
        leads = ep.group_leads(graph, paths)
        say(f"[analyze] evidence paths to {_name(graph, crop)}: "
            f"{len(leads)} lead{'s' if len(leads) != 1 else ''}, "
            f"{len(paths)} path{'s' if len(paths) != 1 else ''}")
        if not leads:
            say("  none: no compound in the graph is recorded as inhibiting a pathogen of this crop")
        for number, lead in enumerate(leads, start=1):
            show_lead(graph, number, lead)


def crop_table(graph: nx.DiGraph, by_crop: dict[str, list[ep.EvidencePath]]) -> list[str]:
    """The per-crop counts as aligned lines."""
    rows = [(_name(graph, c), ep.crop_summary(p)) for c, p in by_crop.items()]
    width = max([4] + [len(n) for n, _ in rows])
    lines = [f"  {'crop':<{width}}  leads  paths  microbes  compounds  papers"]
    for name, s in rows:
        lines.append(f"  {name:<{width}}  {s['leads']:>5}  {s['paths']:>5}  {s['microbes']:>8}  "
                     f"{s['compounds']:>9}  {s['papers']:>6}")
    return lines


def path_rows(graph: nx.DiGraph, by_crop: dict[str, list[ep.EvidencePath]]) -> list[dict[str, Any]]:
    rows = []
    for crop, paths in by_crop.items():
        leads = ep.group_leads(graph, paths)
        lead_of = {(lead.organism, lead.compound, lead.pathogen): i
                   for i, lead in enumerate(leads, start=1)}
        for rank, p in enumerate(paths, start=1):
            rows.append({
                "crop": _name(graph, crop), "rank": rank,
                "lead": lead_of[(p.organism, p.compound, p.pathogen)],
                "organism": _name(graph, p.organism), "cluster": p.cluster,
                "compound": _name(graph, p.compound), "pathogen": _name(graph, p.pathogen),
                "weakest_link": p.weakest, "experiments": p.experiments,
                "weakest_confidence": f"{p.weakest_confidence:.2f}",
                "papers": "|".join(p.papers),
                "organism_id": p.organism, "compound_id": p.compound,
                "pathogen_id": p.pathogen, "crop_id": crop,
            })
    return rows


# =============================================================================
# Hubs, bridges, single points of failure
# =============================================================================
def show_hubs(graph: nx.DiGraph) -> None:
    say("[analyze] hubs: the nodes with the most arrows (degree), three per type")
    hubs = cen.hubs_by_type(graph, top=3)
    width = max(len(k) for k in hubs)
    for kind, nodes in hubs.items():
        for i, (node, degree) in enumerate(nodes):
            say(f"  {kind if i == 0 else '':<{width}}  {degree:>5,}  {label(graph, node, widest=44)}")


def show_bridges(graph: nx.DiGraph, picked: nx.Graph, between: dict[str, float]) -> None:
    facts = cen.layer_facts(picked)
    say("[analyze] bridges: betweenness on the production layer "
        f"({', '.join(cen.PRODUCTION_LAYER)})")
    say(f"  {facts['nodes']:,} nodes, {facts['arrows']:,} arrows, "
        f"{facts['pieces']:,} separate pieces")
    for i, (node, value) in enumerate(cen.top_nodes(between, SHOWN), start=1):
        say(f"  {i:>2}  {value:.5f}  {graph.nodes[node]['node_type']:<11}  "
            f"{label(graph, node, widest=44)}")


def show_whole_graph(graph: nx.DiGraph) -> None:
    say(f"[analyze] for comparison: betweenness on the whole graph, estimated from "
        f"{cen.WHOLE_GRAPH_SAMPLE} starting nodes (seed {cen.SEED})")
    for i, (node, value) in enumerate(cen.top_nodes(cen.whole_graph_betweenness(graph), SHOWN),
                                      start=1):
        say(f"  {i:>2}  {value:.4f}  {graph.nodes[node]['node_type']:<11}  "
            f"{label(graph, node, widest=44)}")


def show_single_points(rows: list[dict[str, Any]], total_leads: int) -> None:
    say(f"[analyze] if one fact were wrong: the leads lost, of {total_leads}")
    say("  lost  crops left with none  fact")
    for row in rows[:SHOWN]:
        none = ", ".join(row["crops_left_with_none"]) or "none"
        kind = "paper" if row["kind"] == "paper" else row["node_type"]
        say(f"  {row['leads_lost']:>4}  {shorten(none, 20):<20}  {shorten(row['label'], 44)} ({kind})")


# =============================================================================
# Communities
# =============================================================================
def show_communities(graph: nx.DiGraph, picked: nx.Graph, found: list[set[str]],
                     rows: list[dict[str, Any]]) -> None:
    q = com.modularity(picked, found)
    say(f"[analyze] communities in the graph without proteins: {len(found)}, "
        f"modularity {q:.3f} (Louvain, seed {cen.SEED})")
    say("   #   size  microbes  clusters  compounds  labels  busiest member")
    for row in rows[:SHOWN]:
        types = row["types"]
        microbes = types.get("Organism", 0) + types.get("Pathogen", 0)
        labels = sum(types.get(k, 0) for k in ("Activity", "CompoundClass", "Pathway"))
        busiest = _name(graph, row["top"][0])
        say(f"  {row['community']:>2}  {row['size']:>5,}  {microbes:>8,}  "
            f"{types.get('GeneCluster', 0):>8,}  {types.get('Compound', 0):>9,}  {labels:>6,}  "
            f"{shorten(busiest, 34)}")
    homes = [f"{_name(graph, c)} in {row['community']}" for row in rows for c in row["crops"]]
    say(f"  the crops: {', '.join(sorted(homes)) or 'none'}")


# =============================================================================
# The full run
# =============================================================================
def run_all(graph: nx.DiGraph, out_dir: Path, db_label: str, whole_graph: bool = False,
            include_inferred: bool = False) -> dict[str, Any]:
    """Every analysis, a short summary on screen, and every file in out_dir. Returns the summary."""
    made_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    note = (f"Made by python -m microbegraph.analyze on {made_at} from {db_label} "
            f"(NetworkX {nx.__version__}, pyvis {pyvis.__version__}, plotly {plotly.__version__}).")

    # 1. Evidence paths
    by_crop = ep.all_crop_paths(graph, include_inferred)
    all_paths = [p for paths in by_crop.values() for p in paths]
    n_leads = sum(len(ep.group_leads(graph, p)) for p in by_crop.values())
    weakest = sorted({p.weakest for p in all_paths}, key=evidence_rank)
    say(f"[analyze] evidence paths: {len(all_paths)} paths, {n_leads} leads, {len(by_crop)} crops "
        f"(weakest links: {', '.join(weakest) or 'none'})")
    for line in crop_table(graph, by_crop):
        say(line)

    # 2. Hubs
    degree = cen.degrees(graph)
    hubs = cen.top_nodes({n: float(d) for n, d in degree.items()}, 3)
    say("[analyze] hubs (most arrows): "
        + ", ".join(f"{label(graph, n)} {int(v):,}" for n, v in hubs))

    # 3. Bridges on the production layer, and single points of failure
    picked = cen.layer(graph)
    between = cen.betweenness(picked)
    facts = cen.layer_facts(picked)
    best_bridges = cen.top_nodes(between, 3)
    say(f"[analyze] bridges on the production layer ({facts['nodes']:,} nodes, "
        f"{facts['arrows']:,} arrows, {facts['pieces']:,} pieces): "
        + ", ".join(label(graph, n) for n, _ in best_bridges))
    single = ep.what_if_wrong(graph, by_crop)
    if single:
        top = single[0]
        none = " and ".join(top["crops_left_with_none"])
        say(f"[analyze] if one fact were wrong: without {top['label']}, {top['leads_lost']} of "
            f"{n_leads} leads are lost" + (f" and {none} would have none" if none else ""))
    if whole_graph:
        show_whole_graph(graph)

    # 4. Communities
    without = com.without_proteins(graph)
    found = com.find_communities(without)
    rows = com.describe(graph, without, found)
    q = com.modularity(without, found)
    crop_homes = {c: row["community"] for row in rows for c in row["crops"]}
    say(f"[analyze] communities without proteins: {len(found)} (modularity {q:.3f}); "
        f"the {len(crop_homes)} crops sit in {len(set(crop_homes.values()))} of them")

    # 5. The files
    members = com.membership(found)
    written = {
        "crop_paths.csv": _csv(
            ["crop", "rank", "lead", "organism", "cluster", "compound", "pathogen",
             "weakest_link", "experiments", "weakest_confidence", "papers",
             "organism_id", "compound_id", "pathogen_id", "crop_id"],
            path_rows(graph, by_crop)),
        "single_points.csv": _csv(
            ["kind", "id", "label", "node_type", "leads_lost", "crops_hit",
             "crops_left_with_none"],
            [{**r, "crops_hit": "|".join(r["crops_hit"]),
              "crops_left_with_none": "|".join(r["crops_left_with_none"])} for r in single]),
        "node_measures.csv": _csv(
            ["node_id", "node_type", "label", "degree", "betweenness_production_layer",
             "community"],
            [{"node_id": n, "node_type": graph.nodes[n]["node_type"], "label": label(graph, n),
              "degree": degree[n],
              "betweenness_production_layer": f"{between[n]:.8f}" if n in between else "",
              "community": members.get(n, "")} for n in sorted(graph.nodes)]),
        "communities.csv": _csv(
            ["community", "size", "types", "busiest", "crops"],
            [{"community": r["community"], "size": r["size"],
              "types": "|".join(f"{k}={v}" for k, v in r["types"].items()),
              "busiest": "|".join(label(graph, n) for n in r["top"]),
              "crops": "|".join(_name(graph, c) for c in r["crops"])} for r in rows]),
    }
    for name, text in written.items():
        _write(out_dir / name, text)
    pictures.crop_paths_page(graph, by_crop, out_dir / "crop_paths.html", note)
    pictures.communities_page(graph, without, found, rows, out_dir / "communities.html", note)
    pictures.hubs_page(graph, picked, between, out_dir / "hubs_and_bridges.html", note)

    summary = {
        "made_at": made_at,
        "database": db_label,
        "versions": {"networkx": nx.__version__, "pyvis": pyvis.__version__,
                     "plotly": plotly.__version__, "python": platform.python_version()},
        "settings": {"seed": cen.SEED, "production_layer": list(cen.PRODUCTION_LAYER),
                     "route": [t for t, _ in reversed(ep.ROUTE)],
                     "include_inferred": include_inferred},
        "graph": {"nodes": graph.number_of_nodes(), "arrows": graph.number_of_edges()},
        "evidence_paths": {"paths": len(all_paths), "leads": n_leads, "crops": len(by_crop),
                           "per_crop": {_name(graph, c): ep.crop_summary(p)
                                        for c, p in by_crop.items()}},
        "hubs": [{"node_id": n, "label": label(graph, n), "degree": int(v)} for n, v in hubs],
        "production_layer": facts,
        "bridges": [{"node_id": n, "label": label(graph, n), "betweenness": round(v, 8)}
                    for n, v in cen.top_nodes(between, SHOWN)],
        "single_points": single[:SHOWN],
        "communities": {"count": len(found), "modularity": round(q, 6),
                        "sizes": [len(c) for c in found],
                        "crops": {_name(graph, c): n for c, n in sorted(crop_homes.items())}},
    }
    _write(out_dir / "analytics_summary.json",
           json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    files = [*written, "analytics_summary.json", "crop_paths.html", "communities.html",
             "hubs_and_bridges.html", "plotly.min.js"]
    say(f"[analyze] wrote {relative_to_repo(out_dir)}/:")
    say(f"  {', '.join(files[:4])},")
    say(f"  {', '.join(files[4:])}")
    return summary


def main(argv: list[str] | None = None, db_path: Path | None = None,
         out_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microbegraph.analyze",
        description="Ask the graph questions: evidence paths, hubs, bridges, communities. "
                    "With no option, runs everything and writes data/processed/analytics/.")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--paths", nargs="?", const="", metavar="CROP",
                       help="the evidence paths to every crop, or to one")
    which.add_argument("--hubs", action="store_true", help="the nodes with the most arrows")
    which.add_argument("--bridges", action="store_true",
                       help="bridges on the production layer, and single points of failure")
    which.add_argument("--communities", action="store_true", help="the groups Louvain finds")
    which.add_argument("--around", metavar="NODE",
                       help="write a page of one node (name or identifier) and its neighbours")
    parser.add_argument("--whole-graph", action="store_true",
                        help="with --bridges or the full run: also estimate betweenness on "
                             "the whole graph (about a minute)")
    parser.add_argument("--include-inferred", action="store_true",
                        help="with --paths, --bridges or the full run: let arrows that are "
                             "only hypotheses (evidence level inferred) into the paths")
    args = parser.parse_args(argv)

    database = Path(db_path or DATABASE_FILE)
    target = Path(out_dir or ANALYTICS_DIR)
    started = time.perf_counter()
    try:
        graph = load_graph(database)
    except BuildError as error:
        say(f"[analyze] {error}")
        return 1
    say(f"[analyze] read the graph from {relative_to_repo(database)}: "
        f"{graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} arrows")
    try:
        if args.paths is not None:
            show_paths(graph, args.paths or None, args.include_inferred)
        elif args.hubs:
            show_hubs(graph)
        elif args.bridges:
            picked = cen.layer(graph)
            show_bridges(graph, picked, cen.betweenness(picked))
            by_crop = ep.all_crop_paths(graph, args.include_inferred)
            n_leads = sum(len(ep.group_leads(graph, p)) for p in by_crop.values())
            show_single_points(ep.what_if_wrong(graph, by_crop), n_leads)
            if args.whole_graph:
                show_whole_graph(graph)
        elif args.communities:
            without = com.without_proteins(graph)
            found = com.find_communities(without)
            show_communities(graph, without, found, com.describe(graph, without, found))
        elif args.around:
            centre = ep.find_node(graph, args.around)
            page = target / around_file_name(graph, centre)
            made_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            note = (f"Made by python -m microbegraph.analyze --around on {made_at} from "
                    f"{relative_to_repo(database)}.")
            _, total, drawn = pictures.around_page(graph, centre, page, note)
            shown = f"all {total}" if drawn == total else f"the {drawn} busiest of {total}"
            say(f"[analyze] wrote {relative_to_repo(page)}: {_name(graph, centre)} and "
                f"{shown} neighbours")
            say(f"Next:  open {relative_to_repo(page)} in your browser")
            return 0
        else:
            run_all(graph, target, relative_to_repo(database), whole_graph=args.whole_graph,
                    include_inferred=args.include_inferred)
            say(f"[analyze] done in {time.perf_counter() - started:.1f} s.")
            say(f"Next:  open {relative_to_repo(target)}/crop_paths.html in your browser")
            return 0
    except LookupError as error:
        say(f"[analyze] {error.args[0]}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
