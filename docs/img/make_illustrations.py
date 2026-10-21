"""
MicrobeGraph, the teaching illustrations.

WHAT THIS SCRIPT DOES
    Draws every diagram in docs/img/ as an SVG file, from code:

        python docs/img/make_illustrations.py

    Run it from the repository root, with .venv active. It needs only the
    Python standard library and rewrites every figure in a second or two.

WHY DRAW DIAGRAMS WITH CODE INSTEAD OF A DRAWING PROGRAM
    * A figure made by a script can be regenerated after any change, by
      anyone, identically. A figure made by hand can only be fixed by the
      person who has the original file.
    * Git can show exactly what changed in a figure, line by line.
    * Every colour and every word lives in one place (the constants below),
      so a renamed concept is renamed in every diagram at once.

    A script is to a drawing what a recipe is to a photograph of a cake: you
    can bake the recipe again tomorrow, but you can't bake the photograph.

WHY SVG
    SVG ("scalable vector graphics") describes shapes rather than pixels, so
    diagrams stay sharp at any zoom, files stay small, and GitHub shows them
    directly inside the Markdown documents.

THE COLOUR RULES (kept the same in every figure)
    * Biological layer of a node type: genomics blue, proteomics orange,
      metabolomics aqua, phenotype yellow, context grey.
    * Evidence strength: one blue, darkest = strongest, and "inferred" in
      grey with a dashed line. Every level is also named in text.
    * Releases: 1.0 blue, 2.0 orange, 3.0 aqua.
    The palette was checked for colour-blind separation; every coloured mark
    also carries a text label, so no meaning depends on colour alone.

    Each figure sits on its own light card, so it stays readable when GitHub
    is in dark mode.
"""

from __future__ import annotations

import csv
import math
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent            # docs/img/
DOCS = HERE.parent                                # docs/

# --- Ink and surfaces ---------------------------------------------------------
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SURFACE = "#fcfcfb"
PLANE = "#f3f2ee"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
HAIR = "#e1e0d9"
BASE = "#c3c2b7"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

# --- Meaningful colours (see the module docstring) -------------------------------
LAYER = {
    "genomics": "#2a78d6",
    "proteomics": "#eb6834",
    "metabolomics": "#1baf7a",
    "phenotype": "#eda100",
    "context": "#898781",
}
EVIDENCE = {
    "curated_experimental": "#184f95",
    "database_assertion": "#2a78d6",
    "curated_literature": "#6da7ec",
    "inferred": "#898781",
}
RELEASE = {"design": "#898781", "1.0": "#2a78d6", "2.0": "#eb6834", "3.0": "#1baf7a"}

# --- The nine node types: layer, example identifier, everyday parallel -----------
NODE_INFO = {
    "Organism": ("genomics", "ncbitaxon:326423", "the factory"),
    "GeneCluster": ("genomics", "mibig:BGC0000433", "the production line"),
    "Protein": ("proteomics", "uniprot:Q70KJ7", "the machine on the line"),
    "Compound": ("metabolomics", "mg.compound:surfactin", "the product"),
    "CompoundClass": ("metabolomics", "mg.class:lipopeptide", "the supermarket aisle"),
    "Activity": ("metabolomics", "mg.activity:antibacterial", "what it is for"),
    "Pathogen": ("phenotype", "ncbitaxon:40559", "the problem"),
    "Crop": ("phenotype", "mg.crop:jujube", "who suffers"),
    "Pathway": ("context", "kegg.pathway:map00660", "the wider process"),
}


# =============================================================================
# Small drawing helpers
# =============================================================================
def t(x: float, y: float, s: str, size: float = 14, weight: int = 400, fill: str = INK,
      anchor: str = "start", family: str = FONT, style: str = "", halo: bool = False) -> str:
    """One line of text. Text is always escaped, so '<' and '&' are safe.
    halo=True paints a thin surface-coloured outline behind the letters, so a
    line passing underneath never cuts through the word."""
    italic = ' font-style="italic"' if style == "italic" else ""
    outline = f' paint-order="stroke" stroke="{SURFACE}" stroke-width="5"' if halo else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{italic}{outline}>'
            f"{escape(s)}</text>")


def rect(x: float, y: float, w: float, h: float, fill: str = "none", stroke: str = "none",
         rx: float = 8, sw: float = 1.5, dash: str = "") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


_ARROW_COLOURS: set[str] = set()


def _marker(color: str, arrow: bool) -> str:
    """Arrowheads are coloured like their line; each colour gets its own marker."""
    if not arrow:
        return ""
    _ARROW_COLOURS.add(color)
    return f' marker-end="url(#arrow-{color.lstrip("#")})"'


def line(x1: float, y1: float, x2: float, y2: float, color: str = INK2, sw: float = 2,
         arrow: bool = True, dash: str = "") -> str:
    m = _marker(color, arrow)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round"{d}{m}/>')


def path(d: str, color: str = INK2, sw: float = 2, arrow: bool = True, dash: str = "",
         fill: str = "none") -> str:
    m = _marker(color, arrow)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')


def chip(x: float, y: float, label: str, color: str, w: float | None = None,
         text_fill: str = INK, size: float = 12) -> str:
    """A small rounded label with a coloured dot, so the meaning never rests on colour alone."""
    w = w or (len(label) * size * 0.58 + 30)
    return (rect(x, y, w, size + 12, fill=SURFACE, stroke=HAIR, rx=(size + 12) / 2, sw=1)
            + f'<circle cx="{x + 12:.1f}" cy="{y + (size + 12) / 2:.1f}" r="5" fill="{color}"/>'
            + t(x + 22, y + size + 3, label, size=size, fill=text_fill))


def check_mark(cx: float, cy: float, r: float = 9, color: str = GOOD) -> str:
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            f'<path d="M{cx - r * 0.45:.1f} {cy:.1f} l{r * 0.3:.1f} {r * 0.35:.1f} '
            f'l{r * 0.6:.1f} -{r * 0.7:.1f}" stroke="#fff" stroke-width="2.2" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def cross_mark(cx: float, cy: float, r: float = 9, color: str = CRITICAL) -> str:
    k = r * 0.4
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            f'<path d="M{cx - k} {cy - k} L{cx + k} {cy + k} M{cx + k} {cy - k} L{cx - k} {cy + k}" '
            f'stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>')


def svg(width: int, height: int, body: str, title: str, desc: str) -> str:
    """Wrap a drawing: accessible title and description, arrowheads, and the light card."""
    markers = "\n".join(
        f'  <marker id="arrow-{c.lstrip("#")}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="11" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>'
        for c in sorted(_ARROW_COLOURS))
    _ARROW_COLOURS.clear()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">{escape(desc)}</desc>
<defs>
{markers}
</defs>
{rect(1, 1, width - 2, height - 2, fill=SURFACE, stroke=HAIR, rx=16, sw=1.5)}
{body}
</svg>
"""


def write(name: str, content: str) -> None:
    (HERE / name).write_text(content, encoding="utf-8")
    print(f"  wrote docs/img/{name}")


# =============================================================================
# Pictographs: one small drawing per node type, in a 48 x 48 box
# =============================================================================
def _gear(c: str) -> str:
    teeth, outer, inner = 8, 20, 15
    points = []
    for i in range(teeth * 2):
        angle = math.pi * i / teeth
        r = outer if i % 2 == 0 else inner
        for da in (-0.17, 0.17):
            points.append((24 + r * math.cos(angle + da), 24 + r * math.sin(angle + da)))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{c}"/><circle cx="24" cy="24" r="6" fill="{SURFACE}"/>'


def _hexagon(cx: float, cy: float, r: float) -> str:
    return " ".join(f"{cx + r * math.cos(math.pi / 6 + k * math.pi / 3):.1f},"
                    f"{cy + r * math.sin(math.pi / 6 + k * math.pi / 3):.1f}" for k in range(6))


def _spikes(c: str) -> str:
    out = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        out.append(f'<line x1="{24 + 11 * math.cos(a):.1f}" y1="{24 + 11 * math.sin(a):.1f}" '
                   f'x2="{24 + 18 * math.cos(a):.1f}" y2="{24 + 18 * math.sin(a):.1f}" '
                   f'stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')
        out.append(f'<circle cx="{24 + 19 * math.cos(a):.1f}" cy="{24 + 19 * math.sin(a):.1f}" '
                   f'r="2.2" fill="{c}"/>')
    return "".join(out) + f'<circle cx="24" cy="24" r="11" fill="{c}"/>'


ICON_SHAPES = {
    # a rod-shaped bacterium with a flagellum
    "Organism": lambda c: (f'<rect x="4" y="14" width="32" height="20" rx="10" fill="{c}"/>'
                           f'<path d="M36 24 c3 -6 6 6 9 0" stroke="{c}" stroke-width="2.5" '
                           f'fill="none" stroke-linecap="round"/>'
                           f'<circle cx="13" cy="21" r="2.5" fill="{SURFACE}" opacity=".8"/>'
                           f'<circle cx="22" cy="27" r="2" fill="{SURFACE}" opacity=".8"/>'),
    # genes drawn as arrows on a strand: how gene clusters are drawn in the field
    "GeneCluster": lambda c: (f'<line x1="2" y1="24" x2="46" y2="24" stroke="{c}" stroke-width="2"/>'
                              f'<path d="M3 17 h9 l4 7 l-4 7 h-9 z" fill="{c}"/>'
                              f'<path d="M30 17 h-9 l-4 7 l4 7 h9 z" fill="{c}" opacity=".75"/>'
                              f'<path d="M32 17 h9 l4 7 l-4 7 h-9 z" fill="{c}"/>'),
    # a gear: the machine that does one chemical step
    "Protein": _gear,
    # a ring molecule with a side chain
    "Compound": lambda c: (f'<polygon points="{_hexagon(20, 26, 14)}" fill="none" stroke="{c}" '
                           f'stroke-width="3.5" stroke-linejoin="round"/>'
                           f'<circle cx="20" cy="26" r="6" fill="none" stroke="{c}" stroke-width="2"/>'
                           f'<line x1="32" y1="19" x2="42" y2="13" stroke="{c}" stroke-width="3" '
                           f'stroke-linecap="round"/><circle cx="43" cy="12" r="4" fill="{c}"/>'),
    # three molecules on a shelf: a family
    "CompoundClass": lambda c: (f'<polygon points="{_hexagon(13, 30, 9)}" fill="{c}"/>'
                                f'<polygon points="{_hexagon(35, 30, 9)}" fill="{c}" opacity=".75"/>'
                                f'<polygon points="{_hexagon(24, 13, 9)}" fill="{c}" opacity=".55"/>'
                                f'<line x1="2" y1="42" x2="46" y2="42" stroke="{c}" stroke-width="3" '
                                f'stroke-linecap="round"/>'),
    # a bolt: what the molecule does
    "Activity": lambda c: f'<path d="M27 3 L9 27 h13 l-4 18 L39 19 h-13 z" fill="{c}"/>',
    # a spiky spore: the disease-causing organism
    "Pathogen": _spikes,
    # a sprouting plant
    "Crop": lambda c: (f'<path d="M24 45 V22" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
                       f'<path d="M24 26 C10 26 6 16 6 8 C16 8 24 13 24 26 z" fill="{c}"/>'
                       f'<path d="M24 31 C38 31 42 21 42 13 C32 13 24 18 24 31 z" fill="{c}" opacity=".8"/>'),
    # three stops joined by a route
    "Pathway": lambda c: (f'<path d="M8 38 C16 38 14 12 24 12 C34 12 32 36 40 36" fill="none" '
                          f'stroke="{c}" stroke-width="3" stroke-dasharray="1 5" stroke-linecap="round"/>'
                          f'<circle cx="8" cy="38" r="5" fill="{c}"/><circle cx="24" cy="12" r="5" fill="{c}"/>'
                          f'<circle cx="40" cy="36" r="5" fill="{c}"/>'),
}


def icon(kind: str, cx: float, cy: float, size: float = 48, color: str | None = None) -> str:
    """Place one pictograph centred on (cx, cy)."""
    color = color or LAYER[NODE_INFO[kind][0]]
    s = size / 48
    return (f'<g transform="translate({cx - 24 * s:.1f},{cy - 24 * s:.1f}) scale({s:.3f})">'
            f"{ICON_SHAPES[kind](color)}</g>")


def node_badge(kind: str, cx: float, cy: float, r: float = 34, label: str | None = None) -> str:
    """A pictograph inside a ringed circle, with its name underneath."""
    color = LAYER[NODE_INFO[kind][0]]
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SURFACE}" stroke="{color}" stroke-width="3"/>'
            + icon(kind, cx, cy, size=r * 1.4)
            + t(cx, cy + r + 20, label or kind, size=14, weight=600, anchor="middle", halo=True))


# =============================================================================
# The figures
# =============================================================================
def logo() -> str:
    body = (
        rect(24, 24, 112, 112, fill=PLANE, stroke=HAIR, rx=28)
        + path("M52 98 Q80 40 108 98", color=BASE, sw=3, arrow=False)
        + f'<circle cx="52" cy="98" r="17" fill="{SURFACE}" stroke="{LAYER["genomics"]}" stroke-width="3"/>'
        + icon("Organism", 52, 98, 22)
        + f'<circle cx="80" cy="62" r="19" fill="{SURFACE}" stroke="{LAYER["metabolomics"]}" stroke-width="3"/>'
        + icon("Compound", 80, 62, 26)
        + f'<circle cx="108" cy="98" r="17" fill="{SURFACE}" stroke="{LAYER["phenotype"]}" stroke-width="3"/>'
        + icon("Crop", 108, 98, 22)
        # One <text> with the second word in a <tspan>, so "Graph" always starts
        # right after "Microbe", whatever width the reader's font gives it.
        + (f'<text x="160" y="86" font-family="{FONT}" font-size="34" fill="{INK}">'
           f'Microbe<tspan font-weight="700">Graph</tspan></text>')
        + t(162, 112, "microbes · molecules · crops, with evidence", size=13, fill=INK2)
    )
    return svg(470, 160, body, "MicrobeGraph logo",
               "A microbe, a molecule and a plant joined by an arc, beside the word MicrobeGraph.")


def cover() -> str:
    chain = ["Organism", "GeneCluster", "Protein", "Compound", "Pathogen", "Crop"]
    verbs = ["HARBORS", "ENCODES", "CATALYZES", "INHIBITS", "INFECTS"]
    xs = [140 + i * 184 for i in range(6)]
    y = 220
    parts = [
        t(48, 70, "MicrobeGraph", size=40, weight=700),
        t(48, 104, "From a microbe's genes to a crop's disease, with the evidence for every arrow.",
          size=18, fill=INK2),
    ]
    for i, verb in enumerate(verbs):
        x1, x2 = xs[i] + 42, xs[i + 1] - 42
        parts.append(line(x1, y, x2, y, color=INK2, sw=2.5))
        parts.append(t((x1 + x2) / 2, y - 10, verb, size=12, weight=600, fill=INK2,
                       anchor="middle", family=MONO))
    # the direct shortcut MIBiG records
    parts.append(path(f"M{xs[1]} {y - 40} C{xs[1] + 60} {y - 110} {xs[3] - 60} {y - 110} {xs[3]} {y - 42}",
                      color=MUTED, sw=2, dash="6 5"))
    parts.append(t((xs[1] + xs[3]) / 2, y - 92, "PRODUCES (the direct shortcut)", size=12,
                   fill=MUTED, anchor="middle", family=MONO))
    for kind, x in zip(chain, xs, strict=True):
        parts.append(node_badge(kind, x, y))
    # the four measurement layers underneath
    bands = [("genomics", xs[0], xs[1]), ("proteomics", xs[2], xs[2]),
             ("metabolomics", xs[3], xs[3]), ("phenotype", xs[4], xs[5])]
    for name, a, b in bands:
        parts.append(rect(a - 70, 300, b - a + 140, 8, fill=LAYER[name], rx=4))
        parts.append(t((a + b) / 2, 330, name, size=13, weight=600, fill=INK2, anchor="middle"))
    return svg(1200, 360, "".join(parts), "MicrobeGraph cover",
               "The six-step chain from organism to gene cluster to protein to compound to "
               "pathogen to crop, grouped into genomics, proteomics, metabolomics and phenotype.")


def node_types() -> str:
    parts = [t(32, 46, "The nine node types (the nouns)", size=22, weight=700),
             t(32, 70, "Each card: what it looks like, how it is identified, and something everyday it resembles.",
               size=14, fill=INK2)]
    for i, (kind, (layer, curie, parallel)) in enumerate(NODE_INFO.items()):
        col, row = i % 3, i // 3
        x, y = 32 + col * 312, 92 + row * 132
        parts.append(rect(x, y, 296, 116, fill=SURFACE, stroke=HAIR, rx=12))
        parts.append(rect(x, y, 6, 116, fill=LAYER[layer], rx=3))
        parts.append(f'<circle cx="{x + 54}" cy="{y + 58}" r="34" fill="{PLANE}"/>')
        parts.append(icon(kind, x + 54, y + 58, 44))
        parts.append(t(x + 102, y + 34, kind, size=17, weight=700))
        parts.append(t(x + 102, y + 56, curie, size=11.5, fill=INK2, family=MONO))
        parts.append(t(x + 102, y + 80, parallel, size=13.5, fill=INK, style="italic"))
        parts.append(t(x + 102, y + 101, layer, size=11.5, weight=600, fill=MUTED))
    return svg(970, 500, "".join(parts), "The nine node types",
               "Pictographs for Organism, GeneCluster, Protein, Compound, CompoundClass, "
               "Activity, Pathogen, Crop and Pathway, each with an identifier example and "
               "an everyday comparison.")


def ontology_map() -> str:
    pos = {"Organism": (110, 230), "GeneCluster": (320, 230), "Protein": (530, 120),
           "Compound": (740, 230), "Pathogen": (950, 230), "Crop": (1120, 230),
           "CompoundClass": (620, 400), "Activity": (860, 400), "Pathway": (930, 92)}
    edges = [("Organism", "GeneCluster", "HARBORS"), ("GeneCluster", "Protein", "ENCODES"),
             ("Protein", "Compound", "CATALYZES"), ("GeneCluster", "Compound", "PRODUCES"),
             ("Compound", "Pathogen", "INHIBITS"), ("Pathogen", "Crop", "INFECTS"),
             ("Compound", "CompoundClass", "BELONGS_TO"), ("Compound", "Activity", "HAS_ACTIVITY"),
             ("Compound", "Pathway", "PARTICIPATES_IN")]
    r = 36
    parts = [t(32, 44, "The rulebook as a picture: 9 node types, 10 edge types", size=22, weight=700),
             t(32, 68, "Every arrow in the graph must be one of these, pointing the way shown.",
               size=14, fill=INK2)]
    for a, b, verb in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        d = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        sx, sy, ex, ey = x1 + ux * (r + 4), y1 + uy * (r + 4), x2 - ux * (r + 8), y2 - uy * (r + 8)
        parts.append(line(sx, sy, ex, ey, color=INK2, sw=2))
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        w = len(verb) * 7.4 + 12
        parts.append(rect(mx - w / 2, my - 11, w, 20, fill=SURFACE, rx=6))
        parts.append(t(mx, my + 4, verb, size=11.5, weight=600, fill=INK2, anchor="middle", family=MONO))
    # MEMBER_OF: an organism belongs to a larger group (species -> genus)
    ox, oy = pos["Organism"]
    parts.append(path(f"M{ox - 22} {oy - 30} C{ox - 70} {oy - 110} {ox + 70} {oy - 110} {ox + 22} {oy - 30}",
                      color=INK2, sw=2))
    parts.append(t(ox, oy - 98, "MEMBER_OF", size=11.5, weight=600, fill=INK2, anchor="middle", family=MONO))
    # A Pathogen is a kind of Organism (from Phase 4): a dashed line with an open arrowhead,
    # the usual way diagrams draw "is a kind of".
    # It runs below every other drawing, so it crosses no label.
    px, py = pos["Pathogen"]
    low = 486
    parts.append(path(f"M{px} {py + r + 30} V{low - 16} Q{px} {low} {px - 16} {low} "
                      f"H{ox + 16} Q{ox} {low} {ox} {low - 16} V{oy + r + 30}",
                      color=MUTED, sw=1.8, dash="6 5"))
    parts.append(t((px + ox) / 2, low + 4, "a Pathogen is a kind of Organism (from Phase 4)",
                   size=12, weight=600, fill=INK2, anchor="middle", style="italic", halo=True))
    for kind, (x, y) in pos.items():
        parts.append(node_badge(kind, x, y, r=r))
    legend_x = 32
    for name, color in LAYER.items():
        parts.append(chip(legend_x, 520, name, color))
        legend_x += len(name) * 7 + 52
    return svg(1220, 562, "".join(parts), "The ontology map",
               "Nine node types connected by the ten allowed edge types, coloured by "
               "biological layer. A dashed line marks that a Pathogen is a kind of Organism, so "
               "a pathogen may also harbour gene clusters and sit in the family tree.")


def evidence_ladder() -> str:
    rows = [
        ("curated_experimental", "A curator recorded a published experiment",
         "MIBiG: this cluster makes surfactin", "treat as a measured fact", 5, ""),
        ("database_assertion", "A public database states it",
         "PubChem formula; MIBiG activity without a reference", "reliable reference data", 4, ""),
        ("curated_literature", "This project's own cited reading of a paper",
         "surfactin INHIBITS Botrytis cinerea (with DOI)", "trust it, check the citation", 3, ""),
        ("inferred", "Produced by an algorithm in this repository",
         "a link predicted in Phase 7", "a hypothesis, never a finding", 2, "7 6"),
    ]
    parts = [t(32, 46, "The four evidence levels, strongest first", size=22, weight=700),
             t(32, 70, "Every arrow carries one. A chain of arrows is only as strong as its weakest link.",
               size=14, fill=INK2)]
    for i, (level, meaning, example, use, sw, dash) in enumerate(rows):
        y = 100 + i * 88
        color = EVIDENCE[level]
        parts.append(rect(32, y, 916, 74, fill=SURFACE, stroke=HAIR, rx=12))
        parts.append(t(60, y + 30, f"{i + 1}", size=26, weight=700, fill=color))
        parts.append(line(96, y + 38, 196, y + 38, color=color, sw=sw, dash=dash))
        parts.append(t(220, y + 30, level, size=15, weight=700, family=MONO))
        parts.append(t(220, y + 54, meaning, size=13.5, fill=INK2))
        parts.append(t(560, y + 30, "e.g. " + example, size=13, fill=INK))
        parts.append(t(560, y + 54, "use: " + use, size=13, weight=600, fill=INK))
    parts.append(t(32, 470, "Line weight and dashes repeat the level, so it never depends on colour.",
                   size=12.5, fill=MUTED))
    return svg(980, 490, "".join(parts), "The evidence ladder",
               "Four evidence levels from curated_experimental (strongest) to inferred "
               "(a hypothesis), each with meaning, example and how to treat it.")


def _magnifier(cx: float, cy: float, c: str) -> str:
    return (f'<circle cx="{cx - 4}" cy="{cy - 4}" r="11" fill="none" stroke="{c}" stroke-width="3.5"/>'
            f'<line x1="{cx + 4}" y1="{cy + 4}" x2="{cx + 14}" y2="{cy + 14}" stroke="{c}" '
            f'stroke-width="4" stroke-linecap="round"/>')


def _download(cx: float, cy: float, c: str) -> str:
    return (f'<path d="M{cx} {cy - 14} V{cy + 6} M{cx - 8} {cy - 2} L{cx} {cy + 6} L{cx + 8} {cy - 2}" '
            f'stroke="{c}" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M{cx - 15} {cy + 4} V{cy + 14} H{cx + 15} V{cy + 4}" stroke="{c}" '
            f'stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def _table(cx: float, cy: float, c: str) -> str:
    out = [rect(cx - 16, cy - 13, 32, 26, stroke=c, sw=3, rx=3)]
    out.append(f'<line x1="{cx - 16}" y1="{cy - 4}" x2="{cx + 16}" y2="{cy - 4}" stroke="{c}" stroke-width="3"/>')
    out.append(f'<line x1="{cx - 16}" y1="{cy + 5}" x2="{cx + 16}" y2="{cy + 5}" stroke="{c}" stroke-width="2"/>')
    out.append(f'<line x1="{cx - 3}" y1="{cy - 13}" x2="{cx - 3}" y2="{cy + 13}" stroke="{c}" stroke-width="2"/>')
    return "".join(out)


def adapter_contract() -> str:
    sources = [("MIBiG", "Phase 1", True), ("PubChem", "Phase 2", True),
               ("NCBI Taxonomy", "Phase 2", True), ("KEGG", "Phase 2", True),
               ("curated bridge", "Phase 2", True), ("UniProt", "Phase 3", True)]
    parts = [t(32, 46, "One socket, many plugs: the adapter contract", size=22, weight=700),
             t(32, 70, "Every source fits the same three verbs, so adding one changes nothing downstream.",
               size=14, fill=INK2)]
    for i, (name, phase, built) in enumerate(sources):
        y = 104 + i * 54
        parts.append(rect(32, y, 210, 40, fill=SURFACE, stroke=INK2 if built else BASE, rx=10,
                          dash="" if built else "6 5"))
        parts.append(t(50, y + 25, name, size=14, weight=600 if built else 400,
                       fill=INK if built else INK2))
        parts.append(t(228, y + 25, phase, size=11.5, fill=MUTED, anchor="end"))
        parts.append(line(242, y + 20, 318, 252, color=INK2 if built else BASE, sw=2 if built else 1.5,
                          dash="" if built else "4 5"))
    # the socket
    parts.append(rect(322, 168, 196, 168, fill=PLANE, stroke=INK2, rx=18, sw=2))
    parts.append(t(420, 214, "the socket", size=15, weight=700, anchor="middle"))
    parts.append(t(420, 236, "sources/base.py", size=12, fill=INK2, anchor="middle", family=MONO))
    for k in range(3):
        parts.append(rect(366 + k * 38, 262, 14, 34, fill=INK2, rx=4))
    parts.append(t(420, 318, "probe · fetch · tidy", size=12, fill=INK2, anchor="middle", family=MONO))
    verbs = [("probe()", "What is out there?", "asks about version, size, limits and keys;",
              "downloads nothing", _magnifier),
             ("fetch()", "Bring it home, untouched.", "into data/raw/<source>/, fingerprinted,",
              "one provenance row for every file", _download),
             ("tidy()", "Make it fit the rulebook.", "reads only the locker, never the internet;",
              "writes staging CSVs that pass the 12 rules", _table)]
    for i, (name, q, l1, l2, draw) in enumerate(verbs):
        y = 108 + i * 108
        parts.append(line(518, 252, 586, y + 44, color=INK2, sw=2))
        parts.append(rect(590, y, 480, 88, fill=SURFACE, stroke=HAIR, rx=12))
        parts.append(f'<circle cx="{634}" cy="{y + 44}" r="28" fill="{PLANE}"/>')
        parts.append(draw(634, y + 44, LAYER["genomics"]))
        parts.append(t(680, y + 30, name, size=16, weight=700, family=MONO))
        parts.append(t(770, y + 30, q, size=14, fill=INK, style="italic"))
        parts.append(t(680, y + 54, l1, size=13, fill=INK2))
        parts.append(t(680, y + 74, l2, size=13, fill=INK2))
    parts.append(t(32, 440, "All six are built (Phases 1-3). A new source is one more plug.",
                   size=12.5, fill=MUTED))
    return svg(1100, 460, "".join(parts), "The adapter contract",
               "Six data sources plug into one socket that requires three functions: "
               "probe, fetch and tidy.")


def ingestion_flow() -> str:
    parts = [t(32, 46, "Phase 1, end to end: from Zenodo to staging tables", size=22, weight=700),
             t(32, 70, "Three commands. Each box is a file or a check you can open and inspect.",
               size=14, fill=INK2)]
    boxes = [
        (32, "Zenodo", "MIBiG 4.0 release", "record 14169073", "CC BY 4.0"),
        (262, "fetch", "download to .part", "verify the MD5", "then rename"),
        (492, "evidence locker", "data/raw/mibig/", "mibig_json_4.0.tar.gz", "never edited"),
        (722, "tidy (offline)", "read every entry", "check the 12 rules", "then write"),
        (952, "staging", "data/processed/staging/", "mibig_nodes.csv", "mibig_edges.csv"),
    ]
    y = 150
    for i, (x, head, a, b, c) in enumerate(boxes):
        locker = head == "evidence locker"
        parts.append(rect(x, y, 200, 132, fill=PLANE if locker else SURFACE,
                          stroke=INK2 if locker else HAIR, rx=14, sw=2 if locker else 1.5))
        parts.append(t(x + 100, y + 32, head, size=16, weight=700, anchor="middle"))
        for k, s in enumerate((a, b, c)):
            mono = "/" in s or "." in s
            parts.append(t(x + 100, y + 62 + k * 22, s, size=12.5 if mono else 13.5,
                           fill=INK2, anchor="middle", family=MONO if mono else FONT))
        if i < len(boxes) - 1:
            parts.append(line(x + 204, y + 66, x + 226, y + 66, color=INK2, sw=2.5))
    # commands above
    cmds = [(146, "--probe", "asks, downloads nothing"), (492 + 100, "--source mibig", "fetch + tidy"),
            (822, "--tidy-only --all", "re-run tidy, no network")]
    for cx, flag, note in cmds:
        parts.append(rect(cx - 112, 92, 224, 44, fill=SURFACE, stroke=LAYER["genomics"], rx=10, sw=1.5))
        parts.append(t(cx, 111, flag, size=12.5, weight=700, fill=LAYER["genomics"], anchor="middle",
                       family=MONO))
        parts.append(t(cx, 128, note, size=11.5, fill=INK2, anchor="middle"))
    # checksum branch
    parts.append(check_mark(290, 316, 10))
    parts.append(t(308, 321, "match: filed", size=12.5, fill=INK))
    parts.append(cross_mark(290, 344, 10))
    parts.append(t(308, 349, "mismatch: thrown away", size=12.5, fill=INK))
    # provenance
    parts.append(rect(492, 306, 200, 56, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(592, 328, "provenance.csv", size=13, weight=700, anchor="middle", family=MONO))
    parts.append(t(592, 348, "+1 row: what, where, when", size=12, fill=INK2, anchor="middle"))
    parts.append(line(592, 286, 592, 302, color=INK2, sw=2))
    parts.append(t(822, 320, "rule broken? nothing is written,", size=12.5, fill=INK2, anchor="middle"))
    parts.append(t(822, 340, "and the message says which rule", size=12.5, fill=INK2, anchor="middle"))
    parts.append(t(1052, 320, "+ mibig_summary.json", size=12, fill=INK2, anchor="middle", family=MONO))
    parts.append(t(1052, 340, "(the counts)", size=12, fill=INK2, anchor="middle"))
    return svg(1184, 390, "".join(parts), "Phase 1 ingestion flow",
               "Zenodo to fetch with checksum check, to the evidence locker and provenance "
               "log, to the offline tidy with rule checks, to staging tables.")


def checksum_fingerprint() -> str:
    parts = [t(32, 46, "A checksum is a fingerprint of a file", size=22, weight=700),
             t(32, 70, "Change one byte anywhere and the fingerprint changes completely.",
               size=14, fill=INK2)]
    rows = [("the file Zenodo published", "ce1736f4fac7168d85dae3b37c77d3d2", None, "listed on the record page"),
            ("your download, intact", "ce1736f4fac7168d85dae3b37c77d3d2", True, "identical: filed in the locker"),
            ("your download, one byte damaged", "8f04c1aa9be03d6e1c7f52d0b9e4a611", False,
             "different: thrown away")]
    for i, (label, digest, ok, verdict) in enumerate(rows):
        y = 100 + i * 70
        parts.append(rect(32, y, 270, 50, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(f'<path d="M50 {y + 12} h16 l8 8 v18 h-24 z" fill="{PLANE}" stroke="{INK2}" stroke-width="1.5"/>')
        parts.append(t(84, y + 30, label, size=13, fill=INK))
        parts.append(line(306, y + 25, 352, y + 25, color=INK2, sw=2))
        parts.append(t(329, y + 17, "MD5", size=10.5, weight=700, fill=MUTED, anchor="middle"))
        parts.append(rect(356, y + 6, 330, 38, fill=PLANE, stroke=HAIR, rx=8))
        parts.append(t(521, y + 30, digest, size=13, fill=INK if ok is not False else CRITICAL,
                       anchor="middle", family=MONO))
        if ok is True:
            parts.append(check_mark(714, y + 25, 11))
        elif ok is False:
            parts.append(cross_mark(714, y + 25, 11))
        parts.append(t(734 if ok is not None else 700, y + 30, verdict, size=13, fill=INK2))
    parts.append(t(32, 330, "Like counting a parcel against its packing slip before you sign for it.",
                   size=13, fill=INK2, style="italic"))
    return svg(1000, 350, "".join(parts), "How a checksum works",
               "The published MD5 matches an intact download and differs completely from a "
               "download with one damaged byte.")


def git_branch_model() -> str:
    parts = [t(32, 46, "Where your work goes: develop, then beta and master", size=22, weight=700),
             t(32, 70, "You only ever work on develop. One push updates all three branches on GitHub.",
               size=14, fill=INK2)]
    # laptop
    parts.append(rect(32, 100, 330, 230, fill=PLANE, stroke=INK2, rx=16, sw=2))
    parts.append(t(197, 128, "your computer", size=15, weight=700, anchor="middle"))
    parts.append(rect(62, 150, 270, 52, fill=SURFACE, stroke=LAYER["genomics"], rx=10, sw=2))
    parts.append(t(197, 173, "develop", size=15, weight=700, anchor="middle", family=MONO))
    parts.append(t(197, 192, "every change happens here", size=12, fill=INK2, anchor="middle"))
    parts.append(rect(62, 250, 270, 52, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(197, 273, "master", size=15, weight=700, anchor="middle", family=MONO))
    parts.append(t(197, 292, "kept in step, never edited", size=12, fill=INK2, anchor="middle"))
    # github
    parts.append(rect(640, 100, 330, 270, fill=PLANE, stroke=INK2, rx=16, sw=2))
    parts.append(t(805, 128, "GitHub (origin)", size=15, weight=700, anchor="middle"))
    for k, (name, note) in enumerate([("develop", "daily work, backed up"),
                                      ("beta", "finished phases"),
                                      ("master", "what visitors see")]):
        y = 146 + k * 72
        parts.append(rect(670, y, 270, 56, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(t(805, y + 24, f"origin/{name}", size=14, weight=700, anchor="middle", family=MONO))
        parts.append(t(805, y + 44, note, size=12, fill=INK2, anchor="middle"))
        parts.append(path(f"M336 176 C470 176 520 {y + 28} 666 {y + 28}", color=LAYER["genomics"], sw=2))
    parts.append(rect(376, 92, 250, 48, fill=SURFACE, stroke=LAYER["genomics"], rx=8))
    parts.append(t(501, 112, "git push origin develop", size=12, weight=700,
                   fill=LAYER["genomics"], anchor="middle", family=MONO))
    parts.append(t(501, 130, "develop:beta develop:master", size=12, weight=700,
                   fill=LAYER["genomics"], anchor="middle", family=MONO))
    parts.append(path("M666 330 C560 330 470 276 336 276", color=INK2, sw=2, dash="6 5"))
    parts.append(rect(376, 334, 250, 26, fill=SURFACE, rx=6))
    parts.append(t(501, 352, "git pull --ff-only origin master", size=12, weight=700, fill=INK2,
                   anchor="middle", family=MONO))
    parts.append(check_mark(604, 394, 9))
    parts.append(t(620, 399, "GitHub runs the tests whenever master changes (Actions tab)", size=12, fill=INK2))
    return svg(1000, 420, "".join(parts), "The three-branch model",
               "Work on local develop; one push updates origin develop, beta and master; "
               "local master is then fast-forwarded from origin master.")


def setup_flow() -> str:
    once = [("Python 3.11 or 3.12", "Step 1"), ("VS Code", "Step 2"), ("Git + your identity", "Step 3"),
            ("GitHub account", "Step 4"), ("token or SSH key", "Step 5"), ("clone the repository", "Step 6"),
            ("create the .venv toolbox", "Step 7"), ("install the packages", "Step 8 · requirements.txt"),
            ("install MicrobeGraph itself", "Step 8 · pip install -e ."),
            ("run the setup check", "Step 12 · check-setup.py")]
    every = ["activate .venv", "git switch develop", "build the phase", "pytest + ruff check",
             "git add -A", "./check-public-safe.sh", "git commit", "git push (all three)",
             "sync local master"]
    parts = [t(32, 46, "Set up once per machine, then repeat a short loop", size=22, weight=700),
             t(32, 70, "Setup is long exactly once. After it, every session uses the same nine steps.",
               size=14, fill=INK2)]
    parts.append(t(32, 106, "ONCE PER MACHINE  (docs/01-setup.md)", size=12.5, weight=700, fill=MUTED))
    for i, (step, where) in enumerate(once):
        col, row = i % 5, i // 5
        x, y = 32 + col * 230, 118 + row * 70
        parts.append(rect(x, y, 218, 56, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(f'<circle cx="{x + 22}" cy="{y + 28}" r="13" fill="{LAYER["genomics"]}"/>')
        parts.append(t(x + 22, y + 33, str(i + 1), size=12.5, weight=700, fill=SURFACE, anchor="middle"))
        mono = step.startswith(("pip", "python", "."))
        parts.append(t(x + 44, y + 25, step, size=11.5 if mono else 13, fill=INK,
                       family=MONO if mono else FONT))
        parts.append(t(x + 44, y + 44, where, size=11, fill=MUTED))
    parts.append(t(32, 292, "EVERY SESSION  (docs/HANDBOOK.md, section 'Every session')", size=12.5,
                   weight=700, fill=MUTED))
    cx, cy = 600, 410
    rx_, ry_ = 430, 92
    parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_ - 120}" ry="{ry_ - 34}" fill="none" '
                 f'stroke="{BASE}" stroke-width="2" stroke-dasharray="4 6"/>')
    parts.append(t(cx, cy - 4, "the loop", size=15, weight=700, fill=INK2, anchor="middle"))
    parts.append(t(cx, cy + 16, "a few minutes of ritual per session", size=12, fill=MUTED, anchor="middle"))
    for i, step in enumerate(every):
        a = -math.pi / 2 + 2 * math.pi * i / len(every)
        x, y = cx + rx_ * math.cos(a), cy + ry_ * math.sin(a)
        mono = step.startswith(("git", "./", "pytest"))
        w = 196
        parts.append(rect(x - w / 2, y - 17, w, 34, fill=SURFACE, stroke=HAIR, rx=17))
        parts.append(t(x - w / 2 + 18, y + 5, str(i + 1), size=12, weight=700, fill=LAYER["genomics"]))
        parts.append(t(x + 8, y + 5, step, size=11.5 if mono else 12.5, fill=INK, anchor="middle",
                       family=MONO if mono else FONT))
    return svg(1200, 530, "".join(parts), "Setup once, then the loop",
               "Ten one-time setup steps, then a repeating nine-step working loop.")


def journey_map() -> str:
    phases = list(csv.DictReader((DOCS / "phases.csv").open(encoding="utf-8")))
    groups = [("design", "Phase 0, design"), ("1.0", "Release 1.0, the science"),
              ("2.0", "Release 2.0, the platform"), ("3.0", "Release 3.0, the product")]
    parts = [t(32, 46, "The journey, day 0 to the finished product", size=22, weight=700),
             t(32, 70, "Every phase ends at a checkpoint with something working and committed.",
               size=14, fill=INK2)]
    y = 100
    for key, label in groups:
        members = [p for p in phases if p["release"] == key]
        rows = (len(members) + 5) // 6
        parts.append(t(32, y + 18, label, size=14, weight=700, fill=INK))
        core = [p for p in members if p["optional"] == "no"]
        extra = [p for p in members if p["optional"] == "yes"]
        hours = f"~{sum(int(p['effort_low']) for p in core)}-{sum(int(p['effort_high']) for p in core)} h"
        if extra:
            hours += (f"  (+{sum(int(p['effort_low']) for p in extra)}-"
                      f"{sum(int(p['effort_high']) for p in extra)} h optional)")
        parts.append(t(1168, y + 18, hours, size=12.5, fill=MUTED, anchor="end"))
        for i, p in enumerate(members):
            col, row = i % 6, i // 6
            x, yy = 32 + col * 190, y + 30 + row * 78
            done = p["status"] == "done"
            optional = p["optional"] == "yes"
            parts.append(rect(x, yy, 178, 66, fill=SURFACE, stroke=RELEASE[key], rx=12,
                              sw=2.2 if done else 1.6, dash="6 5" if optional else ""))
            parts.append(rect(x, yy, 6, 66, fill=RELEASE[key], rx=3))
            parts.append(t(x + 18, yy + 22, f"Phase {p['phase']}" + (" (optional)" if optional else ""),
                           size=11.5, weight=700, fill=INK2))
            parts.append(t(x + 18, yy + 44, p["short"], size=13.5, fill=INK))
            if done:
                parts.append(check_mark(x + 160, yy + 18, 9))
            else:
                parts.append(f'<circle cx="{x + 160}" cy="{yy + 18}" r="8" fill="none" '
                             f'stroke="{BASE}" stroke-width="2"/>')
            parts.append(t(x + 18, yy + 60, f"{p['effort_low']}-{p['effort_high']} h", size=10.5,
                           fill=MUTED))
        y += 46 + rows * 78
    parts.append(check_mark(42, y + 6, 8))
    parts.append(t(58, y + 11, "built and tested", size=12, fill=INK2))
    parts.append(f'<circle cx="190" cy="{y + 6}" r="7" fill="none" stroke="{BASE}" stroke-width="2"/>')
    parts.append(t(204, y + 11, "planned", size=12, fill=INK2))
    parts.append(rect(276, y - 4, 26, 20, fill="none", stroke=INK2, rx=5, dash="5 4"))
    parts.append(t(310, y + 11, "optional", size=12, fill=INK2))
    parts.append(t(1168, y + 11, "status is read from docs/phases.csv", size=11.5, fill=MUTED, anchor="end"))
    return svg(1200, int(y + 34), "".join(parts), "The MicrobeGraph journey",
               "All phases from Phase 0 to Phase 19, grouped into three releases, with "
               "status and hour estimates.")


def _screen(cx: float, cy: float, c: str) -> str:
    """A plain computer screen on a stand: any make, any system."""
    return (rect(cx - 13, cy - 11, 26, 18, stroke=c, sw=2.5, rx=3)
            + f'<path d="M{cx} {cy + 7} V{cy + 12} M{cx - 7} {cy + 12} H{cx + 7}" stroke="{c}" '
            f'stroke-width="2.5" fill="none" stroke-linecap="round"/>')


def ci_checks() -> str:
    """What one run on the Actions tab is made of: the trigger, the seven jobs, the five steps."""
    blue = LAYER["genomics"]
    parts = [t(32, 46, "What GitHub does with your code", size=22, weight=700),
             t(32, 70, "Seven fresh computers install MicrobeGraph from nothing and run the same "
               "checks you run at home.", size=14, fill=INK2)]
    # what starts a run
    parts.append(rect(32, 100, 236, 150, fill=PLANE, stroke=HAIR, rx=12))
    parts.append(t(48, 124, "A RUN STARTS WHEN", size=12, weight=700, fill=MUTED))
    for k, (what, how) in enumerate([("master changes", "your end-of-phase push"),
                                     ("you click Run workflow", "on the Actions tab"),
                                     ("a pull request opens", "someone proposes a change")]):
        y = 150 + k * 36
        parts.append(f'<circle cx="54" cy="{y - 4}" r="4" fill="{blue}"/>')
        parts.append(t(66, y, what, size=13, weight=700))
        parts.append(t(66, y + 16, how, size=11.5, fill=MUTED))
    parts.append(line(272, 175, 314, 175, color=blue))
    # the instructions
    parts.append(rect(318, 135, 150, 80, fill=SURFACE, stroke=blue, rx=12, sw=2))
    parts.append(t(393, 168, "ci.yml", size=16, weight=700, anchor="middle", family=MONO))
    parts.append(t(393, 190, "the instructions", size=12, fill=INK2, anchor="middle"))
    parts.append(line(472, 175, 498, 175, color=blue))
    parts.append(t(393, 238, "one copy goes to", size=11.5, fill=MUTED, anchor="middle"))
    parts.append(t(393, 253, "each of the seven", size=11.5, fill=MUTED, anchor="middle"))
    # the seven jobs
    jobs = [("Ubuntu Linux", "3.11"), ("Ubuntu Linux", "3.12"), ("Windows", "3.11"),
            ("Windows", "3.12"), ("macOS", "3.11"), ("macOS", "3.12")]
    for k, (system, py) in enumerate(jobs):
        x, y = 506 + (k % 2) * 237, 96 + (k // 2) * 56
        parts.append(rect(x, y, 225, 46, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(_screen(x + 26, y + 22, INK2))
        parts.append(t(x + 50, y + 20, system, size=13, weight=700))
        parts.append(t(x + 50, y + 37, f"Python {py}", size=11.5, fill=MUTED))
        parts.append(check_mark(x + 203, y + 23, 9))
    x, y = 506, 264
    parts.append(rect(x, y, 462, 46, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(_screen(x + 26, y + 22, INK2))
    parts.append(t(x + 50, y + 20, "RHEL 8 (Red Hat's UBI 8 container)", size=13, weight=700))
    parts.append(t(x + 50, y + 37, "Python 3.11, with RHEL 8's own system libraries", size=11.5, fill=MUTED))
    parts.append(check_mark(x + 440, y + 23, 9))
    # inside every job
    parts.append(t(32, 352, "INSIDE EVERY ONE OF THE SEVEN, IN THIS ORDER", size=12, weight=700, fill=MUTED))
    steps = [("get the code", "actions/checkout"), ("install Python", "actions/setup-python"),
             ("install the project", "pip install -e ."), ("style check", "ruff check ."),
             ("the tests", "pytest")]
    for k, (what, how) in enumerate(steps):
        x = 32 + k * 192
        parts.append(rect(x, 366, 168, 62, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(f'<circle cx="{x + 20}" cy="{386}" r="11" fill="{blue}"/>')
        parts.append(t(x + 20, 390.5, str(k + 1), size=12, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(x + 38, 391, what, size=13, weight=700))
        parts.append(t(x + 14, 416, how, size=11.5, fill=INK2, family=MONO))
        if k < len(steps) - 1:
            parts.append(line(x + 171, 397, x + 189, 397, color=BASE, sw=2))
    # reading the result
    parts.append(check_mark(44, 466, 9))
    parts.append(t(62, 471, "All seven green: the test badge at the top of the README turns green.",
                   size=13))
    parts.append(cross_mark(44, 496, 9))
    parts.append(t(62, 501, "One red: click it, open the step marked with a cross, and read what it says.",
                   size=13))
    return svg(1000, 528, "".join(parts), "What GitHub does with your code",
               "A push to master, the Run workflow button or a pull request starts a run. "
               "ci.yml sends one copy to each of seven machines: Ubuntu Linux, Windows and "
               "macOS with Python 3.11 and 3.12, and a RHEL 8 container with Python 3.11. "
               "Each one gets the code, installs Python and the project, runs ruff and "
               "then pytest.")


# =============================================================================
# Phase 2 figures
# =============================================================================
def _file_icon(x: float, y: float, c: str, fill: str = PLANE) -> str:
    """A small page with a folded corner, its top-left at (x, y)."""
    return (f'<path d="M{x} {y} h14 l6 6 v20 h-20 z" fill="{fill}" stroke="{c}" stroke-width="1.6" '
            f'stroke-linejoin="round"/><path d="M{x + 14} {y} v6 h6" fill="none" stroke="{c}" '
            f'stroke-width="1.6" stroke-linejoin="round"/>')


def _padlock(cx: float, cy: float, c: str) -> str:
    return (f'<path d="M{cx - 7} {cy - 2} v-6 a7 7 0 0 1 14 0 v6" fill="none" stroke="{c}" '
            f'stroke-width="2.6" stroke-linecap="round"/>'
            + rect(cx - 11, cy - 3, 22, 17, fill=c, rx=3)
            + f'<circle cx="{cx}" cy="{cy + 5}" r="2.4" fill="{SURFACE}"/>')


def _envelope(cx: float, cy: float, c: str) -> str:
    return (rect(cx - 18, cy - 12, 36, 24, fill=SURFACE, stroke=c, rx=3, sw=2.2)
            + f'<path d="M{cx - 18} {cy - 11} L{cx} {cy + 2} L{cx + 18} {cy - 11}" fill="none" '
            f'stroke="{c}" stroke-width="2.2" stroke-linejoin="round"/>')


def sources_map() -> str:
    """Phases 1-3: six sources, what each one needs first, and what each adds to the graph."""
    rows = [
        ("1", "MIBiG", "Phase 1 (gene records: Phase 3; protein file: Phase 3b)", "CC BY 4.0", GOOD,
         "needs: nothing",
         ["Organism", "GeneCluster", "Protein", "Compound", "CompoundClass", "Activity"],
         "HARBORS · PRODUCES · HAS_ACTIVITY · BELONGS_TO · ENCODES · CATALYZES"),
        ("2", "PubChem", "Phase 2", "no NCBI restrictions", GOOD, "needs: MIBiG's compound numbers",
         ["Compound"], "formula, structure, other names, KEGG and ChEBI numbers"),
        ("3", "NCBI Taxonomy", "Phase 2", "no NCBI restrictions", GOOD,
         "needs: MIBiG's organisms, the bridge's pathogens",
         ["Organism", "Pathogen"], "MEMBER_OF: strain > species > genus > ... > domain"),
        ("4", "KEGG", "Phase 2", "academic use only", CRITICAL, "needs: PubChem's KEGG numbers",
         ["Pathway"], "PARTICIPATES_IN: compound > pathway map"),
        ("5", "UniProt", "Phase 3", "CC BY 4.0", GOOD,
         "needs: the protein numbers in MIBiG's tables",
         ["Protein"], "what each enzyme is: names, organism, length, EC number, function"),
        ("6", "curated bridge", "Phase 2", "MIT, this repository", GOOD,
         "checked against: MIBiG and NCBI", ["Pathogen", "Crop"],
         "INHIBITS · INFECTS, every row cited (curated_literature)"),
    ]
    step, height = 108, 96
    parts = [t(32, 46, "Six sources, one graph", size=22, weight=700),
             t(32, 70, "They run in this order, because each one builds on what the ones above "
               "it wrote. Every licence is recorded.", size=14, fill=INK2)]
    parts.append(t(84, 104, "SOURCE, AND WHAT IT NEEDS FIRST", size=12, weight=700, fill=MUTED))
    parts.append(t(640, 104, "WHAT IT ADDS TO THE GRAPH", size=12, weight=700, fill=MUTED))
    for i, (num, name, phase, licence, lic_colour, needs, kinds, adds) in enumerate(rows):
        y = 118 + i * step
        parts.append(f'<circle cx="52" cy="{y + height / 2}" r="16" fill="{LAYER["genomics"]}"/>')
        parts.append(t(52, y + height / 2 + 5.5, num, size=14, weight=700, fill=SURFACE,
                       anchor="middle"))
        if i < len(rows) - 1:
            parts.append(line(52, y + height / 2 + 18, 52, y + step + height / 2 - 18,
                              color=BASE, sw=2, arrow=False))
        parts.append(rect(84, y, 470, height, fill=SURFACE, stroke=HAIR, rx=12))
        parts.append(t(104, y + 32, name, size=16, weight=700))
        parts.append(t(104, y + 54, phase, size=12, fill=MUTED))
        parts.append(t(104, y + 78, needs, size=13, fill=INK2))
        parts.append(chip(360, y + 14, licence, lic_colour, w=180, size=11.5))
        parts.append(line(558, y + height / 2, 628, y + height / 2, color=INK2, sw=2))
        parts.append(rect(632, y, 536, height, fill=PLANE, stroke=HAIR, rx=12))
        for k, kind in enumerate(kinds):
            cx = 676 + k * 86
            parts.append(f'<circle cx="{cx}" cy="{y + 27}" r="18" fill="{SURFACE}" '
                         f'stroke="{LAYER[NODE_INFO[kind][0]]}" stroke-width="2.2"/>')
            parts.append(icon(kind, cx, y + 27, 24))
            parts.append(t(cx, y + 60, kind, size=11, weight=600, anchor="middle"))
        parts.append(t(648, y + 84, adds, size=12, fill=INK2,
                       family=MONO if adds.isupper() or "_" in adds else FONT))
    y = 118 + len(rows) * step + 2
    parts.append(chip(84, y, "open: reuse allowed, with credit", GOOD, w=250, size=11.5))
    parts.append(chip(346, y, "academic use only: never in a public release", CRITICAL, w=330, size=11.5))
    parts.append(t(1168, y + 17, "python -m microbegraph.fetch --all runs 1 to 6", size=12, fill=MUTED,
                   anchor="end", family=MONO))
    return svg(1200, y + 46, "".join(parts), "Six sources, one graph",
               "MIBiG, PubChem, NCBI Taxonomy, KEGG, UniProt and the curated bridge, in the order "
               "they run, with what each needs first, its licence, and the node and edge types "
               "it adds. MIBiG's gene records (read from Phase 3) supply the ENCODES and "
               "CATALYZES arrows, its protein file (from Phase 3b) ENCODES arrows for every "
               "cluster; UniProt describes each enzyme.")


def secrets_env() -> str:
    """Phase 2: where an API key lives, how it travels, and every place it never goes."""
    blue = LAYER["genomics"]
    parts = [t(32, 46, "Where a key lives, and where it never goes", size=22, weight=700),
             t(32, 70, "One private file on your computer, one sealed trip to NCBI, and a gate that "
               "stops it reaching GitHub.", size=14, fill=INK2)]
    # your computer
    parts.append(rect(32, 96, 452, 300, fill=PLANE, stroke=INK2, rx=16, sw=2))
    parts.append(t(258, 124, "your computer", size=15, weight=700, anchor="middle"))
    parts.append(rect(56, 142, 404, 92, fill=SURFACE, stroke=blue, rx=12, sw=2))
    parts.append(_file_icon(74, 160, blue, fill=SURFACE))
    parts.append(t(106, 176, ".env", size=15, weight=700, family=MONO))
    parts.append(_padlock(430, 172, blue))
    parts.append(t(74, 206, "NCBI_API_KEY=a1b2...(36 characters)", size=12, fill=INK, family=MONO))
    parts.append(t(74, 224, "listed in .gitignore, so Git never sees it", size=12, fill=INK2))
    parts.append(line(258, 238, 258, 262, color=INK2, sw=2))
    parts.append(rect(56, 266, 404, 110, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(74, 292, "python -m microbegraph.fetch", size=13, weight=700, family=MONO))
    parts.append(t(74, 314, "reads .env when it starts", size=12.5, fill=INK2))
    parts.append(t(74, 340, "on screen:  API key : set", size=12.5, fill=INK, family=MONO))
    parts.append(t(74, 362, "never the key itself", size=12.5, fill=INK2))
    # the trip to NCBI
    parts.append(line(488, 186, 690, 186, color=blue, sw=2.5))
    parts.append(_envelope(589, 160, blue))
    parts.append(t(589, 210, "POST body (sealed)", size=12.5, weight=700, fill=blue, anchor="middle"))
    parts.append(t(589, 228, "id=..., api_key=...", size=11.5, fill=INK2, anchor="middle", family=MONO))
    parts.append(rect(694, 140, 274, 92, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(831, 172, "NCBI E-utilities", size=15, weight=700, anchor="middle"))
    parts.append(t(831, 194, "10 requests a second", size=12.5, fill=INK2, anchor="middle"))
    parts.append(t(831, 212, "instead of 3", size=12.5, fill=INK2, anchor="middle"))
    # github
    parts.append(rect(694, 262, 274, 134, fill=PLANE, stroke=INK2, rx=16, sw=2))
    parts.append(t(831, 288, "GitHub (public)", size=15, weight=700, anchor="middle"))
    parts.append(_file_icon(714, 302, INK2, fill=SURFACE))
    parts.append(t(744, 318, ".env.example", size=13, weight=700, family=MONO))
    parts.append(t(744, 336, "NCBI_API_KEY=   (empty)", size=11.5, fill=INK2, family=MONO))
    parts.append(cross_mark(726, 368, 9))
    parts.append(t(744, 373, ".env, or any key-shaped text", size=12, fill=INK))
    parts.append(path("M460 330 C560 330 600 360 690 366", color=CRITICAL, sw=2, dash="6 5"))
    parts.append(rect(500, 340, 178, 26, fill=SURFACE, rx=6))
    parts.append(t(589, 358, "check-public-safe.sh", size=12, weight=700, fill=CRITICAL, anchor="middle",
                   family=MONO))
    parts.append(t(589, 384, "stops the push", size=12, fill=INK2, anchor="middle"))
    # where it never goes
    parts.append(t(32, 434, "THE KEY IS NEVER", size=12, weight=700, fill=MUTED))
    never = ["in a web address", "in provenance.csv", "in a manifest", "on screen", "in a commit"]
    for k, where in enumerate(never):
        x = 32 + k * 190
        parts.append(cross_mark(x + 10, 460, 9))
        parts.append(t(x + 26, 465, where, size=13))
    parts.append(t(32, 500, "Without a key everything still works, just more slowly.", size=13,
                   fill=INK2, style="italic"))
    return svg(1000, 520, "".join(parts), "Where a key lives",
               "The NCBI key sits in .env on your computer, which Git ignores. The program reads "
               "it, shows only 'set', and sends it to NCBI inside a POST body. GitHub only ever "
               "gets .env.example with empty values, and the safety gate stops any push that "
               "contains a key.")


def api_snapshot() -> str:
    """Phase 2: how an answer from a web API is kept as evidence."""
    blue = LAYER["genomics"]
    parts = [t(32, 46, "An answer from an API, kept as evidence", size=22, weight=700),
             t(32, 70, "Answers change from day to day, so every fetch gets its own dated folder, and "
               "nothing in it is ever edited.", size=14, fill=INK2)]
    # the service
    parts.append(rect(32, 110, 196, 120, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(130, 142, "PubChem", size=16, weight=700, anchor="middle"))
    parts.append(t(130, 166, "24 questions,", size=12.5, fill=INK2, anchor="middle"))
    parts.append(t(130, 184, "100 compounds each,", size=12.5, fill=INK2, anchor="middle"))
    parts.append(t(130, 202, "paced under its limit", size=12.5, fill=INK2, anchor="middle"))
    parts.append(line(232, 170, 290, 170, color=INK2, sw=2.5))
    # the snapshot folder
    parts.append(rect(294, 96, 420, 268, fill=PLANE, stroke=INK2, rx=14, sw=2))
    parts.append(t(314, 124, "data/raw/pubchem/2026-10-12T055202Z/", size=13, weight=700, family=MONO))
    files = [("properties_001.json", "answer 1, as it arrived"),
             ("synonyms_001.json", "answer 2"),
             ("...", ""),
             ("synonyms_012.json", "answer 24")]
    for k, (name, note) in enumerate(files):
        y = 142 + k * 38
        if name == "...":
            parts.append(t(330, y + 22, "...", size=14, fill=MUTED))
            continue
        parts.append(_file_icon(314, y + 4, INK2, fill=SURFACE))
        parts.append(t(344, y + 21, name, size=12.5, family=MONO))
        parts.append(t(556, y + 21, note, size=11.5, fill=MUTED))
    parts.append(rect(310, 300, 388, 50, fill=SURFACE, stroke=blue, rx=10, sw=2))
    parts.append(_file_icon(324, 312, blue, fill=SURFACE))
    parts.append(t(354, 322, "manifest.json", size=13, weight=700, family=MONO))
    parts.append(t(354, 340, "what was asked; written LAST, so it marks 'finished'", size=11.5,
                   fill=INK2))
    # provenance
    parts.append(line(718, 230, 774, 230, color=INK2, sw=2))
    parts.append(rect(778, 186, 390, 88, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(798, 214, "provenance.csv", size=13.5, weight=700, family=MONO))
    parts.append(t(798, 238, "+1 row for every answer: when, from where,", size=12, fill=INK2))
    parts.append(t(798, 256, "size, and its SHA-256 fingerprint", size=12, fill=INK2))
    # the shelf over time
    parts.append(t(32, 410, "THE SHELF OVER TIME: tidy reads the newest FINISHED folder", size=12,
                   weight=700, fill=MUTED))
    shelf = [("2026-10-12T055202Z", "finished", True, ""),
             ("2026-10-12T091510Z", "no manifest: the line dropped, so tidy skips it", False, ""),
             ("2026-11-03T074005Z", "finished, newest: tidy reads this one", True, "newest")]
    for k, (name, note, ok, tag) in enumerate(shelf):
        x = 32 + k * 380
        parts.append(rect(x, 424, 364, 76, fill=SURFACE, stroke=blue if tag else HAIR, rx=12,
                          sw=2 if tag else 1.5, dash="" if ok else "6 5"))
        parts.append((check_mark if ok else cross_mark)(x + 24, 450, 10))
        parts.append(t(x + 44, 455, name, size=13, weight=700, family=MONO))
        parts.append(t(x + 20, 484, note, size=12, fill=INK2))
    parts.append(t(32, 532, "Same questions on the same day? The fetch reuses today's folder and asks "
                   "nothing. A new day, or new questions, makes a new folder.", size=12.5,
                   fill=INK2, style="italic"))
    return svg(1200, 552, "".join(parts), "An API answer kept as evidence",
               "PubChem's answers are saved byte for byte in a dated folder with a manifest "
               "written last, each answer gets a provenance row, and tidy reads the newest "
               "finished folder.")


# =============================================================================
# Phase 3 figures
# =============================================================================
def _edge_with_level(x1: float, x2: float, y: float, verb: str, level: str, note: str) -> str:
    """A horizontal arrow drawn in its evidence level's style, with its name and level."""
    width = {"curated_experimental": 4.5, "database_assertion": 3}[level]
    out = line(x1, y, x2, y, color=EVIDENCE[level], sw=width)
    out += t((x1 + x2) / 2, y - 14, verb, size=12.5, weight=700, fill=INK2, anchor="middle",
             family=MONO)
    out += t((x1 + x2) / 2, y + 24, level, size=11, fill=INK2, anchor="middle", family=MONO)
    if note:
        out += t((x1 + x2) / 2, y + 40, note, size=11, fill=MUTED, anchor="middle")
    return out


def protein_layer() -> str:
    """Phase 3: the protein route beside the PRODUCES shortcut, with surfactin's nine genes."""
    y = 222
    xs = {"Organism": 110, "GeneCluster": 340, "Protein": 610, "Compound": 880}
    names = {"Organism": ("FZB42", "ncbitaxon:326423"), "GeneCluster": ("BGC0000433", "mibig:BGC0000433"),
             "Protein": ("srfAA", "ncbiprotein:CAE02630.1"),
             "Compound": ("surfactin", "mg.compound:surfactin")}
    parts = [t(32, 46, "The protein layer: how a gene cluster makes its molecule", size=22, weight=700),
             t(32, 70, "MIBiG's gene records add the enzymes in between. UniProt then says what each "
               "enzyme is.", size=14, fill=INK2)]
    # the shortcut from Phase 1, over the top
    parts.append(path(f"M{xs['GeneCluster']} {y - 40} C{xs['GeneCluster'] + 90} {y - 128} "
                      f"{xs['Compound'] - 90} {y - 128} {xs['Compound']} {y - 42}", color=MUTED, sw=2,
                      dash="6 5"))
    parts.append(t((xs["GeneCluster"] + xs["Compound"]) / 2, y - 112,
                   "PRODUCES: the direct shortcut (Phase 1)", size=12, fill=MUTED, anchor="middle",
                   family=MONO))
    parts.append(_edge_with_level(xs["Organism"] + 40, xs["GeneCluster"] - 44, y, "HARBORS",
                                  "curated_experimental", ""))
    parts.append(_edge_with_level(xs["GeneCluster"] + 40, xs["Protein"] - 44, y, "ENCODES",
                                  "database_assertion", "MIBiG lists the gene in the cluster"))
    parts.append(_edge_with_level(xs["Protein"] + 40, xs["Compound"] - 44, y, "CATALYZES",
                                  "curated_experimental", "a knock-out showed its job"))
    for kind, x in xs.items():
        label, curie = names[kind]
        parts.append(node_badge(kind, x, y, label=label))
        parts.append(t(x, y + 72, curie, size=11, fill=INK2, anchor="middle", family=MONO, halo=True))
    # what UniProt adds, under the protein
    parts.append(line(xs["Protein"], y + 82, xs["Protein"], y + 112, color=LAYER["proteomics"], sw=2,
                      dash="4 4"))
    parts.append(t(xs["Protein"] + 10, y + 102, "ID mapping", size=11.5, weight=600,
                   fill=LAYER["proteomics"]))
    parts.append(rect(xs["Protein"] - 150, y + 116, 300, 104, fill=SURFACE, stroke=LAYER["proteomics"],
                      rx=12, sw=2))
    parts.append(t(xs["Protein"] - 134, y + 140, "UniProt: uniprot:Q70KJ7", size=13, weight=700,
                   family=MONO))
    parts.append(t(xs["Protein"] - 134, y + 162, "Surfactin synthetase A", size=13))
    parts.append(t(xs["Protein"] - 134, y + 182, "3,584 amino acids", size=12.5, fill=INK2))
    parts.append(t(xs["Protein"] - 134, y + 202, "unreviewed: made from the sequence record",
                   size=12, fill=INK2))
    # why both routes stay
    parts.append(rect(976, y - 44, 192, 136, fill=PLANE, stroke=HAIR, rx=12))
    parts.append(t(992, y - 18, "Why keep both?", size=13, weight=700))
    for k, s in enumerate(["PRODUCES says which", "cluster makes it.", "The protein route",
                           "says how."]):
        parts.append(t(992, y + 6 + k * 20, s, size=12.5, fill=INK2))
    # surfactin's nine gene records
    top = 480
    parts.append(t(32, top, "SURFACTIN'S NINE GENE RECORDS IN MIBiG 4.0 (BGC0000433)", size=12,
                   weight=700, fill=MUTED))
    genes = [("srfAA", "CAE02630.1", "Scaffold biosynthesis, knock-out", True),
             ("srfAB", "CAE02631.1", "Scaffold biosynthesis", True),
             ("srfAC", "CAE02633.1", "Scaffold biosynthesis", True),
             ("sfp", "CAE02638.1", "Activation / processing, knock-out", False),
             ("ycxD", "CAE02637.1", "Regulation", False),
             ("ycxc", "CAE02636.1", "Transport", False),
             ("comS", "CAE02632.1", "no job stated", False),
             ("srfAD", "CAE02634.1", "no job stated", False),
             ("yczE", "CAE02639.1", "no job stated", False)]
    for k, (gene, pid, job, builds) in enumerate(genes):
        col, row = k % 3, k // 3
        x, yy = 32 + col * 382, top + 14 + row * 58
        parts.append(rect(x, yy, 370, 48, fill=SURFACE, stroke=LAYER["proteomics"] if builds else HAIR,
                          rx=10, sw=2 if builds else 1.5))
        if builds:
            parts.append(check_mark(x + 22, yy + 24, 10))
        else:
            parts.append(f'<circle cx="{x + 22}" cy="{yy + 24}" r="9" fill="none" stroke="{BASE}" '
                         f'stroke-width="2"/>')
        parts.append(t(x + 42, yy + 21, gene, size=14, weight=700))
        parts.append(t(x + 100, yy + 21, pid, size=11.5, fill=INK2, family=MONO))
        parts.append(t(x + 42, yy + 39, job, size=12, fill=INK2))
    y_legend = top + 14 + 3 * 58 + 18
    parts.append(check_mark(42, y_legend, 9))
    parts.append(t(60, y_legend + 5, "builds the molecule: ENCODES and CATALYZES", size=12.5))
    parts.append(f'<circle cx="430" cy="{y_legend}" r="8" fill="none" stroke="{BASE}" stroke-width="2"/>')
    parts.append(t(446, y_legend + 5, "another job, or none stated: ENCODES only", size=12.5))
    parts.append(t(32, y_legend + 34, "From Phase 3b, MIBiG's protein file adds the cluster's other "
                   "14 proteins (CAE02619.1 to CAE02641.1), each with ENCODES only.", size=12.5,
                   fill=INK2, style="italic"))
    return svg(1200, int(y_legend + 56), "".join(parts), "The protein layer",
               "Bacillus velezensis FZB42 harbors cluster BGC0000433, which encodes the enzyme "
               "srfAA (CAE02630.1), which catalyzes a step in making surfactin; the direct "
               "PRODUCES arrow from Phase 1 stays as a shortcut. UniProt's ID mapping says "
               "CAE02630.1 is entry Q70KJ7, Surfactin synthetase A. Of the nine gene records in "
               "the surfactin entry, the three scaffold genes get a CATALYZES arrow and the other "
               "six get ENCODES only. From Phase 3b the protein file adds the cluster's other 14 "
               "proteins, with ENCODES only.")


def gene_jobs() -> str:
    """Phase 3: the seven jobs MIBiG gives genes, and which ones become CATALYZES arrows."""
    jobs = [("Scaffold biosynthesis", 964, True, "builds the backbone of the molecule"),
            ("Tailoring", 629, True, "changes the backbone once it exists"),
            ("Precursor biosynthesis", 398, True, "makes a building block the backbone needs"),
            ("Regulation", 231, False, "switches the cluster on or off"),
            ("Transport", 167, False, "carries the finished molecule out of the cell"),
            ("Activation / processing", 81, False, "switches the big enzymes on so they can work"),
            ("Resistance/immunity", 43, False, "protects the cell from its own product")]
    parts = [t(32, 46, "Seven jobs a gene can have in MIBiG", size=22, weight=700),
             t(32, 70, "Only the first three carry out a step in making the molecule, so only they "
               "give a CATALYZES arrow.", size=14, fill=INK2)]
    bar_x, bar_w, top = 250, 330, 104
    for i, (job, n, builds, what) in enumerate(jobs):
        y = top + i * 46
        colour = LAYER["proteomics"] if builds else BASE
        parts.append(t(32, y + 22, job, size=13.5, weight=700 if builds else 400))
        width = bar_w * n / jobs[0][1]
        parts.append(rect(bar_x, y + 6, width, 24, fill=colour, rx=5))
        parts.append(t(bar_x + width + 8, y + 23, f"{n:,}", size=12.5, weight=600, fill=INK2))
        parts.append(t(650, y + 23, what, size=13, fill=INK))
        parts.append(chip(990, y + 4, "CATALYZES" if builds else "ENCODES only",
                          LAYER["proteomics"] if builds else BASE, w=126, size=11.5))
    y = top + len(jobs) * 46 + 14
    parts.append(t(32, y, "Counts: jobs recorded across the 452 MIBiG 4.0 entries that have gene "
                   "records (one gene can have more than one job).", size=12, fill=MUTED))
    parts.append(t(32, y + 26, "On a car assembly line, the first three build the car; the other "
                   "four keep the line running.", size=13, fill=INK2, style="italic"))
    return svg(1150, int(y + 48), "".join(parts), "Seven jobs a gene can have in MIBiG",
               "Scaffold biosynthesis 964, Tailoring 629, Precursor biosynthesis 398 (these three "
               "give CATALYZES arrows); Regulation 231, Transport 167, Activation / processing 81, "
               "Resistance/immunity 43 (ENCODES only). Counts are jobs recorded in MIBiG 4.0.")


def idmapping_flow() -> str:
    """Phase 3: UniProt's ID mapping, a job with a ticket number, and what the snapshot keeps."""
    orange = LAYER["proteomics"]
    parts = [t(32, 46, "Asking UniProt: a job with a ticket number", size=22, weight=700),
             t(32, 70, "Like a busy cafe counter: hand in the order, take a number, ask if it's "
               "ready, collect.", size=14, fill=INK2)]
    boxes = [(32, "1", "Hand in the ids"), (422, "2", "Is it ready?"), (812, "3", "Collect")]
    for x, num, head in boxes:
        parts.append(rect(x, 96, 356, 262, fill=SURFACE, stroke=HAIR, rx=14))
        parts.append(f'<circle cx="{x + 26}" cy="{124}" r="14" fill="{orange}"/>')
        parts.append(t(x + 26, 129, num, size=14, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(x + 50, 130, head, size=16, weight=700))
    for k in range(2):
        x = 392 + k * 390
        parts.append(line(x, 226, x + 26, 226, color=INK2, sw=2.5))
    # 1: the order
    lines1 = [("POST /idmapping/run", True, 700), ("from = EMBL-GenBank-DDBJ_CDS", True, 400),
              ("to   = UniProtKB", True, 400), ("ids  = AAA16191.1,...,CAE02630.1,...", True, 400),
              ("(up to 10,000 ids per job from Phase 3b)", False, 400)]
    for k, (s, mono, w) in enumerate(lines1):
        parts.append(t(52, 160 + k * 22, s, size=12 if mono else 12.5, weight=w,
                       fill=INK if mono else MUTED, family=MONO if mono else FONT))
    parts.append(rect(52, 276, 316, 30, fill=PLANE, rx=8))
    parts.append(t(64, 296, 'answer: {"jobId": "8Pr33gbOw8"}', size=12, family=MONO))
    parts.append(_file_icon(54, 318, INK2, fill=SURFACE))
    parts.append(t(82, 334, "kept: insdc_001_job.json", size=12, fill=INK2, family=MONO))
    # 2: the waiting
    parts.append(t(442, 160, "GET /idmapping/status/8Pr33gbOw8", size=12, weight=700, family=MONO))
    parts.append(t(442, 180, "redirects turned off, so the answer is seen as sent", size=12,
                   fill=MUTED))
    parts.append(rect(442, 196, 240, 30, fill=PLANE, rx=8))
    parts.append(t(454, 216, '{"jobStatus": "RUNNING"}', size=12, family=MONO))
    parts.append(path("M682 203 C730 186 730 238 686 220", color=MUTED, sw=1.8))
    parts.append(t(454, 246, "not ready: wait 3 s, then ask again", size=11.5, fill=MUTED))
    parts.append(rect(442, 264, 316, 30, fill=PLANE, rx=8))
    parts.append(t(454, 284, 'HTTP 303 {"jobStatus": "FINISHED"}', size=12, family=MONO))
    parts.append(check_mark(772, 279, 9))
    parts.append(t(442, 334, "not kept: says nothing about proteins", size=12, fill=INK2))
    # 3: the results
    parts.append(t(832, 160, "GET .../uniprotkb/results/stream/", size=12, weight=700, family=MONO))
    parts.append(t(832, 178, "8Pr33gbOw8?format=tsv&fields=...", size=12, weight=700, family=MONO))
    table = [("From", "Entry", "Protein names", True), ("CAE02630.1", "Q70KJ7", "Surfactin synthetase A", None),
             ("CAE02631.1", "Q70KJ6", "Surfactin synthetase B", None), ("...", "", "", None)]
    for k, (a, b, c, head) in enumerate(table):
        yy = 202 + k * 20
        w = 700 if head else 400
        parts.append(t(832, yy, a, size=11.5, weight=w, family=MONO))
        parts.append(t(924, yy, b, size=11.5, weight=w, family=MONO))
        parts.append(t(990, yy, c, size=11.5, weight=w, fill=INK if head else INK2))
    parts.append(cross_mark(842, 288, 8))
    parts.append(t(858, 292, "XYZ99999.99: no row, so it didn't map", size=12, fill=INK))
    parts.append(_file_icon(834, 318, INK2, fill=SURFACE))
    parts.append(t(862, 334, "kept: insdc_001_results.tsv", size=12, fill=INK2, family=MONO))
    # the snapshot
    parts.append(t(32, 398, "WHAT THE SNAPSHOT HOLDS: data/raw/uniprot/<moment>/", size=12,
                   weight=700, fill=MUTED))
    files = ["insdc_001_job.json", "insdc_001_results.tsv", "...", "refseq_001_job.json",
             "refseq_001_results.tsv", "manifest.json"]
    for k, name in enumerate(files):
        x = 32 + k * 190
        if name == "...":
            parts.append(t(x + 60, 430, "...", size=14, fill=MUTED))
            continue
        last = name == "manifest.json"
        parts.append(_file_icon(x, 412, orange if last else INK2, fill=SURFACE))
        parts.append(t(x + 28, 428, name, size=11.5, weight=700 if last else 400, family=MONO))
    parts.append(t(32, 470, "tidy: asked minus answered = not mapped, counted and listed in "
                   "uniprot_summary.json. manifest.json is written last.", size=12.5, fill=INK2))
    return svg(1200, 494, "".join(parts), "Asking UniProt: a job with a ticket number",
               "Step 1 posts the identifiers to /idmapping/run and gets a job number, which is "
               "kept. Step 2 asks /idmapping/status without following redirects until the "
               "answer is HTTP 303 FINISHED; these answers are not kept. Step 3 downloads the "
               "results table, which is kept; an identifier with no row did not map.")


def protein_coverage() -> str:
    """Phase 3: how far the protein layer reaches, from the first real run (2026-10-12)."""
    orange = LAYER["proteomics"]
    rows = [
        ("Active MIBiG entries", [(452, "452 with gene records (19%)", orange),
                                  (1985, "1,985 without: Phase 3b covers them", MUTED)]),
        ("Their gene records", [(4089, "4,089 named by an INSDC or RefSeq number", orange),
                                (648, "648 by a locus tag or name: not looked up", MUTED)]),
        ("Numbers sent to UniProt", [(2449, "2,449 found: 2,442 UniProt entries", orange),
                                     (1640, "1,640 not found, all listed", MUTED)]),
        ("Gene records by job", [(1991, "1,991 build the molecule: CATALYZES", orange),
                                 (522, "522 other jobs", MUTED),
                                 (2224, "2,224 with no job recorded", BASE)]),
    ]
    x0, width, step = 330, 740, 96
    parts = [t(32, 46, "How far the protein layer reaches", size=22, weight=700),
             t(32, 70, "MIBiG 4.0 and UniProt release 2026_03, first run on 2026-10-12. Each bar is "
               "its own total.", size=14, fill=INK2)]
    for i, (label, segments) in enumerate(rows):
        y = 104 + i * step
        total = sum(n for n, _, _ in segments)
        parts.append(t(32, y + 28, label, size=14, weight=700))
        parts.append(t(1168, y + 28, f"{total:,}", size=14, weight=700, anchor="end"))
        x = x0
        for k, (n, text, colour) in enumerate(segments):
            w = width * n / total
            gap = 2 if k < len(segments) - 1 else 0
            parts.append(rect(x, y + 10, max(w - gap, 1), 28, fill=colour, rx=4))
            if k == len(segments) - 1 and k > 0:
                parts.append(t(x0 + width, y + 60, text, size=12.5, fill=INK, anchor="end"))
            else:
                parts.append(t(x, y + 60, text, size=12.5, fill=INK))
            x += w
    y = 104 + len(rows) * step + 4
    parts.append(t(32, y + 1, "Nothing grey is dropped: every part is counted, and the ids "
                   "UniProt didn't find are listed in uniprot_summary.json.", size=12.5, fill=INK2))
    parts.append(t(32, y + 26, "Every gene record becomes a Protein node with an ENCODES arrow, "
                   "whichever way it is named and whether or not UniProt knows it.", size=12.5,
                   fill=MUTED, style="italic"))
    return svg(1200, int(y + 52), "".join(parts), "How far the protein layer reaches",
               "Of 2,437 active MIBiG entries, 452 have gene records and 1,985 don't (Phase 3b "
               "covers them with MIBiG's protein file). "
               "Their 4,737 gene records: 4,089 named by an INSDC or RefSeq number, 648 by a "
               "locus tag or gene name. Of the 4,089 numbers sent to UniProt, 2,449 were found "
               "(2,442 entries) and 1,640 weren't. By job: 1,991 build the molecule and get "
               "CATALYZES arrows, 522 have other jobs, 2,224 have no job recorded.")


def fasta_header() -> str:
    """Phase 3b: one record of MIBiG's protein file, part by part, and what each part becomes."""
    orange, blue = LAYER["proteomics"], LAYER["genomics"]
    parts = [t(32, 46, "Reading one protein from MIBiG's protein file", size=22, weight=700),
             t(32, 70, "Each protein is two lines in a FASTA file: a header with seven parts, then "
               "its sequence, one letter per amino acid.", size=14, fill=INK2)]
    fields = [("0", "BGC0000433.5", "entry and version", blue),
              ("1", "c1", "record", MUTED),
              ("2", "8558-19312", "position", INK2),
              ("3", "+", "strand", INK2),
              ("4", "CAE02630.1", "label", INK2),
              ("5", "surfactin_synthetase_A", "product", INK2),
              ("6", "CAE02630.1", "protein number", orange)]
    size, char = 14, 8.45
    x, y = 46, 120
    parts.append(t(32, y + 26, ">", size=size + 2, weight=700, family=MONO))
    for k, (num, text, label, colour) in enumerate(fields):
        w = len(text) * char + 20
        parts.append(rect(x, y, w, 40, fill=SURFACE, stroke=colour, rx=8, sw=2))
        parts.append(t(x + w / 2, y + 26, text, size=size, family=MONO, anchor="middle"))
        parts.append(f'<circle cx="{x + w / 2:.1f}" cy="{y - 16}" r="11" fill="{colour}"/>')
        parts.append(t(x + w / 2, y - 11.5, num, size=12, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(x + w / 2, y + 60, label, size=12, fill=INK2, anchor="middle"))
        x += w
        if k < len(fields) - 1:
            parts.append(t(x + 6, y + 27, "|", size=size + 2, weight=700, fill=MUTED, family=MONO,
                           anchor="middle"))
            x += 12
    parts.append(rect(46, y + 80, 1122, 36, fill=PLANE, rx=8))
    parts.append(t(60, y + 104, "MEITFYPLTNAQKRIWYTEKFYPNTSISNLAGFGKLISEDGVQAHYVEKAIQEFVRRYES...",
                   size=size, family=MONO))
    parts.append(t(1154, y + 104, "3,584 letters", size=12.5, fill=INK2, anchor="end"))
    # what each part becomes
    top = y + 152
    parts.append(t(32, top, "WHAT MICROBEGRAPH KEEPS", size=12, weight=700, fill=MUTED))
    keeps = [
        ("part 6", "names the node", "ncbiprotein:CAE02630.1", "or mg.protein:<entry>-<name> when "
         "it isn't a number", orange),
        ("part 0", "the cluster that ENCODES it", "mibig:BGC0000433", "version 5, the same as the "
         "JSON entry", blue),
        ("part 4", "locus_tags, when it isn't part 6", "TSTA_117750 (for EED18001.1)", "a genome's own "
         "label for the gene", INK2),
        ("part 5", "product, with _ back to spaces", "surfactin synthetase A", "a gene record's own "
         "product wins", INK2),
        ("parts 2, 3", "locations", "BGC0000433:8558-19312:+", "one per place the file lists it", INK2),
        ("sequence", "sequence_length and sequence_md5", "3584, f8ecefd278c1a5e6...", "the letters "
         "stay in the file in the locker", INK2),
    ]
    for k, (which, becomes, example, note, colour) in enumerate(keeps):
        yy = top + 16 + k * 50
        parts.append(rect(32, yy, 1136, 42, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(f'<circle cx="52" cy="{yy + 21}" r="6" fill="{colour}"/>')
        parts.append(t(68, yy + 26, which, size=13, weight=700))
        parts.append(t(170, yy + 26, becomes, size=13))
        parts.append(t(440, yy + 26, example, size=12.5, family=MONO))
        parts.append(t(740, yy + 26, note, size=12, fill=MUTED))
    y_end = top + 16 + len(keeps) * 50 + 14
    parts.append(t(32, y_end, "Part 1 is always c1 in MIBiG 4.0 (each entry has one sequence record), "
                   "so it isn't kept.", size=12.5, fill=INK2))
    return svg(1200, int(y_end + 26), "".join(parts), "Reading one protein from MIBiG's protein file",
               "The header BGC0000433.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A|"
               "CAE02630.1 has seven parts: entry and version, record, position, strand, label, "
               "product and protein number, followed by the 3,584-letter sequence. Part 6 names "
               "the node ncbiprotein:CAE02630.1, part 0 is the cluster that encodes it, part 4 is "
               "kept as a locus tag when it differs, part 5 as the product, parts 2 and 3 as the "
               "location, and the sequence as its length and MD5 fingerprint.")


def protein_file_matching() -> str:
    """Phase 3b: what happens to one cluster's proteins, in three steps, with the real counts."""
    orange = LAYER["proteomics"]
    parts = [t(32, 46, "Every cluster's proteins, in three steps", size=22, weight=700),
             t(32, 70, "For each active entry, the curators' notes in the JSON are lined up with "
               "the proteins the file lists.", size=14, fill=INK2)]
    boxes = [(32, "1", "Leave out the curators' removals"),
             (422, "2", "Match each gene record"),
             (812, "3", "Add every other protein")]
    for x, num, head in boxes:
        parts.append(rect(x, 96, 356, 320, fill=SURFACE, stroke=HAIR, rx=14))
        parts.append(f'<circle cx="{x + 26}" cy="124" r="14" fill="{orange}"/>')
        parts.append(t(x + 26, 129, num, size=14, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(x + 50, 130, head, size=15, weight=700))
    for k in range(2):
        x = 392 + k * 390
        parts.append(line(x, 256, x + 26, 256, color=INK2, sw=2.5))

    def row(x: float, yy: float, mark: str, rule: str, example: str, n: str) -> None:
        parts.append(rect(x, yy, 316, 42, fill=PLANE, rx=8))
        parts.append(mark)
        parts.append(t(x + 32, yy + 18, rule, size=12.5, weight=600))
        parts.append(t(x + 32, yy + 35, example, size=11, fill=INK2, family=MONO))
        if n:
            parts.append(t(x + 306, yy + 27, n, size=13, weight=700, anchor="end"))

    def open_mark(x: float, y: float) -> str:
        return f'<circle cx="{x}" cy="{y}" r="7" fill="none" stroke="{BASE}" stroke-width="2"/>'

    # 1: removals
    parts.append(t(52, 162, "\"to_delete\" in the JSON, looked up among", size=12.5, fill=INK2))
    parts.append(t(52, 180, "the same entry's proteins:", size=12.5, fill=INK2))
    for k, (rule, example, n) in enumerate([("by number", "AFD30968.1", "4"),
                                            ("by product", "CrmK = CrmK", "2"),
                                            ("by word in product", "LOC100273419 (8 isoforms)", "12")]):
        yy = 196 + k * 48
        row(52, yy, cross_mark(68, yy + 21, 8), rule, example, n)
    for k, s1 in enumerate(["18 proteins left out, each listed with", "the curators' reason. 4 removals name",
                            "genes the file doesn't show: listed."]):
        parts.append(t(52, 358 + k * 18, s1, size=12.5))
    # 2: gene records
    parts.append(t(442, 162, "Each of the 4,737 gene records is looked", size=12.5, fill=INK2))
    parts.append(t(442, 180, "up the same way (a product only if unique):", size=12.5, fill=INK2))
    for k, (rule, example, n, ok) in enumerate([
            ("by number or label", "TSTA_117750 > EED18001.1", "4,661", True),
            ("by one product", "nisA = NisA > ADJ56352.1", "17", True),
            ("not in the file", "baeB, mscA, ...", "59", False)]):
        yy = 196 + k * 48
        row(442, yy, check_mark(458, yy + 21, 8) if ok else open_mark(458, yy + 21),
            rule, example, n)
    for k, s1 in enumerate(["Found: the node takes the file's number,", "so 452 locus tags and names gain one.",
                            "Not found: kept as in Phase 3, listed."]):
        parts.append(t(442, 358 + k * 18, s1, size=12.5))
    # 3: everything else
    parts.append(t(832, 162, "Each remaining protein becomes a", size=12.5, fill=INK2))
    parts.append(t(832, 180, "Protein node with an ENCODES arrow.", size=12.5, fill=INK2))
    for k, (rule, result) in enumerate([("same protein as a gene record", "one node, one arrow"),
                                        ("same protein twice in a cluster", "one node, both positions"),
                                        ("same protein in two clusters", "one node, two arrows")]):
        yy = 196 + k * 48
        row(832, yy, check_mark(848, yy + 21, 8, color=orange), rule, result, "")
    for k, s1 in enumerate(["The 661 genes the curators added", "(\"to_add\") are already in the file, with",
                            "sequences, and arrive here."]):
        parts.append(t(832, 358 + k * 18, s1, size=12.5))
    # the arithmetic
    top = 448
    parts.append(t(32, top, "THE REAL NUMBERS, MIBiG 4.0", size=12, weight=700, fill=MUTED))
    flow = [("46,987", "proteins in the file", INK), ("- 6,978", "in 199 pending entries", MUTED),
            ("- 18", "removed by curators", CRITICAL), ("- 2", "repeats in one cluster", MUTED),
            ("+ 59", "gene records not in the file", MUTED),
            ("= 40,048", "ENCODES arrows", orange), ("40,037", "Protein nodes", orange)]
    x = 32
    for k, (n, label, colour) in enumerate(flow):
        w = 154 if k < len(flow) - 1 else 180
        parts.append(rect(x, top + 14, w, 66, fill=SURFACE, stroke=colour if colour not in (INK, MUTED)
                          else HAIR, rx=10, sw=2 if colour == orange else 1.5))
        parts.append(t(x + w / 2, top + 44, n, size=17, weight=700, fill=colour if colour != MUTED
                       else INK2, anchor="middle"))
        parts.append(t(x + w / 2, top + 66, label, size=10.5, fill=INK2, anchor="middle"))
        x += w + 8
    parts.append(t(32, top + 108, "40,048 arrows but 40,037 nodes: 11 proteins are encoded by two "
                   "clusters each. CATALYZES still comes only from gene records.", size=12.5,
                   fill=INK2))
    return svg(1200, top + 130, "".join(parts), "Every cluster's proteins, in three steps",
               "Step 1 leaves out the proteins MIBiG's curators removed: 18 found by number, gene "
               "name in the product, or NCBI gene number inside the product; 4 removals name genes "
               "the file doesn't show. Step 2 matches each gene record: 4,661 by number or label, "
               "17 by a single matching product, 59 not in the file. Step 3 adds every other "
               "protein. From 46,987 proteins in the file: minus 6,978 in pending entries, minus "
               "18 removed, minus 2 repeats, plus 59 gene records not in the file, gives 40,048 "
               "ENCODES arrows to 40,037 Protein nodes.")


# The UniProt numbers in protein_file_coverage() come from the real Phase 3b run.
UNIPROT_3B = {"asked": 39_053, "mapped": 20_671, "entries": 20_507, "release": "2026_03"}


def protein_file_coverage() -> str:
    """Phase 3b: the protein layer before and after MIBiG's protein file, from the real runs."""
    orange = LAYER["proteomics"]
    mapped = UNIPROT_3B["mapped"]
    rows = [
        ("Active entries with proteins", 452, 2437, "all 2,437 active entries"),
        ("Protein nodes", 4737, 40037, "39,053 with an INSDC or RefSeq number"),
        ("ENCODES arrows", 4737, 40048, "11 proteins sit in two clusters"),
        ("Numbers sent to UniProt", 4089, 39053, "10,000 per job: still 5 jobs"),
        ("Numbers UniProt found", 2449, mapped, "the rest are listed, not dropped"),
        ("CATALYZES arrows", 4492, 4492, "unchanged: only gene records give jobs"),
    ]
    parts = [t(32, 46, "How far the protein layer reaches now", size=22, weight=700),
             t(32, 70, "Phase 3 read MIBiG's gene records; Phase 3b adds MIBiG's protein file. "
               "Each row has its own scale.", size=14, fill=INK2)]
    x0, width, step = 330, 600, 74
    parts.append(chip(330, 88, "Phase 3: gene records only", BASE, w=220, size=11.5))
    parts.append(chip(564, 88, "Phase 3b: with the protein file", orange, w=250, size=11.5))
    for i, (label, before, after, note) in enumerate(rows):
        y = 132 + i * step
        top_value = max(before, after or 0) or 1
        parts.append(t(32, y + 18, label, size=14, weight=700))
        parts.append(t(32, y + 38, note, size=11.5, fill=MUTED))
        parts.append(rect(x0, y + 4, max(width * before / top_value, 2), 18, fill=BASE, rx=4))
        parts.append(t(x0 + width * before / top_value + 8, y + 18, f"{before:,}", size=12.5,
                       fill=INK2))
        if after is None:
            parts.append(t(x0, y + 44, "after the real run", size=12.5, fill=MUTED, style="italic"))
        else:
            parts.append(rect(x0, y + 28, max(width * after / top_value, 2), 18, fill=orange, rx=4))
            parts.append(t(x0 + width * after / top_value + 8, y + 42, f"{after:,}", size=12.5,
                           weight=700))
    y = 132 + len(rows) * step + 8
    release = UNIPROT_3B["release"] or "the release of the run"
    parts.append(t(32, y, f"MIBiG 4.0 (fixed by the pins); UniProt {release}. UniProt's numbers "
                   "can move a little with each release.", size=12.5, fill=INK2))
    return svg(1200, int(y + 26), "".join(parts), "How far the protein layer reaches now",
               "Phase 3 against Phase 3b: active entries with proteins 452 against 2,437; Protein "
               "nodes 4,737 against 40,037; ENCODES arrows 4,737 against 40,048; numbers sent to "
               f"UniProt 4,089 against 39,053; numbers UniProt found 2,449 against "
               f"{mapped if mapped is not None else 'the real run'}; CATALYZES arrows 4,492 in both.")


# The numbers in the Phase 4 figures come from the real run of 2026-10-12
# (MIBiG 4.0, UniProt 2026_03), as docs/06-entity-resolution-graph-build.md shows.
PHASE4 = {
    "sources": [("mibig", 47_907), ("pubchem", 1_171), ("ncbi_taxonomy", 2_457),
                ("kegg", 39), ("uniprot", 20_507), ("curation", 11)],
    "rows": 72_092, "identifiers": 70_613, "nodes": 48_264, "edges": 57_012,
    "edges_read": 57_111, "ledger": 23_989, "left_out": 347,
}


def resolution_flow() -> str:
    """Phase 4: six sources' tables become one graph, with every decision in the ledger."""
    green = LAYER["metabolomics"]
    parts = [t(32, 46, "From six sources to one graph", size=22, weight=700),
             t(32, 70, "The resolver decides which records are the same thing, writes every "
               "decision down, and the build loads the result twice.", size=14, fill=INK2)]
    # 1. the six staging tables
    parts.append(t(32, 108, "1  SIX SOURCES' TABLES", size=12, weight=700, fill=MUTED))
    for i, (name, n) in enumerate(PHASE4["sources"]):
        y = 120 + i * 50
        parts.append(rect(32, y, 220, 40, fill=SURFACE, stroke=HAIR, rx=8))
        parts.append(_table(52, y + 20, INK2))
        parts.append(t(74, y + 25, name, size=13, weight=600, family=MONO))
        parts.append(t(240, y + 25, f"{n:,}", size=13, anchor="end"))
    parts.append(t(32, 440, f"{PHASE4['rows']:,} node rows for", size=12.5, fill=INK2))
    parts.append(t(32, 458, f"{PHASE4['identifiers']:,} identifiers", size=12.5, fill=INK2))
    # 2. the rules
    parts.append(t(300, 108, "2  THE RULES, IN ORDER", size=12, weight=700, fill=MUTED))
    groups = [
        ("Organisms", LAYER["genomics"], ["same identifier, several sources: 1,478",
                                          "NCBI's merged numbers moved: 7",
                                          "organism and pathogen: 2"]),
        ("Compounds", LAYER["metabolomics"], ["PubChem number confirmed: 1,105",
                                              "kept apart: 81 (names or formulas)",
                                              "same NPAtlas number and formula: 3"]),
        ("Proteins", LAYER["proteomics"], ["UniProt entry joined: 20,629",
                                           "same sequence, same organism: 220",
                                           "gene name confirmed by UniProt: 38"]),
    ]
    for i, (head, colour, lines_) in enumerate(groups):
        y = 120 + i * 110
        parts.append(rect(300, y, 330, 96, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(rect(300, y, 6, 96, fill=colour, rx=3))
        parts.append(t(320, y + 26, head, size=15, weight=700))
        for k, text in enumerate(lines_):
            parts.append(t(320, y + 50 + k * 19, text, size=12.5, fill=INK2))
    parts.append(t(300, 458, "Anything the evidence can't settle stays apart.", size=12.5,
                   fill=INK2))
    for y in (290,):
        parts.append(line(258, y, 292, y, color=INK2, sw=2.5))
        parts.append(line(636, y, 670, y, color=INK2, sw=2.5))
    # 3. the outputs
    parts.append(t(680, 108, "3  WHAT IT WRITES", size=12, weight=700, fill=MUTED))
    outs = [("nodes.csv", f"{PHASE4['nodes']:,} nodes"), ("edges.csv", f"{PHASE4['edges']:,} arrows"),
            ("resolution_ledger.csv", f"{PHASE4['ledger']:,} decisions, each with grounds")]
    for i, (name, what) in enumerate(outs):
        y = 120 + i * 58
        parts.append(rect(680, y, 330, 48, fill=SURFACE, stroke=green if i == 2 else HAIR,
                          rx=8, sw=2 if i == 2 else 1.5))
        parts.append(_file_icon(694, y + 10, INK2))
        parts.append(t(722, y + 21, name, size=13, weight=600, family=MONO))
        parts.append(t(722, y + 39, what, size=12, fill=INK2))
    parts.append(t(680, 314, "the twelve rules run again: all pass", size=12.5, weight=600))
    parts.append(check_mark(990, 310, 9))
    # 4. the two shapes
    parts.append(line(845, 324, 845, 350, color=INK2, sw=2.5))
    parts.append(rect(680, 356, 160, 70, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(760, 384, "DuckDB", size=15, weight=700, anchor="middle"))
    parts.append(t(760, 406, "tables, for SQL", size=12, fill=INK2, anchor="middle"))
    parts.append(rect(850, 356, 160, 70, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(930, 384, "NetworkX", size=15, weight=700, anchor="middle"))
    parts.append(t(930, 406, "a graph, for walking", size=12, fill=INK2, anchor="middle"))
    parts.append(t(680, 452, f"Counted in both, type by type: {PHASE4['nodes']:,} and "
                   f"{PHASE4['edges']:,} in each.", size=12.5, fill=INK2))
    return svg(1040, 476, "".join(parts), "From six sources to one graph",
               f"Six staging tables ({PHASE4['rows']:,} node rows, {PHASE4['identifiers']:,} "
               "identifiers) go through the organism, compound and protein rules. The resolver "
               f"writes nodes.csv ({PHASE4['nodes']:,} nodes), edges.csv ({PHASE4['edges']:,} "
               f"arrows) and the ledger ({PHASE4['ledger']:,} decisions), checks the twelve rules, "
               "and the build loads the result into DuckDB and NetworkX with matching counts.")


def pubchem_check() -> str:
    """Phase 4: how a PubChem number MIBiG gives is confirmed, with the real counts and examples."""
    green, red = GOOD, CRITICAL
    parts = [t(32, 46, "Is MIBiG's PubChem number right?", size=22, weight=700),
             t(32, 70, "A shared number isn't enough on its own. A second, independent clue must "
               "agree before two records become one node.", size=14, fill=INK2)]
    # the question boxes
    parts.append(rect(32, 96, 300, 60, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(48, 122, "MIBiG gives a compound a", size=13.5))
    parts.append(t(48, 142, "PubChem number (1,186 compounds)", size=13.5, weight=700))
    rows = [
        ("Only one MIBiG name on the number", "Does PubChem list the name, OR do the formulas agree?",
         [("name and formula", "637", True), ("name only", "135", True),
          ("formula only", "325", True), ("neither", "64", False)]),
        ("Several MIBiG names on one number", "Each name must be one PubChem lists: isomers share formulas",
         [("name confirmed", "8", True), ("name not listed", "12", False)]),
        ("A number PubChem doesn't have", "Nothing to compare with",
         [("kept apart, listed", "5", False)]),
    ]
    y = 176
    for head, test, outcomes in rows:
        parts.append(line(182, y - 14, 182, y + 4, color=INK2, sw=2))
        parts.append(rect(32, y + 6, 620, 66 + 26 * ((len(outcomes) + 1) // 2), fill=SURFACE,
                          stroke=HAIR, rx=10))
        parts.append(t(48, y + 30, head, size=14, weight=700))
        parts.append(t(48, y + 50, test, size=12.5, fill=INK2))
        for k, (label, n, ok) in enumerate(outcomes):
            cx = 48 + (k % 2) * 300
            cy = y + 74 + (k // 2) * 26
            parts.append(check_mark(cx + 8, cy - 4, 8, green) if ok else cross_mark(cx + 8, cy - 4, 8, red))
            parts.append(t(cx + 24, cy, f"{label}: {n}", size=12.5,
                           weight=700 if not ok else 400))
        y += 66 + 26 * ((len(outcomes) + 1) // 2) + 22
    # the examples on the right
    ex_x = 690
    parts.append(t(ex_x, 108, "THREE REAL CASES", size=12, weight=700, fill=MUTED))
    cases = [
        ("erythromycin and erythromycin A", "both give CID 12560, and PubChem lists",
         "both names: one node", True),
        ("bacillomycin D", "gives the number of PubChem's \"Bacillomycin Fc\":",
         "C49H76N10O15 against C52H84N12O14", False),
        ("minutissamides B and C", "both give the number of minutissamide D:",
         "same formula, different molecules", False),
    ]
    for i, (name, l1, l2, ok) in enumerate(cases):
        cy = 122 + i * 96
        parts.append(rect(ex_x, cy, 340, 84, fill=SURFACE, stroke=green if ok else red, rx=10,
                          sw=1.8))
        parts.append(check_mark(ex_x + 22, cy + 24, 9, green) if ok
                     else cross_mark(ex_x + 22, cy + 24, 9, red))
        parts.append(t(ex_x + 40, cy + 29, name, size=13.5, weight=700))
        parts.append(t(ex_x + 18, cy + 52, l1, size=12, fill=INK2))
        parts.append(t(ex_x + 18, cy + 70, l2, size=12, fill=INK2,
                       family=MONO if "C49" in l2 else FONT))
    parts.append(t(ex_x, 432, "Kept apart: the MIBiG compound stays as it", size=12.5))
    parts.append(t(ex_x, 450, "was, and its number moves to", size=12.5))
    parts.append(t(ex_x, 468, "pubchem_cid_not_confirmed.", size=12.5, family=MONO))
    height = max(y, 490)
    return svg(1060, int(height), "".join(parts), "Is MIBiG's PubChem number right?",
               "1,186 MIBiG compounds give a PubChem number. With one name on a number, a "
               "matching name or formula confirms it: 637 both, 135 name only, 325 formula only, "
               "64 neither and kept apart. With several names on one number, each name must be "
               "listed by PubChem: 8 confirmed, 12 not. 5 numbers PubChem doesn't have. Examples: "
               "erythromycin and erythromycin A joined; bacillomycin D's number belongs to "
               "Bacillomycin Fc, with a different formula; minutissamides B and C share D's number "
               "and formula but are different molecules.")


def uniprot_choice() -> str:
    """Phase 4: one protein number with several UniProt entries, decided step by step."""
    orange = LAYER["proteomics"]
    parts = [t(32, 46, "Which UniProt entry is this protein?", size=22, weight=700),
             t(32, 70, "UniProt lists each protein number under one or more entries. One entry "
               "joins at once; several need a reason to pick one.", size=14, fill=INK2)]
    parts.append(rect(32, 96, 300, 96, fill=SURFACE, stroke=HAIR, rx=10))
    parts.append(t(48, 124, "20,671 protein numbers", size=16, weight=700))
    parts.append(t(48, 146, "found in UniProt (release 2026_03)", size=12.5, fill=INK2))
    parts.append(t(48, 172, "UniProt's own cross-reference", size=12.5, fill=INK2))
    parts.append(line(332, 128, 380, 128, color=INK2, sw=2.5))
    parts.append(rect(388, 100, 300, 56, fill=SURFACE, stroke=orange, rx=10, sw=2))
    parts.append(check_mark(410, 128, 9, orange))
    parts.append(t(428, 124, "one entry: joins it", size=14, weight=700))
    parts.append(t(428, 144, "20,589 numbers", size=12.5, fill=INK2))
    parts.append(line(182, 192, 182, 226, color=INK2, sw=2.5))
    parts.append(t(196, 214, "several entries: 82 numbers", size=12.5, weight=600))
    steps = [("1", "the entry for the cluster's organism", "33", "WP_012444311.1 > Q8KWW8"),
             ("2", "of those, the one as long as MIBiG's sequence", "2", "NP_851152.1 > F4K051"),
             ("3", "of those, the one a curator reviewed", "5", "XP_001798919.1 > Q0UI04")]
    for i, (num, rule, n, example) in enumerate(steps):
        y = 234 + i * 72
        parts.append(rect(32, y, 656, 60, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(f'<circle cx="58" cy="{y + 30}" r="14" fill="{orange}"/>')
        parts.append(t(58, y + 35, num, size=14, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(84, y + 26, rule, size=13.5, weight=600))
        parts.append(t(84, y + 46, example, size=12, fill=INK2, family=MONO))
        parts.append(t(672, y + 36, f"{n} joined", size=13.5, weight=700, anchor="end"))
    y = 234 + 3 * 72
    parts.append(rect(32, y, 656, 60, fill=SURFACE, stroke=CRITICAL, rx=10, sw=1.8))
    parts.append(cross_mark(58, y + 30, 11))
    parts.append(t(84, y + 26, "still not one: the number stays on its own", size=13.5,
                   weight=600))
    parts.append(t(84, y + 46, "26 with no entry for the organism, 16 with equal ties",
                   size=12, fill=INK2))
    parts.append(t(672, y + 36, "42 kept apart", size=13.5, weight=700, anchor="end"))
    parts.append(t(720, 250, "Several numbers can choose one entry:", size=12.5))
    parts.append(t(720, 268, "the same protein submitted twice.", size=12.5))
    parts.append(t(720, 286, "It becomes one node, encoded by", size=12.5))
    parts.append(t(720, 304, "every cluster that lists it.", size=12.5))
    parts.append(t(720, 340, "An entry no number chooses is left", size=12.5))
    parts.append(t(720, 358, "out of the graph (278 entries), and", size=12.5))
    parts.append(t(720, 376, "the ledger says which numbers", size=12.5))
    parts.append(t(720, 394, "led to it.", size=12.5))
    return svg(1000, y + 84, "".join(parts), "Which UniProt entry is this protein?",
               "Of 20,671 protein numbers UniProt found, 20,589 have one entry and join it. 82 have "
               "several: 33 are decided by the cluster's organism, 2 more by sequence length, 5 "
               "more by review status, and 42 stay on their own. 278 entries no number chose are "
               "left out of the graph.")


def ledger_row() -> str:
    """Phase 4: one real row of the resolution ledger, column by column."""
    parts = [t(32, 46, "One decision, written down", size=22, weight=700),
             t(32, 70, "A real row of data/processed/resolution_ledger.csv, about bacillomycin D, "
               "read column by column.", size=14, fill=INK2)]
    grounds = ["MIBiG gives CID 3086563; PubChem doesn't list the name 'bacillomycin D'",
               "(its title is 'Bacillomycin Fc'); the formulas differ (MIBiG C49H76N10O15,",
               "PubChem C52H84N12O14). Nothing besides the number confirms it, so the two",
               "stay apart."]
    cols = [
        ("rule", ["pubchem_number_confirmed"], "which rule decided"),
        ("decision", ["kept_apart"], "what was decided (one of five kinds)"),
        ("identifier", ["mg.compound:bacillomycin-d"], "the record this row is about"),
        ("node_id", ["mg.compound:bacillomycin-d"], "where it ended up: its own node"),
        ("compared_with", ["pubchem.compound:3086563"], "the record it wasn't joined to"),
        ("node_type", ["Compound"], "what kind of thing"),
        ("grounds", grounds, "the evidence, in sentences"),
        ("sources", ["mibig|pubchem"], "whose records were compared"),
    ]
    y = 96
    for k, (name, values, meaning) in enumerate(cols):
        height = 12 + 22 * len(values)
        if k % 2 == 1:
            parts.append(rect(32, y, 1036, height, fill=PLANE, rx=6))
        parts.append(t(46, y + 23, name, size=13, weight=700, family=MONO))
        for i, value in enumerate(values):
            parts.append(t(190, y + 23 + i * 22, value, size=12.5, family=MONO))
        parts.append(t(830, y + 23, meaning, size=12, fill=INK2))
        y += height + 4
    parts.append(t(32, y + 22, "Look up any identifier in the identifier column to see where it "
                   "went; look up a node in node_id to see what became it.", size=12.5, fill=INK2))
    parts.append(t(32, y + 44, "The query cookbook has both as recipes (R5 and R6), and R7 "
                   "counts every refusal by rule.", size=12.5, fill=INK2))
    return svg(1100, int(y + 66), "".join(parts), "One decision, written down",
               "A ledger row: rule pubchem_number_confirmed, decision kept_apart, identifier and "
               "node_id mg.compound:bacillomycin-d, compared with pubchem.compound:3086563, node "
               "type Compound, grounds explaining that PubChem's title is Bacillomycin Fc and the "
               "formulas differ, sources mibig and pubchem.")


def two_shapes() -> str:
    """Phase 4: the same facts as SQL tables (DuckDB) and as a walkable graph (NetworkX)."""
    blue, green = LAYER["genomics"], LAYER["metabolomics"]
    parts = [t(32, 46, "Two shapes of the same facts", size=22, weight=700),
             t(32, 70, "DuckDB holds the truth as tables; the NetworkX graph is rebuilt from it "
               "on every load and never edited.", size=14, fill=INK2)]
    # left: the tables
    parts.append(rect(32, 96, 470, 300, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(52, 124, "DuckDB: microbegraph.duckdb", size=15, weight=700))
    parts.append(t(52, 144, "the catalogue: count, filter, group, join", size=12.5, fill=INK2))
    header = ["source_id", "edge_type", "target_id"]
    rows = [("ncbitaxon:326423", "HARBORS", "mibig:BGC0000433"),
            ("mibig:BGC0000433", "PRODUCES", "mg.compound:surfactin"),
            ("mg.compound:surfactin", "INHIBITS", "ncbitaxon:40559"),
            ("ncbitaxon:40559", "INFECTS", "mg.crop:jujube")]
    xs = [52, 216, 314]
    parts.append(rect(48, 160, 440, 26, fill=PLANE, rx=4))
    for x, h in zip(xs, header, strict=True):
        parts.append(t(x, 178, h, size=11.5, weight=700, family=MONO))
    for i, row in enumerate(rows):
        for x, value in zip(xs, row, strict=True):
            parts.append(t(x, 206 + i * 26, value, size=11, family=MONO))
    parts.append(t(52, 330, "SELECT edge_type, count(*) FROM edges", size=11.5, family=MONO,
                   fill=blue))
    parts.append(t(52, 348, "GROUP BY edge_type;", size=11.5, family=MONO, fill=blue))
    parts.append(t(52, 378, f"{PHASE4['nodes']:,} nodes, {PHASE4['edges']:,} arrows", size=12.5,
                   weight=600))
    # middle arrow
    parts.append(line(510, 246, 576, 246, color=INK2, sw=2.5))
    parts.append(t(543, 232, "load_graph()", size=11.5, family=MONO, anchor="middle"))
    parts.append(t(543, 270, "rebuilt,", size=11.5, fill=INK2, anchor="middle"))
    parts.append(t(543, 286, "never edited", size=11.5, fill=INK2, anchor="middle"))
    # right: the graph
    parts.append(rect(584, 96, 470, 300, fill=SURFACE, stroke=HAIR, rx=12))
    parts.append(t(604, 124, "NetworkX: a directed graph", size=15, weight=700))
    parts.append(t(604, 144, "the shelves: walk from one dot to the next", size=12.5, fill=INK2))
    chain = [("Organism", 640, 240, "FZB42"), ("GeneCluster", 740, 240, "BGC0000433"),
             ("Compound", 840, 240, "surfactin"), ("Pathogen", 940, 240, "B. cinerea"),
             ("Crop", 1010, 316, "jujube")]
    for (_, x1, y1, _), (_, x2, y2, _) in zip(chain, chain[1:], strict=False):
        d = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        parts.append(line(x1 + ux * 30, y1 + uy * 30, x2 - ux * 34, y2 - uy * 34, color=INK2,
                          sw=2))
    for kind, x, y, label in chain:
        parts.append(f'<circle cx="{x}" cy="{y}" r="26" fill="{PLANE}"/>')
        parts.append(icon(kind, x, y, 32))
        parts.append(t(x, y + 46 if kind != "Crop" else y + 44, label, size=11.5, anchor="middle"))
    parts.append(t(604, 348, "nx.shortest_path(G, \"ncbitaxon:326423\",", size=11.5, family=MONO,
                   fill=green))
    parts.append(t(604, 366, "                 \"mg.crop:jujube\")", size=11.5, family=MONO,
                   fill=green))
    parts.append(t(32, 424, "Every build counts nodes and arrows of each type in both shapes and "
                   "stops if any number differs.", size=12.5, fill=INK2))
    return svg(1086, 446, "".join(parts), "Two shapes of the same facts",
               "Left, DuckDB tables: four rows of the edges table for the chain from Bacillus "
               "velezensis FZB42 to jujube, and a SQL query. Right, the same four arrows as a "
               "NetworkX graph from FZB42 through the surfactin cluster, surfactin and Botrytis "
               "cinerea to jujube, found with shortest_path. Both hold "
               f"{PHASE4['nodes']:,} nodes and {PHASE4['edges']:,} arrows.")


# =============================================================================
# Phase 4b: closing the gaps
# =============================================================================
def _waiting(cx: float, cy: float, r: float = 9, color: str = MUTED) -> str:
    """A small clock: built, waiting for a run (never meaning 'done')."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            f'<path d="M{cx} {cy - r * 0.55:.1f} L{cx} {cy:.1f} L{cx + r * 0.45:.1f} {cy + r * 0.3:.1f}" '
            f'stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def gaps_closed() -> str:
    """Phase 4b: each gap Phase 4 left, what closed it, and the real counts (2026-10-12)."""
    blue, aqua, orange = LAYER["genomics"], LAYER["metabolomics"], LAYER["proteomics"]
    kinds = {"evidence": ("more evidence", blue), "kept": ("nothing thrown away", aqua),
             "person": ("a person's decision", orange)}
    parts = [t(32, 46, "Closing the gaps Phase 4 left", size=22, weight=700),
             t(32, 70, "Phase 4's rules refused every join they couldn't confirm and listed what "
               "was left. Phase 4b works through that list.", size=14, fill=INK2)]
    x = 32
    for label, colour in kinds.values():
        parts.append(chip(x, 86, label, colour))
        x += len(label) * 12 * 0.58 + 46
    parts.append(t(42, 140, "WHAT PHASE 4 LEFT", size=12, weight=700, fill=MUTED))
    parts.append(t(452, 140, "WHAT CLOSED IT", size=12, weight=700, fill=MUTED))
    parts.append(t(842, 140, "THE RESULT", size=12, weight=700, fill=MUTED))
    rows = [
        ("21 gene records named only by a gene name", "no list gave their protein number",
         "MIBiG's GenBank file", "every name each gene goes by", "evidence",
         "all 59 such records placed", "before the resolver runs", "done"),
        ("4 genes the curators removed", "named LOC100272490 and so on",
         "MIBiG's GenBank file", "GeneID ties LOC names to proteins", "evidence",
         "4 of 4 removed", "22 removals in all, none left", "done"),
        ("275 values MIBiG's entries disagree on", "only the first one was kept",
         "every value, with its entry", "<property>_by_entry", "kept",
         "every value kept, on 135 nodes", "showed why two joins were wrong", "done"),
        ("2 wrong joins", "2-methylisoborneol, desosamine",
         "the review file", "a reason and a source on each row", "person",
         "kept apart by hand", "recorded as reviewed_by_hand", "done"),
        ("activity words meaning the same", "antitumor, anticancer...",
         "activity_synonyms.csv", "4 rows, each with a source", "person",
         "74 activities became 70", "the old words kept as names", "done"),
        ("325 joins on the formula alone", "and 2,656 compounds with no number",
         "PubChem's name search", "in PubChem's names file, on your computer", "evidence",
         "322 became 82", "80 after the follow-ups; 865 found by name", "partial"),
        ("42 protein numbers with tied entries", "UniProt couldn't choose one",
         "the review file", "one number at a time", "person",
         "1 decided, 1 removed", "40 still open", "partial"),
    ]
    y = 152
    for left1, left2, mid1, mid2, kind, right1, right2, status in rows:
        colour = kinds[kind][1]
        parts.append(rect(32, y, 1136, 58, fill=SURFACE, stroke=HAIR, rx=10))
        parts.append(t(48, y + 25, left1, size=13.5, weight=700))
        parts.append(t(48, y + 44, left2, size=12, fill=INK2))
        parts.append(line(398, y + 29, 436, y + 29, color=INK2, sw=2))
        parts.append(rect(446, y + 8, 352, 42, fill=SURFACE, stroke=colour, rx=8, sw=2,
                          dash="6 4" if kind == "waiting" else ""))
        parts.append(f'<circle cx="464" cy="{y + 29}" r="6" fill="{colour}"/>')
        parts.append(t(478, y + 25, mid1, size=13, weight=600))
        parts.append(t(478, y + 42, mid2, size=11.5, fill=INK2,
                       family=MONO if mid2.startswith("<") else FONT))
        parts.append(line(800, y + 29, 834, y + 29, color=INK2, sw=2))
        mark = (check_mark(856, y + 29, 10) if status == "done"
                else _waiting(856, y + 29, 10) if status == "waiting"
                else check_mark(856, y + 29, 10, color=MUTED))
        parts.append(mark)
        parts.append(t(876, y + 25, right1, size=13.5, weight=700))
        parts.append(t(876, y + 44, right2, size=12, fill=INK2))
        y += 66
    parts.append(t(32, y + 18, "Also fixed: a circular import (two files that each needed the other "
                   "to load). The shared table helpers moved to src/microbegraph/tables.py.",
                   size=12.5, fill=INK2))
    parts.append(t(32, y + 40, "Counts from the build after the Phase 4b follow-ups (the "
                   "PubChem run of 2026-10-12 at 23:07 UTC).", size=12.5, fill=MUTED))
    return svg(1200, int(y + 64), "".join(parts), "Closing the gaps Phase 4 left",
               "Seven gaps Phase 4 left and what closed each one. MIBiG's GenBank file placed all "
               "59 gene records named only by a gene name, and the 4 genes the curators removed. "
               "Every value MIBiG's entries disagree on is now kept with its entry, on 135 "
               "nodes. The review file keeps two wrong joins apart with five decisions, each with "
               "a source. Four activity words are folded, so 74 activities became 70. PubChem's "
               "name search, done in PubChem's names file, cut the joins on the formula alone "
               "from 322 to 82 (80 after the follow-ups) and found 865 compounds with no number by name. Of 42 protein numbers with tied UniProt "
               "entries, one is decided by hand, one left with a removed protein, and 40 are "
               "still open. The circular import is fixed.")


def genbank_record() -> str:
    """Phase 4b: one real CDS from MIBiG's GenBank file, line by line, and what is read."""
    blue, orange = LAYER["genomics"], LAYER["proteomics"]
    parts = [t(32, 46, "One gene, as MIBiG's GenBank file describes it", size=22, weight=700),
             t(32, 70, "A real CDS feature from entry BGC0002390 (zealexins, maize), without its "
               "protein sequence. Each line starting with / is a qualifier.", size=14, fill=INK2)]
    lines = [
        ("CDS  complement(join(63720..63793,63898..64033,73837..73862,", "where the gene sits",
         "opposite strand, seven pieces", "skip", INK2),
        ("     74207..74251,74359..74474,74580..74676,74787..75168))", "", "the location wraps "
         "onto a second line", "skip", INK2),
        ('/codon_start=1', "how to start reading the DNA", "", "skip", MUTED),
        ('/db_xref="GeneID:100272490"', "NCBI's gene number", "LOC100272490 is this number",
         "read", blue),
        ('/gene="LOC100272490"', "the gene's name", "what MIBiG's curators wrote", "read", blue),
        ('/gene_synonym="GRMZM2G134862"', "another name", "split on ; when there are several",
         "read", blue),
        ('/note="Derived by automated computational analysis using', "a note", "", "skip", MUTED),
        ('      gene prediction method: BestRefSeq."', "", "still the note: never read as a name",
         "skip", MUTED),
        ('/product="translin"', "the protein's name", "the protein file has it too",
         "skip", INK2),
        ('/protein_id="NP_001140431.1"', "the protein's number", "where every name above leads",
         "read", orange),
    ]
    y = 100
    parts.append(rect(32, y, 640, 34 * len(lines) + 20, fill=PLANE, rx=10))
    for k, (code, what, note, status, colour) in enumerate(lines):
        yy = y + 32 + k * 34
        parts.append(rect(40, yy - 18, 5, 26, fill=colour, rx=2))
        indent = (len(code) - len(code.lstrip(" "))) * 7.5     # SVG drops leading spaces
        parts.append(t(56 + indent, yy, code.lstrip(" "), size=12.5, family=MONO,
                       fill=INK if status == "read" else INK2))
        if status == "read":
            parts.append(check_mark(700, yy - 5, 9, GOOD))
        else:
            parts.append(f'<circle cx="700" cy="{yy - 5}" r="9" fill="none" stroke="{BASE}" '
                         f'stroke-width="2"/>')
        parts.append(t(720, yy, what, size=13, weight=600))
        if note:
            parts.append(t(912 if what else 720, yy, note, size=12, fill=INK2))
    y_end = y + 34 * len(lines) + 40
    parts.append(check_mark(42, y_end - 4, 8, GOOD))
    parts.append(t(58, y_end, "read by src/microbegraph/sources/mibig_genbank.py", size=12.5))
    parts.append(f'<circle cx="420" cy="{y_end - 4}" r="8" fill="none" stroke="{BASE}" '
                 f'stroke-width="2"/>')
    parts.append(t(436, y_end, "skipped, wrapped lines included", size=12.5))
    # how it is used
    y2 = y_end + 30
    parts.append(t(32, y2, "HOW MICROBEGRAPH USES IT", size=12, weight=700, fill=MUTED))
    steps = [("MIBiG's curators remove", '"LOC100272490"', INK2),
             ("the GenBank file", "GeneID:100272490", blue),
             ("names the protein", "NP_001140431.1", orange),
             ("so the cluster loses it", "removal 4 of 4", GOOD)]
    x = 32
    for k, (top, value, colour) in enumerate(steps):
        parts.append(rect(x, y2 + 14, 252, 58, fill=SURFACE, stroke=colour, rx=10, sw=2))
        parts.append(t(x + 14, y2 + 38, top, size=12.5, fill=INK2))
        parts.append(t(x + 14, y2 + 60, value, size=13.5, weight=700, family=MONO))
        if k < len(steps) - 1:
            parts.append(line(x + 254, y2 + 43, x + 286, y2 + 43, color=INK2, sw=2))
        x += 290
    parts.append(t(32, y2 + 100, "The same lookup gives the 59 gene records named only by a gene "
                   "name (baeI, agqA, SCO6265...) their protein numbers.", size=12.5, fill=INK2))
    return svg(1200, int(y2 + 124), "".join(parts), "One gene, as MIBiG's GenBank file describes it",
               "A real CDS from MIBiG entry BGC0002390: a location that wraps onto two lines, "
               "codon_start, db_xref GeneID:100272490, gene LOC100272490, gene_synonym "
               "GRMZM2G134862, a note that wraps onto a second line, product translin and "
               "protein_id NP_001140431.1. The reader keeps the gene number, the names and the "
               "protein number, and skips the rest, including wrapped lines. MIBiG's curators "
               "remove LOC100272490; the GenBank file ties it to NP_001140431.1, so that protein "
               "leaves the cluster.")


def clue_ladder() -> str:
    """Phase 4b: the four clues that confirm a PubChem number, strongest first."""
    aqua = LAYER["metabolomics"]
    parts = [t(32, 46, "Four clues for a compound's PubChem number", size=22, weight=700),
             t(32, 70, "Every number MIBiG gives, and every number PubChem's name search finds, is "
               "a candidate. The strongest clue present decides.", size=14, fill=INK2)]
    rungs = [
        ("1", "name", "MIBiG gives the number, and PubChem lists MIBiG's name under it",
         "(its title or any of its names), or the name search returns that very number",
         "785 joins", "erythromycin A and CID 12560"),
        ("2", "same structure", "MIBiG gives the number; PubChem files the name under another",
         "record with the same first InChIKey block: the same molecule, drawn another way",
         "180 joins", "with or without its 3D shape"),
        ("3", "name search", "MIBiG gives no number that passes 1 or 2, but the name search finds",
         "the name under exactly one number whose formula agrees with MIBiG's",
         "927 joins", "for the 1,254 with a formula, no number"),
        ("4", "formula alone", "MIBiG gives one number and the formulas agree; nothing above",
         "points elsewhere. The weakest clue, so two things switch it off:",
         "80 joins", "R19 lists them"),
    ]
    y = 98
    for k, (num, name, l1, l2, count, example) in enumerate(rungs):
        weight = 4 - k
        parts.append(rect(32, y, 760, 76, fill=SURFACE, stroke=aqua, rx=10, sw=1 + weight * 0.6))
        parts.append(f'<circle cx="62" cy="{y + 38}" r="18" fill="{aqua}" opacity="{0.4 + weight * 0.15:.2f}"/>')
        parts.append(t(62, y + 44, num, size=16, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(94, y + 26, name, size=15, weight=700))
        parts.append(t(94, y + 46, l1, size=12.5, fill=INK2))
        parts.append(t(94, y + 64, l2, size=12.5, fill=INK2))
        parts.append(t(808, y + 32, count, size=13, weight=700))
        parts.append(t(808, y + 52, example, size=12, fill=MUTED))
        y += 88
    # the two stops on rung 4
    stops = [("the name search files the name under a different molecule",
              "2-methylisoborneol: its MIBiG number is a bromine compound's"),
             ("MIBiG's entries disagree about the formula",
              "ferrichrome (with and without iron), lasalocid (salt and acid)")]
    for k, (head, example) in enumerate(stops):
        yy = y + k * 56
        parts.append(rect(94, yy, 698, 48, fill=SURFACE, stroke=CRITICAL, rx=8, sw=1.6))
        parts.append(cross_mark(116, yy + 24, 9))
        parts.append(t(134, yy + 20, head, size=13, weight=600))
        parts.append(t(134, yy + 38, example, size=12, fill=INK2))
    y += 2 * 56 + 16
    notes = ["Before any clue: a person's decision in the review file wins, and says so.",
             "Clue 2 skips a record built with an unusual isotope, a tracer such as ferrichrome's "
             "[55Fe] record.",
             "Two candidates equally strong and different: kept apart, both named in the ledger.",
             "A number several MIBiG compounds share: clue 1 only (isomers share formulas).",
             "The ledger names the clue that decided: \"Confirmed by name.\", \"Confirmed by the "
             "formula alone.\""]
    for k, note in enumerate(notes):
        parts.append(f'<circle cx="40" cy="{y + k * 22 - 4}" r="3" fill="{INK2}"/>')
        parts.append(t(52, y + k * 22, note, size=12.5, fill=INK2))
    parts.append(t(32, y + len(notes) * 22 + 4, "Counts from the build after the Phase 4b "
                   "follow-ups.", size=12, fill=MUTED))
    return svg(1060, int(y + len(notes) * 22 + 22), "".join(parts),
               "Four clues for a compound's PubChem number",
               "Four clues, strongest first. 1, name: PubChem lists MIBiG's name under the number, "
               "785 joins. 2, same structure: the name is filed under another record with the same "
               "first InChIKey block, 180 joins, but not for a tracer built with an unusual "
               "isotope. 3, name search: the name is found under exactly one "
               "number with an agreeing formula, 927 joins. 4, formula alone: 80 joins, switched off when the name "
               "search points at a different molecule or MIBiG's entries disagree about the "
               "formula, as for 2-methylisoborneol, ferrichrome and lasalocid. A person's "
               "decision comes first; ties stay apart; shared numbers need clue 1.")


def review_row() -> str:
    """Phase 4b: one real row of the review file, column by column, and its ledger row."""
    orange = LAYER["proteomics"]
    parts = [t(32, 46, "A decision by hand, written down", size=22, weight=700),
             t(32, 70, "A real row of curation/resolution_decisions.csv, read column by column, "
               "and the ledger row the resolver writes from it.", size=14, fill=INK2)]
    cols = [
        ("identifier", ["mg.compound:desosamine"], "one record"),
        ("other_identifier", ["mg.compound:methymycin"], "the other record"),
        ("decision", ["keep_apart"], "join, or keep_apart"),
        ("reason", ["Desosamine is the sugar part of methymycin, not another name",
                    "for it. The two share an NPAtlas number only because entry",
                    "BGC0000898 gives desosamine methymycin's records."], "why, so anyone can check"),
        ("citation", ["pubmed:9770448"], "where to check it"),
        ("decided_on", ["2026-10-12"], "when"),
    ]
    y = 96
    for k, (name, values, meaning) in enumerate(cols):
        height = 12 + 22 * len(values)
        if k % 2 == 1:
            parts.append(rect(32, y, 1036, height, fill=PLANE, rx=6))
        parts.append(t(46, y + 23, name, size=13, weight=700, family=MONO))
        for i, value in enumerate(values):
            parts.append(t(210, y + 23 + i * 22, value, size=12.5, family=MONO))
        parts.append(t(860, y + 23, meaning, size=12, fill=INK2))
        y += height + 4
    parts.append(line(550, y + 8, 550, y + 44, color=orange, sw=2.5))
    parts.append(t(566, y + 32, "python -m microbegraph.resolve applies it before the rules "
                   "that join compounds and proteins", size=12.5, fill=INK2))
    y += 56
    parts.append(rect(32, y, 1036, 156, fill=SURFACE, stroke=orange, rx=10, sw=2))
    parts.append(t(48, y + 26, "THE LEDGER ROW IT BECOMES", size=12, weight=700, fill=MUTED))
    for x, label, value in ((48, "rule", "reviewed_by_hand"), (250, "decision", "kept_apart"),
                            (420, "identifier", "mg.compound:desosamine"),
                            (660, "compared_with", "mg.compound:methymycin")):
        parts.append(t(x, y + 50, label, size=11.5, weight=700, fill=INK2, family=MONO))
        parts.append(t(x, y + 70, value, size=12.5, family=MONO))
    parts.append(t(48, y + 98, "grounds", size=11.5, weight=700, fill=INK2, family=MONO))
    grounds = ["Decided by hand on 2026-10-12: mg.compound:desosamine and mg.compound:methymycin "
               "are different things.",
               "Desosamine is the sugar part of methymycin, ... Source: pubmed:9770448 "
               "(curation/resolution_decisions.csv, line 4)."]
    for i, g in enumerate(grounds):
        parts.append(t(48, y + 118 + i * 20, g, size=12.5, family=MONO, fill=INK2))
    y += 174
    parts.append(t(32, y + 14, "keep_apart: the two can never end up in one node, by any rule or any "
                   "chain of joins. join: they become one node at once.", size=12.5, fill=INK2))
    parts.append(t(32, y + 36, "Recipe R20 in the query cookbook lists every decision by hand.",
                   size=12.5, fill=INK2))
    return svg(1100, int(y + 58), "".join(parts), "A decision by hand, written down",
               "A row of the review file: identifier mg.compound:desosamine, other_identifier "
               "mg.compound:methymycin, decision keep_apart, a reason saying desosamine is the "
               "sugar part of methymycin, citation pubmed:9770448, decided on 2026-10-12. The "
               "resolver applies it before the rules that join compounds and proteins and "
               "writes a ledger row with rule "
               "reviewed_by_hand, decision kept_apart, and grounds that quote the reason and the "
               "source.")


def follow_ups() -> str:
    """Phase 4b follow-ups: four small changes after the real run, before and after."""
    aqua, orange, grey = LAYER["metabolomics"], LAYER["proteomics"], LAYER["context"]
    parts = [t(32, 46, "Four follow-ups after the real run", size=22, weight=700),
             t(32, 70, "Small things found while checking Phase 4b's run, settled before Phase 5. "
               "Three changed the graph and one the ledger's wording.", size=14,
               fill=INK2)]
    parts.append(t(300, 104, "BEFORE", size=12, weight=700, fill=MUTED))
    parts.append(t(760, 104, "AFTER", size=12, weight=700, fill=MUTED))
    rows = [
        ("1", "Every number an entry lists", "17 entries list two",
         ("BGC0000900 lists 644246 and 90658043", False),
         ("only the first, after sorting, was read", False),
         ("both numbers are candidates", False),
         ("round 1: 1,193 numbers became 1,209", False), aqua, "compound"),
        ("2", "A tracer isn't the compound", "ferrichrome",
         ("joined 644246, \"[55Fe] Ferrichrome\"", False),
         ("a laboratory tracer with radioactive iron", False),
         ("joins 121489511, \"Ferrichrome\"", False),
         ("clue 2 reads [55Fe+3] in the SMILES", True), aqua, "compound"),
        ("3", "Whose search was it?", "the ledger's sentence",
         ("(; see their pubchem_number rows)", True),
         ("409 records, nothing in the brackets", False),
         ("found this record for 'tiacumicin B'", True),
         ("names the compound and where it went", False), orange, "ledger"),
        ("4", "Maps no arrow reaches", "KEGG maps",
         ("5 maps stayed as lone dots", False),
         ("their only compound was left out", False),
         ("left out, each with a ledger row", False),
         ("Pathway nodes: 53 became 48", False), grey, "map"),
    ]
    y = 116
    for num, title, sub, b1, b2, a1, a2, colour, kind in rows:
        cy = y + 38
        parts.append(f'<circle cx="52" cy="{cy}" r="16" fill="{colour}"/>')
        parts.append(t(52, cy + 5, num, size=15, weight=700, fill=SURFACE, anchor="middle"))
        parts.append(t(80, cy - 4, title, size=15, weight=700))
        parts.append(t(80, cy + 16, sub, size=12.5, fill=INK2))
        # before
        parts.append(rect(300, y, 400, 76, fill=SURFACE, stroke=BASE, rx=10, sw=1.5))
        parts.append(cross_mark(322, cy, 9))
        for k, (text, mono) in enumerate((b1, b2)):
            parts.append(t(342, y + 30 + k * 24, text, size=12.5 if mono else 13,
                           weight=600 if k == 0 else 400, fill=INK if k == 0 else INK2,
                           family=MONO if mono else FONT))
        if kind == "map":           # a lone dot: a node with no line to anything
            parts.append(f'<circle cx="672" cy="{cy}" r="9" fill="{SURFACE}" stroke="{grey}" '
                         f'stroke-width="2"/>')
        parts.append(line(706, cy, 752, cy, color=INK2, sw=2))
        # after
        parts.append(rect(760, y, 408, 76, fill=SURFACE, stroke=colour, rx=10, sw=2))
        parts.append(check_mark(782, cy, 9))
        for k, (text, mono) in enumerate((a1, a2)):
            parts.append(t(802, y + 30 + k * 24, text, size=12.5 if mono else 13,
                           weight=600 if k == 0 else 400, fill=INK if k == 0 else INK2,
                           family=MONO if mono else FONT))
        y += 96
    # what moved
    y += 8
    parts.append(t(32, y, "WHAT IT CHANGED, COMPOUND BY COMPOUND", size=12, weight=700, fill=MUTED))
    groups = [("moved to another record", aqua,
               "ferrichrome to 121489511, psymberin to 11692946, echinomycin to 458034"),
              ("waits for a person", MUTED,
               "valclavam (two numbers tie), corallopyronin and glidobactin (no name confirms)"),
              ("settled by hand", orange,
               "epoxomicin (11226684) and mureidomycin B (101627952): two records with the name")]
    for k, (label, colour, text) in enumerate(groups):
        yy = y + 16 + k * 34
        parts.append(chip(32, yy, label, colour, w=200))
        parts.append(t(248, yy + 16, text, size=13, fill=INK2))
    y += 16 + 3 * 34 + 14
    parts.append(t(32, y, "Compounds with a PubChem record: 1,978 became 1,975. Joins on the "
                   "formula alone: 82 became 80. Decisions by hand: 5 became 7.", size=12.5,
                   fill=INK2))
    parts.append(t(32, y + 22, "Counts from the build after the follow-ups (the PubChem run of "
                   "2026-10-12 at 23:07 UTC). Details in docs/06b-closing-the-gaps.md, Step 10.",
                   size=12.5, fill=MUTED))
    return svg(1200, int(y + 46), "".join(parts), "Four follow-ups after the real run",
               "Four small changes after Phase 4b's real run, before and after. 1: 17 MIBiG "
               "entries list two PubChem numbers for one compound, such as BGC0000900 with "
               "644246 and 90658043; only the first was read, and now both are candidates, so "
               "round 1 asks about 1,209 numbers instead of 1,193. 2: ferrichrome was joined to "
               "644246, a laboratory tracer with radioactive iron-55; clue 2 now reads the "
               "isotope label in the SMILES, and ferrichrome joins 121489511. 3: 409 ledger "
               "sentences had nothing in their brackets; they now name the compound whose name "
               "search found the record and where it went. 4: 5 KEGG maps stayed as lone dots; "
               "they are left out with a ledger row, so Pathway nodes went from 53 to 48. "
               "Ferrichrome, psymberin and echinomycin moved to another record; valclavam, "
               "corallopyronin and glidobactin wait for a person; epoxomicin and mureidomycin B "
               "were settled by hand. Compounds with a PubChem record went from 1,978 to 1,975, "
               "joins on the formula alone from 82 to 80, decisions by hand from 5 to 7.")


def three_d_check() -> str:
    """Phase 4c: the 3D check of same-structure joins, with echinomycin's real centres."""
    aqua, orange = LAYER["metabolomics"], LAYER["proteomics"]
    parts = [t(32, 46, "Checking the 3D detail of a shared skeleton", size=22, weight=700),
             t(32, 70, "Two PubChem records can share a skeleton and still be different "
               "compounds. The resolver compares them place by place before trusting clue 2.",
               size=14, fill=INK2)]
    parts.append(t(32, 108, "ECHINOMYCIN: ONE SKELETON, TWO DRAWINGS, THE 8 CHIRAL CENTRES BOTH DESCRIBE", size=12,
                   weight=700, fill=MUTED))
    given = "RRRSRRRS"          # CID 458034, a number MIBiG gives (the one clue 2 reached)
    named = "SRRSRSRS"          # CID 6857732, the record PubChem titles "Echinomycin"
    for cid, sub, labels, cy in (("CID 458034", "a number MIBiG gives", given, 146),
                                 ("CID 6857732", "PubChem's \"Echinomycin\"", named, 230)):
        parts.append(t(32, cy - 2, cid, size=15, weight=700))
        parts.append(t(32, cy + 18, sub, size=12.5, fill=INK2))
        for k, label in enumerate(labels):
            cx = 290 + k * 62
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="20" fill="{SURFACE}" stroke="{aqua}" '
                         f'stroke-width="2"/>')
            parts.append(t(cx, cy + 6, label, size=16, weight=700, anchor="middle"))
    for k, (a, b) in enumerate(zip(given, named, strict=True)):
        cx = 290 + k * 62
        parts.append(check_mark(cx, 188, 9) if a == b else cross_mark(cx, 188, 9))
    parts.append(t(800, 136, "6 centres agree and 2 differ (the two", size=13, fill=INK2))
    parts.append(t(800, 156, "alanines), so these are two stereoisomers.", size=13, fill=INK2))
    parts.append(t(800, 186, "MIBiG's own structure matches CID 458034,", size=13, weight=600))
    parts.append(t(800, 206, "so the rule would keep that number. A review", size=13, weight=600))
    parts.append(t(800, 226, "gives L-alanine (S), as in CID 6857732,", size=13, weight=600))
    parts.append(t(800, 246, "so a decision by hand joins 6857732.", size=13, weight=600))
    # what the resolver does with every pair
    parts.append(t(32, 300, "WHAT THE RESOLVER DOES WITH EACH PAIR (183 IN THE REAL DATA)", size=12,
                   weight=700, fill=MUTED))
    boxes = [(32, 316, "A pair for clue 2", "MIBiG's number and the name's",
              "record share one skeleton"),
             (322, 316, "Compare the 3D detail", "every chiral centre (R or S) and",
              "double bond (E or Z) both describe"),
             (322, 448, "Ask MIBiG's own structure", "the SMILES in MIBiG's entry,",
              "compared with both records")]
    for x, y, head, l1, l2 in boxes:
        parts.append(rect(x, y, 250, 80, fill=SURFACE, stroke=BASE, rx=10, sw=1.5))
        parts.append(t(x + 16, y + 26, head, size=14, weight=700))
        parts.append(t(x + 16, y + 48, l1, size=12.5, fill=INK2))
        parts.append(t(x + 16, y + 66, l2, size=12.5, fill=INK2))
    parts.append(line(282, 356, 318, 356, color=INK2))
    parts.append(line(572, 356, 608, 356, color=INK2))
    parts.append(line(447, 396, 447, 444, color=INK2))
    parts.append(t(458, 426, "65 differ", size=13, weight=700, halo=True))
    outcomes = [(316, 80, aqua, True, "118 agree: clue 2 counts",
                 "joined, unless another candidate is just as good (valclavam's two numbers tie)"),
                (432, 56, aqua, True, "38 match MIBiG's number: it stands",
                 "n-myristoyl-D-asparagine keeps 102500690 (R, the D form)"),
                (498, 56, orange, True, "17 match the name's record: the compound moves there",
                 "macbecin II moves to 5778325, \"Macbecin II\""),
                (564, 56, MUTED, False, "10 can't be decided: neither record joins",
                 "9 compounds wait for a person (recipe R24); kosinostatin's other number joined")]
    for y, h, colour, good, head, example in outcomes:
        parts.append(rect(612, y, 556, h, fill=SURFACE, stroke=colour, rx=10, sw=2))
        mark = check_mark(636, y + h / 2, 9) if good else _waiting(636, y + h / 2)
        parts.append(mark)
        parts.append(t(656, y + h / 2 - 4, head, size=13.5, weight=700))
        parts.append(t(656, y + h / 2 + 15, example, size=12.5, fill=INK2))
    for y in (460, 526, 592):
        parts.append(path(f"M572 488 C 592 488, 590 {y}, 608 {y}", color=INK2))
    parts.append(t(32, 656, "Compounds with a PubChem record: 1,975 became 1,967. Ties for a person: "
                   "35 became 34 (the check settled kosinostatin's). Echinomycin, decided by hand, "
                   "isn't one of the 183.", size=12.5, fill=INK2))
    parts.append(t(32, 678, "Counts from the build of 2026-10-13 after Phase 4c. Details in "
                   "docs/06c-checking-3d-detail.md.", size=12.5, fill=MUTED))
    return svg(1200, 702, "".join(parts), "Checking the 3D detail of a shared skeleton",
               "Echinomycin's two PubChem records share a skeleton. The 8 chiral centres both "
               "describe read R R R S R R R S in CID 458034, a number MIBiG gives, and S R R S R S "
               "R S in CID "
               "6857732, PubChem's Echinomycin: 6 agree and 2 differ, at the two alanines, so "
               "they are two stereoisomers. MIBiG's own structure matches CID 458034, but a "
               "review gives L-alanine (S), as in CID 6857732, so a decision by hand joins that "
               "record. For each of the 183 pairs clue 2 looks at, the resolver compares the 3D "
               "detail. 118 agree and clue 2 counts. 65 differ, and MIBiG's own structure "
               "decides: 38 match MIBiG's number (n-myristoyl-D-asparagine keeps 102500690), 17 "
               "match the record PubChem names (macbecin II moves to 5778325), and 10 can't be "
               "decided, leaving 9 compounds for a person. Compounds with a PubChem record went "
               "from 1,975 to 1,967, and ties for a person from 35 to 34.")


# =============================================================================
# Phase 5: graph analytics
# =============================================================================
def graph_analytics() -> str:
    """Phase 5: the three questions, with the real numbers from the build after Phase 5."""
    blue, aqua, yellow = LAYER["genomics"], LAYER["metabolomics"], LAYER["phenotype"]
    parts = [t(32, 46, "Three questions for the finished graph", size=22, weight=700),
             t(32, 70, "Which microbes might help a crop, which nodes matter, and which groups "
               "the graph falls into. Every answer comes with its evidence.", size=14, fill=INK2)]
    # 1. paths
    parts.append(t(32, 110, "1. EVIDENCE PATHS: FOLLOW THE TYPED ROUTE, NOT THE SHORTEST ONE",
                   size=12, weight=700, fill=MUTED))
    chain = [("Organism", "FZB42"), ("GeneCluster", "BGC0000433"), ("Compound", "surfactin"),
             ("Pathogen", "Botrytis cinerea"), ("Crop", "jujube")]
    verbs = ["HARBORS", "PRODUCES", "INHIBITS", "INFECTS"]
    xs = [80 + i * 150 for i in range(5)]
    for i, (kind, name) in enumerate(chain):
        parts.append(node_badge(kind, xs[i], 160, r=26, label=name))
        if i < 4:
            parts.append(line(xs[i] + 30, 160, xs[i + 1] - 32, 160, color=INK2))
            parts.append(t((xs[i] + xs[i + 1]) / 2, 150, verbs[i], size=10.5, weight=600,
                           anchor="middle", family=MONO, fill=INK2, halo=True))
    parts.append(check_mark(720, 160, 10))
    parts.append(t(740, 156, "Each step may only take", size=13, weight=600))
    parts.append(t(740, 175, "the next arrow type.", size=13, weight=600))
    parts.append(cross_mark(48, 236, 10))
    parts.append(t(68, 241, "jujube - Botrytis cinerea - surfactin - antibacterial - coelimycin P1 "
                   "- its cluster - Streptomyces coelicolor A3(2)", size=13, family=MONO))
    parts.append(t(68, 262, "Six real arrows, ignoring their direction, through a label that 936 "
                   "compounds share: 592 microbes are this close to jujube.", size=12.5, fill=INK2))
    parts.append(rect(912, 96, 256, 112, fill=PLANE, stroke=HAIR, rx=10, sw=1))
    for k, (big, small) in enumerate((("10 paths, 9 leads", "to 5 crops along the route"),
                                       ("weakest link: a paper", "on every path (curated_literature)"))):
        parts.append(t(926, 126 + k * 48, big, size=15, weight=700))
        parts.append(t(926, 145 + k * 48, small, size=12, fill=INK2))
    # 2. hubs and bridges
    parts.append(t(32, 310, "2. HUBS AND BRIDGES: TWO MEANINGS OF IMPORTANT", size=12, weight=700,
                   fill=MUTED))
    hx, hy = 150, 420
    for k in range(10):
        a = math.pi * 2 * k / 10
        x, y = hx + 70 * math.cos(a), hy + 62 * math.sin(a)
        parts.append(line(hx, hy, x, y, color=BASE, sw=1.5, arrow=False))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{SURFACE}" stroke="{aqua}" '
                     f'stroke-width="2"/>')
    parts.append(f'<circle cx="{hx}" cy="{hy}" r="22" fill="{SURFACE}" stroke="{aqua}" '
                 f'stroke-width="3"/>' + icon("Activity", hx, hy, 30))
    parts.append(t(hx, 512, "hub: many arrows", size=13, weight=700, anchor="middle"))
    parts.append(t(hx, 530, "antibacterial, 936", size=12, fill=INK2, anchor="middle"))
    left = [(300, 380), (330, 450), (370, 400)]
    right = [(510, 390), (540, 455), (480, 440)]
    bx, by = 425, 425
    for group in (left, right):
        for i, (x1, y1) in enumerate(group):
            for x2, y2 in group[i + 1:]:
                parts.append(line(x1, y1, x2, y2, color=BASE, sw=1.5, arrow=False))
    parts.append(line(370, 400, bx, by, color=INK2, sw=2, arrow=False))
    parts.append(line(bx, by, 480, 440, color=INK2, sw=2, arrow=False))
    for x, y in left + right:
        parts.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{SURFACE}" stroke="{blue}" '
                     f'stroke-width="2"/>')
    parts.append(f'<circle cx="{bx}" cy="{by}" r="16" fill="{SURFACE}" stroke="{aqua}" '
                 f'stroke-width="3"/>' + icon("Compound", bx, by, 22))
    parts.append(t(bx, 512, "bridge: on the routes between", size=13, weight=700, anchor="middle"))
    parts.append(t(bx, 530, "carotenoid, made by 17 microbes", size=12, fill=INK2, anchor="middle"))
    parts.append(t(32, 562, "On the whole graph the labels win both. Bridges are looked for",
                   size=12.5, fill=INK2))
    parts.append(t(32, 580, "on the production layer only (HARBORS, PRODUCES, INHIBITS, INFECTS).",
                   size=12.5, fill=INK2))
    # 3. communities
    parts.append(t(640, 310, "3. COMMUNITIES: GROUPS THAT LINK MOSTLY TO EACH OTHER", size=12,
                   weight=700, fill=MUTED))
    blobs = [(740, 420, 80, 58, blue, 7), (900, 400, 70, 52, aqua, 6), (1060, 430, 78, 56,
                                                                        yellow, 6)]
    for cx, cy, rx, ry, colour, n in blobs:
        parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{PLANE}" '
                     f'stroke="{colour}" stroke-width="2" stroke-dasharray="5 4"/>')
        pts = [(cx + rx * 0.55 * math.cos(2 * math.pi * k / n),
                cy + ry * 0.5 * math.sin(2 * math.pi * k / n)) for k in range(n)]
        for i, (x1, y1) in enumerate(pts):
            for x2, y2 in pts[i + 1:i + 3]:
                parts.append(line(x1, y1, x2, y2, color=BASE, sw=1.2, arrow=False))
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{SURFACE}" '
                         f'stroke="{colour}" stroke-width="2"/>')
    parts.append(line(820, 420, 830, 410, color=INK2, sw=1.5, arrow=False))
    parts.append(line(970, 410, 982, 420, color=INK2, sw=1.5, arrow=False))
    parts.append(t(900, 512, "63 communities without the proteins", size=13, weight=700,
                   anchor="middle"))
    parts.append(t(900, 530, "modularity 0.778 (Louvain, seed 42)", size=12, fill=INK2,
                   anchor="middle"))
    parts.append(t(640, 562, "Groups read as themes: Streptomyces, siderophores, antivirals,",
                   size=12.5, fill=INK2))
    parts.append(t(640, 580, "and a Pseudomonas group that holds cotton.", size=12.5, fill=INK2))
    parts.append(t(32, 618, "Counts from the survey script and python -m microbegraph.analyze on the "
                   "build after Phase 5, NetworkX 3.6.1. Details in docs/07-graph-analytics.md.",
                   size=12.5, fill=MUTED))
    return svg(1200, 642, "".join(parts), "Three questions for the finished graph",
               "Evidence paths follow the typed route organism, cluster, compound, pathogen, "
               "crop, as in FZB42, BGC0000433, surfactin, Botrytis cinerea, jujube. The shortest "
               "route ignoring directions runs through the label antibacterial instead, and puts "
               "592 microbes within six steps of jujube. The route finds 10 paths and 9 leads to "
               "5 crops, and every weakest link is a paper. Hubs have many arrows (antibacterial, "
               "936); bridges sit on the routes between groups (carotenoid, made by 17 microbes, "
               "on the production layer). Without the proteins the graph splits into 63 "
               "communities with modularity 0.778.")


def single_points() -> str:
    """Phase 5: what each crop's leads rest on, from the full run after Phase 5."""
    blue = LAYER["genomics"]
    parts = [t(32, 46, "What each crop's leads rest on", size=22, weight=700),
             t(32, 70, "A lead is one microbe, one compound, one pathogen and one crop. A fact "
               "every path of a lead uses is a single point of failure.", size=14, fill=INK2)]
    rows = [("cotton", [("Pseudomonas protegens Pf-5", "pyoluteorin", False),
                        ("Pseudomonas sp. M18", "pyoluteorin", False),
                        ("Pseudomonas chlororaphis", "pyrrolnitrin", False)], 2, 2),
            ("jujube", [("Bacillus velezensis FZB42", "surfactin", True)], 1, 1),
            ("maize", [("Bacillus velezensis FZB42", "bacillomycin D", True)], 1, 1),
            ("melon", [("Bacillus velezensis FZB42", "fengycin", True),
                       ("Bacillus subtilis", "iturin", False)], 2, 1),
            ("wheat", [("Bacillus velezensis FZB42", "bacillomycin D", True),
                       ("Pseudomonas fluorescens", "2,4-diacetylphloroglucinol (2 clusters)",
                        False)], 2, 2)]
    parts.append(t(32, 108, "CROP", size=12, weight=700, fill=MUTED))
    parts.append(t(140, 108, "LEADS (MICROBE AND COMPOUND)", size=12, weight=700, fill=MUTED))
    parts.append(t(1000, 108, "COMPOUNDS", size=12, weight=700, fill=MUTED, anchor="middle"))
    parts.append(t(1110, 108, "PAPERS", size=12, weight=700, fill=MUTED, anchor="middle"))
    y = 124
    for crop, leads, compounds, papers in rows:
        h = 34 * len(leads) + 10
        parts.append(rect(24, y, 1152, h, fill=PLANE if crop in ("jujube", "maize") else SURFACE,
                          stroke=HAIR, rx=8, sw=1))
        parts.append(icon("Crop", 46, y + 22, 22))
        parts.append(t(64, y + 27, crop, size=14, weight=700))
        for k, (microbe, compound, fzb) in enumerate(leads):
            ly = y + 10 + 34 * k
            colour = blue if fzb else BASE
            parts.append(rect(140, ly, 820, 26, fill=SURFACE, stroke=colour, rx=13,
                              sw=2.5 if fzb else 1.2))
            parts.append(icon("Organism", 158, ly + 13, 18))
            parts.append(t(174, ly + 18, microbe, size=13, weight=700 if fzb else 400))
            parts.append(icon("Compound", 452, ly + 13, 18))
            parts.append(t(468, ly + 18, compound, size=13))
        parts.append(t(1000, y + 27, str(compounds), size=16, weight=700, anchor="middle"))
        parts.append(t(1110, y + 27, str(papers), size=16, weight=700, anchor="middle"))
        y += h + 8
    parts.append(rect(24, y + 4, 1152, 70, fill=SURFACE, stroke=blue, rx=10, sw=2))
    parts.append(t(44, y + 32, "Without Bacillus velezensis FZB42 (thick outline), 4 of the 9 "
                   "leads are lost, and jujube and maize (shaded) have none.", size=14,
                   weight=700))
    parts.append(t(44, y + 56, "Each pathogen rests on one or two compounds and one paper; the "
                   "papers are the curated bridge's, from this project's own reading.", size=13,
                   fill=INK2))
    parts.append(t(32, y + 104, "From python -m microbegraph.analyze on the build after Phase 5 "
                   "(the downloads of Phase 4c). Details in docs/07-graph-analytics.md.",
                   size=12.5, fill=MUTED))
    return svg(1200, int(y + 126), "".join(parts), "What each crop's leads rest on",
               "Cotton has 3 leads (Pseudomonas protegens Pf-5 and Pseudomonas sp. M18 with "
               "pyoluteorin, Pseudomonas chlororaphis with pyrrolnitrin), 2 compounds and 2 "
               "papers. Jujube has 1 lead (FZB42, surfactin), maize 1 (FZB42, bacillomycin D), "
               "each resting on one compound and one paper. Melon has 2 leads (FZB42 with "
               "fengycin, Bacillus subtilis with iturin), 2 compounds and 1 paper. Wheat has 2 "
               "leads (FZB42 with bacillomycin D, Pseudomonas fluorescens with "
               "2,4-diacetylphloroglucinol from two clusters), 2 compounds and 2 papers. Without "
               "Bacillus velezensis FZB42, 4 of the 9 leads are lost and jujube and maize have "
               "none.")


FIGURES = {
    "logo_microbegraph.svg": logo,
    "cover_microbegraph.svg": cover,
    "node_types.svg": node_types,
    "ontology_map.svg": ontology_map,
    "evidence_ladder.svg": evidence_ladder,
    "adapter_contract.svg": adapter_contract,
    "ingestion_flow.svg": ingestion_flow,
    "checksum_fingerprint.svg": checksum_fingerprint,
    "git_branch_model.svg": git_branch_model,
    "setup_flow.svg": setup_flow,
    "journey_map.svg": journey_map,
    "ci_checks.svg": ci_checks,
    "sources_map.svg": sources_map,
    "secrets_env.svg": secrets_env,
    "api_snapshot.svg": api_snapshot,
    "protein_layer.svg": protein_layer,
    "gene_jobs.svg": gene_jobs,
    "idmapping_flow.svg": idmapping_flow,
    "protein_coverage.svg": protein_coverage,
    "fasta_header.svg": fasta_header,
    "protein_file_matching.svg": protein_file_matching,
    "protein_file_coverage.svg": protein_file_coverage,
    "resolution_flow.svg": resolution_flow,
    "pubchem_check.svg": pubchem_check,
    "uniprot_choice.svg": uniprot_choice,
    "ledger_row.svg": ledger_row,
    "two_shapes.svg": two_shapes,
    "gaps_closed.svg": gaps_closed,
    "genbank_record.svg": genbank_record,
    "clue_ladder.svg": clue_ladder,
    "review_row.svg": review_row,
    "follow_ups.svg": follow_ups,
    "three_d_check.svg": three_d_check,
    "graph_analytics.svg": graph_analytics,
    "single_points.svg": single_points,
}


def main() -> None:
    print("Drawing MicrobeGraph illustrations")
    for name, draw in FIGURES.items():
        write(name, draw())
    print(f"Done: {len(FIGURES)} figures in docs/img/")


if __name__ == "__main__":
    main()
