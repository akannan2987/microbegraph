"""
MicrobeGraph, the curated bridge (Phase 2).

WHAT THE BRIDGE IS
    MIBiG says which molecules a microbe makes and that a molecule is, say,
    "antifungal". No public database says, in a form a program can read,
    "this molecule protects THIS crop against THIS disease". That last link
    lives in papers.

    So the project keeps its own small table of those links, read from the
    papers by hand, one cited row each:

        curation/compound_pathogen_crop.csv

    A row says: compound X was shown to inhibit pathogen Y, which causes
    disease Z on crop W, in the paper with this DOI. It's the bridge from
    "the chemistry" to "the farm", which is where the name comes from.

    The picture I keep in mind is a reading list with notes in the margin.
    Every claim has its page number, so anyone can open the paper and check.

WHY IT'S IN THE REPOSITORY, NOT IN data/
    Every other source is downloaded, so it lives in data/ and is rebuilt
    on demand. The bridge is written by hand, so it can't be rebuilt from
    anywhere: it IS the original. It's committed to Git, and Git's history
    is its provenance log (who changed which row, when, and why).

    So fetch() has nothing to download. It says so and moves on.

WHAT tidy() CHECKS, ROW BY ROW
    Before anything is written, every row must pass these checks. One
    failure stops the tidy and names the row, so a typo can't slip in.

     1. The columns are exactly the ones listed in BRIDGE_COLUMNS, in order.
     2. Every column except notes is filled in.
     3. relationship is INHIBITS (the only kind of row the bridge holds).
     4. The compound exists in MIBiG's tables, under that exact identifier.
     5. The pathogen is an NCBI taxid (ncbitaxon:<digits>).
     6. pathogen_type is one of PATHOGEN_TYPES.
     7. crop_curie is mg.crop:<crop_name, lowercase and hyphenated>.
     8. crop_category is one of CROP_CATEGORIES.
     9. citation is doi:10.<...> or pmid:<digits> (several joined by "|").
    10. confidence is a number from 0 to 1.
    11. added_on is a real date, written YYYY-MM-DD.
    12. No two rows describe the same compound, pathogen and crop.
    13. When NCBI Taxonomy has been fetched: the pathogen exists there, its
        name matches NCBI's current scientific name, and its type matches
        NCBI's group (fungus = Fungi, oomycete = Oomycetes...). A paper's
        older name belongs in the notes column.

WHAT tidy() TURNS THE ROWS INTO
    nodes  Pathogen   ncbitaxon:<taxid>   name, pathogen_type, diseases
           Crop       mg.crop:<slug>      name, scientific_name, category
    edges  INHIBITS   Compound -> Pathogen   curated_literature
           INFECTS    Pathogen -> Crop       curated_literature
    Both edges carry the row's citation and confidence. Rows that share an
    arrow (one paper testing one compound on two crops, say) become one arrow
    that keeps every citation, the higher confidence and the earliest date.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

from microbegraph.paths import BRIDGE_FILE, relative_to_repo
from microbegraph.sources.base import (
    FetchResult,
    ProbeReport,
    Source,
    SourceError,
    TidyResult,
    slugify,
)
from microbegraph.staging import (
    edge_row,
    node_row,
    properties_of,
    read_table,
    staging_path,
    write_tables,
)

BRIDGE_COLUMNS: tuple[str, ...] = (
    "compound_name", "compound_curie", "pathogen_name", "pathogen_curie", "pathogen_type",
    "disease", "crop_name", "crop_curie", "crop_scientific_name", "crop_category",
    "relationship", "citation", "confidence", "added_on", "notes",
)
OPTIONAL_COLUMNS = frozenset({"notes"})

PATHOGEN_TYPES = ("fungus", "oomycete", "bacterium", "virus", "nematode", "other")
CROP_CATEGORIES = ("cereal", "fruit", "vegetable", "legume", "fibre", "oilseed", "other")

# Which NCBI group each pathogen type must belong to (check 13).
GROUP_FOR_TYPE = {"fungus": "Fungi", "oomycete": "Oomycetes", "bacterium": "Bacteria",
                  "virus": "Viruses", "nematode": "Animals"}

_CITATION = re.compile(r"^(doi:10\.\d{4,9}/\S+|pmid:\d+)$")
_TAXID = re.compile(r"^ncbitaxon:\d+$")


def read_bridge(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    """
    The header and every row of the bridge, each row with its line number in
    the file (the header is line 1), so a problem can point at the line.

    "utf-8-sig" also reads a file that a spreadsheet program saved with an
    invisible marker at the start. Editing the file in VS Code avoids that.
    """
    if not path.exists():
        raise SourceError(f"{relative_to_repo(path)} is missing. It is part of the "
                          f"repository; restore it with:  git checkout -- {relative_to_repo(path)}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows = [(reader.line_num, {k: (v or "").strip() for k, v in row.items() if k})
                for row in reader]
    return header, rows


def check_rows(header: list[str], rows: list[tuple[int, dict[str, str]]],
               mibig_compounds: set[str],
               ncbi: dict[str, dict[str, Any]] | None) -> list[str]:
    """
    Every problem in the bridge, as sentences naming the line. Empty = all good.

    `ncbi` maps a pathogen node id to {name, group} from NCBI Taxonomy's
    tables, or is None when NCBI hasn't been fetched yet (check 13 is skipped).
    """
    if tuple(header) != BRIDGE_COLUMNS:
        return [f"check 1: the columns should be exactly: {','.join(BRIDGE_COLUMNS)}\n"
                f"      found: {','.join(header)}"]
    problems: list[str] = []
    seen: dict[tuple[str, str, str], int] = {}
    for line, row in rows:
        where = f"line {line}"
        for column in BRIDGE_COLUMNS:
            if column not in OPTIONAL_COLUMNS and not row.get(column):
                problems.append(f"check 2: {where}: {column} is empty")
        if row.get("relationship") and row["relationship"] != "INHIBITS":
            problems.append(f"check 3: {where}: relationship is {row['relationship']!r}; "
                            f"the bridge only holds INHIBITS rows")
        compound = row.get("compound_curie", "")
        if compound and compound not in mibig_compounds:
            problems.append(f"check 4: {where}: {compound} is not a compound in MIBiG's tables")
        pathogen = row.get("pathogen_curie", "")
        if pathogen and not _TAXID.match(pathogen):
            problems.append(f"check 5: {where}: pathogen_curie {pathogen!r} should be "
                            f"ncbitaxon:<digits>")
        kind = row.get("pathogen_type", "")
        if kind and kind not in PATHOGEN_TYPES:
            problems.append(f"check 6: {where}: pathogen_type {kind!r} should be one of "
                            f"{', '.join(PATHOGEN_TYPES)}")
        crop_name, crop = row.get("crop_name", ""), row.get("crop_curie", "")
        if crop_name and crop and crop != f"mg.crop:{slugify(crop_name)}":
            problems.append(f"check 7: {where}: crop_curie should be "
                            f"mg.crop:{slugify(crop_name)} for crop {crop_name!r}")
        category = row.get("crop_category", "")
        if category and category not in CROP_CATEGORIES:
            problems.append(f"check 8: {where}: crop_category {category!r} should be one of "
                            f"{', '.join(CROP_CATEGORIES)}")
        for citation in filter(None, row.get("citation", "").split("|")):
            if not _CITATION.match(citation.strip()):
                problems.append(f"check 9: {where}: citation {citation!r} should be "
                                f"doi:10.<...> or pmid:<digits>")
        if row.get("confidence"):
            try:
                value = float(row["confidence"])
                if not 0.0 <= value <= 1.0:
                    raise ValueError
            except ValueError:
                problems.append(f"check 10: {where}: confidence {row['confidence']!r} should be "
                                f"a number from 0 to 1")
        if row.get("added_on"):
            try:
                date.fromisoformat(row["added_on"])
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["added_on"]):
                    raise ValueError
            except ValueError:
                problems.append(f"check 11: {where}: added_on {row['added_on']!r} should be a "
                                f"date written YYYY-MM-DD")
        key = (compound, pathogen, crop)
        if all(key):
            if key in seen:
                problems.append(f"check 12: {where} repeats line {seen[key]} "
                                f"(same compound, pathogen and crop)")
            else:
                seen[key] = line
        if ncbi is not None and pathogen and _TAXID.match(pathogen):
            facts = ncbi.get(pathogen)
            if facts is None:
                problems.append(f"check 13: {where}: {pathogen} is not in NCBI Taxonomy's "
                                f"tables. Run: python -m microbegraph.fetch --source ncbi_taxonomy")
                continue
            if row.get("pathogen_name") and row["pathogen_name"] != facts["name"]:
                problems.append(f"check 13: {where}: NCBI calls {pathogen} {facts['name']!r}, "
                                f"not {row['pathogen_name']!r}. Use NCBI's name and put the "
                                f"paper's name in notes.")
            wanted = GROUP_FOR_TYPE.get(kind)
            if wanted and facts.get("group") and facts["group"] != wanted:
                problems.append(f"check 13: {where}: pathogen_type is {kind!r} but NCBI files "
                                f"{pathogen} under {facts['group']}")
    return problems


class CurationSource(Source):
    """The curated bridge: compound -> pathogen -> crop, one cited row at a time."""

    name = "curation"
    licence = "MIT (this repository)"
    homepage = "curation/compound_pathogen_crop.csv"

    def __init__(self, *args: Any, bridge_file: Path = BRIDGE_FILE, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bridge_file = Path(bridge_file)

    # ---------------------------------------------------------------- probe()
    def probe(self) -> ProbeReport:
        """Read and check the bridge, without writing anything. No network."""
        report = ProbeReport(source=self.name, reachable=self.bridge_file.exists())
        if not report.reachable:
            report.warnings.append(f"{relative_to_repo(self.bridge_file)} is missing.")
            return report
        header, rows = read_bridge(self.bridge_file)
        report.facts.append(f"file           : {relative_to_repo(self.bridge_file)}")
        report.facts.append(f"rows           : {len(rows)}")
        if rows:
            def distinct(column: str) -> int:
                return len({r.get(column, "") for _, r in rows})
            papers = {c for _, r in rows for c in r.get("citation", "").split("|") if c}
            report.facts.append(f"covers         : {distinct('compound_curie')} compounds, "
                                f"{distinct('pathogen_curie')} pathogens, "
                                f"{distinct('crop_curie')} crops, {len(papers)} papers")
        try:
            ncbi = self._ncbi_facts(announce=False)
            problems = check_rows(header, rows, self._mibig_compounds(), ncbi)
        except SourceError as error:
            report.warnings.append(str(error))
            return report
        if problems:
            report.warnings.append(f"{len(problems)} problem(s); the tidy will refuse until "
                                   f"they're fixed:\n    " + "\n    ".join(problems[:10]))
        elif ncbi is None:
            report.facts.append("checks         : every row passes checks 1 to 12 (check 13 "
                                "waits for NCBI Taxonomy)")
        else:
            report.facts.append("checks         : every row passes all 13 checks")
        return report

    # ---------------------------------------------------------------- fetch()
    def fetch(self) -> list[FetchResult]:
        self.say(f"  [{self.name}] nothing to download: the rows live in "
                 f"{relative_to_repo(self.bridge_file)}, and Git records every change to them")
        return []

    # ---------------------------------------------------------------- tidy()
    def tidy(self) -> TidyResult:
        header, rows = read_bridge(self.bridge_file)
        mibig_compounds = self._mibig_compounds()
        ncbi = self._ncbi_facts()
        problems = check_rows(header, rows, mibig_compounds, ncbi)
        if problems:
            shown = "\n    ".join(problems[:15])
            raise SourceError(
                f"{relative_to_repo(self.bridge_file)} has {len(problems)} problem(s). "
                f"Nothing was written. Fix these lines and run the tidy again:\n    {shown}"
            )

        pathogens: dict[str, dict[str, Any]] = {}
        crops: dict[str, dict[str, Any]] = {}
        arrows: dict[tuple[str, str, str], dict[str, Any]] = {}
        for _, row in rows:
            pathogen, crop = row["pathogen_curie"], row["crop_curie"]
            citations = set(row["citation"].split("|"))
            confidence, added = float(row["confidence"]), row["added_on"]

            p = pathogens.setdefault(pathogen, {"name": row["pathogen_name"],
                                                "type": row["pathogen_type"],
                                                "diseases": set(), "date": added})
            p["diseases"].add(f"{row['disease']} ({row['crop_name']})")
            p["date"] = min(p["date"], added)
            c = crops.setdefault(crop, {"name": row["crop_name"],
                                        "scientific_name": row["crop_scientific_name"],
                                        "category": row["crop_category"], "date": added})
            c["date"] = min(c["date"], added)

            for key in ((row["compound_curie"], pathogen, "INHIBITS"),
                        (pathogen, crop, "INFECTS")):
                arrow = arrows.setdefault(key, {"citations": set(), "confidence": 0.0,
                                                "date": added})
                arrow["citations"] |= citations
                arrow["confidence"] = max(arrow["confidence"], confidence)
                arrow["date"] = min(arrow["date"], added)

        nodes = [node_row(pid, "Pathogen", p["name"],
                          {"pathogen_type": p["type"], "diseases": "|".join(sorted(p["diseases"]))},
                          self.name, p["date"]) for pid, p in pathogens.items()]
        nodes += [node_row(cid, "Crop", c["name"],
                           {"scientific_name": c["scientific_name"], "category": c["category"]},
                           self.name, c["date"]) for cid, c in crops.items()]
        edges = [edge_row(src, dst, kind, "curated_literature", self.name,
                          self.bridge_file.name, a["date"],
                          citation="|".join(sorted(a["citations"])),
                          confidence=f"{a['confidence']:.2f}")
                 for (src, dst, kind), a in arrows.items()]

        used_compounds = {row["compound_curie"] for _, row in rows}
        counts = {
            "rows_read": len(rows),
            "compounds_used": len(used_compounds),
            "pathogen_nodes": len(pathogens),
            "crop_nodes": len(crops),
            "inhibits_edges": sum(1 for k in arrows if k[2] == "INHIBITS"),
            "infects_edges": sum(1 for k in arrows if k[2] == "INFECTS"),
            "papers_cited": len({c for a in arrows.values() for c in a["citations"]}),
            "rows_checked_against_ncbi": len(rows) if ncbi is not None else 0,
        }
        summary = {
            "source": self.name,
            "source_version": "repository file",
            "file": relative_to_repo(self.bridge_file),
            "retrieved_at": max((r["added_on"] for _, r in rows), default=""),
            "counts": counts,
        }
        external = {cid: "Compound" for cid in used_compounds}
        return write_tables(self.name, nodes, edges, summary, self.staging_dir,
                            external_node_types=external)

    # ---------------------------------------------------------------- helpers
    def _mibig_compounds(self) -> set[str]:
        return {row["node_id"] for row in read_table("mibig", "nodes", self.staging_dir,
                                                     needed_by=self.name)
                if row["node_type"] == "Compound"}

    def _ncbi_facts(self, announce: bool = True) -> dict[str, dict[str, Any]] | None:
        """Name and group of every NCBI node, or None if NCBI hasn't been tidied yet."""
        if not staging_path("ncbi_taxonomy", "nodes", self.staging_dir).exists():
            if announce:
                self.say(f"  [{self.name}] NCBI Taxonomy isn't tidied yet, so check 13 is "
                         f"skipped. Run: python -m microbegraph.fetch --source ncbi_taxonomy")
            return None
        rows = read_table("ncbi_taxonomy", "nodes", self.staging_dir, needed_by=self.name)
        return {row["node_id"]: {"name": row["name"], "group": properties_of(row).get("group")}
                for row in rows}
