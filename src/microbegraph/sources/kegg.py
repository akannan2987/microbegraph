"""
MicrobeGraph, the KEGG adapter (Phase 2).

WHAT KEGG IS
    KEGG (Kyoto Encyclopedia of Genes and Genomes) is a set of hand-drawn
    maps of how living cells work, made by Kanehisa Laboratories in Japan
    since 1995. Its best-known part is the PATHWAY maps: chains of chemical
    reactions such as "glycolysis" or "C5-branched dibasic acid metabolism",
    each with a number (map00010, map00660...). Compounds on those maps have
    KEGG numbers of their own (C00490 is itaconic acid).

    If PubChem is the product catalogue, KEGG is the factory floor plan:
    it shows which production lines each product passes along.

WHY IT MATTERS HERE
    A compound on a pathway map is part of a known biological process. That
    gives the graph a way to say what a molecule is involved in, beyond
    "it kills fungus X".

HOW IT ASKS
    KEGG's API is plain text over the web (rest.kegg.jp). Four questions, all
    downloaded whole, three seconds' worth of requests in all:

        /info/kegg              when each part of KEGG was last updated
        /list/pathway           every pathway map: number and name
        /link/pathway/compound  every compound-to-map link (about 20,000 lines)
        /get/br:br08901         the categories maps are filed under

    KEGG asks for no more than 3 requests a second; this adapter waits
    0.4 seconds between requests.

WHAT tidy() TURNS THE ANSWERS INTO
    It reads PubChem's tables to see which of OUR compounds have a KEGG
    number, then follows the links:

        pubchem.compound:811 (itaconic acid, KEGG C00490)
            --PARTICIPATES_IN--> kegg.pathway:map00660
                                 (C5-Branched dibasic acid metabolism)

    nodes  Pathway          kegg.pathway:mapNNNNN, only the maps actually used,
                            with the category and subcategory KEGG files them under
    edges  PARTICIPATES_IN  Compound -> Pathway, database_assertion

    Two kinds of map are left out on purpose and counted: "Global and
    overview maps" (map01100 "Metabolic pathways" draws nearly every compound
    KEGG has) and "Chemical structure transformation maps". Both are maps of
    other maps, so an arrow to them says almost nothing about a compound.

LICENCE: READ THIS BEFORE USING OR SHARING KEGG DATA
    KEGG is not open data. In Kanehisa Laboratories' own words, "KEGG API is
    provided for academic use by academic users belonging to academic
    institutions", "Non-academic use of KEGG requires a commercial license",
    and academic users who provide services using KEGG are asked to get an
    academic service provider licence (kegg.jp/kegg/legal.html). The API
    page also asks for no more than 3 calls a second, or access is blocked.

    So this project:
      * fetches KEGG only on your own machine, for study (data/ never goes
        to GitHub), at under 3 requests a second,
      * keeps KEGG-derived rows out of the public app and the public data
        release (ROADMAP, Phase 9), which publish only openly licensed data,
      * leaves KEGG out entirely if you aren't an academic user: run the
        other sources by name instead of --all (docs/04-more-sources-secrets.md).

    Cite: Kanehisa M et al. (2025) KEGG: biological systems database as a
    model of the real world. Nucleic Acids Research 53(D1):D672-D677.
    doi:10.1093/nar/gkae909
"""

from __future__ import annotations

import re
from pathlib import Path

import requests

from microbegraph.paths import relative_to_repo
from microbegraph.sources.api import ApiSource
from microbegraph.sources.base import FetchResult, ProbeReport, SourceError, TidyResult
from microbegraph.staging import edge_row, node_row, properties_of, read_table, write_tables

KEGG = "https://rest.kegg.jp"
LEGAL_PAGE = "https://www.kegg.jp/kegg/legal.html"

# file name in the snapshot -> question
QUESTIONS: dict[str, str] = {
    "info_kegg.txt": f"{KEGG}/info/kegg",
    "list_pathway.txt": f"{KEGG}/list/pathway",
    "link_pathway_compound.txt": f"{KEGG}/link/pathway/compound",
    "pathway_categories.txt": f"{KEGG}/get/br:br08901",
}

# Maps of maps, left out (see the docstring above).
SKIPPED_SUBCATEGORIES = frozenset({"Global and overview maps",
                                   "Chemical structure transformation maps"})

_RELEASE_LINE = re.compile(r"^\s*(pathway|compound)\s+[\d,]+\s+(\d{4}/\d{2}/\d{2})\s*$")
_LINK_LINE = re.compile(r"^cpd:(C\d{5})\tpath:(map\d{5})$")
_MAP_NUMBER = re.compile(r"^C\s+(\d{5})\s+(.+)$")


def release_dates(info_text: str) -> dict[str, str]:
    """{'pathway': '2026/10/09', 'compound': '2026/10/09'} from the /info/kegg answer."""
    found = {}
    for line in info_text.splitlines():
        match = _RELEASE_LINE.match(line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def version_text(info_text: str) -> str:
    dates = release_dates(info_text)
    return (f"pathway {dates.get('pathway', '?')}, compound {dates.get('compound', '?')}"
            if dates else "unknown")


def parse_pathway_list(text: str) -> dict[str, str]:
    """'map00660\\tC5-Branched dibasic acid metabolism' lines -> {map00660: name}."""
    names = {}
    for line in text.splitlines():
        number, _, name = line.partition("\t")
        if number.startswith("map") and name:
            names[number.strip()] = name.strip()
    return names


def parse_links(text: str) -> dict[str, set[str]]:
    """'cpd:C00490\\tpath:map00660' lines -> {C00490: {map00660, ...}}."""
    links: dict[str, set[str]] = {}
    for line in text.splitlines():
        match = _LINK_LINE.match(line.strip())
        if match:
            links.setdefault(match.group(1), set()).add(match.group(2))
    return links


def parse_categories(text: str) -> dict[str, tuple[str, str]]:
    """
    The br08901 hierarchy -> {map00660: ("Metabolism", "Carbohydrate metabolism")}.

    The file is an outline: lines starting "A" are top categories, "B"
    subcategories, "C" the maps themselves. A map filed twice keeps its
    first place.
    """
    categories: dict[str, tuple[str, str]] = {}
    top = sub = ""
    for line in text.splitlines():
        if line.startswith("A"):
            top = line[1:].strip()
        elif line.startswith("B"):
            sub = line[1:].strip()
        elif line.startswith("C"):
            match = _MAP_NUMBER.match(line)
            if match:
                categories.setdefault(f"map{match.group(1)}", (top, sub))
    return categories


class KeggSource(ApiSource):
    """KEGG: which pathway maps our compounds appear on."""

    name = "kegg"
    licence = "KEGG: academic use only (kegg.jp/kegg/legal.html)"
    homepage = "https://www.kegg.jp"
    pause_seconds = 0.4

    # ======================================================================
    # probe()
    # ======================================================================
    def probe(self) -> ProbeReport:
        report = ProbeReport(source=self.name, reachable=False)
        try:
            info = self.http_get(QUESTIONS["info_kegg.txt"]).content.decode("utf-8")
            report.reachable = True
            report.facts.append(f"release        : {version_text(info)}")
        except (requests.RequestException, SourceError, UnicodeDecodeError) as error:
            report.warnings.append(f"Could not reach KEGG ({error}). Check your connection.")
        report.facts.append(f"terms of use   : academic use only, see {LEGAL_PAGE}")
        report.facts.append("public release : KEGG rows are kept out of it (ROADMAP, Phase 9)")
        report.facts.append(f"to ask about   : {len(QUESTIONS)} requests, whole lists")
        facts, warnings = self.locker_facts()
        report.facts += facts
        report.warnings += warnings
        return report

    # ======================================================================
    # fetch()
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        asked_for = {"questions": list(QUESTIONS.values())}
        reused = self.reuse_today(asked_for)
        if reused:
            return reused

        snapshot = self.start_snapshot(asked_for)
        version = "unknown"
        for filename, url in QUESTIONS.items():
            body = self.http_get(url).content
            text = body.decode("utf-8", errors="replace")
            if filename == "info_kegg.txt":
                version = version_text(text)
            path = snapshot.save(filename, body, url=url, method="GET", sent={},
                                 n_records=_count_records(filename, text),
                                 source_version=version)
            self.say(f"  [{self.name}] {relative_to_repo(path)}")
            self.pause()
        return snapshot.finish(version, notes={"terms_of_use": LEGAL_PAGE})

    # ======================================================================
    # tidy()
    # ======================================================================
    def tidy(self) -> TidyResult:
        folder, manifest = self.latest_snapshot()
        retrieved_at = manifest["started_at"][:10]
        texts = {name: _read_text(folder / name) for name in QUESTIONS}
        names = parse_pathway_list(texts["list_pathway.txt"])
        links = parse_links(texts["link_pathway_compound.txt"])
        categories = parse_categories(texts["pathway_categories.txt"])
        for name, found in (("list_pathway.txt", names), ("link_pathway_compound.txt", links),
                            ("pathway_categories.txt", categories)):
            if not found:
                raise SourceError(
                    f"{relative_to_repo(folder / name)} has none of the lines expected from "
                    f"KEGG. Open it to see what arrived, then run the fetch again."
                )

        # Which of our compounds have a KEGG number? PubChem's tables say.
        compounds: dict[str, list[str]] = {}
        for row in read_table("pubchem", "nodes", self.staging_dir, needed_by=self.name):
            kegg_ids = properties_of(row).get("kegg_compound_ids", "")
            if row["node_type"] == "Compound" and kegg_ids:
                compounds[row["node_id"]] = kegg_ids.split("|")

        counts = {"pathways_listed": len(names),
                  "compound_pathway_links": sum(len(v) for v in links.values()),
                  "our_compounds_with_kegg_id": len(compounds),
                  "our_kegg_ids_on_no_map": 0, "links_to_overview_maps_skipped": 0,
                  "participates_in_edges": 0, "pathways_used": 0}
        edges: dict[tuple[str, str], set[str]] = {}
        used: set[str] = set()
        for compound_id, kegg_ids in compounds.items():
            for kegg_id in kegg_ids:
                maps = links.get(kegg_id, set())
                if not maps:
                    counts["our_kegg_ids_on_no_map"] += 1
                for map_id in sorted(maps):
                    if categories.get(map_id, ("", ""))[1] in SKIPPED_SUBCATEGORIES:
                        counts["links_to_overview_maps_skipped"] += 1
                        continue
                    edges.setdefault((compound_id, map_id), set()).add(kegg_id)
                    used.add(map_id)

        nodes = []
        for map_id in sorted(used):
            category, subcategory = categories.get(map_id, ("", ""))
            nodes.append(node_row(f"kegg.pathway:{map_id}", "Pathway",
                                  names.get(map_id, map_id),
                                  {"category": category, "subcategory": subcategory},
                                  self.name, retrieved_at))
        edge_rows = [edge_row(compound_id, f"kegg.pathway:{map_id}", "PARTICIPATES_IN",
                              "database_assertion", self.name, "|".join(sorted(kegg_ids)),
                              retrieved_at)
                     for (compound_id, map_id), kegg_ids in edges.items()]
        counts["participates_in_edges"] = len(edge_rows)
        counts["pathways_used"] = len(nodes)

        summary = {
            "source": self.name,
            "source_version": manifest.get("source_version", ""),
            "snapshot": relative_to_repo(folder),
            "retrieved_at": retrieved_at,
            "terms_of_use": LEGAL_PAGE,
            "counts": counts,
        }
        external = {compound_id: "Compound" for compound_id in compounds}
        return write_tables(self.name, nodes, edge_rows, summary, self.staging_dir,
                            external_node_types=external)


def _count_records(filename: str, text: str) -> int:
    if filename == "pathway_categories.txt":
        return sum(1 for line in text.splitlines() if line.startswith("C"))
    if filename == "info_kegg.txt":
        return 1
    return sum(1 for line in text.splitlines() if line.strip())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SourceError(f"{relative_to_repo(path)} can't be read ({error}). "
                          f"Run the fetch again.") from error
