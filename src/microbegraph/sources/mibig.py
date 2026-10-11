"""
MicrobeGraph, the MIBiG adapter (Phase 1).

WHAT MIBiG IS
    MIBiG (Minimum Information about a Biosynthetic Gene Cluster) is a public,
    hand-curated catalogue of gene clusters whose products are KNOWN. Each
    entry records, among much else: which organism carries the cluster, what
    kind of chemical machinery it is (NRPS, PKS, terpene...), which molecules
    it makes, and what those molecules have been seen to do.

    You can picture it as a register of factories that records, for each
    one, who owns it, what kind of production line it runs, what it makes and
    what the products are used for, with a named inspector who checked the
    entry.

WHY IT COMES FIRST
    It supplies the first two arrows of every chain this project is built
    around, signed off by human curators against published experiments:

        Organism --HARBORS--> GeneCluster --PRODUCES--> Compound

WHICH VERSION, EXACTLY
    MIBiG 4.0, published on Zenodo (record 14169073) under CC BY 4.0, with
    an MD5 checksum we verify on every download. Pinning one exact,
    citable release means anyone re-running this project gets the same data,
    byte for byte. Moving to a newer release is a planned, documented upgrade
    (change the four constants below, re-run, compare), so it never happens
    by surprise.

    Cite: Zdouc MM et al. (2025) MIBiG 4.0: advancing biosynthetic gene
    cluster curation through global collaboration. Nucleic Acids Research
    53(D1):D678-D690. doi:10.1093/nar/gkae1115

WHAT tidy() TURNS ONE ENTRY INTO
    nodes  Organism       ncbitaxon:<taxid>
           GeneCluster    mibig:<accession>
           Compound       mg.compound:<slug of name>   (PubChem comes in Phase 4)
           Activity       mg.activity:<slug>           (only activities SEEN; a
                                                        curator's comment on one is
                                                        kept on the compound, as
                                                        activity_notes)
           CompoundClass  mg.class:<slug>              (when MIBiG gives one)
    edges  HARBORS, PRODUCES, HAS_ACTIVITY, BELONGS_TO

HOW EVIDENCE AND CONFIDENCE ARE SET (two separate questions)
    evidence_level answers "what KIND of evidence stands behind this?"
        HARBORS and PRODUCES follow the evidence MIBiG records for the cluster:
          an experiment (knock-out, heterologous expression, enzyme assays...)
                                       -> curated_experimental
          only a prediction (homology, syn-BNP) or nothing
                                       -> database_assertion
        HAS_ACTIVITY with a reference  -> curated_experimental
        HAS_ACTIVITY without one       -> database_assertion
        BELONGS_TO                     -> database_assertion

    confidence answers "how much does the source itself trust this entry?"
        MIBiG grades every entry: high, medium, low or questionable.
        We carry that grade through instead of inventing our own:
        high 0.95, medium 0.85, low 0.70, questionable 0.50.

WHAT tidy() LEAVES OUT ON PURPOSE
    * Entries whose status is not "active" (retired, pending, embargoed).
      MIBiG withdrew or has not yet released them.
    * Bioactivities recorded with "observed": false. Those are NEGATIVE
      results, where someone tested for the activity and did not find it, so
      an arrow saying "has activity" would state the opposite of the record.
      They are counted in the summary, so nothing disappears silently.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from microbegraph import provenance
from microbegraph.ontology import evidence_rank
from microbegraph.paths import relative_to_repo
from microbegraph.sources.base import (
    EDGE_COLUMNS,
    NODE_COLUMNS,
    FetchResult,
    ProbeReport,
    Source,
    SourceError,
    TidyResult,
    count_tar_json,
    file_digests,
    iter_tar_json,
    slugify,
    table_text,
    write_files_together,
)
from microbegraph.validate import check_tables

# --- The pinned release: change these four together, in one commit ----------
ZENODO_RECORD = "14169073"
MIBIG_VERSION = "4.0"
FILENAME = "mibig_json_4.0.tar.gz"
EXPECTED_MD5 = "ce1736f4fac7168d85dae3b37c77d3d2"

DOWNLOAD_URL = f"https://zenodo.org/records/{ZENODO_RECORD}/files/{FILENAME}?download=1"
RECORD_API_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD}"
RECORD_PAGE_URL = f"https://zenodo.org/records/{ZENODO_RECORD}"

# MIBiG's own quality grade, carried through as our confidence score.
QUALITY_CONFIDENCE: dict[str, float] = {
    "high": 0.95,
    "medium": 0.85,
    "low": 0.70,
    "questionable": 0.50,
}

# MIBiG's locus evidence methods that are predictions rather than experiments.
# Every other method MIBiG allows (knock-out studies, heterologous expression,
# enzymatic assays, in vitro expression, expression correlated with production,
# correlation of genomic and metabolomic data) involved measuring something.
PREDICTION_METHODS = frozenset({
    "Homology-based prediction",
    "Synthetic-bioinformatic natural product (syn-BNP)",
})


class MibigSource(Source):
    """The MIBiG 4.0 adapter: probe Zenodo, fetch one archive, tidy every entry."""

    name = "mibig"
    licence = "CC-BY-4.0"
    homepage = "https://mibig.secondarymetabolites.org"

    # ======================================================================
    # probe(): what is out there?
    # ======================================================================
    def probe(self) -> ProbeReport:
        """
        Ask Zenodo about the pinned release, without downloading it, and
        check what is already in the locker.

        It never raises for network trouble. An unreachable server is a fact
        worth reporting ("you are offline"), and crashing over it would help
        nobody.
        """
        report = ProbeReport(source=self.name, reachable=False)
        report.facts.append(f"pinned release : MIBiG {MIBIG_VERSION}, Zenodo record {ZENODO_RECORD}")
        report.facts.append(f"record page    : {RECORD_PAGE_URL}")

        try:
            response = self.http_get(RECORD_API_URL)
            record = response.json()
            report.reachable = True
        except (requests.RequestException, SourceError, ValueError) as error:
            report.warnings.append(
                f"Could not read the record from Zenodo ({error}). "
                f"Check your connection; fetch will not work until this does."
            )
            record = {}

        if record:
            metadata = record.get("metadata", {})
            report.facts.append(f"title          : {metadata.get('title', '?')}")
            report.facts.append(f"version        : {metadata.get('version', '?')}")
            report.facts.append(f"published      : {metadata.get('publication_date', '?')}")
            licence = metadata.get("license") or metadata.get("rights") or {}
            if isinstance(licence, dict):
                report.facts.append(f"licence        : {licence.get('id', '?')}")

            # Find our file in the record's file list and compare fingerprints.
            files = record.get("files") or []
            if isinstance(files, dict):            # some API versions nest the list
                files = files.get("entries") or []
                files = list(files.values()) if isinstance(files, dict) else files
            ours = next((f for f in files if f.get("key") == FILENAME), None)
            if ours is None:
                report.warnings.append(f"{FILENAME} is not listed in the record any more.")
            else:
                size_mb = (ours.get("size") or 0) / 1_048_576
                published_md5 = str(ours.get("checksum", "")).removeprefix("md5:")
                report.facts.append(f"file           : {FILENAME} ({size_mb:.1f} MB)")
                if published_md5 == EXPECTED_MD5:
                    report.facts.append("checksum       : matches the pinned MD5")
                else:
                    report.warnings.append(
                        f"Zenodo lists MD5 {published_md5} but this project pins "
                        f"{EXPECTED_MD5}. Do not fetch until you know why."
                    )

            # Has MIBiG published something newer than our pinned release?
            state, detail = self._newer_version(record)
            if state == "newer":
                report.warnings.append(
                    f"A newer MIBiG release exists on Zenodo: {detail}\n"
                    f"    This project stays on {MIBIG_VERSION} until an upgrade is made on "
                    f"purpose (docs/03-ingestion-mibig.md, section 16, 'Upgrading MIBiG later')."
                )
            elif state == "newest":
                report.facts.append("newer release  : none, this is the newest version")
            else:
                report.facts.append(f"newer release  : could not tell ({detail})")

        # What is already on our shelf?
        local = self.locker / FILENAME
        if local.exists():
            n_bytes, md5, _ = file_digests(local)
            state = "verified" if md5 == EXPECTED_MD5 else "DOES NOT MATCH the pinned MD5"
            report.facts.append(f"in your locker : yes, {n_bytes / 1_048_576:.1f} MB, {state}")
        else:
            report.facts.append("in your locker : not yet (run the fetch)")
        return report

    def _newer_version(self, record: dict[str, Any]) -> tuple[str, str]:
        """
        Work out whether Zenodo holds a newer release than the pinned one.

        Returns ("newest", ""), ("newer", "<link and version>") or
        ("unknown", "<reason>"). Two ways of asking, because Zenodo has
        described versions in two ways over the years:
          1. the record's own note on its version family ("is this the last?"),
          2. following the record's "latest" link and reading where it lands.
        """
        family = (record.get("metadata", {}).get("relations") or {}).get("version") or []
        if family and isinstance(family[0], dict):
            if family[0].get("is_last") is True:
                return "newest", ""
            last_id = str((family[0].get("last") or {}).get("pid_value") or "")
            if last_id and last_id != ZENODO_RECORD:
                return "newer", f"https://zenodo.org/records/{last_id}"

        latest_api = record.get("links", {}).get("latest")
        if not latest_api:
            return "unknown", "the record does not link to a latest version"
        try:
            latest = self.http_get(str(latest_api)).json()
        except (requests.RequestException, SourceError, ValueError) as error:
            return "unknown", str(error)
        latest_id = str(latest.get("id") or latest.get("recid") or "")
        if not latest_id:
            return "unknown", "the latest-version answer had no record number"
        if latest_id == ZENODO_RECORD:
            return "newest", ""
        version = (latest.get("metadata") or {}).get("version", "?")
        return "newer", f"version {version}, https://zenodo.org/records/{latest_id}"

    # ======================================================================
    # fetch(): bring it home, untouched
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        """Download the pinned archive into data/raw/mibig/ and log one provenance row."""
        path, outcome, n_bytes, md5, sha256 = self.download_to_locker(
            DOWNLOAD_URL, FILENAME, EXPECTED_MD5
        )
        # The file is in the locker now, so it gets its row in the log whatever
        # happens next. If the archive can't be opened, the row is still written
        # (with the record count left blank) and only THEN does the fetch stop.
        # A file sitting in the locker with no row in the log is exactly the
        # gap the log exists to close.
        unreadable: Exception | None = None
        try:
            n_records: int | str = count_tar_json(path)
        except (tarfile.TarError, EOFError, OSError) as error:
            n_records, unreadable = "", error
        provenance.append(
            {
                "retrieved_at": provenance.utc_now(),
                "source": self.name,
                "source_version": MIBIG_VERSION,
                "url": DOWNLOAD_URL,
                "local_path": relative_to_repo(path),
                "n_bytes": n_bytes,
                "md5": md5,
                "sha256": sha256,
                "n_records": n_records,
                "licence": self.licence,
                "outcome": outcome,
            },
            log_path=self.provenance_log,
        )
        if unreadable is not None:
            raise SourceError(
                f"{FILENAME} arrived intact (its MD5 matches the published one) and is "
                f"logged, but it can't be read as an archive: {unreadable}"
            ) from unreadable
        self.say(f"  [{self.name}] {outcome}: {relative_to_repo(path)} "
                 f"({n_bytes / 1_048_576:.1f} MB, {n_records} records), provenance logged")
        return [FetchResult(self.name, path, outcome, n_bytes, n_records)]

    # ======================================================================
    # tidy(): make it fit the rulebook
    # ======================================================================
    def tidy(self) -> TidyResult:
        """Read the archive from the locker and write staging tables. Offline."""
        archive = self.locker / FILENAME
        if not archive.exists():
            raise SourceError(
                f"{relative_to_repo(archive)} is not in the evidence locker yet.\n"
                f"  Run:  python -m microbegraph.fetch --source mibig"
            )

        retrieved_at = self._retrieved_date(archive)
        builder = _GraphBuilder(retrieved_at)

        # Read every entry in the order the archive stores them (fast), keep only
        # the fields we use (small), then sort by file name (same order on every
        # machine, so the output is identical everywhere).
        entries: list[tuple[str, Any]] = []
        for member_name, payload in iter_tar_json(archive):
            builder.counts["files_read"] += 1
            try:
                raw = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                builder.counts["files_unreadable"] += 1
                self.say(f"  [{self.name}] skipped {member_name}: not readable JSON")
                continue
            entries.append((member_name, _slim(raw)))
        for _, raw in sorted(entries, key=lambda item: item[0]):
            builder.add_entry(raw)

        nodes = builder.node_rows()
        edges = builder.edge_rows()

        # Check our own output against the twelve rules BEFORE writing it.
        problems = check_tables(nodes, edges)
        if problems:
            shown = "\n    ".join(problems[:10])
            raise SourceError(
                f"The MIBiG tidy produced rows that break the rulebook "
                f"({len(problems)} problems). Nothing was written. First ones:\n    {shown}"
            )

        nodes_path = self.staging_dir / f"{self.name}_nodes.csv"
        edges_path = self.staging_dir / f"{self.name}_edges.csv"
        summary_path = self.staging_dir / f"{self.name}_summary.json"
        counts = dict(sorted(builder.counts.items()))
        summary = {
            "source": self.name,
            "source_version": MIBIG_VERSION,
            "archive": relative_to_repo(archive),
            "retrieved_at": retrieved_at,
            "counts": counts,
        }
        # All three files change together, or none of them does.
        write_files_together({
            nodes_path: table_text(NODE_COLUMNS, nodes),
            edges_path: table_text(EDGE_COLUMNS, edges),
            summary_path: json.dumps(summary, indent=2) + "\n",
        })
        return TidyResult(self.name, nodes_path, edges_path, counts)

    def _retrieved_date(self, archive: Path) -> str:
        """
        The date the archive was DOWNLOADED, from the provenance log.

        Falls back to the file's own timestamp (and says so) if the log has no
        row, for example when someone copied the archive in by hand.
        """
        row = provenance.latest(self.name, relative_to_repo(archive), self.provenance_log)
        if row:
            return row["retrieved_at"][:10]
        stamp = datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
        self.say(f"  [{self.name}] no provenance row for this archive; "
                 f"using the file's date ({stamp:%Y-%m-%d}) as retrieved_at")
        return f"{stamp:%Y-%m-%d}"


# ==========================================================================
# The translation from one MIBiG entry to our nodes and edges
# ==========================================================================
class _GraphBuilder:
    """
    Collects nodes and edges from many entries, merging repeats.

    WHY MERGING IS NEEDED
        A compound can be made by clusters in several organisms. Each entry
        mentions it, but the graph must have ONE dot for that compound with
        several arrows into it, rather than one dot per entry. The same goes
        for activities: "antibacterial" is one dot, however many compounds
        have it.

    HOW REPEATED ARROWS ARE MERGED
        The same arrow from two entries (surfactin HAS_ACTIVITY antibacterial)
        becomes one row that remembers both entries in source_record_id,
        keeps the STRONGER evidence level and the HIGHER confidence, and
        keeps every citation.
    """

    def __init__(self, retrieved_at: str) -> None:
        self.retrieved_at = retrieved_at
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.counts: dict[str, int] = {
            "files_read": 0, "files_unreadable": 0, "files_not_mibig4": 0,
            "entries_active": 0, "entries_skipped_status": 0,
            "entries_with_experimental_evidence": 0, "entries_predicted_or_unstated": 0,
            "compounds_read": 0, "bioactivities_observed": 0,
            "bioactivities_not_observed": 0, "compound_name_collisions": 0,
            "property_conflicts": 0,
        }
        # slug -> the exact (case-folded) name that first claimed it
        self._slug_owner: dict[str, str] = {}

    # ---------------------------------------------------------------- entries
    def add_entry(self, raw: Any) -> None:
        # A MIBiG 4 entry is an object with these keys. A 3.x entry would have
        # a "cluster" key instead; anything else is not an entry at all.
        if not isinstance(raw, dict) or not {"accession", "taxonomy", "compounds"} <= raw.keys():
            self.counts["files_not_mibig4"] += 1
            return
        if raw.get("status") != "active":
            self.counts["entries_skipped_status"] += 1
            return
        self.counts["entries_active"] += 1

        accession = str(raw["accession"])
        quality = str(raw.get("quality", "questionable"))
        confidence = QUALITY_CONFIDENCE.get(quality, QUALITY_CONFIDENCE["questionable"])
        entry_refs = _entry_references(raw)

        # What kind of evidence links this organism, cluster and compound?
        methods = {str(ev.get("method")) for locus in raw.get("loci") or []
                   for ev in locus.get("evidence") or [] if ev.get("method")}
        if methods - PREDICTION_METHODS:
            cluster_level = "curated_experimental"
            self.counts["entries_with_experimental_evidence"] += 1
        else:
            cluster_level = "database_assertion"
            self.counts["entries_predicted_or_unstated"] += 1

        # --- the organism ---------------------------------------------------
        taxonomy = raw.get("taxonomy") or {}
        organism_name = str(taxonomy.get("name") or "unnamed organism")
        taxid = taxonomy.get("ncbiTaxId")
        if isinstance(taxid, int) or (isinstance(taxid, str) and taxid.isdigit()):
            organism_id = f"ncbitaxon:{int(taxid)}"
        else:
            # No NCBI number: mint our own identifier, visibly marked as ours.
            organism_id = f"mg.organism:{slugify(organism_name)}"
        self._add_node(organism_id, "Organism", organism_name, {})

        # --- the gene cluster -------------------------------------------------
        compounds = [c for c in raw.get("compounds") or [] if c.get("name")]
        compound_names = [str(c["name"]) for c in compounds]
        bgc_classes = [str(c.get("class")) for c in (raw.get("biosynthesis") or {}).get("classes", [])
                       if c.get("class")]
        cluster_id = f"mibig:{accession}"
        self._add_node(cluster_id, "GeneCluster", _cluster_name(accession, compound_names), {
            "bgc_class": "|".join(bgc_classes),
            "quality": quality,
            "completeness": raw.get("completeness"),
            "entry_version": raw.get("version"),
            "loci": "|".join(str(locus.get("accession")) for locus in raw.get("loci") or []
                             if locus.get("accession")),
        })
        self._add_edge(organism_id, cluster_id, "HARBORS", cluster_level,
                       accession, confidence, entry_refs)

        # --- each compound ------------------------------------------------------
        for compound in compounds:
            self.counts["compounds_read"] += 1
            compound_id = self._compound_id(str(compound["name"]))
            database_ids = sorted({str(d) for d in compound.get("databaseIds") or []})
            self._add_node(compound_id, "Compound", str(compound["name"]), {
                "formula": compound.get("formula"),
                "mass": compound.get("mass"),
                "synonyms": "|".join(sorted({str(s) for s in compound.get("synonyms") or []})),
                "database_ids": "|".join(database_ids),
                "pubchem_cid": next((d.split(":", 1)[1] for d in database_ids
                                     if d.startswith("pubchem:")), None),
                "smiles": compound.get("structure"),
            })
            compound_refs = sorted({str(ref) for ev in compound.get("evidence") or []
                                    for ref in ev.get("references") or []} | set(entry_refs))
            self._add_edge(cluster_id, compound_id, "PRODUCES", cluster_level,
                           accession, confidence, compound_refs)

            notes: set[str] = set()
            for activity in compound.get("bioactivities") or []:
                activity_name, note = _activity_name_and_note(activity.get("name"))
                if not activity_name:
                    continue
                if activity.get("observed") is False:
                    self.counts["bioactivities_not_observed"] += 1
                    continue
                self.counts["bioactivities_observed"] += 1
                refs = sorted({str(r) for r in activity.get("references") or []})
                level = "curated_experimental" if refs else "database_assertion"
                activity_id = f"mg.activity:{slugify(activity_name)}"
                self._add_node(activity_id, "Activity", activity_name, {})
                self._add_edge(compound_id, activity_id, "HAS_ACTIVITY", level,
                               accession, confidence, refs)
                if note:
                    notes.add(f"{activity_name}: {note}")
            if notes:
                # A curator's comment qualifies what THIS compound does (for
                # example how it is antialgal), so it belongs on the compound,
                # not on the Activity node that every antialgal compound shares.
                self._add_node(compound_id, "Compound", str(compound["name"]),
                               {"activity_notes": "|".join(sorted(notes))})

            for chem_class in compound.get("classes") or []:
                class_name = str(chem_class).strip()
                if not class_name:
                    continue
                class_id = f"mg.class:{slugify(class_name)}"
                self._add_node(class_id, "CompoundClass", class_name, {})
                self._add_edge(compound_id, class_id, "BELONGS_TO", "database_assertion",
                               accession, confidence, [])

    # ---------------------------------------------------------------- helpers
    def _compound_id(self, name: str) -> str:
        """
        The identifier for a compound name, stable and collision-safe.

        Names that differ only in capitals ("Surfactin", "surfactin") are the
        same compound. Names that really are different but squash to the
        same slug ("(+)-x" and "(-)-x" are protected by slugify, but stranger
        cases exist) get a short fingerprint added, so two different molecules
        can never silently become one node.
        """
        slug = slugify(name) or "unnamed"
        key = name.casefold().strip()
        owner = self._slug_owner.setdefault(slug, key)
        if owner == key:
            return f"mg.compound:{slug}"
        self.counts["compound_name_collisions"] += 1
        fingerprint = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6]
        return f"mg.compound:{slug}-{fingerprint}"

    def _add_node(self, node_id: str, node_type: str, name: str, props: dict[str, Any]) -> None:
        clean = {k: v for k, v in props.items() if v not in (None, "", [])}
        existing = self.nodes.get(node_id)
        if existing is None:
            self.nodes[node_id] = {"node_type": node_type, "name": name, "properties": clean}
            return
        merged = existing["properties"]
        for key, value in clean.items():
            if key in ("synonyms", "database_ids", "loci", "bgc_class", "activity_notes"):
                parts = set(str(merged.get(key, "")).split("|")) | set(str(value).split("|"))
                merged[key] = "|".join(sorted(p for p in parts if p))
            elif key not in merged:
                merged[key] = value
            elif merged[key] != value:
                # Two entries disagree (e.g. two masses for one compound). Keep
                # the first, count the disagreement, and let Phase 4 resolve it.
                self.counts["property_conflicts"] += 1
        if name != existing["name"]:
            others = set(str(merged.get("other_names", "")).split("|")) | {name}
            merged["other_names"] = "|".join(sorted(o for o in others if o))

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, level: str,
                  accession: str, confidence: float, refs: list[str]) -> None:
        key = (source_id, target_id, edge_type)
        existing = self.edges.get(key)
        if existing is None:
            self.edges[key] = {"evidence_level": level, "records": {accession},
                               "confidence": confidence, "citations": set(refs)}
            return
        existing["records"].add(accession)
        existing["citations"].update(refs)
        existing["confidence"] = max(existing["confidence"], confidence)
        if evidence_rank(level) < evidence_rank(existing["evidence_level"]):
            existing["evidence_level"] = level      # lower rank = stronger evidence

    # ---------------------------------------------------------------- output
    def node_rows(self) -> list[dict[str, Any]]:
        rows = [
            {
                "node_id": node_id,
                "node_type": node["node_type"],
                "name": node["name"],
                "properties": json.dumps(node["properties"], sort_keys=True, ensure_ascii=False),
                "source": "mibig",
                "retrieved_at": self.retrieved_at,
            }
            for node_id, node in self.nodes.items()
        ]
        return sorted(rows, key=lambda r: (r["node_type"], r["node_id"]))

    def edge_rows(self) -> list[dict[str, Any]]:
        rows = [
            {
                "source_id": source_id,
                "target_id": target_id,
                "edge_type": edge_type,
                "evidence_level": edge["evidence_level"],
                "source": "mibig",
                "source_record_id": "|".join(sorted(edge["records"])),
                "citation": "|".join(sorted(edge["citations"])),
                "confidence": f"{edge['confidence']:.2f}",
                "retrieved_at": self.retrieved_at,
            }
            for (source_id, target_id, edge_type), edge in self.edges.items()
        ]
        return sorted(rows, key=lambda r: (r["edge_type"], r["source_id"], r["target_id"]))


def _cluster_name(accession: str, compound_names: list[str]) -> str:
    """A readable label: 'surfactin BGC', or the accession if no compound is named."""
    if not compound_names:
        return accession
    shown = ", ".join(compound_names[:3])
    more = f" +{len(compound_names) - 3} more" if len(compound_names) > 3 else ""
    return f"{shown}{more} BGC"


def _slim(raw: Any) -> Any:
    """
    Keep only the parts of an entry that tidy() reads, so three thousand
    entries fit comfortably in memory while they are sorted. Anything that is
    not an entry is passed through untouched, to be counted by add_entry().
    """
    if not isinstance(raw, dict) or "accession" not in raw:
        return raw
    keep = ("accession", "status", "quality", "completeness", "version", "taxonomy",
            "compounds", "legacy_references")
    slim = {key: raw[key] for key in keep if key in raw}
    slim["loci"] = [{"accession": locus.get("accession"),
                     "evidence": locus.get("evidence") or []}
                    for locus in raw.get("loci") or [] if isinstance(locus, dict)]
    classes = (raw.get("biosynthesis") or {}).get("classes") or []
    slim["biosynthesis"] = {"classes": [{"class": c.get("class")} for c in classes
                                        if isinstance(c, dict)]}
    return slim


def _entry_references(raw: dict[str, Any]) -> list[str]:
    """
    The references an entry gives for the cluster itself: the evidence behind
    each locus, plus older references carried over from previous releases.
    Written as 'pubmed:14762003' or 'doi:10....', exactly as MIBiG writes them.
    """
    refs = {str(ref) for locus in raw.get("loci") or []
            for ev in locus.get("evidence") or [] for ref in ev.get("references") or []}
    refs.update(str(ref) for ref in raw.get("legacy_references") or [])
    return sorted(refs)


def _activity_name_and_note(raw_name: Any) -> tuple[str, str]:
    """
    Read an activity's name, whichever of MIBiG 4.0's two styles it is in.

    The same release writes it both ways:
        {"activity": "antibacterial"}                  an object
        {"activity": "antialgal", "comment": "..."}    an object with a curator's note
        "antibacterial (gram-negative)"                plain text

    Returns (activity, note): the activity in lower case, and the curator's
    comment as written, or "" when there isn't one.

    Why this matters: the first version of tidy() expected plain text only.
    Given the object style it turned the whole object into text, so the
    graph got nodes like mg.activity:activity-antibacterial, next to a
    separate mg.activity:antibacterial for entries written the other way.
    The tests passed because my copy of the surfactin record used plain text;
    the real record, opened from the archive, uses the object style.
    """
    if isinstance(raw_name, dict):
        activity = str(raw_name.get("activity") or "")
        note = str(raw_name.get("comment") or "")
    else:
        activity, note = str(raw_name or ""), ""
    return activity.strip().lower(), note.strip()
