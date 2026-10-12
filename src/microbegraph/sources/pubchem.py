"""
MicrobeGraph, the PubChem adapter (Phase 2; the name search from Phase 4b).

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

HOW IT ASKS (PUG REST), IN THREE ROUNDS
    PubChem's API is called PUG REST.

    Round 1, the numbers MIBiG gives (Phase 2). You can ask about many
    compounds in one request by POSTing a list of CIDs. This adapter sends
    100 at a time, twice per batch: once for the properties, once for the
    names (synonyms):

        POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/property/<list>/JSON
        POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/synonyms/JSON
             body: cid=811,5281917,...

    From Phase 4b the list also holds the second numbers MIBiG's entries
    give (pubchem_cid_by_entry, see mibig.py) and every PubChem number named
    in the review file, curation/resolution_decisions.csv.

    Round 2, the name search (Phase 4b). For a MIBiG compound whose numbers
    don't list its name, or that has no number at all, the adapter asks
    PubChem which compound carries that name, one name per request:

        POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/cids/JSON
             body: name=2-methylisoborneol

    PubChem answers with the numbers it files the name under, or with 404
    "No CID found". Only names that could change a decision are asked: a
    compound whose own number already lists its name is skipped, and so is
    a compound with no number and no formula, because a name match is only
    accepted when the formula agrees too (src/microbegraph/resolution/compounds.py).

    Round 3, the numbers the name search found (Phase 4b): their formula,
    structure key and names, asked the same way as round 1.

PUBCHEM'S LIMITS, AND WHAT HAPPENED WHEN THEY WERE TESTED
    PubChem asks for at most 5 requests a second and 400 a minute. Every
    answer carries a traffic light in a header called X-Throttling-Control
    (Green, Yellow, Red, Black). The adapter slows down when it turns Yellow
    or worse, the way you ease off the accelerator when the lights change.

    A name search costs PubChem's servers more than a number lookup. While
    this phase was being built, a survey asking four names a second was
    refused with "429 Too Many Requests" after about 400 names, and the
    refusals went on for hours. So round 2 asks one name a second,
    and waits 15, 30, 60 and 60 seconds before giving up on a request
    PubChem refuses as busy.

    If PubChem still refuses, the fetch stops cleanly: everything that
    arrived is kept, the snapshot is finished and marked incomplete, and the
    message says how many names are left. Run the same command later; it
    carries the earlier answers over and asks only the names still missing.
    Round 3 then waits for that next run (asking a server that is refusing
    only prolongs the block). If round 3 itself fails, every name-search
    answer is kept and carried over in the same way, and the next run repeats
    round 3. Until then, tidy leaves out the search answers of every compound
    whose search found a number round 3 had to describe.

WHAT tidy() TURNS THE ANSWERS INTO
    nodes  Compound    pubchem.compound:<CID>
    edges  none. The arrows to these compounds come from KEGG (pathways) and
           from the resolver, which joins MIBiG's compounds to them.

    Each node remembers the MIBiG compounds that point at it:
        mibig_compound_ids    the MIBiG compounds that give this number
        found_by_name         the MIBiG compounds whose name search returned it (Phase 4b)
        names_matching_mibig  the names in PubChem's FULL list that match one of
                              those compounds' names (Phase 4b; synonyms keeps
                              only the first 20 of what can be hundreds)
        synonym_count         how many names PubChem lists in all (Phase 4b)

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

import csv
import json
import re
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import CURATION_DIR, relative_to_repo
from microbegraph.resolution.names import name_key, split_list
from microbegraph.sources.api import ApiSource, Snapshot, batches_text, chunks
from microbegraph.sources.base import (
    FetchResult,
    ProbeReport,
    SourceError,
    TidyResult,
    TransientHTTPError,
)
from microbegraph.staging import node_row, properties_of, read_table, write_tables

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# The properties we read. SMILES and ConnectivitySMILES are the names PubChem
# has used since 2025 (they replaced IsomericSMILES and CanonicalSMILES).
PROPERTIES = ("Title,MolecularFormula,MolecularWeight,MonoisotopicMass,"
              "IUPACName,InChIKey,SMILES,ConnectivitySMILES")
PROPERTIES_URL = f"{PUG}/compound/cid/property/{PROPERTIES}/JSON"
SYNONYMS_URL = f"{PUG}/compound/cid/synonyms/JSON"
NAME_SEARCH_URL = f"{PUG}/compound/name/cids/JSON"                # Phase 4b
PROBE_URL = f"{PUG}/compound/cid/2519/property/Title/JSON"     # caffeine, a safe question

BATCH_SIZE = 100            # CIDs per request
SYNONYMS_KEPT = 20          # names kept per compound; PubChem lists the most used first
NAMES_PER_FILE = 50         # name-search answers saved together in one file
MAX_NUMBERS_PER_NAME = 10   # a name filed under more numbers is too vague to choose from
NAME_PAUSE_FACTOR = 4.0     # a name search waits 4 x pause_seconds: one a second

# What round 2 asks, written into every manifest so that two fetches asking
# the same questions can be recognised (see reuse_today in api.py).
NAME_SEARCH_RULE = ("each MIBiG compound whose numbers don't list its name, and each with "
                    "no number but a formula")

REVIEW_FILE = CURATION_DIR / "resolution_decisions.csv"

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
    """PubChem: properties and names for every CID MIBiG recorded, and a name search."""

    name = "pubchem"
    licence = "NCBI: no restrictions; some depositors add their own terms"
    homepage = "https://pubchem.ncbi.nlm.nih.gov"
    pause_seconds = 0.25        # 4 requests a second at most, under the limit of 5

    def __init__(self, *args: Any, retry_wait_seconds: float = 15.0, **kwargs: Any) -> None:
        # PubChem's "busy" refusals last minutes, not seconds (see the notes above),
        # so its retries start at 15 s instead of the usual 2 s.
        super().__init__(*args, retry_wait_seconds=retry_wait_seconds, **kwargs)

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
            compounds = self._mibig_compounds()
            cids = sorted({c for item in compounds for c in item["cids"]} | self._review_cids(),
                          key=int)
            n_batches = len(chunks(cids, BATCH_SIZE))
            report.facts.append(f"to ask about   : {len(cids):,} CIDs from MIBiG and the review "
                                f"file, {2 * n_batches} requests")
            most = sum(1 for item in compounds if item["cids"] or item["formula"])
            report.facts.append(f"name search    : up to {most:,} names, one a second, decided "
                                f"after the numbers are in")
        except SourceError:
            report.facts.append("to ask about   : unknown until MIBiG is tidied (Phase 1)")
        facts, warnings = self.locker_facts()
        report.facts += facts
        report.warnings += warnings
        return report

    # ======================================================================
    # what to ask
    # ======================================================================
    def _mibig_compounds(self) -> list[dict[str, Any]]:
        """
        Every MIBiG compound with what the fetch needs: its names, its formula
        and every PubChem number its entries give (Phase 4b: the second numbers
        in pubchem_cid_by_entry too).
        """
        compounds = []
        for row in read_table("mibig", "nodes", self.staging_dir, needed_by=self.name):
            if row["node_type"] != "Compound":
                continue
            props = properties_of(row)
            cids = {str(props["pubchem_cid"]).strip()} if props.get("pubchem_cid") else set()
            for item in split_list(props.get("pubchem_cid_by_entry")):
                cids.add(item.partition(": ")[2].strip())
            names = [row["name"]] + split_list(props.get("synonyms")) + split_list(
                props.get("other_names"))
            compounds.append({"id": row["node_id"], "name": row["name"], "names": names,
                              "formula": props.get("formula") or "",
                              "cids": sorted((c for c in cids if c.isdigit()), key=int)})
        return compounds

    def _review_cids(self) -> set[str]:
        """Every PubChem number named in the review file, so a person's join can be applied."""
        if not REVIEW_FILE.exists():
            return set()
        with REVIEW_FILE.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        found = set()
        for row in rows:
            for column in ("identifier", "other_identifier"):
                value = str(row.get(column) or "").strip()
                if value.startswith("pubchem.compound:") and value.split(":", 1)[1].isdigit():
                    found.add(value.split(":", 1)[1])
        return found

    def _cids_from_mibig(self) -> dict[str, list[str]]:
        """CID -> the MIBiG compound ids that give it, in number order."""
        found: dict[str, set[str]] = {}
        for item in self._mibig_compounds():
            for cid in item["cids"]:
                found.setdefault(cid, set()).add(item["id"])
        return {cid: sorted(ids) for cid, ids in sorted(found.items(), key=lambda kv: int(kv[0]))}

    # ======================================================================
    # fetch()
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        compounds = self._mibig_compounds()
        by_cid = self._cids_from_mibig()
        cids = sorted(set(by_cid) | self._review_cids(), key=int)
        asked_for = {"cids": cids, "properties": PROPERTIES, "name_search": NAME_SEARCH_RULE}
        reused = self.reuse_today(asked_for)
        if reused:
            return reused

        earlier, earlier_folder = self._earlier_name_answers(asked_for)
        snapshot = self.start_snapshot(asked_for, {"mibig_compounds_by_cid": by_cid})

        # Round 1: the numbers MIBiG gives
        self.say(f"  [{self.name}] round 1: asking about {len(cids):,} CIDs in "
                 f"{batches_text(len(chunks(cids, BATCH_SIZE)))} of up to {BATCH_SIZE}")
        try:
            _, names_by_cid, titles = self._ask_numbers(snapshot, cids, first_file=1)
        except TransientHTTPError as error:
            raise SourceError(refused_message(error)) from error

        # Round 2: the name search
        to_search = self._names_to_search(compounds, names_by_cid, titles)
        searched, not_asked = self._search_names(snapshot, to_search, earlier, earlier_folder)

        # Round 3: the numbers the name search found. Skipped when PubChem stopped
        # answering in round 2: asking a server that is refusing only prolongs the block.
        found = sorted({c for answer in searched.values() for c in answer["cids"]
                        if len(answer["cids"]) <= MAX_NUMBERS_PER_NAME} - set(cids), key=int)
        names_missing = list(not_asked)            # names round 2 never got to ask
        round_3_finished = not found
        if found and not names_missing:
            self.say(f"  [{self.name}] round 3: asking about the {len(found):,} CIDs the name "
                     f"search found")
            try:
                self._ask_numbers(snapshot, found, first_file=len(chunks(cids, BATCH_SIZE)) + 1)
                round_3_finished = True
            except (TransientHTTPError, SourceError, requests.RequestException):
                pass
        if not round_3_finished:
            # Keep round 2's answers (they took the longest), but list every compound
            # whose search found a number round 3 had to describe: tidy won't use those
            # answers, and the next run carries the search over and repeats round 3.
            waiting = set(found)
            not_asked = names_missing + sorted(c for c, a in searched.items()
                                               if waiting & set(a["cids"]))

        snapshot.context["mibig_names"] = {
            item["id"]: item["names"] for item in compounds
            if item["cids"] or item["id"] in searched}
        snapshot.context["name_search"] = {k: v["name"] for k, v in searched.items()}
        results = snapshot.finish("live", notes={"names_not_asked": not_asked,
                                                 "round_3_finished": round_3_finished},
                                  complete=not not_asked)
        kept_in = relative_to_repo(results[0].local_path)
        if names_missing:
            raise SourceError(
                f"PubChem stopped answering after {len(searched):,} of "
                f"{len(searched) + len(names_missing):,} names (it limits how much one computer "
                f"may ask). Everything that arrived is kept in {kept_in}/.\n"
                f"  Wait a few hours, then run the same command again: it carries those "
                f"answers over and asks only the {len(names_missing):,} names still missing.")
        if not round_3_finished:
            raise SourceError(
                f"PubChem stopped answering in round 3, after the name search. The search's "
                f"{len(searched):,} answers are kept in {kept_in}/.\n"
                f"  Wait a few hours, then run the same command again: it carries those answers "
                f"over and asks round 3 again.")
        return results

    def _ask_numbers(self, snapshot: Snapshot, cids: list[str], first_file: int,
                     ) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]], dict[str, str]]:
        """Properties and names for these CIDs, 100 to a request (rounds 1 and 3)."""
        properties: dict[str, dict[str, Any]] = {}
        names: dict[str, list[str]] = {}
        for number, batch in enumerate(chunks(cids, BATCH_SIZE), start=first_file):
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
                data = json.loads(body)
                if kind == "properties":
                    for entry in data.get("PropertyTable", {}).get("Properties", []):
                        properties[str(entry.get("CID"))] = entry
                else:
                    for entry in data.get("InformationList", {}).get("Information", []):
                        names[str(entry.get("CID"))] = list(entry.get("Synonym") or [])
                if light != "Green":
                    self.say(f"  [{self.name}] PubChem's traffic light is {light}; slowing down")
                self.say(f"  [{self.name}] {relative_to_repo(path)}")
                self.pause(THROTTLE_FACTOR[light])
        titles = {cid: str(entry.get("Title") or "") for cid, entry in properties.items()}
        return properties, names, titles

    def _names_to_search(self, compounds: list[dict[str, Any]], names_by_cid: dict[str, list[str]],
                         titles: dict[str, str]) -> list[tuple[str, str]]:
        """(compound id, name) for every compound round 2 should ask about (see the notes)."""
        wanted = []
        for item in compounds:
            ours = {name_key(n) for n in item["names"]} - {""}
            if item["cids"]:
                listed = any(ours & {name_key(n) for n in [titles.get(c, "")] + names_by_cid.get(c, [])}
                             for c in item["cids"])
                if listed:
                    continue
            elif not item["formula"]:
                continue
            wanted.append((item["id"], item["name"]))
        return wanted

    def _earlier_name_answers(self, asked_for: dict[str, Any],
                              ) -> tuple[dict[str, dict[str, Any]], str]:
        """
        The name-search answers of the newest snapshot that asked the same
        questions but stopped halfway (complete is false), so they needn't be
        asked again. Only real answers count: numbers found, or "no CID found".
        """
        wanted = json.loads(json.dumps(asked_for))
        for folder in reversed(self.snapshots()):
            manifest = self.read_manifest(folder)
            if manifest.get("complete", True) or manifest.get("asked_for") != wanted:
                continue
            answers: dict[str, dict[str, Any]] = {}
            for answer in manifest.get("answers", []):
                if answer["file"].startswith("names_"):
                    for item in json.loads((folder / answer["file"]).read_text(encoding="utf-8")):
                        if item.get("status") in (200, 404):
                            answers[item["compound"]] = item
            return answers, relative_to_repo(folder)
        return {}, ""

    def _search_names(self, snapshot: Snapshot, to_search: list[tuple[str, str]],
                      earlier: dict[str, dict[str, Any]], earlier_folder: str,
                      ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """
        Round 2. Returns ({compound id: answer}, compound ids not asked because
        PubChem stopped answering). Each answer is {"compound", "name",
        "status", "cids", "answer"}.
        """
        searched: dict[str, dict[str, Any]] = {}
        carried = [earlier[c] for c, _ in to_search if c in earlier]
        if carried:
            snapshot.save("names_carried_over.json", _json_bytes(carried), url=NAME_SEARCH_URL,
                          method="POST", sent={"carried_over_from": earlier_folder},
                          n_records=sum(1 for a in carried if a["cids"]), source_version="live",
                          outcome="already_present")
            searched.update({a["compound"]: a for a in carried})
        todo = [(c, n) for c, n in to_search if c not in earlier]
        # One a second, plus the time PubChem takes to answer: about 1.5 s a name.
        self.say(f"  [{self.name}] round 2: the name search, {len(todo):,} names, one a second "
                 f"(about {max(1, round(len(todo) * 1.5 / 60))} minutes)"
                 + (f"; {len(carried):,} answers carried over from {earlier_folder}/"
                    if carried else ""))
        batch: list[dict[str, Any]] = []
        file_number = 1
        not_asked: list[str] = []

        def save_batch() -> None:
            nonlocal batch, file_number
            if batch:
                snapshot.save(f"names_{file_number:03d}.json", _json_bytes(batch),
                              url=NAME_SEARCH_URL, method="POST",
                              sent={"names": [a["name"] for a in batch]},
                              n_records=sum(1 for a in batch if a["cids"]), source_version="live")
                batch, file_number = [], file_number + 1

        for position, (compound, name) in enumerate(todo):
            try:
                response = self.http_post(NAME_SEARCH_URL, {"name": name}, accept=(400, 404))
            except (TransientHTTPError, SourceError, requests.RequestException):
                not_asked = [c for c, _ in todo[position:]]
                break
            try:
                answer: Any = response.json()
            except ValueError:
                answer = response.content.decode("utf-8", errors="replace")[:500]
            numbers = ([str(c) for c in answer.get("IdentifierList", {}).get("CID", [])]
                       if isinstance(answer, dict) else [])
            item = {"compound": compound, "name": name, "status": response.status_code,
                    "cids": numbers, "answer": answer}
            batch.append(item)
            searched[compound] = item
            if len(batch) == NAMES_PER_FILE:
                save_batch()
            done = position + 1
            if done % 100 == 0 or done == len(todo):
                found = sum(1 for c, _ in todo[:done] if searched[c]["cids"])
                self.say(f"  [{self.name}] name search: {done:,} of {len(todo):,} asked, "
                         f"{found:,} found")
            light = worst_light(response.headers.get("X-Throttling-Control", ""))
            self.pause(NAME_PAUSE_FACTOR * THROTTLE_FACTOR[light])
        save_batch()
        return searched, not_asked

    # ======================================================================
    # tidy()
    # ======================================================================
    def tidy(self) -> TidyResult:
        folder, manifest = self.latest_snapshot()
        retrieved_at = manifest["started_at"][:10]
        context = manifest.get("context", {})
        by_cid = context.get("mibig_compounds_by_cid", {})
        mibig_names = context.get("mibig_names", {})
        phase_4b = "name_search" in manifest.get("asked_for", {})

        properties: dict[str, dict[str, Any]] = {}
        synonyms: dict[str, list[str]] = {}
        searched: list[dict[str, Any]] = []
        for answer in manifest["answers"]:
            name = answer["file"]
            if name.startswith("properties_"):
                data = _load_json(folder / name)
                for entry in data.get("PropertyTable", {}).get("Properties", []):
                    properties[str(entry.get("CID"))] = entry
            elif name.startswith("synonyms_"):
                data = _load_json(folder / name)
                for entry in data.get("InformationList", {}).get("Information", []):
                    synonyms[str(entry.get("CID"))] = list(entry.get("Synonym") or [])
            elif name.startswith("names_"):
                searched.extend(_load_json(folder / name))

        found_by: dict[str, list[str]] = {}
        unfinished = set(manifest.get("notes", {}).get("names_not_asked", []))
        for item in searched:
            if item["compound"] in unfinished:
                continue                 # its round 3 didn't finish: never use half an answer
            if len(item["cids"]) <= MAX_NUMBERS_PER_NAME:
                for cid in item["cids"]:
                    found_by.setdefault(str(cid), []).append(item["compound"])

        asked = list(manifest["asked_for"]["cids"])
        extra = sorted(set(found_by) - set(asked), key=int)
        counts = {"cids_requested": len(asked), "compounds_found": 0,
                  "cids_not_in_pubchem": 0, "compounds_with_synonyms": 0,
                  "compounds_with_kegg_id": 0, "compounds_with_chebi_id": 0}
        not_found: list[str] = []
        nodes = []
        for cid in asked + extra:
            entry = properties.get(cid, {})
            if len(entry) <= 1:                  # only {"CID": n}: PubChem has no such compound
                if cid in asked:
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
            if phase_4b:
                connected = by_cid.get(cid, []) + found_by.get(cid, [])
                keys = {name_key(n) for c in connected for n in mibig_names.get(c, [])} - {""}
                props.update({
                    "synonym_count": len(names),
                    "found_by_name": "|".join(sorted(set(found_by.get(cid, [])))),
                    "names_matching_mibig": "|".join(dict.fromkeys(
                        n for n in [entry.get("Title") or ""] + names if name_key(n) in keys)),
                })
            title = entry.get("Title") or entry.get("IUPACName") or f"PubChem CID {cid}"
            nodes.append(node_row(f"pubchem.compound:{cid}", "Compound", title, props,
                                  self.name, retrieved_at))

        summary: dict[str, Any] = {
            "source": self.name,
            "source_version": manifest.get("source_version", "live"),
            "snapshot": relative_to_repo(folder),
            "retrieved_at": retrieved_at,
            "counts": counts,
            "cids_not_in_pubchem": not_found,
        }
        if phase_4b:
            outcome = {"names_searched": len(searched), "names_found_one_number": 0,
                       "names_found_several_numbers": 0, "names_found_too_many_numbers": 0,
                       "names_not_found": 0, "names_pubchem_could_not_read": 0}
            for item in searched:
                n = len(item["cids"])
                key = ("names_found_one_number" if n == 1 else "names_found_several_numbers"
                       if 1 < n <= MAX_NUMBERS_PER_NAME else "names_found_too_many_numbers"
                       if n else "names_not_found" if item["status"] == 404
                       else "names_pubchem_could_not_read")
                outcome[key] += 1
            not_asked = manifest.get("notes", {}).get("names_not_asked", [])
            counts.update(outcome)
            counts["names_not_asked"] = len(not_asked)
            counts["cids_found_by_name"] = len(extra)
            summary["name_search_complete"] = manifest.get("complete", True)
            summary["names_not_asked"] = not_asked
        return write_tables(self.name, nodes, [], summary, self.staging_dir)


def refused_message(error: Exception) -> str:
    """What to say when PubChem keeps refusing a number lookup after every wait."""
    busy = "429" in str(error)
    reason = ("PubChem is refusing requests from this computer for now (HTTP 429, too many "
              "requests). It does this for a while after it was asked too fast"
              if busy else f"PubChem kept failing ({error})")
    return (f"{reason}. Nothing from this run is used: tidy keeps reading the snapshot you "
            f"already have.\n  Try again in a few hours (a block can last until the next "
            f"day) with the same command. The rest of the project works meanwhile.")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


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


def _load_json(path: Path) -> Any:
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
