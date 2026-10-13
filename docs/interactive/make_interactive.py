"""
MicrobeGraph, the interactive teaching pages.

WHAT THIS SCRIPT DOES
    Writes four self-contained web pages into docs/interactive/:

        ontology_explorer.html    the rulebook: hover a node type or an arrow
        evidence_chain.html       one real chain, with evidence filters
        roadmap_timeline.html     every phase, its hours and its status
        resolution_cases.html     seven real cases the resolver decided, clue by
                                  clue (Phase 4b and its follow-ups)

        python docs/interactive/make_interactive.py

    Run it from the repository root with .venv active.

HOW TO OPEN THE PAGES
    Double-click the .html file, or drag it into any web browser. Each page
    is ONE file with everything inside it, so you need no internet
    connection, no server and nothing installed. (GitHub shows .html files
    as source code, which is why you open them locally.)

WHY THEY ARE GENERATED FROM THE PROJECT'S OWN FILES
    * The ten arrow types come from src/microbegraph/ontology.py, the same
      list the validation code enforces. If the rulebook changes, re-running
      this script brings the explorer up to date; a teaching page that
      disagreed with the code would be worse than having none.
    * Colours, pictographs and node descriptions come from
      docs/img/make_illustrations.py, so the static and interactive figures
      always match.
    * Phases, hours and status come from docs/phases.csv.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent              # docs/interactive/
DOCS = HERE.parent
sys.path.insert(0, str(DOCS / "img"))               # to share make_illustrations.py

import make_illustrations as mi  # noqa: E402

from microbegraph.ontology import EDGE_TYPES  # noqa: E402

# Dark-mode steps of the same hues (stepped for a dark surface, not inverted).
DARK = {"#2a78d6": "#3987e5", "#eb6834": "#d95926", "#1baf7a": "#199e70",
        "#eda100": "#c98500", "#898781": "#898781", "#184f95": "#86b6ef",
        "#6da7ec": "#5598e7"}

NODE_TEXT = {
    "Organism": ("A microbe (a bacterium, fungus or yeast) that makes something interesting.",
                 "Phase 1 (MIBiG); its family tree arrives in Phase 2 (NCBI Taxonomy)"),
    "GeneCluster": ("A run of neighbouring genes that together build one specialised molecule.",
                    "Phase 1 (MIBiG)"),
    "Protein": ("An enzyme encoded by the cluster: the machine that performs one chemical step.",
                "Phase 3 (MIBiG's gene records), every cluster's from Phase 3b (MIBiG's "
                "protein file); joined to its UniProt entry in Phase 4"),
    "Compound": ("The molecule the cluster makes.",
                 "Phase 1 (MIBiG); PubChem identities in Phase 2, joined to MIBiG's in Phase 4 "
                 "where the name or formula confirms the number"),
    "CompoundClass": ("A family of chemically related molecules.",
                      "Phase 1 (MIBiG, when it gives one)"),
    "Activity": ("What a molecule has been seen to do: antibacterial, antifungal, surfactant...",
                 "Phase 1 (MIBiG)"),
    "Pathogen": ("An organism that causes a plant disease. A kind of Organism (from Phase 4), so "
                 "it may also harbour gene clusters and has a family tree.",
                 "Phase 2 (the cited curated bridge; name, lineage and group from NCBI Taxonomy)"),
    "Crop": ("A cultivated plant that the disease harms.", "Phase 2 (the cited curated bridge)"),
    "Pathway": ("A chain of biochemical reactions the molecule takes part in.",
                "Phase 2 (KEGG; only the maps our compounds appear on)"),
}

EDGE_TEXT = {
    "HARBORS": ("The organism carries the gene cluster in its DNA.", "MIBiG, Phase 1"),
    "ENCODES": ("The cluster's genes are the instructions for the protein.",
                "MIBiG's gene records (Phase 3) and protein file (Phase 3b)"),
    "CATALYZES": ("The protein performs a step in making the molecule.",
                  "MIBiG's gene records, Phase 3 (only genes whose job builds the molecule)"),
    "PRODUCES": ("The cluster is known to make the molecule: the direct shortcut.", "MIBiG, Phase 1"),
    "BELONGS_TO": ("The molecule is a member of a chemical family.", "MIBiG, Phase 1"),
    "HAS_ACTIVITY": ("The molecule has been seen to do this.", "MIBiG, Phase 1"),
    "INHIBITS": ("The molecule suppresses the pathogen.",
                 "the cited curated bridge, Phase 2 (always with a citation)"),
    "INFECTS": ("The pathogen causes disease in the crop.", "the cited curated bridge, Phase 2"),
    "PARTICIPATES_IN": ("The molecule takes part in this pathway.", "KEGG, Phase 2"),
    "MEMBER_OF": ("The organism belongs to a larger group: strain, species, genus...",
                  "NCBI Taxonomy, Phase 2"),
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --plane: #f3f2ee; --ink: #0b0b0b; --ink2: #52514e;
  --muted: #898781; --hair: #e1e0d9; --base: #c3c2b7; --focus: #2a78d6;
{light_vars}
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --plane: #242422; --ink: #f0efec; --ink2: #c3c2b7;
    --muted: #898781; --hair: #2c2c2a; --base: #383835; --focus: #3987e5;
{dark_vars}
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --plane: #242422; --ink: #f0efec; --ink2: #c3c2b7;
  --muted: #898781; --hair: #2c2c2a; --base: #383835; --focus: #3987e5;
{dark_vars}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink);
       font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }}
.lede {{ color: var(--ink2); margin: 0 0 16px; max-width: 70ch; }}
.card {{ background: var(--surface); border: 1px solid var(--hair); border-radius: 14px; padding: 16px; }}
.figure {{ overflow-x: auto; }}
svg {{ display: block; width: 100%; height: auto; min-width: 720px; }}
svg text {{ fill: var(--ink); }}
.mono {{ font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }}
.muted {{ color: var(--muted); }}
.panel {{ margin-top: 12px; min-height: 120px; }}
.panel h2 {{ font-size: 18px; margin: 0 0 4px; }}
.panel p {{ margin: 4px 0; }}
.hot {{ cursor: pointer; }}
.hot:focus {{ outline: none; }}
.hot:focus-visible .ring, .hot:focus-visible .hit {{ stroke: var(--focus); stroke-width: 4; }}
.dim {{ opacity: .18; transition: opacity .15s; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--hair); vertical-align: top; }}
th {{ color: var(--ink2); font-weight: 600; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
details {{ margin-top: 16px; }}
summary {{ cursor: pointer; color: var(--ink2); font-weight: 600; }}
.chip {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--hair);
        border-radius: 999px; padding: 2px 10px; margin: 2px 4px 2px 0; font-size: 13px;
        background: var(--surface); }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 0 0 12px; }}
.controls label {{ display: inline-flex; align-items: center; gap: 6px; font-size: 14px; }}
.tooltip {{ position: fixed; pointer-events: none; background: var(--surface); color: var(--ink);
           border: 1px solid var(--hair); border-radius: 10px; padding: 10px 12px; font-size: 13px;
           max-width: 320px; box-shadow: 0 6px 24px rgba(0,0,0,.12); display: none; z-index: 5; }}
footer {{ margin-top: 20px; color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
{body}
<footer>Built by <span class="mono">docs/interactive/make_interactive.py</span> from the
project's own files. MicrobeGraph · MIT licence.</footer>
</main>
<script>
{script}
</script>
</body>
</html>
"""


def page(title: str, body: str, script: str, colours: dict[str, str]) -> str:
    light = "\n".join(f"  --{k}: {v};" for k, v in colours.items())
    dark = "\n".join(f"    --{k}: {DARK.get(v, v)};" for k, v in colours.items())
    return PAGE.format(title=escape(title), body=body, script=script,
                       light_vars=light, dark_vars=dark)


def write(name: str, html: str) -> None:
    (HERE / name).write_text(html, encoding="utf-8")
    print(f"  wrote docs/interactive/{name}")


# =============================================================================
# 1. The ontology explorer
# =============================================================================
def ontology_explorer() -> str:
    pos = {"Organism": (110, 250), "GeneCluster": (320, 250), "Protein": (530, 130),
           "Compound": (740, 250), "Pathogen": (950, 250), "Crop": (1120, 250),
           "CompoundClass": (620, 420), "Activity": (860, 420), "Pathway": (930, 110)}
    r = 38
    shapes: list[str] = []
    for edge, (a, b) in EDGE_TYPES.items():
        if a == b:   # MEMBER_OF: a loop over the node
            x, y = pos[a]
            d = f"M{x - 22} {y - 32} C{x - 70} {y - 115} {x + 70} {y - 115} {x + 22} {y - 32}"
            mx, my = x, y - 100
        else:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            dist = math.hypot(x2 - x1, y2 - y1)
            ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
            sx, sy, ex, ey = x1 + ux * (r + 4), y1 + uy * (r + 4), x2 - ux * (r + 9), y2 - uy * (r + 9)
            d = f"M{sx:.1f} {sy:.1f} L{ex:.1f} {ey:.1f}"
            mx, my = (sx + ex) / 2, (sy + ey) / 2
        w = len(edge) * 7.4 + 14
        shapes.append(
            f'<g class="hot edge" tabindex="0" role="button" data-edge="{edge}" data-from="{a}" '
            f'data-to="{b}" aria-label="{edge}: {a} to {b}">'
            f'<path class="hit" d="{d}" stroke="transparent" stroke-width="16" fill="none"/>'
            f'<path d="{d}" stroke="var(--ink2)" stroke-width="2" fill="none" marker-end="url(#ah)"/>'
            f'<rect x="{mx - w / 2:.1f}" y="{my - 11:.1f}" width="{w:.1f}" height="21" rx="6" '
            f'fill="var(--surface)"/>'
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" font-size="11.5" '
            f'font-weight="600" class="mono" style="fill:var(--ink2)">{edge}</text></g>')
    for kind, (x, y) in pos.items():
        layer = mi.NODE_INFO[kind][0]
        shapes.append(
            f'<g class="hot node" tabindex="0" role="button" data-node="{kind}" aria-label="{kind}">'
            f'<circle class="ring" cx="{x}" cy="{y}" r="{r}" fill="var(--surface)" '
            f'stroke="var(--{layer})" stroke-width="3"/>'
            f'{mi.icon(kind, x, y, size=r * 1.4, color=mi.LAYER[layer])}'
            f'<text x="{x}" y="{y + r + 20}" text-anchor="middle" font-size="14" font-weight="600" '
            f'paint-order="stroke" stroke="var(--surface)" stroke-width="5">{kind}</text></g>')
    svg = (f'<svg viewBox="0 0 1230 500" role="group" aria-label="Ontology map">'
           f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
           f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" '
           f'style="fill:var(--ink2)"/></marker></defs>{"".join(shapes)}</svg>')

    nodes = {k: {"layer": v[0], "curie": v[1], "parallel": v[2], "what": NODE_TEXT[k][0],
                 "arrives": NODE_TEXT[k][1]} for k, v in mi.NODE_INFO.items()}
    edges = {k: {"from": a, "to": b, "what": EDGE_TEXT[k][0], "source": EDGE_TEXT[k][1]}
             for k, (a, b) in EDGE_TYPES.items()}
    legend = "".join(f'<span class="chip"><span class="dot" style="background:var(--{name})"></span>'
                     f"{name}</span>" for name in mi.LAYER)
    rows_n = "".join(f"<tr><td>{k}</td><td class='mono'>{escape(v['curie'])}</td><td>{escape(v['what'])}</td>"
                     f"<td>{escape(v['arrives'])}</td></tr>" for k, v in nodes.items())
    rows_e = "".join(f"<tr><td class='mono'>{k}</td><td>{v['from']} &rarr; {v['to']}</td>"
                     f"<td>{escape(v['what'])}</td><td>{escape(v['source'])}</td></tr>"
                     for k, v in edges.items())
    body = f"""
<h1>The MicrobeGraph ontology, explorable</h1>
<p class="lede">Nine kinds of dot, ten kinds of arrow. Hover, tap, or press Tab to move through
them: each one explains itself, says how it is identified, and which phase brings it into the graph.
The arrows are read straight from <span class="mono">src/microbegraph/ontology.py</span>.</p>
<div class="card figure">{svg}</div>
<div>{legend}</div>
<div class="card panel" id="panel" aria-live="polite">
  <h2>Pick something</h2><p class="muted">Hover or focus a node type or an arrow.</p></div>
<details><summary>All of it as a table</summary>
<table><tr><th>Node type</th><th>Identifier example</th><th>What it is</th><th>Arrives in</th></tr>{rows_n}</table>
<br><table><tr><th>Edge type</th><th>Connects</th><th>Meaning</th><th>Comes from</th></tr>{rows_e}</table>
</details>"""
    script = f"""
const NODES = {json.dumps(nodes)};
const EDGES = {json.dumps(edges)};
const panel = document.getElementById('panel');
const all = [...document.querySelectorAll('.hot')];
function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}
function focusOn(el) {{
  const node = el.dataset.node, edge = el.dataset.edge;
  all.forEach(g => {{
    let keep = g === el;
    if (node) keep = keep || g.dataset.from === node || g.dataset.to === node ||
      (g.dataset.node && Object.values(EDGES).some(e => (e.from === node && e.to === g.dataset.node) ||
                                                      (e.to === node && e.from === g.dataset.node)));
    if (edge) keep = keep || g.dataset.node === el.dataset.from || g.dataset.node === el.dataset.to;
    g.classList.toggle('dim', !keep);
  }});
  if (node) {{
    const n = NODES[node];
    panel.innerHTML = `<h2>${{esc(node)}}</h2><p>${{esc(n.what)}}</p>
      <p><b>Identifier:</b> <span class="mono">${{esc(n.curie)}}</span> &middot; <b>Think of it as:</b> ${{esc(n.parallel)}}</p>
      <p><b>Layer:</b> ${{esc(n.layer)}} &middot; <b>Arrives in:</b> ${{esc(n.arrives)}}</p>`;
  }} else {{
    const e = EDGES[edge];
    panel.innerHTML = `<h2 class="mono">${{esc(edge)}}</h2><p>${{esc(e.what)}}</p>
      <p><b>Allowed only as:</b> ${{esc(e.from)}} &rarr; ${{esc(e.to)}} (anything else is rejected, rule 8)</p>
      <p><b>Comes from:</b> ${{esc(e.source)}}</p>`;
  }}
}}
function clear() {{ all.forEach(g => g.classList.remove('dim')); }}
all.forEach(g => {{
  g.addEventListener('mouseenter', () => focusOn(g));
  g.addEventListener('focus', () => focusOn(g));
  g.addEventListener('click', () => focusOn(g));
  g.addEventListener('mouseleave', clear);
  g.addEventListener('blur', clear);
}});
"""
    return page("MicrobeGraph ontology explorer", body, script, mi.LAYER)


# =============================================================================
# 2. One evidence chain, with filters
# =============================================================================
CHAIN_NODES = [
    ("ncbitaxon:326423", "Organism", "Bacillus velezensis FZB42", 110, 150),
    ("mibig:BGC0000433", "GeneCluster", "surfactin BGC", 340, 150),
    ("uniprot:Q70KJ7", "Protein", "srfAA (UniProt Q70KJ7)", 470, 370),
    ("mg.compound:surfactin", "Compound", "surfactin", 600, 150),
    ("mg.activity:antibacterial", "Activity", "antibacterial", 760, 380),
    ("mg.activity:surfactant", "Activity", "surfactant", 980, 380),
    ("ncbitaxon:40559", "Pathogen", "Botrytis cinerea (grey mould)", 840, 150),
    ("mg.crop:jujube", "Crop", "jujube", 1080, 150),
]
CHAIN_EDGES = [
    ("ncbitaxon:326423", "mibig:BGC0000433", "HARBORS", "curated_experimental", "mibig",
     "BGC0000433", "pubmed:14762003", "0.50", True),
    ("mibig:BGC0000433", "mg.compound:surfactin", "PRODUCES", "curated_experimental", "mibig",
     "BGC0000433", "pubmed:14762003", "0.50", True),
    ("mibig:BGC0000433", "uniprot:Q70KJ7", "ENCODES", "database_assertion", "mibig",
     "BGC0000433", "pubmed:14762003", "0.50", False),
    ("uniprot:Q70KJ7", "mg.compound:surfactin", "CATALYZES", "curated_experimental", "mibig",
     "BGC0000433", "pubmed:14762003", "0.50", False),
    ("mg.compound:surfactin", "mg.activity:antibacterial", "HAS_ACTIVITY", "database_assertion",
     "mibig", "BGC0000433", "", "0.50", False),
    ("mg.compound:surfactin", "mg.activity:surfactant", "HAS_ACTIVITY", "database_assertion",
     "mibig", "BGC0000433", "", "0.50", False),
    ("mg.compound:surfactin", "ncbitaxon:40559", "INHIBITS", "curated_literature", "curation",
     "compound_pathogen_crop.csv", "doi:10.1186/s13568-023-01543-w", "0.90", True),
    ("ncbitaxon:40559", "mg.crop:jujube", "INFECTS", "curated_literature", "curation",
     "compound_pathogen_crop.csv", "doi:10.1186/s13568-023-01543-w", "0.90", True),
]
LEVEL_STYLE = {"curated_experimental": (4.5, ""), "database_assertion": (3, ""),
               "curated_literature": (2.2, ""), "inferred": (2, "7 6")}


def evidence_chain() -> str:
    where = {n[0]: (n[3], n[4]) for n in CHAIN_NODES}
    r = 38
    shapes = []
    for i, (a, b, verb, level, *_rest) in enumerate(CHAIN_EDGES):
        (x1, y1), (x2, y2) = where[a], where[b]
        dist = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
        sx, sy, ex, ey = x1 + ux * (r + 4), y1 + uy * (r + 4), x2 - ux * (r + 10), y2 - uy * (r + 10)
        width, dash = LEVEL_STYLE[level]
        along = 0.5 if y1 == y2 else 0.62           # diagonal arrows: label nearer the end
        mx, my = sx + (ex - sx) * along, sy + (ey - sy) * along + (0 if y1 == y2 else 18)
        label_w = len(verb) * 7.4 + 14
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        shapes.append(
            f'<g class="hot edge" tabindex="0" role="button" data-i="{i}" data-level="{level}" '
            f'aria-label="{verb}, {level}">'
            f'<path class="hit" d="M{sx:.1f} {sy:.1f} L{ex:.1f} {ey:.1f}" stroke="transparent" stroke-width="18"/>'
            f'<path d="M{sx:.1f} {sy:.1f} L{ex:.1f} {ey:.1f}" stroke="var(--{level})" stroke-width="{width}" '
            f'stroke-linecap="round"{dash_attr} marker-end="url(#ah-{level})"/>'
            f'<rect x="{mx - label_w / 2:.1f}" y="{my - 24:.1f}" width="{label_w:.1f}" height="20" rx="6" '
            f'fill="var(--surface)"/>'
            f'<text x="{mx:.1f}" y="{my - 10:.1f}" text-anchor="middle" font-size="11.5" font-weight="600" '
            f'class="mono" style="fill:var(--ink2)">{verb}</text></g>')
    for node_id, kind, name, x, y in CHAIN_NODES:
        layer = mi.NODE_INFO[kind][0]
        shapes.append(
            f'<g class="node" data-id="{node_id}"><circle cx="{x}" cy="{y}" r="{r}" fill="var(--surface)" '
            f'stroke="var(--{layer})" stroke-width="3"/>{mi.icon(kind, x, y, size=r * 1.4, color=mi.LAYER[layer])}'
            f'<text x="{x}" y="{y + r + 20}" text-anchor="middle" font-size="13.5" font-weight="600" '
            f'paint-order="stroke" stroke="var(--surface)" stroke-width="5">{escape(name)}</text>'
            f'<text x="{x}" y="{y + r + 37}" text-anchor="middle" font-size="11" class="mono" '
            f'paint-order="stroke" stroke="var(--surface)" stroke-width="5" '
            f'style="fill:var(--muted)">{escape(node_id)}</text></g>')
    markers = "".join(
        f'<marker id="ah-{lvl}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" '
        f'markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" '
        f'style="fill:var(--{lvl})"/></marker>' for lvl in mi.EVIDENCE)
    svg = (f'<svg viewBox="0 0 1180 480" role="group" aria-label="Evidence chain">'
           f"<defs>{markers}</defs>{''.join(shapes)}</svg>")
    boxes = "".join(
        f'<label><input type="checkbox" checked data-filter="{lvl}"> '
        f'<span class="dot" style="background:var(--{lvl})"></span><span class="mono">{lvl}</span></label>'
        for lvl in mi.EVIDENCE)
    rows = "".join(
        f"<tr><td class='mono'>{a}</td><td class='mono'>{v}</td><td class='mono'>{b}</td>"
        f"<td class='mono'>{lvl}</td><td>{src}</td><td class='mono'>{escape(rec)}</td>"
        f"<td>{escape(cit) or '<span class=muted>none</span>'}</td><td class='num'>{conf}</td></tr>"
        for a, b, v, lvl, src, rec, cit, conf, _ in CHAIN_EDGES)
    data = [dict(zip(["from", "to", "verb", "level", "source", "record", "citation", "confidence",
                      "on_path"], e)) for e in CHAIN_EDGES]
    body = f"""
<h1>One chain, every arrow with its evidence</h1>
<p class="lede">From a soil bacterium to grey mould on jujube fruit, with one of the enzymes that makes the
molecule on the way. Hover or focus an arrow to see where it came from. Untick an evidence level to
hide those arrows, and watch what still connects: this is the "show me only what is actually known"
filter the app gets in Phase 8.</p>
<div class="controls" role="group" aria-label="Evidence filters">{boxes}</div>
<div class="card figure">{svg}</div>
<div class="card panel" id="panel" aria-live="polite"></div>
<details open><summary>The same rows as a table</summary>
<table><tr><th>source_id</th><th>edge_type</th><th>target_id</th><th>evidence_level</th><th>source</th>
<th>source_record_id</th><th>citation</th><th class="num">confidence</th></tr>{rows}</table>
<p class="muted">The MIBiG rows are what the MIBiG adapter writes from the public entry BGC0000433 on
its own, which MIBiG grades "questionable" (hence confidence 0.50). Other surfactin entries in the
full release can add their record numbers and citations to the same arrows. ENCODES and CATALYZES
come from the entry's gene record for srfAA (Phase 3): a knock-out showed that srfAA builds the
molecule's backbone, so its CATALYZES arrow is curated_experimental, while ENCODES only states that
the gene is in the cluster (from Phase 3b, MIBiG's protein file lists it too, with the cluster's 22
other proteins). UniProt's ID mapping says MIBiG's protein number CAE02630.1 is the entry Q70KJ7,
Surfactin synthetase A, and since Phase 4 the two records are one node, uniprot:Q70KJ7, still named
srfAA. The protein route sits beside the PRODUCES shortcut, so hiding it never breaks the
chain. The two curation rows come
from one row of the cited bridge (Phase 2): Xiao et al. (2023) found that purified surfactin inhibited
<i>Botrytis cinerea</i> and reduced grey mould on harvested winter jujube. The bridge refuses any row
without a citation.</p>
</details>"""
    script = f"""
const EDGES = {json.dumps(data)};
const RANK = {json.dumps(list(mi.EVIDENCE))};
const panel = document.getElementById('panel');
const groups = [...document.querySelectorAll('.edge')];
function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}
function summary() {{
  const visible = EDGES.filter((e, i) => e.on_path && !groups[i].classList.contains('dim'));
  const pathLen = EDGES.filter(e => e.on_path).length;
  if (visible.length < pathLen) {{
    panel.innerHTML = `<h2>The chain is broken</h2><p>With the hidden levels removed, nothing connects
      the bacterium to the jujube any more. That gap is information: it shows exactly which kind of
      evidence the connection depends on.</p>`;
    return;
  }}
  const weakest = visible.reduce((w, e) => RANK.indexOf(e.level) > RANK.indexOf(w.level) ? e : w);
  panel.innerHTML = `<h2>Organism to crop: connected</h2><p>The weakest link on the path is
    <span class="mono">${{esc(weakest.verb)}}</span> at <span class="mono">${{esc(weakest.level)}}</span>.
    A chain is only as strong as its weakest arrow, so that is the strength of the whole claim.</p>`;
}}
function show(i) {{
  const e = EDGES[i];
  panel.innerHTML = `<h2 class="mono">${{esc(e.verb)}}</h2>
    <p><span class="mono">${{esc(e.from)}}</span> &rarr; <span class="mono">${{esc(e.to)}}</span></p>
    <p><b>Evidence:</b> <span class="mono">${{esc(e.level)}}</span> &middot; <b>Confidence:</b> ${{esc(e.confidence)}}
    &middot; <b>Source:</b> ${{esc(e.source)}}, record <span class="mono">${{esc(e.record)}}</span></p>
    <p><b>Citation:</b> ${{e.citation ? esc(e.citation) : '<span class="muted">none given by the source</span>'}}</p>`;
}}
groups.forEach((g, i) => {{
  g.addEventListener('mouseenter', () => show(i));
  g.addEventListener('focus', () => show(i));
  g.addEventListener('click', () => show(i));
  g.addEventListener('mouseleave', summary);
  g.addEventListener('blur', summary);
}});
document.querySelectorAll('[data-filter]').forEach(box => box.addEventListener('change', () => {{
  groups.forEach(g => {{ if (g.dataset.level === box.dataset.filter) g.classList.toggle('dim', !box.checked); }});
  summary();
}}));
summary();
"""
    return page("MicrobeGraph evidence chain", body, script, {**mi.LAYER, **mi.EVIDENCE})


# =============================================================================
# 3. The roadmap timeline
# =============================================================================
def roadmap_timeline() -> str:
    phases = list(csv.DictReader((DOCS / "phases.csv").open(encoding="utf-8")))
    left, top, row_h, scale = 230, 40, 30, 4.2           # scale: pixels per hour
    shapes, cursor = [], 0.0
    data = []
    for i, p in enumerate(phases):
        lo, hi = int(p["effort_low"]), int(p["effort_high"])
        mid = (lo + hi) / 2
        optional = p["optional"] == "yes"
        start = cursor
        y = top + i * row_h
        colour = f"var(--r{p['release'].replace('.', '')})"
        dash = ' stroke-dasharray="5 4"' if optional else ""
        fill = "var(--surface)" if optional else colour
        done = p["status"] == "done"
        shapes.append(
            f'<g class="hot bar" tabindex="0" role="button" data-i="{i}" aria-label="Phase {p["phase"]}">'
            f'<rect x="0" y="{y - 2}" width="{left + (cursor + hi) * scale + 120:.1f}" height="{row_h}" '
            f'fill="transparent"/>'
            f'<text x="{left - 12}" y="{y + 17}" text-anchor="end" font-size="13">'
            f'{"&#10003; " if done else ""}Phase {p["phase"]}: {escape(p["short"])}</text>'
            f'<rect x="{left + start * scale:.1f}" y="{y + 4}" width="{mid * scale:.1f}" height="{row_h - 10}" '
            f'rx="4" fill="{fill}" stroke="{colour}" stroke-width="1.5"{dash}/>'
            f'<line x1="{left + (start + lo) * scale:.1f}" x2="{left + (start + hi) * scale:.1f}" '
            f'y1="{y + row_h / 2}" y2="{y + row_h / 2}" stroke="var(--ink2)" stroke-width="1.5"/>'
            f'</g>')
        data.append({**p, "start": start})
        if not optional:
            cursor += mid
    total = cursor
    grid = []
    for h in range(0, int(total) + 21, 20):
        x = left + h * scale
        grid.append(f'<line x1="{x}" x2="{x}" y1="{top - 8}" y2="{top + len(phases) * row_h}" '
                    f'stroke="var(--hair)"/><text x="{x}" y="{top - 14}" text-anchor="middle" '
                    f'font-size="11" style="fill:var(--muted)">{h} h</text>')
    width = left + (total + 30) * scale
    svg = (f'<svg viewBox="0 0 {width:.0f} {top + len(phases) * row_h + 10}" role="group" '
           f'aria-label="Roadmap timeline">{"".join(grid)}{"".join(shapes)}</svg>')
    legend = "".join(
        f'<span class="chip"><span class="dot" style="background:var(--r{k.replace(".", "")})"></span>{label}</span>'
        for k, label in [("design", "Phase 0, design"), ("1.0", "Release 1.0, the science"),
                         ("2.0", "Release 2.0, the platform"), ("3.0", "Release 3.0, the product")])
    rows = "".join(
        f"<tr><td>{p['phase']}</td><td>{escape(p['title'])}</td><td>{p['release']}</td>"
        f"<td class='num'>{p['effort_low']}-{p['effort_high']}</td>"
        f"<td>{'built' if p['status'] == 'done' else 'planned'}{' (optional)' if p['optional'] == 'yes' else ''}</td>"
        f"<td>{escape(p['adds'])}</td></tr>" for p in phases)
    colours = {"rdesign": mi.RELEASE["design"], "r10": mi.RELEASE["1.0"], "r20": mi.RELEASE["2.0"],
               "r30": mi.RELEASE["3.0"]}
    body = f"""
<h1>The roadmap, phase by phase</h1>
<p class="lede">Each bar is one phase, placed after the ones before it; its length is the middle of the
hour estimate, and the thin line shows the range. Dashed bars are optional and do not push the rest
back. A tick marks what is built. Hover or focus a row for what it adds.</p>
<div>{legend}</div>
<div class="card figure">{svg}</div>
<div class="card panel" id="panel" aria-live="polite"><p class="muted">Hover or focus a phase.</p></div>
<details><summary>The same plan as a table</summary>
<table><tr><th>Phase</th><th>Title</th><th>Release</th><th class="num">Hours</th><th>Status</th><th>Adds</th></tr>{rows}</table>
</details>"""
    script = f"""
const PHASES = {json.dumps(data)};
const panel = document.getElementById('panel');
function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}
document.querySelectorAll('.bar').forEach(g => {{
  const show = () => {{
    const p = PHASES[g.dataset.i];
    panel.innerHTML = `<h2>Phase ${{esc(p.phase)}}: ${{esc(p.title)}}</h2>
      <p><b>Release:</b> ${{esc(p.release)}} &middot; <b>Hours:</b> ${{esc(p.effort_low)}}-${{esc(p.effort_high)}}
      &middot; <b>Status:</b> ${{p.status === 'done' ? 'built and tested' : 'planned'}}${{p.optional === 'yes' ? ' (optional)' : ''}}</p>
      <p><b>Adds:</b> ${{esc(p.adds)}}</p><p><b>Tutorial:</b> <span class="mono">docs/${{esc(p.doc)}}</span></p>`;
  }};
  g.addEventListener('mouseenter', show); g.addEventListener('focus', show); g.addEventListener('click', show);
}});
"""
    return page("MicrobeGraph roadmap timeline", body, script, colours)


# =============================================================================
# 4. Real resolution cases, clue by clue (Phase 4b)
# =============================================================================
# Every value below is copied from the real tables and the real ledger of the
# build of 2026-10-12 (docs/06b-closing-the-gaps.md, Step 10). The grounds are
# the ledger's own sentences.
CASES = [
    {
        "id": "mib", "kind": "Compound", "title": "2-methylisoborneol",
        "hook": "the earthy smell in tap water, and a bromine compound's number",
        "sources": [
            ["MIBiG BGC0000657", "pubchem:9237955", "formula C15H16BrN3O4S"],
            ["MIBiG BGC0000658", "pubchem:16913", "formula C11H20O"],
            ["MIBiG BGC0000659", "pubchem:16913", "formula C11H20O"],
            ["PubChem 9237955", "its title", "methyl (2S,4S)-1-[[5-(3-bromophenyl)-...]...-2-"
             "carboxylate, C15H16BrN3O4S"],
            ["PubChem 16913", "its title", "2-Bornanol, 2-methyl-, C11H20O"],
            ["PubChem 11062802", "its title", "2-Methylisoborneol, C11H20O"],
        ],
        "phase4": "Phase 4 kept only the first entry's number and formula, so the two formulas "
                  "agreed and MIBiG's 2-methylisoborneol was joined to the bromine compound's "
                  "record on the formula alone.",
        "steps": [
            ["info", "Every value, by entry", "Three entries give two numbers (9237955 once, "
             "16913 twice) and two formulas. Both numbers are candidates now."],
            ["person", "The review file", "A person read PubChem's record 9237955 (a bromine and "
             "sulfur compound) and wrote keep_apart, with that record as the source. That number "
             "is out, whatever the clues say."],
            ["fail", "Clue 1, name", "Record 16913 is titled '2-Bornanol, 2-methyl-' and doesn't "
             "list the name."],
            ["pass", "Clue 2, same structure", "The name search files the name under 11062802. Its "
             "InChIKey starts LFYXNXGVLGKVCJ, like 16913's: the same molecule, drawn with its 3D "
             "shape (11062802) and without it (16913)."],
        ],
        "rule": "pubchem_number_confirmed", "decision": "merged",
        "grounds": "MIBiG gives CID 16913; PubChem doesn't list the name '2-methylisoborneol' "
                   "under CID 16913 (its title is '2-Bornanol, 2-methyl-'), but files it under "
                   "CID 11062802, the same molecule drawn another way: both InChIKeys start "
                   "LFYXNXGVLGKVCJ; the formulas agree (C11H20O). Confirmed by name, through the "
                   "same structure.",
        "next": "Settled: one node, pubchem.compound:16913, named 2-methylisoborneol. 11062802 "
                "stays out of the graph (16913 is better supported, being the number MIBiG "
                "gives), and the decision by hand stays in the ledger.",
    },
    {
        "id": "des", "kind": "Compound", "title": "desosamine",
        "hook": "a sugar, merged into the antibiotic that carries it",
        "sources": [
            ["MIBiG BGC0000898", "pubchem:5282034, npatlas:NPA01238", "formula C25H43NO7"],
            ["MIBiG BGC0000899", "pubchem:419813", "formula C8H17NO3"],
            ["MIBiG BGC0000094 (methymycin)", "npatlas:NPA01238", "formula C25H43NO7"],
            ["PubChem 5282034", "its title", "Methymycin, C25H43NO7"],
            ["PubChem 419813", "its title", "3,4,6-Trideoxy-3-(dimethylamino-b-D-xylo-"
             "hexopyranose), C8H17NO3, the sugar drawn as a ring"],
            ["PubChem 168997", "its title", "3,4,6-Trideoxy-3-(dimethylamino)-D-xylo-hexose, "
             "C8H17NO3, the sugar drawn as an open chain"],
        ],
        "phase4": "Phase 4 joined desosamine to PubChem's methymycin record on the formula "
                  "alone, then the NPAtlas rule pulled MIBiG's methymycin into the same node: "
                  "a sugar merged into the molecule it is part of.",
        "steps": [
            ["info", "Every value, by entry", "Two entries, two numbers, two formulas. Entry "
             "BGC0000898 gives desosamine methymycin's number, formula and NPAtlas number."],
            ["person", "The review file", "Two decisions, both citing the paper MIBiG cites "
             "(pubmed:9770448): desosamine is not PubChem's methymycin, and not MIBiG's "
             "methymycin."],
            ["fail", "Clue 1, name", "Neither 5282034 (titled Methymycin) nor 419813 lists "
             "'desosamine'."],
            ["pass", "Clue 3, name search", "The name search finds 'desosamine' under 168997, "
             "with the same formula as BGC0000899's, C8H17NO3."],
            ["stop", "Clue 4 for 419813", "The name is filed under a record with another "
             "structure key, so the formula alone isn't trusted. 419813 draws the sugar as a ring "
             "and 168997 as an open chain (in water a sugar switches between the two), so their "
             "first InChIKey blocks differ."],
        ],
        "rule": "pubchem_name_search", "decision": "merged",
        "grounds": "PubChem's name search finds 'desosamine' under CID 168997 ('3,4,6-Trideoxy-"
                   "3-(dimethylamino)-D-xylo-hexose'); the formulas agree (C8H17NO3). Confirmed "
                   "by name and formula.",
        "next": "Settled: one node, pubchem.compound:168997, named desosamine. Methymycin has a "
                "node of its own, PubChem's 5282034, which the name search found for it.",
    },
    {
        "id": "fer", "kind": "Compound", "title": "ferrichrome",
        "hook": "an iron carrier, and a record of it with radioactive iron",
        "sources": [
            ["MIBiG BGC0000900", "pubchem:644246, pubchem:90658043", "formula C26H43N9O12, "
             "without iron"],
            ["MIBiG BGC0000901", "pubchem:644246", "formula C27H42FeN9O12, with iron"],
            ["PubChem 644246", "its title", "[55Fe] Ferrichrome, C27H42FeN9O12; its SMILES "
             "writes the iron as [55Fe+3]"],
            ["PubChem 90658043", "its title", "N-[3-[(2S,14S,17S)-...]propyl]-N-hydroxyacetamide, "
             "C26H43N9O12, a relative without iron"],
            ["PubChem 121489511", "its title", "Ferrichrome, C27H42FeN9O12"],
        ],
        "phase4": "Phase 4 compared the first formula (without iron) with PubChem's (with "
                  "iron): they differ, and PubChem doesn't list the name, so the two stayed "
                  "apart.",
        "steps": [
            ["info", "Every value, by entry", "Both entries give 644246, BGC0000900 also lists "
             "90658043, and one formula has an iron atom while the other doesn't. Since the "
             "Phase 4b follow-ups, both numbers are candidates."],
            ["fail", "Clue 1, name", "Neither record lists 'ferrichrome': 644246 is titled "
             "'[55Fe] Ferrichrome', the molecule built with radioactive iron-55, and 90658043 "
             "has only a long systematic name."],
            ["stop", "Clue 2, same structure", "The name search files 'ferrichrome' under "
             "121489511, and both InChIKeys start GGUNGDGGXMHBMJ. But that first block leaves "
             "isotopes out, and 644246's SMILES writes its iron as [55Fe+3]: a laboratory "
             "tracer. Since the follow-ups, clue 2 doesn't confirm a tracer when the name's "
             "record has ordinary iron. (On the first run it did, and ferrichrome joined the "
             "tracer.)"],
            ["pass", "Clue 3, name search", "121489511, 'Ferrichrome', has the formula "
             "C27H42FeN9O12, which agrees with BGC0000901's."],
            ["stop", "Clue 4 for 90658043", "The name is filed under a record with another "
             "structure key, so the formula alone isn't trusted."],
        ],
        "rule": "pubchem_name_search", "decision": "merged",
        "grounds": "PubChem's name search finds 'ferrichrome' under CID 121489511 "
                   "('Ferrichrome'); the formulas agree (C27H42FeN9O12). Confirmed by name and "
                   "formula.",
        "next": "Settled with the Phase 4b follow-ups: one node, pubchem.compound:121489511, "
                "named ferrichrome. The tracer record 644246 and the relative 90658043 stay out "
                "of the graph, each with its reason in the ledger.",
    },
    {
        "id": "epo", "kind": "Compound", "title": "epoxomicin",
        "hook": "one entry, two numbers, both with the name",
        "sources": [
            ["MIBiG BGC0000346", "pubchem:11226684, pubchem:9915668", "formula C28H50N4O7"],
            ["PubChem 11226684", "its title", "Epoxomicin, C28H50N4O7, drawn with its eight "
             "chiral centres"],
            ["PubChem 9915668", "its title", "Epoxomicin (BU-4061T), C28H50N4O7, the same "
             "structure drawn flat"],
        ],
        "phase4": "Phase 4 read only the first number the entry lists, 11226684. PubChem lists "
                  "the name under it, so the two were joined by name.",
        "steps": [
            ["info", "Every number the entry lists", "Since the Phase 4b follow-ups, both "
             "numbers BGC0000346 gives are candidates."],
            ["pass", "Clue 1, name, for 11226684", "PubChem titles it 'Epoxomicin'."],
            ["pass", "Clue 1, name, for 9915668", "PubChem lists 'Epoxomicin?' among its names, "
             "the same name once the question mark is dropped."],
            ["stop", "Two candidates equally strong", "Both pass clue 1 and they are different "
             "records, so the rules alone keep the compound apart from both: choosing would be "
             "a guess."],
            ["person", "The review file", "A person read both records: the same structure (both "
             "InChIKeys start DOGIDQKFVLKMLQ), 11226684 drawn with its eight chiral centres and "
             "9915668 drawn flat. join, with PubChem's record 11226684 as the source."],
        ],
        "rule": "reviewed_by_hand", "decision": "merged",
        "grounds": "Decided by hand on 2026-10-13: mg.compound:epoxomicin and "
                   "pubchem.compound:11226684 are the same thing. MIBiG's entry BGC0000346 gives "
                   "two PubChem numbers for epoxomicin, and both records list the name. Record "
                   "11226684 is titled Epoxomicin and is drawn with its 3D shape (eight chiral "
                   "centres; InChIKey DOGIDQKFVLKMLQ-JTHVHQAWSA-N). Record 9915668 is the same "
                   "structure drawn without it (DOGIDQKFVLKMLQ-UHFFFAOYSA-N). Source: "
                   "pubchem.compound:11226684 (curation/resolution_decisions.csv, line 7).",
        "next": "Settled: one node, pubchem.compound:11226684, named epoxomicin. Mureidomycin B "
                "had the same kind of tie and the same kind of decision; valclavam's tie waits "
                "for a person.",
    },
    {
        "id": "las", "kind": "Compound", "title": "lasalocid",
        "hook": "a salt and its acid",
        "sources": [
            ["MIBiG BGC0000086", "pubchem:2724110", "formula C34H53NaO8, the sodium salt"],
            ["MIBiG BGC0000087", "pubchem:2724110", "formula C34H53NaO8, the sodium salt"],
            ["MIBiG BGC0001648", "no number", "formula C34H54O8, the acid"],
            ["PubChem 2724110", "its title", "Sodium;6-[7-[5-ethyl-...]...]-2-hydroxy-3-"
             "methylbenzoate, C34H53NaO8"],
            ["PubChem 5360807", "its title", "Lasalocid A, C34H54O8"],
        ],
        "phase4": "Phase 4 kept the first formula, the salt's, which matched PubChem's salt "
                  "record, so the two were joined on the formula alone.",
        "steps": [
            ["info", "Every value, by entry", "Three entries, two formulas: the sodium salt twice, "
             "the acid once."],
            ["fail", "Clue 1, name", "PubChem's title is the salt's chemical name; it doesn't "
             "list 'lasalocid'."],
            ["stop", "Clue 4, formula alone", "Switched off: the entries disagree about the "
             "formula."],
            ["pass", "Clue 3, name search", "The name search finds 'lasalocid' under 5360807, "
             "'Lasalocid A', whose formula agrees with the acid's (BGC0001648)."],
        ],
        "rule": "pubchem_name_search", "decision": "merged",
        "grounds": "PubChem's name search finds 'lasalocid' under CID 5360807 ('Lasalocid A'); "
                   "the formulas agree (C34H54O8). Confirmed by name and formula.",
        "next": "Settled: one node, pubchem.compound:5360807, named lasalocid: the compound "
                "itself. The sodium salt's record, 2724110, stays out of the graph.",
    },
    {
        "id": "cbf", "kind": "Protein", "title": "CBF82293.1",
        "hook": "one sequence, two proteins",
        "sources": [
            ["MIBiG BGC0002180 ((+)-asperlin)", "CBF82293.1", "822 amino acids, Aspergillus "
             "nidulans FGSC A4"],
            ["UniProt P0CU77", "reviewed", "alnG, 368 amino acids, lists CBF82293.1"],
            ["UniProt P0CU78", "reviewed", "alnR, 407 amino acids, lists CBF82293.1"],
        ],
        "phase4": "UniProt lists the number under two entries. The organism, length and "
                  "review-status steps couldn't pick one, so the number stayed on its own, "
                  "listed as a tie.",
        "steps": [
            ["info", "The cluster's organism", "Both entries are for Aspergillus nidulans: no "
             "choice yet."],
            ["fail", "The same length as MIBiG's sequence", "Neither entry is 822 amino acids "
             "long."],
            ["fail", "Reviewed by a curator", "Both are reviewed: still a tie."],
            ["person", "The review file", "A person read UniProt's entries: both carry the locus "
             "name AN9221, and MIBiG's 822-amino-acid sequence reads the two genes as one. "
             "keep_apart from each, with UniProt's entry as the source."],
        ],
        "rule": "reviewed_by_hand", "decision": "kept_apart",
        "grounds": "Decided by hand on 2026-10-12: ncbiprotein:CBF82293.1 and uniprot:P0CU77 "
                   "are different things. UniProt's reviewed entries P0CU77 (alnG, 368 amino "
                   "acids) and P0CU78 (alnR, 407) both carry the locus name AN9221 and both list "
                   "CBF82293.1. MIBiG's sequence for CBF82293.1 is 822 amino acids long, so it "
                   "reads the two genes as one and is neither protein alone. Source: "
                   "uniprot:P0CU77 (curation/resolution_decisions.csv, line 5).",
        "next": "Settled. 40 other protein numbers with tied UniProt entries wait for the same "
                "kind of reading.",
    },
    {
        "id": "bae", "kind": "Protein", "title": "baeI",
        "hook": "a gene name no list could place",
        "sources": [
            ["MIBiG BGC0001089 (bacillaene), gene record", "baeI", "polyketide biosynthesis "
             "enoyl-CoA hydratase, no protein number"],
            ["MIBiG's protein file", "CAG23956.1", "label CAG23956.1, product "
             "enoyl-CoA-hydratase"],
            ["MIBiG's GenBank file", "a CDS", "/gene=\"baeI\" and /protein_id=\"CAG23956.1\""],
            ["UniProt Q1RS74", "unreviewed", "lists CAG23956.1"],
        ],
        "phase4": "No list linked the name to a number. Phase 4's gene-name rule should have "
                  "found it through UniProt (Q1RS74 lists 'baeI|PV946_13250'), but it split "
                  "UniProt's gene names on spaces and semicolons, never on '|', so it missed "
                  "every entry with two names. "
                  "The gene record stayed a node of its own, beside its own protein.",
        "steps": [
            ["fail", "The protein file, by number or label", "The gene record has no number, and "
             "no label in the file is 'baeI'."],
            ["fail", "The protein file, by product", "'polyketide biosynthesis enoyl-CoA "
             "hydratase' isn't the file's 'enoyl-CoA-hydratase'."],
            ["pass", "MIBiG's GenBank file", "One CDS in BGC0001089 has /gene=\"baeI\" and "
             "/protein_id=\"CAG23956.1\". This happens in the MIBiG tidy, counted as "
             "genes_found_by_genbank."],
            ["pass", "UniProt", "UniProt lists CAG23956.1 under Q1RS74, so the resolver joins "
             "them as for any protein number."],
        ],
        "rule": "uniprot_cross_reference", "decision": "merged",
        "grounds": "UniProt lists CAG23956.1 under entry Q1RS74.",
        "next": "Settled: one node, uniprot:Q1RS74, named baeI. Bacillus velezensis FZB42 now "
                "leads to 174 proteins instead of 175 (cookbook recipe N5).",
    },
]

STEP_LOOK = {"pass": ("&#10003;", "passes"), "fail": ("&#10007;", "doesn't confirm"),
             "stop": ("&#9940;", "switched off"), "wait": ("&#9719;", "waiting"),
             "info": ("i", "what the data says"), "person": ("&#9998;", "a person decides")}


def resolution_cases() -> str:
    buttons = "".join(
        f'<button class="case" data-id="{c["id"]}" aria-pressed="false">'
        f'<span class="kind mono">{c["kind"]}</span><b>{escape(c["title"])}</b>'
        f'<span class="muted">{escape(c["hook"])}</span></button>' for c in CASES)
    body = f"""
<h1>Seven real cases, clue by clue</h1>
<p class="lede">Each case is a record the resolver had to decide about in Phase 4b, with what the
sources say, what Phase 4 did, and each clue in turn. Pick a case, then press <b>Next clue</b>
(or the right arrow key) to walk through it. Every value and every ledger sentence is copied from
the real build after the Phase 4b follow-ups (the PubChem run of 2026-10-12 at 23:07 UTC).</p>
<div class="layout">
<div class="cases" role="group" aria-label="Cases">{buttons}</div>
<div class="card" id="detail" aria-live="polite"></div>
</div>
<details><summary>How to read the marks</summary>
<p>{''.join(f'<span class="chip"><span class="mark {k}">{m}</span>{w}</span>'
               for k, (m, w) in STEP_LOOK.items())}</p>
<p class="muted">The four clues for a compound, strongest first, are explained in
<span class="mono">docs/06b-closing-the-gaps.md</span>, Step 6; the review file in Step 7. Recipe R20
in the query cookbook lists every decision made by hand.</p>
</details>"""
    style = """<style>
.layout { display: grid; grid-template-columns: minmax(220px, 300px) 1fr; gap: 16px; }
@media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
.cases { display: flex; flex-direction: column; gap: 8px; }
.case { text-align: left; background: var(--surface); color: var(--ink); border: 1px solid var(--hair);
        border-radius: 12px; padding: 10px 12px; cursor: pointer; display: flex; flex-direction: column;
        gap: 2px; font: inherit; }
.case[aria-pressed="true"] { border-color: var(--focus); box-shadow: 0 0 0 2px var(--focus) inset; }
.case:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.kind { font-size: 12px; color: var(--muted); }
.step { display: grid; grid-template-columns: 34px 1fr; gap: 8px; padding: 8px 0;
        border-top: 1px solid var(--hair); }
.mark { display: inline-flex; width: 26px; height: 26px; border-radius: 50%; align-items: center;
        justify-content: center; font-weight: 700; color: #fff; margin-right: 6px; flex: none; }
.mark.pass { background: #0ca30c; } .mark.fail { background: #898781; }
.mark.stop { background: #d03b3b; } .mark.wait { background: #c3c2b7; color: #0b0b0b; }
.mark.info { background: #2a78d6; } .mark.person { background: #eb6834; }
.grounds { background: var(--plane); border-radius: 10px; padding: 10px 12px; font-size: 14px; }
.btns { display: flex; gap: 8px; margin: 10px 0; }
.btns button { font: inherit; border: 1px solid var(--hair); background: var(--surface); color: var(--ink);
               border-radius: 8px; padding: 6px 12px; cursor: pointer; }
.btns button:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.btns button[disabled] { opacity: .45; cursor: default; }
</style>"""
    script = f"""
const CASES = {json.dumps(CASES)};
const LOOK = {json.dumps({k: list(v) for k, v in STEP_LOOK.items()})};
const detail = document.getElementById('detail');
const buttons = [...document.querySelectorAll('.case')];
let current = null, shown = 0;
function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}
function render() {{
  const c = current;
  const rows = c.sources.map(s => `<tr><td>${{esc(s[0])}}</td><td class="mono">${{esc(s[1])}}</td><td>${{esc(s[2])}}</td></tr>`).join('');
  const steps = c.steps.slice(0, shown).map(s => `<div class="step"><span class="mark ${{s[0]}}" aria-hidden="true">${{LOOK[s[0]][0]}}</span>
    <div><b>${{esc(s[1])}}</b> <span class="muted">(${{LOOK[s[0]][1]}})</span><br>${{esc(s[2])}}</div></div>`).join('');
  const done = shown >= c.steps.length;
  const end = done ? `<h3>The decision</h3><p><span class="mono">${{esc(c.rule)}}</span> &middot;
    <span class="mono">${{esc(c.decision)}}</span></p><div class="grounds">${{esc(c.grounds)}}</div>
    <p><b>Next:</b> ${{esc(c.next)}}</p>` : '';
  detail.innerHTML = `<h2>${{esc(c.title)}}<span class="muted" style="font-weight:400">: ${{esc(c.hook)}}</span></h2>
    <table><tr><th>Who</th><th>Record</th><th>What it says</th></tr>${{rows}}</table>
    <p><b>What Phase 4 did:</b> ${{esc(c.phase4)}}</p>
    <h3>The clues, one by one</h3>${{steps || '<p class="muted">Press Next clue to start.</p>'}}
    <div class="btns"><button id="prev" ${{shown === 0 ? 'disabled' : ''}}>Back</button>
    <button id="next" ${{done ? 'disabled' : ''}}>Next clue</button>
    <button id="all" ${{done ? 'disabled' : ''}}>Show all</button></div>${{end}}`;
  document.getElementById('next').onclick = () => {{ shown++; render(); }};
  document.getElementById('prev').onclick = () => {{ shown--; render(); }};
  document.getElementById('all').onclick = () => {{ shown = c.steps.length; render(); }};
}}
function pick(id) {{
  current = CASES.find(c => c.id === id); shown = 0;
  buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
  render();
}}
buttons.forEach(b => b.addEventListener('click', () => pick(b.dataset.id)));
document.addEventListener('keydown', e => {{
  if (!current || e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowRight' && shown < current.steps.length) {{ shown++; render(); }}
  if (e.key === 'ArrowLeft' && shown > 0) {{ shown--; render(); }}
}});
pick(CASES[0].id);
"""
    return page("MicrobeGraph resolution cases", style + body, script, dict(mi.LAYER))


def main() -> None:
    print("Writing MicrobeGraph interactive pages")
    write("ontology_explorer.html", ontology_explorer())
    write("evidence_chain.html", evidence_chain())
    write("roadmap_timeline.html", roadmap_timeline())
    write("resolution_cases.html", resolution_cases())


if __name__ == "__main__":
    main()
