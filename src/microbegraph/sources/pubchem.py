"""
MicrobeGraph, the PubChem adapter (Phase 2).

WHAT PUBCHEM IS
    PubChem is the world's largest free chemistry database, run by the US
    National Library of Medicine. Every distinct chemical structure gets a
    number, its CID (compound identifier), and a page of facts: its formula,
    its weight, its structure written as text, and the many names it goes by.

    If MIBiG is a register of factories and what they make, PubChem is the
    product catalogue that gives each product a stock number and a full
    specification sheet.

WHY IT COMES SECOND
    MIBiG records a PubChem CID for about a third of its compounds (1,176 of
    3,842 in MIBiG 4.0). Asking PubChem about those numbers gives each
    compound a precise identity (two names for one molecule share one CID)
    and, through its list of names, the compound's number in KEGG and ChEBI.
    The KEGG number is what lets the KEGG adapter place a compound on a map
    of metabolism.

HOW IT ASKS (PUG REST)
    PubChem's API is called PUG REST. You can ask about many compounds in one
    request by POSTing a list of CIDs. This adapter sends 100 at a time, twice
    per batch: once for the properties, once for the names (synonyms):

        POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/property/<list>/JSON
        POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/synonyms/JSON
             body: cid=811,5281917,...

    PubChem's limits: at most 5 requests a second and 400 a minute. Every
    answer carries a traffic light in a header called X-Throttling-Control
    (Green, Yellow, Red, Black). The adapter slows down when it turns Yellow
    or worse, the way you ease off the accelerator when the lights change.

WHAT tidy() TURNS THE ANSWERS INTO
    nodes  Compound    pubchem.compound:<CID>
    edges  none. The arrows to these compounds come from KEGG (pathways) and,
           in Phase 4, from linking MIBiG's compounds to their CIDs. To make
           that link easy, each node remembers which MIBiG compound(s) gave
           its CID (mibig_compound_ids).

    A CID that PubChem doesn't know comes back holding nothing but its own
    number. That's counted (cids_not_in_pubchem) and listed in the summary,
    never turned into an empty node.

LICENCE AND CITATION
    NCBI places no restrictions on using PubChem data, but some depositors
    attach their own terms to what they contributed, so the provenance log
    says exactly that.

    Cite: Kim S et al. (2025) PubChem 2025 update. Nucleic Acids Research
    53(D1):D1516-D1525. doi:10.1093/nar/gkae1059
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import relative_to_repo
from microbegraph.sources.api import ApiSource, batches_text, chunks
from microbegraph.sources.base import FetchResult, ProbeReport, SourceError, TidyResult
from microbegraph.staging import node_row, properties_of, read_table, write_tables

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# The properties we read. SMILES and ConnectivitySMILES are the names PubChem
# has used since 2025 (they replaced IsomericSMILES and CanonicalSMILES).
PROPERTIES = ("Title,MolecularFormula,MolecularWeight,MonoisotopicMass,"
              "IUPACName,InChIKey,SMILES,ConnectivitySMILES")
PROPERTIES_URL = f"{PUG}/compound/cid/property/{PROPERTIES}/JSON"
SYNONYMS_URL = f"{PUG}/compound/cid/synonyms/JSON"
PROBE_URL = f"{PUG}/compound/cid/2519/property/Title/JSON"     # caffeine, a safe question

BATCH_SIZE = 100            # CIDs per request
SYNONYMS_KEPT = 20          # names kept per compound; PubChem lists the most used first

# Outside identifiers PubChem lists among a compound's names.
KEGG_COMPOUND = re.compile(r"^C\d{5}$")      # KEGG COMPOUND, e.g. C00490
KEGG_DRUG = re.compile(r"^D\d{5}$")          # KEGG DRUG, e.g. D00528
CHEBI = re.compile(r"^CHEBI:\d+$")           # ChEBI, e.g. CHEBI:30838

# How much longer to wait for each traffic-light colour (times the normal pause).
THROTTLE_FACTOR = {"Green": 1.0, "Yellow": 4.0, "Red": 20.0, "Black": 120.0}
_COLOUR = re.compile(r"\b(Green|Yellow|Red|Black)\b")


def worst_light(header: str) -> str:
    """The worst colour in an X-Throttling-Control header ("Green" if none is named)."""
    colours = _COLOUR.findall(header or "")
    return max(colours, key=lambda c: THROTTLE_FACTOR[c]) if colours else "Green"


class PubchemSource(ApiSource):
    """PubChem: properties and names for every CID MIBiG recorded."""

    name = "pubchem"
    licence = "NCBI: no restrictions; some depositors add their own terms"
    homepage = "https://pubchem.ncbi.nlm.nih.gov"
    pause_seconds = 0.25        # 4 requests a second at most, under the limit of 5

    # ======================================================================
    # probe()
    # ======================================================================
    def probe(self) -> ProbeReport:
        report = ProbeReport(source=self.name, reachable=False)
        try:
            response = self.http_get(PROBE_URL)
            title = response.json()["PropertyTable"]["Properties"][0].get("Title", "?")
            report.reachable = True
            light = worst_light(response.headers.get("X-Throttling-Control", ""))
            report.facts.append(f"service        : answering (test question: CID 2519 is {title})")
            report.facts.append(f"traffic light  : {light}")
            report.facts.append("version        : live database, no release numbers")
        except (requests.RequestException, SourceError, ValueError, KeyError, IndexError) as error:
            report.warnings.append(f"Could not reach PubChem ({error}). Check your connection.")

        try:
            cids = self._cids_from_mibig()
            n_batches = len(chunks(list(cids), BATCH_SIZE))
            report.facts.append(f"to ask about   : {len(cids):,} CIDs from MIBiG, "
                                f"{2 * n_batches} requests")
        except SourceError:
            report.facts.append("to ask about   : unknown until MIBiG is tidied (Phase 1)")
        facts, warnings = self.locker_facts()
        report.facts += facts
        report.warnings += warnings
        return report

    def _cids_from_mibig(self) -> dict[str, list[str]]:
        """CID -> the MIBiG compound ids that recorded it, in number order."""
        found: dict[str, set[str]] = {}
        for row in read_table("mibig", "nodes", self.staging_dir, needed_by=self.name):
            if row["node_type"] != "Compound":
                continue
            cid = properties_of(row).get("pubchem_cid")
            if cid not in (None, ""):
                found.setdefault(str(cid).strip(), set()).add(row["node_id"])
        return {cid: sorted(ids) for cid, ids in sorted(found.items(), key=lambda kv: int(kv[0]))}

    # ======================================================================
    # fetch()
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        cids_to_compounds = self._cids_from_mibig()
        cids = list(cids_to_compounds)
        asked_for = {"cids": cids, "properties": PROPERTIES}
        reused = self.reuse_today(asked_for)
        if reused:
            return reused

        snapshot = self.start_snapshot(asked_for, {"mibig_compounds_by_cid": cids_to_compounds})
        batches = chunks(cids, BATCH_SIZE)
        self.say(f"  [{self.name}] asking about {len(cids):,} CIDs in "
                 f"{batches_text(len(batches))} of up to {BATCH_SIZE}")
        for number, batch in enumerate(batches, start=1):
            for kind, url in (("properties", PROPERTIES_URL), ("synonyms", SYNONYMS_URL)):
                response = self.http_post(url, {"cid": ",".join(batch)})
                body = response.content
                light = worst_light(response.headers.get("X-Throttling-Control", ""))
                n_found = _count_found(kind, body)
                path = snapshot.save(
                    f"{kind}_{number:03d}.json", body, url=url, method="POST",
                    sent={"cid": batch}, n_records=n_found, source_version="live")
                if n_found == "":
                    # Saved and logged first (it's evidence of what happened), then stop:
                    # carrying on would make every compound in this batch look unknown.
                    raise SourceError(
                        f"{relative_to_repo(path)} arrived and is logged, but it isn't the "
                        f"answer expected ({_fault_message(body)}). Run the fetch again in a "
                        f"few minutes; the unfinished folder is ignored by tidy."
                    )
                if light != "Green":
                    self.say(f"  [{self.name}] PubChem's traffic light is {light}; slowing down")
                self.say(f"  [{self.name}] {relative_to_repo(path)}")
                self.pause(THROTTLE_FACTOR[light])
        return snapshot.finish("live")

    # ======================================================================
    # tidy()
    # ======================================================================
    def tidy(self) -> TidyResult:
        folder, manifest = self.latest_snapshot()
        retrieved_at = manifest["started_at"][:10]
        by_cid = manifest.get("context", {}).get("mibig_compounds_by_cid", {})

        properties: dict[str, dict[str, Any]] = {}
        synonyms: dict[str, list[str]] = {}
        for answer in manifest["answers"]:
            data = _load_json(folder / answer["file"])
            if answer["file"].startswith("properties_"):
                for entry in data.get("PropertyTable", {}).get("Properties", []):
                    properties[str(entry.get("CID"))] = entry
            elif answer["file"].startswith("synonyms_"):
                for entry in data.get("InformationList", {}).get("Information", []):
                    synonyms[str(entry.get("CID"))] = list(entry.get("Synonym") or [])

        counts = {"cids_requested": len(manifest["asked_for"]["cids"]), "compounds_found": 0,
                  "cids_not_in_pubchem": 0, "compounds_with_synonyms": 0,
                  "compounds_with_kegg_id": 0, "compounds_with_chebi_id": 0}
        not_found: list[str] = []
        nodes = []
        for cid in manifest["asked_for"]["cids"]:
            entry = properties.get(cid, {})
            if len(entry) <= 1:                  # only {"CID": n}: PubChem has no such compound
                counts["cids_not_in_pubchem"] += 1
                not_found.append(cid)
                continue
            names = synonyms.get(cid, [])
            kegg = sorted({n for n in names if KEGG_COMPOUND.match(n)})
            chebi = sorted({n for n in names if CHEBI.match(n)})
            counts["compounds_found"] += 1
            counts["compounds_with_synonyms"] += bool(names)
            counts["compounds_with_kegg_id"] += bool(kegg)
            counts["compounds_with_chebi_id"] += bool(chebi)
            props = {
                "pubchem_cid": int(cid),
                "formula": entry.get("MolecularFormula", ""),
                "molecular_weight": _number(entry.get("MolecularWeight")),
                "monoisotopic_mass": _number(entry.get("MonoisotopicMass")),
                "iupac_name": entry.get("IUPACName", ""),
                "inchikey": entry.get("InChIKey", ""),
                "smiles": entry.get("SMILES", ""),
                "connectivity_smiles": entry.get("ConnectivitySMILES", ""),
                "synonyms": "|".join(names[:SYNONYMS_KEPT]),
                "kegg_compound_ids": "|".join(kegg),
                "kegg_drug_ids": "|".join(sorted({n for n in names if KEGG_DRUG.match(n)})),
                "chebi_ids": "|".join(chebi),
                "mibig_compound_ids": "|".join(by_cid.get(cid, [])),
            }
            name = entry.get("Title") or entry.get("IUPACName") or f"PubChem CID {cid}"
            nodes.append(node_row(f"pubchem.compound:{cid}", "Compound", name, props,
                                  self.name, retrieved_at))

        summary = {
            "source": self.name,
            "source_version": manifest.get("source_version", "live"),
            "snapshot": relative_to_repo(folder),
            "retrieved_at": retrieved_at,
            "counts": counts,
            "cids_not_in_pubchem": not_found,
        }
        return write_tables(self.name, nodes, [], summary, self.staging_dir)


def _count_found(kind: str, body: bytes) -> int | str:
    """
    How many compounds an answer really describes (entries with more than a CID),
    or "" if the answer isn't the kind expected at all.
    """
    try:
        data = json.loads(body)
    except ValueError:
        return ""
    table = "PropertyTable" if kind == "properties" else "InformationList"
    rows = "Properties" if kind == "properties" else "Information"
    if not isinstance(data, dict) or table not in data:
        return ""
    return sum(1 for e in data[table].get(rows, []) if len(e) > 1)


def _fault_message(body: bytes) -> str:
    """PubChem's own explanation, when it sends one instead of an answer."""
    try:
        fault = json.loads(body).get("Fault", {})
        return f"PubChem says: {fault.get('Message', '?')} {' '.join(fault.get('Details', []))}".strip()
    except (ValueError, AttributeError):
        return "it isn't JSON"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SourceError(
            f"{relative_to_repo(path)} can't be read as JSON ({error}).\n"
            f"  Run the fetch again; the new snapshot will replace this one for tidy."
        ) from error


def _number(text: Any) -> float | str:
    """PubChem sends weights as text ("130.10"); store a number when it is one."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return ""
