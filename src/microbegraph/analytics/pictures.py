"""
MicrobeGraph, interactive pages you open in a browser (Phase 5).

TWO TOOLS, TWO KINDS OF PAGE
    pyvis draws NETWORKS. You give it nodes and arrows in Python, and it
    writes one HTML page that uses a JavaScript library called vis-network to
    draw them. In the browser you can drag nodes, zoom, and hover over a node
    or an arrow to see its details.

    plotly draws CHARTS (here a scatter plot and a bar chart). It too writes
    HTML, with hover, zoom and a button to save the chart as a picture.

    Both are only for looking. The numbers behind every page are also written
    as CSV files beside it (see analyze.py), so nothing here is the only copy
    of a result.

THE PAGES WORK WITHOUT AN INTERNET CONNECTION
    pyvis can either link to vis-network on a website or copy it into the
    page. These pages copy it in (cdn_resources="in_line"), and the two links
    to a styling library that pyvis's page template always adds are taken out,
    because nothing here uses them. The plotly pages share one copy of
    plotly's own script, plotly.min.js, written once beside them.

    So each page opens straight from your folder, on a train or behind a
    company firewall, and asks no website for anything.

THE SAME COLOURS AND SHAPES AS THE DIAGRAMS IN docs/img/
    Colour shows a node's biological layer (genomics blue, proteomics orange,
    metabolomics aqua, phenotype yellow, context grey), the same colours
    docs/img/make_illustrations.py uses. Two types can share a layer, so each
    type also has its own shape, and every node carries its name: no meaning
    rests on colour alone. Arrows are blue, darker for stronger evidence, and
    thicker too, with the evidence written on the arrow.

WHAT IS IN EACH PAGE
    crop_paths.html        every crop's evidence paths, laid out in five
                           columns: microbe, cluster, compound, pathogen, crop
    communities.html       the 63 communities as bubbles, sized by members,
                           with the links between them
    hubs_and_bridges.html  degree against betweenness for every node of the
                           production layer, and the top bridges as bars
    around_<name>.html     one node and its neighbours (--around)
"""

from __future__ import annotations

import re
from collections import Counter
from html import escape
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline import get_plotlyjs
from pyvis.network import Network

from microbegraph.analytics.evidence_paths import EvidencePath
from microbegraph.analytics.labels import label

# --- The colours of docs/img/make_illustrations.py ------------------------------
INK, INK2, MUTED, HAIR, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
LAYER = {"genomics": "#2a78d6", "proteomics": "#eb6834", "metabolomics": "#1baf7a",
         "phenotype": "#eda100", "context": "#898781"}
EVIDENCE = {"curated_experimental": "#184f95", "database_assertion": "#2a78d6",
            "curated_literature": "#6da7ec", "inferred": "#898781"}
# Thicker is stronger, so the strength can be read without telling the blues apart.
EVIDENCE_WIDTH = {"curated_experimental": 4.0, "database_assertion": 2.5,
                  "curated_literature": 2.0, "inferred": 1.5}
EVIDENCE_WORD = {"curated_experimental": "experiment", "database_assertion": "database",
                 "curated_literature": "paper", "inferred": "inferred"}

# node type -> (layer, vis-network shape, plotly marker symbol)
TYPE_STYLE: dict[str, tuple[str, str, str]] = {
    "Organism": ("genomics", "dot", "circle"),
    "GeneCluster": ("genomics", "square", "square"),
    "Protein": ("proteomics", "triangle", "triangle-up"),
    "Compound": ("metabolomics", "diamond", "diamond"),
    "CompoundClass": ("metabolomics", "triangleDown", "triangle-down"),
    "Activity": ("metabolomics", "star", "star"),
    "Pathogen": ("phenotype", "hexagon", "hexagon"),
    "Crop": ("phenotype", "ellipse", "pentagon"),
    "Pathway": ("context", "box", "cross"),
}
# Columns of the crop page, left to right.
ROUTE_COLUMN = {"Organism": 0, "GeneCluster": 1, "Compound": 2, "Pathogen": 3, "Crop": 4}
SEED = 42                       # vis-network's starting positions: the same every time
MOST_NEIGHBOURS = 150           # an --around page shows at most this many neighbours

# A styling library pyvis's template links to on every page; nothing here uses it.
_UNUSED_LINKS = re.compile(r"<link[^>]*bootstrap[^>]*/?>|<script[^>]*bootstrap[^>]*>\s*</script>",
                           re.DOTALL)
_EMPTY_HEADING = re.compile(r"<center>\s*<h1>\s*</h1>\s*</center>")


def type_colour(node_type: str) -> str:
    return LAYER[TYPE_STYLE.get(node_type, ("context", "dot", "circle"))[0]]


# =============================================================================
# The parts every page shares
# =============================================================================
STYLE = f"""
<style>
  body {{ margin: 0; background: {SURFACE}; color: {INK};
         font-family: system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  .mg-head {{ padding: 16px 20px 8px; max-width: 1100px; }}
  .mg-head h1 {{ font-size: 22px; margin: 0 0 6px; }}
  .mg-head p {{ color: {INK2}; margin: 0 0 8px; line-height: 1.45; max-width: 75ch; }}
  .mg-key {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 6px 0 4px;
            color: {INK2}; font-size: 13px; }}
  .mg-key span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .mg-key i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; }}
  .mg-key b {{ display: inline-block; width: 22px; height: 0; border-top-style: solid; }}
  .mg-foot {{ padding: 8px 20px 20px; color: {MUTED}; font-size: 12px; }}
  table.mg {{ border-collapse: collapse; margin: 8px 20px 16px; font-size: 13px; }}
  table.mg th, table.mg td {{ text-align: left; padding: 4px 10px;
                              border-bottom: 1px solid {HAIR}; }}
  table.mg td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  #mynetwork {{ border: 1px solid {HAIR} !important; }}
  div.vis-tooltip {{ white-space: pre-line !important; font-family: inherit !important; }}
  .card {{ border: 0; }}
</style>
"""


def _key(types: list[str], evidence: list[str] | None = None) -> str:
    """The legend: one chip per node type shown (colour and shape name), then the arrows."""
    chips = [f'<span><i style="background:{type_colour(t)}"></i>{escape(t)} '
             f'({escape(TYPE_STYLE[t][1])})</span>' for t in types if t in TYPE_STYLE]
    for level in evidence or []:
        chips.append(f'<span><b style="border-top-width:{EVIDENCE_WIDTH[level]:.0f}px;'
                     f'border-top-color:{EVIDENCE[level]}"></b>{escape(EVIDENCE_WORD[level])}'
                     f' ({escape(level)})</span>')
    return f'<div class="mg-key">{"".join(chips)}</div>'


def _head(title: str, lede: str, key: str = "") -> str:
    return (f'<div class="mg-head"><h1>{escape(title)}</h1><p>{escape(lede)}</p>{key}</div>')


def _foot(note: str) -> str:
    return f'<div class="mg-foot">{escape(note)}</div>'


def _network(directed: bool = True, height: str = "720px") -> Network:
    """A pyvis network whose page carries vis-network inside it (no internet needed)."""
    return Network(height=height, width="100%", directed=directed, cdn_resources="in_line",
                   bgcolor=SURFACE, font_color=INK)


def _save_network(net: Network, path: Path, title: str, lede: str, key: str, foot: str) -> Path:
    """Write a pyvis page with our heading, legend and footnote, without the unused links."""
    page = net.generate_html(name=path.name)
    page = _UNUSED_LINKS.sub("", page)
    page = _EMPTY_HEADING.sub("", page)
    page = page.replace("<head>", f"<head>\n<title>{escape(title)}</title>", 1)
    page = page.replace("</head>", STYLE + "</head>", 1)
    page = re.sub(r"<body>", "<body>\n" + _head(title, lede, key), page, count=1)
    page = page.replace("</body>", _foot(foot) + "\n</body>", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8", newline="\n")
    return path


def _node_tooltip(graph: nx.DiGraph, node: str, extra: str = "") -> str:
    data = graph.nodes[node]
    lines = [str(data.get("name") or node), f"{data['node_type']}, {node}"]
    if data.get("node_type") == "Protein":
        lines.insert(1, label(graph, node, widest=80))
    if extra:
        lines.append(extra)
    return "\n".join(lines)


def _add_node(net: Network, graph: nx.DiGraph, node: str, **extra: object) -> None:
    kind = str(graph.nodes[node]["node_type"])
    layer, shape, _ = TYPE_STYLE.get(kind, ("context", "dot", "circle"))
    options: dict[str, object] = {
        "label": label(graph, node, widest=34), "title": _node_tooltip(graph, node),
        "color": LAYER[layer], "shape": shape, "size": 16,
        "font": {"color": INK, "size": 14, "face": "system-ui"},
    }
    if shape in ("ellipse", "box"):               # these carry their label inside
        options["font"] = {"color": INK, "size": 14, "face": "system-ui"}
    options.update(extra)
    net.add_node(node, **options)


def _arrow_options(data: dict[str, object]) -> dict[str, object]:
    level = str(data.get("evidence_level"))
    lines = [f"{data.get('edge_type')}: {level}", f"source: {data.get('source') or '-'}"]
    if data.get("citation"):
        lines.append(f"citation: {data.get('citation')}")
    if data.get("confidence") is not None:
        lines.append(f"confidence: {float(data['confidence']):.2f}")   # type: ignore[arg-type]
    return {"title": "\n".join(lines), "color": EVIDENCE.get(level, MUTED),
            "width": EVIDENCE_WIDTH.get(level, 1.5),
            "label": f"{data.get('edge_type')}, {EVIDENCE_WORD.get(level, level)}",
            "font": {"size": 11, "color": INK2, "strokeWidth": 3, "strokeColor": SURFACE,
                     "align": "top"}}


# =============================================================================
# 1. The crop paths
# =============================================================================
def crop_paths_page(graph: nx.DiGraph, by_crop: dict[str, list[EvidencePath]],
                    path: Path, note: str) -> Path:
    """Every crop's evidence paths, in five columns from microbe to crop."""
    net = _network()
    seen_nodes: set[str] = set()
    seen_arrows: set[tuple[str, str]] = set()
    for paths in by_crop.values():
        for p in paths:
            for node in p.nodes:
                if node not in seen_nodes:
                    seen_nodes.add(node)
                    kind = str(graph.nodes[node]["node_type"])
                    _add_node(net, graph, node,
                              level=ROUTE_COLUMN.get("Organism" if kind == "Pathogen"
                                                     and node == p.organism else kind, 0))
            for arrow in p.arrows:
                if (arrow.start, arrow.end) not in seen_arrows:
                    seen_arrows.add((arrow.start, arrow.end))
                    net.add_edge(arrow.start, arrow.end,
                                 **_arrow_options(graph.edges[arrow.start, arrow.end]))
    net.options = {
        "layout": {"randomSeed": SEED,
                   "hierarchical": {"enabled": True, "direction": "LR", "sortMethod": "directed",
                                    "levelSeparation": 300, "nodeSpacing": 70}},
        "physics": {"enabled": False},
        "interaction": {"hover": True, "tooltipDelay": 120, "navigationButtons": False},
        "edges": {"smooth": {"enabled": True, "type": "cubicBezier", "roundness": 0.4},
                  "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}},
    }
    n_paths = sum(len(p) for p in by_crop.values())
    lede = (f"{n_paths} paths to {len(by_crop)} crops, read left to right: a microbe "
            f"harbours a cluster, the cluster produces a compound, the compound inhibits a "
            f"pathogen, the pathogen infects a crop. Hover over a node or an arrow for its "
            f"details; drag to move, scroll to zoom.")
    key = _key(["Organism", "GeneCluster", "Compound", "Pathogen", "Crop"],
               ["curated_experimental", "database_assertion", "curated_literature"])
    return _save_network(net, path, "Evidence paths from crops back to microbes", lede, key, note)


# =============================================================================
# 2. One node and its neighbours
# =============================================================================
def around_page(graph: nx.DiGraph, centre: str, path: Path, note: str) -> tuple[Path, int, int]:
    """
    The centre node and every node one arrow away (either direction). Busy
    nodes have hundreds, so at most MOST_NEIGHBOURS are drawn: the ones with
    the most arrows of their own, ties by identifier. Returns the page, how
    many neighbours there are, and how many were drawn.
    """
    neighbours = sorted(set(graph.predecessors(centre)) | set(graph.successors(centre)))
    drawn = sorted(neighbours, key=lambda n: (-graph.degree(n), n))[:MOST_NEIGHBOURS]
    net = _network()
    _add_node(net, graph, centre, size=30, borderWidth=3)
    for node in sorted(drawn):
        _add_node(net, graph, node)
    for node in sorted(drawn):
        for start, end in ((node, centre), (centre, node)):
            if graph.has_edge(start, end):
                net.add_edge(start, end, **_arrow_options(graph.edges[start, end]))
    net.options = {
        "layout": {"randomSeed": SEED},
        "physics": {"enabled": True, "solver": "forceAtlas2Based",
                    "forceAtlas2Based": {"gravitationalConstant": -60, "springLength": 120},
                    "stabilization": {"enabled": True, "iterations": 400, "fit": True}},
        "interaction": {"hover": True, "tooltipDelay": 120},
        "edges": {"smooth": False, "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}}},
    }
    name = str(graph.nodes[centre].get("name") or centre)
    shown = (f"all {len(neighbours)} neighbours" if len(drawn) == len(neighbours)
             else f"the {len(drawn)} busiest of its {len(neighbours)} neighbours")
    lede = (f"{name} ({graph.nodes[centre]['node_type']}, {centre}) and {shown}: every node one "
            f"arrow away, whichever way the arrow points. Hover for details; drag to move.")
    types = sorted({str(graph.nodes[n]["node_type"]) for n in [centre, *drawn]})
    levels = sorted({str(graph.edges[a, b]["evidence_level"]) for n in drawn
                     for a, b in ((n, centre), (centre, n)) if graph.has_edge(a, b)},
                    key=list(EVIDENCE).index)
    _save_network(net, path, f"Around {name}", lede, _key(types, levels), note)
    return path, len(neighbours), len(drawn)


# =============================================================================
# 3. The communities
# =============================================================================
def communities_page(graph: nx.DiGraph, picked: nx.Graph, communities: list[set[str]],
                     rows: list[dict[str, object]], path: Path, note: str) -> Path:
    """The communities as bubbles (bigger = more members), linked by the arrows between them."""
    number_of = {node: i for i, members in enumerate(communities, start=1) for node in members}
    between: Counter[tuple[int, int]] = Counter()
    for a, b in picked.edges:
        i, j = sorted((number_of[a], number_of[b]))
        if i != j:
            between[(i, j)] += 1
    net = _network(directed=False, height="760px")
    for row in rows:
        number = int(row["community"])                    # type: ignore[arg-type]
        top = [label(graph, n, widest=26) for n in row["top"]]   # type: ignore[union-attr]
        crops = [str(graph.nodes[c]["name"]) for c in row["crops"]]   # type: ignore[union-attr]
        types = ", ".join(f"{k} {v:,}" for k, v in row["types"].items())  # type: ignore[union-attr]
        title = "\n".join([f"Community {number}: {row['size']:,} nodes", types,
                           "busiest: " + "; ".join(top)]
                          + ([f"crops: {', '.join(crops)}"] if crops else []))
        text = f"{number}. {top[0]}" + (f" + {', '.join(crops)}" if crops else "")
        net.add_node(number, label=text, title=title, value=int(row["size"]),   # type: ignore[arg-type]
                     shape="dot", color=LAYER["phenotype"] if crops else LAYER["genomics"],
                     font={"color": INK, "size": 14, "face": "system-ui"})
    for (i, j), count in sorted(between.items()):
        net.add_edge(i, j, value=count, title=f"{count:,} arrows between {i} and {j}",
                     color={"color": HAIR, "highlight": INK2, "hover": INK2})
    net.options = {
        "layout": {"randomSeed": SEED},
        "nodes": {"scaling": {"min": 8, "max": 60}},
        "edges": {"scaling": {"min": 1, "max": 8}, "smooth": False},
        "physics": {"enabled": True, "solver": "forceAtlas2Based",
                    "forceAtlas2Based": {"gravitationalConstant": -120, "springLength": 160},
                    "stabilization": {"enabled": True, "iterations": 600, "fit": True}},
        "interaction": {"hover": True, "tooltipDelay": 120},
    }
    q = nx.community.modularity(picked, communities)
    lede = (f"{len(communities)} communities found by the Louvain method in the graph "
            f"without proteins (modularity {q:.3f}). Each bubble is one community, sized by "
            f"how many nodes it holds and named after its busiest member; yellow bubbles hold "
            f"a crop. Lines are the arrows between two communities. Hover for details.")
    key = (f'<div class="mg-key"><span><i style="background:{LAYER["genomics"]}"></i>'
           f'community</span><span><i style="background:{LAYER["phenotype"]}"></i>'
           f'community holding a crop</span></div>')
    return _save_network(net, path, "Communities in the graph", lede, key, note)


# =============================================================================
# 4. Hubs against bridges (plotly)
# =============================================================================
def hubs_page(graph: nx.DiGraph, picked: nx.Graph, between: dict[str, float],
              path: Path, note: str, top: int = 15) -> Path:
    """
    Degree (whole graph) against betweenness (production layer), one marker per
    node of the layer, plus the top bridges as bars and as a table.
    """
    figure = go.Figure()
    order = ["Organism", "GeneCluster", "Compound", "Pathogen", "Crop"]
    for kind in order:
        nodes = sorted(n for n in picked if graph.nodes[n]["node_type"] == kind)
        if not nodes:
            continue
        figure.add_trace(go.Scatter(
            x=[graph.degree(n) for n in nodes], y=[between[n] for n in nodes],
            mode="markers", name=kind,
            marker={"symbol": TYPE_STYLE[kind][2], "size": 9, "color": type_colour(kind),
                    "line": {"width": 1.5, "color": SURFACE}, "opacity": 0.9},
            text=[escape(label(graph, n)) for n in nodes],
            hovertemplate="<b>%{y:.5f}</b> betweenness<br>%{x} arrows<br>%{text}"
                          f"<extra>{escape(kind)}</extra>"))
    figure.update_layout(
        title={"text": "Hubs and bridges: arrows (whole graph) against betweenness "
                       "(production layer)", "font": {"size": 16}},
        xaxis={"title": "arrows touching the node (degree), log scale", "type": "log",
               "gridcolor": HAIR, "zeroline": False,
               "tickvals": [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]},
        yaxis={"title": "betweenness on the production layer", "gridcolor": HAIR,
               "zeroline": False, "rangemode": "tozero"},
        legend={"orientation": "h", "y": -0.18}, plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font={"family": "system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif",
              "color": INK2}, height=560, margin={"l": 70, "r": 20, "t": 60, "b": 90})

    best = sorted(between.items(), key=lambda nv: (-nv[1], nv[0]))[:top]
    bars = go.Figure(go.Bar(
        x=[v for _, v in reversed(best)],
        y=[escape(f"{label(graph, n, widest=40)} ({graph.nodes[n]['node_type']})")
           for n, _ in reversed(best)],
        orientation="h", marker={"color": LAYER["genomics"]}, width=0.6,
        hovertemplate="<b>%{x:.5f}</b><br>%{y}<extra></extra>"))
    bars.update_layout(
        title={"text": f"The {top} biggest bridges of the production layer", "font": {"size": 16}},
        xaxis={"title": "betweenness", "gridcolor": HAIR, "zeroline": False},
        yaxis={"automargin": True}, plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font={"family": "system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif",
              "color": INK2}, height=40 + 32 * len(best), margin={"l": 20, "r": 20, "t": 60, "b": 50})

    table = ["<table class='mg'><tr><th>#</th><th>node</th><th>type</th>"
             "<th>betweenness</th><th>arrows</th></tr>"]
    for i, (n, v) in enumerate(best, start=1):
        table.append(f"<tr><td class='num'>{i}</td><td>{escape(label(graph, n))}</td>"
                     f"<td>{escape(str(graph.nodes[n]['node_type']))}</td>"
                     f"<td class='num'>{v:.5f}</td><td class='num'>{graph.degree(n):,}</td></tr>")
    table.append("</table>")

    config = {"displaylogo": False, "responsive": True}
    scatter_html = pio.to_html(figure, full_html=False, include_plotlyjs=False,
                               div_id="hubs", config=config)
    bars_html = pio.to_html(bars, full_html=False, include_plotlyjs=False,
                            div_id="bridges", config=config)
    lede = ("Each marker is one node of the production layer (the HARBORS, PRODUCES, INHIBITS "
            "and INFECTS arrows). Further right: more arrows in the whole graph, a hub. "
            "Higher: on more shortest routes between other nodes of the layer, a bridge. "
            "Hover for names; drag to zoom, double-click to zoom out.")
    page = ("<!doctype html>\n<html lang='en'>\n<head>\n<meta charset='utf-8'>\n"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            "<title>Hubs and bridges</title>\n" + STYLE
            + "<script src='plotly.min.js'></script>\n</head>\n<body>\n"
            + _head("Hubs and bridges", lede) + scatter_html + bars_html
            + "<p style='margin:0 20px;color:" + INK2 + "'>The same top bridges as a table:</p>"
            + "".join(table) + _foot(note) + "\n</body>\n</html>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8", newline="\n")
    # Written every time, so it always matches the plotly that drew the page.
    (path.parent / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8", newline="\n")
    return path


def slug(text: str) -> str:
    """A safe file-name part for a node: 'mg.compound:surfactin' -> 'mg_compound_surfactin'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()[:60] or "node"
