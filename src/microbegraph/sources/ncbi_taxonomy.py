"""
MicrobeGraph, the NCBI Taxonomy adapter (Phase 2).

WHAT NCBI TAXONOMY IS
    The family tree of every organism that has sequences in the public
    databases, kept by the US National Center for Biotechnology Information
    (NCBI). Each organism, and each group above it, has a number (a "taxid"):
    Bacillus velezensis FZB42 is 326423, the species Bacillus velezensis is
    492670, the genus Bacillus is 1386, all Bacteria are 2.

    Think of a postal address read from the bottom up: house, street, town,
    county, country. Each line is a bigger group that contains the one below.
    In biology the lines are called RANKS: species, genus, family, order,
    class, phylum, kingdom, domain.

WHY IT MATTERS HERE
    MIBiG gives each cluster's organism a taxid, but nothing above it. With
    the family tree, the graph can answer "which gene clusters come from any
    Bacillus?" or "is this antifungal made only by Pseudomonas?". It also
    checks the curated bridge: every pathogen in it must be a real NCBI
    entry, under the name NCBI uses today.

HOW IT ASKS (E-UTILITIES)
    NCBI's API is called E-utilities. Two of its programs are used:
        einfo    facts about the database (its build number and size)
        efetch   full records for a list of taxids, as XML
    The taxids go in a POST body, 200 per request, together with:
        tool     "microbegraph", so NCBI knows which program is asking
        email    yours, if you put one in .env (optional)
        api_key  yours, if you put one in .env (optional)

    WITHOUT a key NCBI allows 3 requests a second; WITH one, 10. This adapter
    paces itself just under whichever applies. The key travels only in the
    POST body: never in a web address, never in a log, never on screen.
    See src/microbegraph/settings.py for the rules on keys.

THE 2025 RANK CHANGES (worth knowing before reading the data)
    NCBI renamed and added ranks in 2025. "superkingdom" became "domain"
    (Bacteria, Archaea, Eukaryota), and bacteria gained a real "kingdom" rank
    (Bacillati, Pseudomonadati...). Because "kingdom" now means something
    specific, the broad grouping this project uses for colouring and filtering
    is called `group` instead: Bacteria, Archaea, Fungi, Oomycetes, Plants,
    Animals, Viruses or Other.

WHAT tidy() TURNS THE ANSWERS INTO
    nodes  Organism   ncbitaxon:<taxid>  each MIBiG organism, with rank,
                                         lineage, group, division, synonyms
           Organism   ncbitaxon:<taxid>  its ancestors at the main ranks
           Pathogen   ncbitaxon:<taxid>  each bridge pathogen, with rank,
                                         lineage, group, synonyms
    edges  MEMBER_OF  child -> parent, one step up at a time
                      (strain -> species -> genus -> ... -> domain)

    Numbers that NCBI has MERGED into another come back under the new number,
    with the old one listed as an "also known as" (AkaTaxIds). The node gets
    the current number and remembers the old one (merged_from). Numbers NCBI
    has DELETED come back with nothing; they're counted and listed in the
    summary.

    One taxid can be both a producer and a pathogen (Botrytis cinerea makes
    botcinic acid and causes grey mould). In these tables it stays an
    Organism and is counted under pathogens_also_organisms; Phase 4 decides
    how one node carries both roles.

LICENCE AND CITATION
    NCBI places no restrictions on using its data. NCBI Taxonomy is not an
    authority on scientific names, so the bridge keeps the name a paper used
    in its notes whenever NCBI's differs.

    Cite: Schoch CL et al. (2020) NCBI Taxonomy: a comprehensive update on
    curation, resources and tools. Database baaa062. doi:10.1093/database/baaa062
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import BRIDGE_FILE, relative_to_repo
from microbegraph.settings import describe, ncbi_api_key, ncbi_email
from microbegraph.sources.api import ApiSource, batches_text, chunks
from microbegraph.sources.base import FetchResult, ProbeReport, SourceError, TidyResult
from microbegraph.staging import edge_row, node_row, read_table, write_tables

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EINFO_URL = f"{EUTILS}/einfo.fcgi"
EFETCH_URL = f"{EUTILS}/efetch.fcgi"
TOOL = "microbegraph"
BATCH_SIZE = 200

PAUSE_WITHOUT_KEY = 0.34    # just under 3 requests a second
PAUSE_WITH_KEY = 0.11       # just under 10 requests a second

# The ranks kept as nodes of the family tree. Everything in between ("clade",
# "species group", "suborder"...) stays in the lineage text but gets no node,
# which keeps the tree readable. "superkingdom" is kept for records written
# before NCBI renamed it "domain" in 2025.
KEPT_RANKS = ("superkingdom", "domain", "kingdom", "phylum", "class", "order",
              "family", "genus", "species")

# The broad group, read from the names in an organism's lineage. Checked in
# this order; the first name found decides.
GROUP_BY_LINEAGE_NAME = (
    ("Viruses", "Viruses"),
    ("Archaea", "Archaea"),
    ("Bacteria", "Bacteria"),
    ("Oomycota", "Oomycetes"),
    ("Fungi", "Fungi"),
    ("Viridiplantae", "Plants"),
    ("Metazoa", "Animals"),
)


def group_of(lineage_names: list[str]) -> str:
    """The broad group of an organism from the names in its lineage, e.g. 'Fungi'."""
    names = set(lineage_names)
    for name, group in GROUP_BY_LINEAGE_NAME:
        if name in names:
            return group
    return "Other"


def parse_taxa(xml_bytes: bytes) -> list[dict[str, Any]]:
    """
    Read one efetch answer into plain records.

    Each record: taxid, name, rank, division, lineage (text), lineage_ex
    (a list of (taxid, name, rank), top first), synonyms, aka (old numbers).
    """
    root = ET.fromstring(xml_bytes)
    if root.tag != "TaxaSet":
        raise ValueError(f"expected <TaxaSet>, found <{root.tag}>")
    records = []
    for taxon in root.findall("Taxon"):
        lineage_ex = [(t.findtext("TaxId", ""), t.findtext("ScientificName", ""),
                       t.findtext("Rank", "")) for t in taxon.findall("LineageEx/Taxon")]
        records.append({
            "taxid": taxon.findtext("TaxId", "").strip(),
            "name": taxon.findtext("ScientificName", "").strip(),
            "rank": taxon.findtext("Rank", "").strip(),
            "division": taxon.findtext("Division", "").strip(),
            "lineage": taxon.findtext("Lineage", "").strip(),
            "lineage_ex": lineage_ex,
            "synonyms": [s.text.strip() for s in taxon.findall("OtherNames/Synonym") if s.text],
            "aka": [a.text.strip() for a in taxon.findall("AkaTaxIds/TaxId") if a.text],
        })
    return records


def bridge_pathogen_taxids(bridge_file: Path) -> list[str]:
    """The taxids of every pathogen in the curated bridge, in number order."""
    if not bridge_file.exists():
        return []
    with bridge_file.open(newline="", encoding="utf-8-sig") as handle:
        curies = {(row.get("pathogen_curie") or "").strip() for row in csv.DictReader(handle)}
    ids = {c.split(":", 1)[1] for c in curies if c.startswith("ncbitaxon:")}
    return sorted((i for i in ids if i.isdigit()), key=int)


class NcbiTaxonomySource(ApiSource):
    """NCBI Taxonomy: the family tree above every organism and pathogen."""

    name = "ncbi_taxonomy"
    licence = "NCBI: no restrictions"
    homepage = "https://www.ncbi.nlm.nih.gov/taxonomy"

    def __init__(self, *args: Any, bridge_file: Path = BRIDGE_FILE, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bridge_file = Path(bridge_file)
        self.api_key = ncbi_api_key()
        self.email = ncbi_email()
        if "pause_seconds" not in kwargs:
            self.pause_seconds = PAUSE_WITH_KEY if self.api_key else PAUSE_WITHOUT_KEY

    # ======================================================================
    # probe()
    # ======================================================================
    def probe(self) -> ProbeReport:
        report = ProbeReport(source=self.name, reachable=False)
        try:
            info = self._einfo()
            report.reachable = True
            report.facts.append(f"database build : {info.get('dbbuild', '?')}")
            report.facts.append(f"taxa           : {int(info.get('count', 0)):,}")
            report.facts.append(f"last update    : {info.get('lastupdate', '?')}")
        except (requests.RequestException, SourceError, ValueError, KeyError, IndexError) as error:
            report.warnings.append(f"Could not reach NCBI E-utilities ({error}). "
                                   f"Check your connection.")
        speed = "10 requests a second" if self.api_key else "3 requests a second"
        report.facts.append(f"API key        : {describe(self.api_key)} ({speed})")
        report.facts.append(f"contact email  : {describe(self.email)}")
        try:
            organisms, pathogens = self._taxids_to_ask()
            n = len(set(organisms) | set(pathogens))
            report.facts.append(f"to ask about   : {len(organisms):,} organisms from MIBiG and "
                                f"{len(pathogens)} pathogens from the bridge, "
                                f"{len(chunks(list(range(n)), BATCH_SIZE)) + 1} requests")
        except SourceError:
            report.facts.append("to ask about   : unknown until MIBiG is tidied (Phase 1)")
        facts, warnings = self.locker_facts()
        report.facts += facts
        report.warnings += warnings
        return report

    def _einfo(self) -> dict[str, Any]:
        # No key and no email here: this is a GET, and a GET's details are part
        # of its web address, which can turn up in error messages.
        response = self.http_get(EINFO_URL, params={"db": "taxonomy", "retmode": "json",
                                                     "tool": TOOL})
        return _dbinfo(response.content)

    def _taxids_to_ask(self) -> tuple[list[str], list[str]]:
        organisms = set()
        for row in read_table("mibig", "nodes", self.staging_dir, needed_by=self.name):
            if row["node_type"] == "Organism" and row["node_id"].startswith("ncbitaxon:"):
                organisms.add(row["node_id"].split(":", 1)[1])
        pathogens = bridge_pathogen_taxids(self.bridge_file)
        return sorted(organisms, key=int), pathogens

    # ======================================================================
    # fetch()
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        organisms, pathogens = self._taxids_to_ask()
        asked_for = {"organism_taxids": organisms, "pathogen_taxids": pathogens}
        reused = self.reuse_today(asked_for)
        if reused:
            return reused

        snapshot = self.start_snapshot(asked_for)
        self.say(f"  [{self.name}] API key {describe(self.api_key)}, pacing for "
                 f"{'10' if self.api_key else '3'} requests a second")
        response = self.http_get(EINFO_URL, params={"db": "taxonomy", "retmode": "json",
                                                     "tool": TOOL})
        version = str(_dbinfo(response.content).get("dbbuild", "unknown"))
        snapshot.save("einfo.json", response.content, url=EINFO_URL, method="GET",
                      sent={"db": "taxonomy", "retmode": "json", "tool": TOOL},
                      n_records=1, source_version=version)
        self.pause()

        every_id = sorted(set(organisms) | set(pathogens), key=int)
        batches = chunks(every_id, BATCH_SIZE)
        self.say(f"  [{self.name}] asking about {len(every_id):,} taxids in "
                 f"{batches_text(len(batches))} of up to {BATCH_SIZE}")
        for number, batch in enumerate(batches, start=1):
            form = {"db": "taxonomy", "id": ",".join(batch), "retmode": "xml", "tool": TOOL}
            if self.email:
                form["email"] = self.email
            if self.api_key:
                form["api_key"] = self.api_key       # in the body only, never the address
            response = self.http_post(EFETCH_URL, form)
            try:
                n_records: int | str = len(parse_taxa(response.content))
            except (ET.ParseError, ValueError):
                n_records = ""
            # What the manifest records: the ids, and only whether a key and
            # an email were sent, never their values.
            sent = {"db": "taxonomy", "retmode": "xml", "tool": TOOL, "id": batch,
                    "email": describe(self.email), "api_key": describe(self.api_key)}
            path = snapshot.save(f"efetch_{number:03d}.xml", response.content, url=EFETCH_URL,
                                 method="POST", sent=sent, n_records=n_records,
                                 source_version=version)
            if n_records == "":
                raise SourceError(
                    f"{relative_to_repo(path)} arrived and is logged, but it isn't the "
                    f"taxonomy XML expected. Open it to see NCBI's message, then run the "
                    f"fetch again."
                )
            self.say(f"  [{self.name}] {relative_to_repo(path)} ({n_records} taxa)")
            self.pause()
        return snapshot.finish(version)

    # ======================================================================
    # tidy()
    # ======================================================================
    def tidy(self) -> TidyResult:
        folder, manifest = self.latest_snapshot()
        retrieved_at = manifest["started_at"][:10]
        organisms = list(manifest["asked_for"]["organism_taxids"])
        pathogens = list(manifest["asked_for"]["pathogen_taxids"])

        by_id: dict[str, dict[str, Any]] = {}
        aka: dict[str, str] = {}
        answers_read = 0
        for answer in manifest["answers"]:
            if not answer["file"].startswith("efetch_"):
                continue
            path = folder / answer["file"]
            try:
                records = parse_taxa(path.read_bytes())
            except (OSError, ET.ParseError, ValueError) as error:
                raise SourceError(f"{relative_to_repo(path)} can't be read ({error}). "
                                  f"Run the fetch again.") from error
            answers_read += 1
            for record in records:
                by_id[record["taxid"]] = record
                for old in record["aka"]:
                    aka[old] = record["taxid"]

        builder = _TreeBuilder(retrieved_at)
        merged: dict[str, str] = {}
        not_found: list[str] = []
        organism_ids, pathogen_ids = set(organisms), set(pathogens)
        for requested in sorted(organism_ids | pathogen_ids, key=int):
            current = requested if requested in by_id else aka.get(requested)
            if current is None:
                not_found.append(requested)
                continue
            if current != requested:
                merged[requested] = current
            record = by_id[current]
            if requested in organism_ids:
                builder.add_organism(record, merged_from=requested if current != requested else "")
            if requested in pathogen_ids:
                builder.add_pathogen(record)

        builder.settle_pathogens()
        counts = {
            "answers_read": answers_read,
            "taxids_requested": len(organism_ids | set(pathogens)),
            "organisms_requested": len(organism_ids),
            "pathogens_requested": len(pathogens),
            "taxa_found": len(organism_ids | set(pathogens)) - len(not_found),
            "taxids_merged": len(merged),
            "taxids_not_found": len(not_found),
            "organism_nodes": builder.count("Organism"),
            "pathogen_nodes": builder.count("Pathogen"),
            "member_of_edges": len(builder.edges),
            "pathogens_also_organisms": len(builder.also_organisms),
        }
        summary = {
            "source": self.name,
            "source_version": manifest.get("source_version", ""),
            "snapshot": relative_to_repo(folder),
            "retrieved_at": retrieved_at,
            "counts": counts,
            "merged_taxids": merged,
            "taxids_not_found": not_found,
            "pathogens_also_organisms": sorted(builder.also_organisms, key=int),
        }
        return write_tables(self.name, builder.node_rows(), builder.edge_rows(), summary,
                            self.staging_dir)


class _TreeBuilder:
    """Collects organism, ancestor and pathogen nodes and the MEMBER_OF arrows between them."""

    def __init__(self, retrieved_at: str) -> None:
        self.retrieved_at = retrieved_at
        self.nodes: dict[str, dict[str, Any]] = {}     # taxid -> {type, name, props, leaf}
        self.pathogens: dict[str, dict[str, Any]] = {}
        self.edges: set[tuple[str, str]] = set()       # (child taxid, parent taxid)
        self.also_organisms: set[str] = set()

    def add_organism(self, record: dict[str, Any], merged_from: str = "") -> None:
        taxid = record["taxid"]
        props = _leaf_props(record)
        # Old numbers that now point here are remembered, however many there are
        # and in whatever order they were asked about.
        old = set(filter(None, self.nodes.get(taxid, {}).get("props", {})
                         .get("merged_from", "").split("|")))
        if merged_from:
            old.add(merged_from)
        if old:
            props["merged_from"] = "|".join(sorted(old, key=int))
        self.nodes[taxid] = {"type": "Organism", "name": record["name"], "props": props,
                             "leaf": True}

        # Walk up the kept ranks: the taxon itself -> nearest kept ancestor -> ...
        chain = [(i, n, r) for i, n, r in record["lineage_ex"] if r in KEPT_RANKS and i]
        child = taxid
        for ancestor_id, ancestor_name, rank in reversed(chain):
            if ancestor_id not in self.nodes:
                self.nodes[ancestor_id] = {"type": "Organism", "name": ancestor_name,
                                           "props": {"rank": rank}, "leaf": False}
            self.edges.add((child, ancestor_id))
            child = ancestor_id

    def add_pathogen(self, record: dict[str, Any]) -> None:
        self.pathogens[record["taxid"]] = {"type": "Pathogen", "name": record["name"],
                                           "props": _leaf_props(record), "leaf": True}

    def settle_pathogens(self) -> None:
        """Add pathogen nodes, except where the same taxid is already an Organism."""
        for taxid, node in self.pathogens.items():
            if taxid in self.nodes:
                self.also_organisms.add(taxid)
                existing = self.nodes[taxid]
                if not existing["leaf"]:                # an ancestor only: give it the details
                    existing["props"] = {**node["props"], **existing["props"]}
                continue
            self.nodes[taxid] = node

    def count(self, node_type: str) -> int:
        return sum(1 for n in self.nodes.values() if n["type"] == node_type)

    def node_rows(self) -> list[dict[str, Any]]:
        return [node_row(f"ncbitaxon:{taxid}", n["type"], n["name"], n["props"],
                         "ncbi_taxonomy", self.retrieved_at) for taxid, n in self.nodes.items()]

    def edge_rows(self) -> list[dict[str, Any]]:
        return [edge_row(f"ncbitaxon:{child}", f"ncbitaxon:{parent}", "MEMBER_OF",
                         "database_assertion", "ncbi_taxonomy", child, self.retrieved_at)
                for child, parent in self.edges]


def _leaf_props(record: dict[str, Any]) -> dict[str, Any]:
    names = [name for _, name, _ in record["lineage_ex"]]
    return {
        "rank": record["rank"],
        "lineage": record["lineage"],
        "group": group_of(names + [record["name"]]),
        "division": record["division"],
        "synonyms": "|".join(record["synonyms"]),
    }


def _dbinfo(body: bytes) -> dict[str, Any]:
    """The database facts from an einfo answer (NCBI sends them as a one-item list)."""
    try:
        info = json.loads(body)["einforesult"]["dbinfo"]
        return info[0] if isinstance(info, list) else info
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise SourceError(f"NCBI's einfo answer wasn't in the expected shape ({error}). "
                          f"Try again in a few minutes.") from error
