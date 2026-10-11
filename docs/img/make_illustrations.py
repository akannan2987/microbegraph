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
    "Protein": ("proteomics", "uniprot:<accession>", "the machine on the line"),
    "Compound": ("metabolomics", "mg.compound:surfactin", "the product"),
    "CompoundClass": ("metabolomics", "mg.class:lipopeptide", "the supermarket aisle"),
    "Activity": ("metabolomics", "mg.activity:antibacterial", "what it is for"),
    "Pathogen": ("phenotype", "ncbitaxon:40559", "the problem"),
    "Crop": ("phenotype", "mg.crop:strawberry", "who suffers"),
    "Pathway": ("context", "kegg.pathway:map01110", "the wider process"),
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
        + t(160, 86, "Microbe", size=34, weight=400)
        + t(287, 86, "Graph", size=34, weight=700)
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
    for kind, (x, y) in pos.items():
        parts.append(node_badge(kind, x, y, r=r))
    legend_x = 32
    for name, color in LAYER.items():
        parts.append(chip(legend_x, 470, name, color))
        legend_x += len(name) * 7 + 52
    return svg(1220, 510, "".join(parts), "The ontology map",
               "Nine node types connected by the ten allowed edge types, coloured by "
               "biological layer.")


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
    sources = [("MIBiG", "Phase 1", True), ("PubChem", "Phase 2", False),
               ("NCBI Taxonomy", "Phase 2", False), ("KEGG", "Phase 2", False),
               ("curated bridge", "Phase 2", False), ("UniProt", "Phase 3", False)]
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
    verbs = [("probe()", "What is out there?", "asks about version, size and checksum;",
              "downloads nothing", _magnifier),
             ("fetch()", "Bring it home, untouched.", "into data/raw/<source>/, checksum verified,",
              "one provenance row per fetch", _download),
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
    parts.append(t(32, 440, "Solid = built. Dashed = planned.", size=12.5, fill=MUTED))
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
}


def main() -> None:
    print("Drawing MicrobeGraph illustrations")
    for name, draw in FIGURES.items():
        write(name, draw())
    print(f"Done: {len(FIGURES)} figures in docs/img/")


if __name__ == "__main__":
    main()
