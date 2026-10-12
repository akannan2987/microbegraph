"""
MicrobeGraph, the interactive teaching pages.

WHAT THIS SCRIPT DOES
    Writes three self-contained web pages into docs/interactive/:

        ontology_explorer.html    the rulebook: hover a node type or an arrow
        evidence_chain.html       one real chain, with evidence filters
        roadmap_timeline.html     every phase, its hours and its status

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
                "protein file); UniProt describes each one"),
    "Compound": ("The molecule the cluster makes.",
                 "Phase 1 (MIBiG); PubChem identities in Phase 2, joined to MIBiG's in Phase 4"),
    "CompoundClass": ("A family of chemically related molecules.",
                      "Phase 1 (MIBiG, when it gives one)"),
    "Activity": ("What a molecule has been seen to do: antibacterial, antifungal, surfactant...",
                 "Phase 1 (MIBiG)"),
    "Pathogen": ("An organism that causes a plant disease.",
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
    ("ncbiprotein:CAE02630.1", "Protein", "srfAA (UniProt Q70KJ7)", 470, 370),
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
    ("mibig:BGC0000433", "ncbiprotein:CAE02630.1", "ENCODES", "database_assertion", "mibig",
     "BGC0000433", "pubmed:14762003", "0.50", False),
    ("ncbiprotein:CAE02630.1", "mg.compound:surfactin", "CATALYZES", "curated_experimental", "mibig",
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
other proteins). UniProt's ID mapping says CAE02630.1 is the entry Q70KJ7, Surfactin
synthetase A. The protein route sits beside the PRODUCES shortcut, so hiding it never breaks the
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


def main() -> None:
    print("Writing MicrobeGraph interactive pages")
    write("ontology_explorer.html", ontology_explorer())
    write("evidence_chain.html", evidence_chain())
    write("roadmap_timeline.html", roadmap_timeline())


if __name__ == "__main__":
    main()
