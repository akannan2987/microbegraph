"""
MicrobeGraph, look at the evidence Phase 4b needs before writing its code.

WHY THIS EXISTS
    Phase 4 refused every join it couldn't confirm and listed what was left
    over (data/processed/resolve_summary.json and the ledger). Phase 4b closes
    those gaps with more evidence. Before any code is written, I want to see
    what that evidence really looks like:

      1. MIBiG's GenBank file (mibig_gbk_4.0.tar.gz, about 80 MB): does it
         name the gene records that Phases 3 to 4 couldn't place, and the four
         maize genes the curators removed from BGC0002390, in a way that leads
         to a protein number?
      2. PubChem's name search: for a sample of MIBiG compounds that have no
         PubChem number, or whose number Phase 4 didn't accept, which numbers
         does PubChem give for the name, and do the formulas agree?
      3. PubChem's full list of names: Phase 2 kept the first 20 names of
         each compound, but its download has them all. How many of the 325
         joins that only the formula confirmed have the name further down?
      4. UniProt's view of the 42 protein numbers that Phase 4 left between
         two or more equally good UniProt entries.
      5. NCBI Gene's view of the four maize genes (LOC100272490 and three
         more), as a second route to their protein numbers.

    Every earlier phase started the same way (capture_samples.py,
    capture_uniprot_samples.py, capture_mibig_protein_samples.py,
    capture_resolution_samples.py): look at real data first, then write code.

WHAT IT DOES
    Part 1 (network): downloads the GenBank file once (about 80 MB), looks up
    the name of each sampled compound (541 names, see below), asks PubChem for
    the formula and names of every number those searches found, and sends one
    request to UniProt and two to NCBI.

    PubChem limits how hard anyone may ask, and a name search costs its
    servers more than the number lookups Phase 2 makes. On the first run of
    this script, at four requests a second, PubChem answered "429 Too Many
    Requests" to everything after about 400 questions, and kept refusing for
    hours. Asking one a second didn't help: the PubChem fetch was refused
    after 372 names that same day. So the names are now looked up in
    PubChem's file of every name, data/raw/pubchem/CID-Synonym-filtered.gz,
    which the PubChem fetch downloads (src/microbegraph/sources/pubchem_names.py
    explains the file). Searching it sends nothing to PubChem.

    If that file isn't on your computer yet, the script stops and says so,
    unless you add --web. Then it asks PubChem's web service one name a
    second, and when PubChem says it's busy (429) or has a temporary fault
    (500 to 504) it waits 15, 30, 60 and then 120 seconds before asking
    again. A run that stops halfway can be started again: the
    downloaded file and every name PubChem has already answered are reused.

    WHEN YOU REPEAT THE BUILD, this script is optional: its findings are in
    docs/06b-closing-the-gaps.md, Step 2, and the PubChem fetch looks up
    every one of these names anyway. If you do run it, run it after
    `python -m microbegraph.fetch --source pubchem`, so the names file is
    there and the script never sends PubChem a name search.

    Part 2 (offline): reads the GenBank file, MIBiG's protein file and the
    Phase 2 PubChem snapshot already in your evidence locker, and counts
    everything listed above. Nothing is sent anywhere in this part.

USAGE (from the project folder, with .venv active, after Phase 4)
    python tests/fixtures/capture_gap_samples.py
    python tests/fixtures/capture_gap_samples.py --web
    python tests/fixtures/capture_gap_samples.py --fixture

    The second form asks PubChem's web service when the names file isn't on
    your computer (see above). The third makes no request at all. It cuts surfactin's record out
    of the GenBank file (the one in your locker, or else the one this script
    downloaded) into tests/fixtures/mibig/genbank/BGC0000433.gbk, keeping
    only the lines the tests need: lines are removed, never edited.

    It reads data/processed/ (the Phase 4 results), so run
    `python -m microbegraph.resolve` first if that folder is empty.
    Everything lands in data/samples/<today>/gaps/, which never goes to
    GitHub. capture_bundle.json holds the survey and the answers in one file,
    so it is the one file to share.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import tarfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import DATA_DIR, PROCESSED_DIR, RAW_DIR, STAGING_DIR, relative_to_repo
from microbegraph.resolution.names import compare_formulas, name_key, split_list
from microbegraph.sources.base import TIMEOUT, USER_AGENT
from microbegraph.sources.mibig_proteins import read_protein_file
from microbegraph.sources.pubchem_names import BULK_FILE, search_synonym_file

SERVER = "https://dl.secondarymetabolites.org/mibig/"
GENBANK_FILE = "mibig_gbk_4.0.tar.gz"
PROTEIN_FILE = "mibig_prot_seqs_4.0.fasta"
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
UNIPROT = "https://rest.uniprot.org/uniprotkb"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

PAUSE = 1.0               # seconds between PubChem requests (see WHAT IT DOES)
BUSY_WAITS = (15, 30, 60, 120)   # seconds to wait after a 429 or 5xx, then ask again
EVERY_NTH = 20            # of the compounds with no PubChem number, ask about every 20th
EXAMPLES = 8
# Names asked about whatever the sample holds: the cases the guides already
# mention, so the survey shows what PubChem says about each one.
NAMED_CASES = ("1233A", "hymeglusin", "desosamine", "methymycin", "2-methylisoborneol",
               "minutissamide A", "minutissamide C", "surfactin")
UNIPROT_FIELDS = ("accession,id,reviewed,protein_name,gene_names,organism_name,organism_id,"
                  "length,fragment,protein_existence,annotation_score,xref_embl,sequence")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))    # some property cells are long


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ======================================================================
# Part 1: the network
# ======================================================================
def download(session: requests.Session, url: str, target: Path) -> dict[str, Any]:
    """Stream a file to disk, fingerprinting it on the way (MD5 and SHA-256)."""
    record: dict[str, Any] = {"method": "GET", "url": url, "asked_at": now()}
    if target.exists():
        data = target.read_bytes()
        record.update({"reused": True, "bytes": len(data), "md5": hashlib.md5(data).hexdigest(),
                       "sha256": hashlib.sha256(data).hexdigest()})
        print(f"    {target.name} is already here from an earlier run; not downloading again")
        return record
    md5, sha256, n_bytes = hashlib.md5(), hashlib.sha256(), 0
    part = target.with_name(target.name + ".part")
    try:
        with session.get(url, stream=True, timeout=TIMEOUT) as response:
            record["status"] = response.status_code
            record["headers"] = {k: v for k, v in response.headers.items()
                                 if k in ("Content-Type", "Content-Length", "Last-Modified", "ETag")}
            response.raise_for_status()
            with part.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    handle.write(chunk)
                    md5.update(chunk)
                    sha256.update(chunk)
                    n_bytes += len(chunk)
                    print(f"\r    {n_bytes / 1_048_576:6.1f} MB", end="", flush=True)
        print()
        part.replace(target)
    except requests.RequestException as error:
        part.unlink(missing_ok=True)
        record["error"] = f"{type(error).__name__}: {error}"
        return record
    record.update({"bytes": n_bytes, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()})
    return record


def ask(session: requests.Session, method: str, url: str, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
    """
    One request, recorded. Returns (parsed JSON or text, record). Never raises.
    A busy answer (429) or a temporary fault (500 to 504) is asked again
    after a wait (BUSY_WAITS); the record keeps every status seen.
    """
    record: dict[str, Any] = {"method": method, "url": url, "asked_at": now()}
    statuses: list[int] = []
    for wait in (*BUSY_WAITS, None):
        try:
            response = session.request(method, url, timeout=TIMEOUT, **kwargs)
        except requests.RequestException as error:
            record["error"] = f"{type(error).__name__}: {error}"
            return None, record
        statuses.append(response.status_code)
        if response.status_code != 429 and response.status_code < 500 or wait is None:
            break
        after = response.headers.get("Retry-After", "")
        pause = int(after) if after.isdigit() else wait
        print(f"\n    the server answered {response.status_code} (busy); waiting {pause} s "
              f"before asking again", flush=True)
        time.sleep(pause)
    if len(statuses) > 1:
        record["statuses_seen"] = statuses
    record["status"] = response.status_code
    light = response.headers.get("X-Throttling-Control", "")
    if light:
        record["throttling"] = light
    try:
        return response.json(), record
    except ValueError:
        return response.text, record


def compounds_to_ask(processed: Path, staging: Path, pubchem_names: dict[str, list[str]],
                     ) -> list[dict[str, Any]]:
    """
    The MIBiG compounds whose names go to PubChem's name search, each with
    the reason it was chosen. Four groups, in this order:
      refused       Phase 4 kept it apart from the number MIBiG gives
      formula_only  joined on the formula alone, and the name isn't in
                    PubChem's full list either
      no_number     no PubChem number at all (every EVERY_NTH, by identifier)
      named         a case the guides mention
    """
    mibig = {r["node_id"]: r for r in read_csv(staging / "mibig_nodes.csv")
             if r["node_type"] == "Compound"}
    ledger = read_csv(processed / "resolution_ledger.csv")
    chosen: dict[str, dict[str, Any]] = {}

    def add(node_id: str, why: str, extra: dict[str, Any] | None = None) -> None:
        if node_id in mibig and node_id not in chosen:
            chosen[node_id] = {"compound": node_id, "name": mibig[node_id]["name"], "why": why,
                               **(extra or {})}

    for row in ledger:
        if row["rule"].startswith("pubchem_number") and row["decision"] == "kept_apart":
            add(row["identifier"], "refused", {"rule": row["rule"],
                                              "given": row["compared_with"]})
    for row in ledger:
        if (row["rule"] == "pubchem_number_confirmed" and row["decision"] == "merged"
                and "doesn't list the name" in row["grounds"]):
            cid = row["compared_with"].split(":", 1)[1]
            keys = {name_key(n) for n in pubchem_names.get(cid, [])}
            props = json.loads(mibig[row["identifier"]]["properties"] or "{}")
            ours = {name_key(n) for n in [mibig[row["identifier"]]["name"]]
                    + split_list(props.get("synonyms")) + split_list(props.get("other_names"))}
            if not (ours - {""}) & keys:
                add(row["identifier"], "formula_only", {"given": row["compared_with"]})
    without = sorted(i for i, r in mibig.items()
                     if not json.loads(r["properties"] or "{}").get("pubchem_cid"))
    for node_id in without[::EVERY_NTH]:
        add(node_id, "no_number")
    wanted = {name_key(n) for n in NAMED_CASES}
    for node_id, row in sorted(mibig.items()):
        if name_key(row["name"]) in wanted:
            add(node_id, "named")
    return list(chosen.values())


def name_search(session: requests.Session, name: str, mode: str) -> tuple[Any, dict[str, Any]]:
    """PubChem's name search, by POST (the name in the body) or GET (in the address)."""
    if mode == "post":
        return ask(session, "POST", f"{PUG}/compound/name/cids/JSON", data={"name": name})
    quoted = requests.utils.quote(name, safe="")
    return ask(session, "GET", f"{PUG}/compound/name/{quoted}/cids/JSON")


def names_from_file(path: Path, chosen: list[dict[str, Any]]) -> dict[str, Any]:
    """
    The name search in PubChem's file of every name instead of on the web
    (src/microbegraph/sources/pubchem_names.py), with each answer in the shape
    the web search gives, so the rest of the survey reads both the same way.
    """
    found = search_synonym_file(path, [item["name"] for item in chosen], say=print)
    not_found = {"Fault": {"Code": "PUGREST.NotFound",
                           "Message": f"No CID lists this name in {BULK_FILE}"}}
    return {item["compound"]: ({"IdentifierList": {"CID": [int(c) for c in found[item["name"]]]}}
                               if found[item["name"]] else not_found)
            for item in chosen}


def web_name_search(session: requests.Session, chosen: list[dict[str, Any]], out_dir: Path,
                    log: dict[str, Any]) -> tuple[dict[str, Any], Counter[str], str]:
    """One name a second on PubChem's web service, reusing answers from an earlier run."""
    earlier: dict[str, Any] = {}
    names_file = out_dir / "pubchem_names.json"
    if names_file.exists():
        saved = json.loads(names_file.read_text(encoding="utf-8"))
        earlier = {k: v for k, v in saved.get("answers", {}).items() if answered(v)}
        print(f"    {len(earlier)} names were answered on an earlier run; asking only the rest")
    _, first = name_search(session, chosen[0]["name"], "post")
    mode = "post" if first.get("status") in (200, 404) else "get"
    log["name_search_mode"] = mode
    print(f"    asking by {mode.upper()} (the first POST answered {first.get('status', 'nothing')})")
    answers: dict[str, Any] = {}
    statuses: Counter[str] = Counter()
    for number, item in enumerate(chosen, start=1):
        if item["compound"] in earlier:
            answers[item["compound"]] = earlier[item["compound"]]
            statuses["answered earlier"] += 1
            continue
        answer, record = name_search(session, item["name"], mode)
        record["name"] = item["name"]
        log["requests"].append(record)
        answers[item["compound"]] = answer
        statuses[str(record.get("status", record.get("error", "?")))] += 1
        light = record.get("throttling", "")
        slow = 4.0 if any(c in light for c in ("Yellow", "Red", "Black")) else 1.0
        print(f"\r    {number:4d} of {len(chosen)} asked", end="", flush=True)
        time.sleep(PAUSE * slow)
    print()
    return answers, statuses, mode


def answered(answer: Any) -> bool:
    """True for a real answer: numbers found, or PubChem's "no CID found"."""
    if not isinstance(answer, dict):
        return False
    return "IdentifierList" in answer or answer.get("Fault", {}).get("Code") == "PUGREST.NotFound"


def cids_in(answer: Any) -> list[int]:
    if isinstance(answer, dict):
        return [int(c) for c in answer.get("IdentifierList", {}).get("CID", []) if c]
    return []


def pubchem_details(session: requests.Session, cids: list[int], out_dir: Path,
                    log: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Formula, title and every name for each number, 100 at a time, as Phase 2 asks."""
    properties: dict[str, dict[str, Any]] = {}
    names: dict[str, list[str]] = {}
    batches = [cids[i:i + 100] for i in range(0, len(cids), 100)]
    for number, batch in enumerate(batches, start=1):
        body = {"cid": ",".join(map(str, batch))}
        answer, record = ask(session, "POST", f"{PUG}/compound/cid/property/"
                             "Title,MolecularFormula,MolecularWeight,InChIKey/JSON", data=body)
        log.append(record)
        (out_dir / f"pubchem_properties_{number:03d}.json").write_text(
            json.dumps(answer, indent=1) + "\n", encoding="utf-8")
        for entry in (answer if isinstance(answer, dict) else {}).get(
                "PropertyTable", {}).get("Properties", []):
            properties[str(entry.get("CID"))] = entry
        time.sleep(PAUSE)
        answer, record = ask(session, "POST", f"{PUG}/compound/cid/synonyms/JSON", data=body)
        log.append(record)
        (out_dir / f"pubchem_synonyms_{number:03d}.json").write_text(
            json.dumps(answer, indent=1) + "\n", encoding="utf-8")
        for entry in (answer if isinstance(answer, dict) else {}).get(
                "InformationList", {}).get("Information", []):
            names[str(entry.get("CID"))] = list(entry.get("Synonym") or [])
        time.sleep(PAUSE)
    return properties, names


# ======================================================================
# Part 2: what the GenBank file holds (offline)
# ======================================================================
FEATURE = re.compile(r"^ {5}(\S+)\s+(\S.*)$")
QUALIFIER = re.compile(r"^ {21}/([^=\s]+)(?:=(.*))?$")
CONTINUED = re.compile(r"^ {21}(?!/)(.*)$")


def read_cds(text: str) -> tuple[list[dict[str, Any]], Counter[str], int]:
    """
    Every CDS feature (a stretch of DNA that codes for a protein) in one
    GenBank file, as {qualifier: [values]}, plus a count of every feature
    kind seen and the number of records (LOCUS lines) in the file.
    """
    cds: list[dict[str, Any]] = []
    kinds: Counter[str] = Counter()
    records = 0
    current: dict[str, Any] | None = None
    key: str | None = None
    in_features = False
    for line in text.splitlines():
        if line.startswith("LOCUS"):
            records += 1
        if line.startswith("FEATURES"):
            in_features = True
            continue
        if not in_features:
            continue
        if line.startswith(("ORIGIN", "CONTIG", "//")) or (line and not line.startswith(" ")):
            in_features = False
            current = key = None
            continue
        feature = FEATURE.match(line)
        if feature:
            kinds[feature.group(1)] += 1
            current = {"_kind": feature.group(1), "_location": feature.group(2)}
            if feature.group(1) == "CDS":
                cds.append(current)
            key = None
            continue
        qualifier = QUALIFIER.match(line)
        if qualifier and current is not None:
            key = qualifier.group(1)
            current.setdefault(key, []).append((qualifier.group(2) or "").strip())
            continue
        more = CONTINUED.match(line)
        if more and current is not None and key is not None:
            current[key][-1] += ("" if key == "translation" else " ") + more.group(1).strip()
            continue
        if line.startswith(" " * 21) and current is not None and key is None:
            current["_location"] += line.strip()
    for feature in cds:
        for name, values in list(feature.items()):
            if isinstance(values, list):
                feature[name] = [v.strip('"') for v in values]
    return cds, kinds, records


def survey_genbank(archive: Path, protein_file: Path, staging: Path,
                   processed: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Count what the GenBank file holds and look up the leftover genes in it."""
    by_entry = read_protein_file(protein_file)
    members: list[str] = []
    kinds: Counter[str] = Counter()
    qualifiers: Counter[str] = Counter()
    cds_by_entry: dict[str, list[dict[str, Any]]] = {}
    records_per_file: Counter[int] = Counter()
    with tarfile.open(archive, mode="r|*") as tar:
        for member in tar:
            if not member.isfile():
                continue
            members.append(member.name)
            if not member.name.endswith((".gbk", ".gb", ".genbank")):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            text = handle.read().decode("utf-8", errors="replace")
            cds, these, records = read_cds(text)
            records_per_file[records] += 1
            kinds.update(these)
            for feature in cds:
                qualifiers.update(k for k in feature if not k.startswith("_"))
            accession = Path(member.name).name.split(".")[0]
            cds_by_entry[accession] = cds

    # Does every protein of the protein file appear as a CDS of its entry?
    in_both = only_file = 0
    for accession, records in by_entry.items():
        numbers = {p for f in cds_by_entry.get(accession, []) for p in f.get("protein_id", [])}
        for record in records:
            if record.protein_id in numbers:
                in_both += 1
            else:
                only_file += 1

    resolve_summary = json.loads((processed / "resolve_summary.json").read_text(encoding="utf-8"))
    left = resolve_summary.get("for_phase_4b") or resolve_summary["still_open"]
    mibig_nodes = {r["node_id"]: r for r in read_csv(staging / "mibig_nodes.csv")
                   if r["node_type"] == "Protein"}

    def look_up(accession: str, name: str) -> list[dict[str, Any]]:
        """Which CDS features of this entry mention `name`, and in which qualifier."""
        found = []
        folded = name.casefold()
        number = name.removeprefix("LOC") if name.startswith("LOC") else ""
        for feature in cds_by_entry.get(accession, []):
            where = [k for k, values in feature.items() if not k.startswith("_")
                     and k != "translation"
                     and any(v.casefold() == folded or (number and v == f"GeneID:{number}")
                             for v in values)]
            if where:
                proteins = feature.get("protein_id", [])
                found.append({"matched_in": where, "protein_id": proteins,
                              "gene": feature.get("gene", []),
                              "locus_tag": feature.get("locus_tag", []),
                              "product": feature.get("product", []),
                              "db_xref": feature.get("db_xref", []),
                              "in_protein_file": [p for p in proteins
                                                  if any(r.protein_id == p
                                                         for r in by_entry.get(accession, []))]})
        return found

    genes: dict[str, Any] = {}
    for node_id in left["gene_records_without_a_protein_number"]:
        props = json.loads(mibig_nodes.get(node_id, {}).get("properties") or "{}")
        raw = str(props.get("protein_id", ""))
        accession = node_id.split(":", 1)[1].split("-", 1)[0].upper()
        genes[node_id] = {"gene_record_id": raw, "gene_name": props.get("gene_name", ""),
                          "genbank": look_up(accession, raw)}
    removals: dict[str, Any] = {}
    for item in left["curators_removals_not_found"]:
        removals[f"{item['entry']}: {item['to_delete']}"] = look_up(item["entry"], item["to_delete"])

    facts = {
        "files_in_archive": len(members),
        "first_member_names": members[:5],
        "entries_with_cds": len(cds_by_entry),
        "records_per_file": dict(records_per_file),
        "feature_kinds": dict(kinds.most_common()),
        "cds_qualifiers": dict(qualifiers.most_common()),
        "cds_total": sum(len(v) for v in cds_by_entry.values()),
        "cds_without_protein_id": sum(1 for v in cds_by_entry.values() for f in v
                                      if not f.get("protein_id")),
        "protein_file_records_also_a_cds": in_both,
        "protein_file_records_not_a_cds": only_file,
        "gene_records_left_by_phase_4": genes,
        "removals_left_by_phase_4": removals,
    }
    keep = {"BGC0002390"} | {n.split(":", 1)[1].split("-", 1)[0].upper() for n in genes}
    without_sequence = {a: [{k: v for k, v in f.items() if k != "translation"}
                            for f in cds_by_entry.get(a, [])] for a in sorted(keep)}
    return facts, without_sequence


# The lines kept in the test sample of a GenBank record: the header lines that
# say what the record is, the FEATURES line, every CDS with the qualifiers the
# adapter reads (and the two that say how it's translated), ORIGIN and "//".
KEEP_HEADER = ("LOCUS", "DEFINITION", "ACCESSION", "VERSION", "KEYWORDS", "SOURCE")
KEEP_QUALIFIERS = ("gene", "locus_tag", "old_locus_tag", "gene_synonym", "protein_id",
                   "product", "codon_start", "transl_table")


def cut_genbank(text: str) -> str:
    """A cut-down copy of one GenBank record: whole lines kept or dropped, none changed."""
    kept: list[str] = []
    section = ""
    feature = ""
    qualifier = ""
    open_quote = False
    for line in text.splitlines():
        if line and not line.startswith(" "):
            section = line.split()[0]
            feature = qualifier = ""
            open_quote = False
            if section in (*KEEP_HEADER, "FEATURES", "ORIGIN", "//"):
                kept.append(line)
            continue
        if section in KEEP_HEADER:
            if line.startswith((" " * 12, "  ORGANISM")):  # a header that carries on
                kept.append(line)
            continue
        if section != "FEATURES":
            continue                                       # the DNA after ORIGIN
        if re.match(r"^ {5}\S", line):
            feature = line.split()[0]
            qualifier, open_quote = "", False
            if feature == "CDS":
                kept.append(line)
            continue
        if open_quote:                                     # inside a value that wrapped
            if feature == "CDS" and qualifier in KEEP_QUALIFIERS:
                kept.append(line)
            open_quote = not line.rstrip().endswith('"')
            continue
        match = re.match(r'^ {21}/([A-Za-z_]+)(?:=(.*))?$', line)
        if match:
            qualifier = match.group(1)
            value = (match.group(2) or "").strip()
            open_quote = value.startswith('"') and (len(value) == 1 or not value.endswith('"'))
            if feature == "CDS" and qualifier in KEEP_QUALIFIERS:
                kept.append(line)
    return "\n".join(kept) + "\n"


def write_fixture() -> int:
    """--fixture: cut surfactin's GenBank record into tests/fixtures/mibig/genbank/."""
    candidates = [RAW_DIR / "mibig" / GENBANK_FILE] + sorted(
        (DATA_DIR / "samples").glob(f"*/gaps/{GENBANK_FILE}"), reverse=True)
    archive = next((p for p in candidates if p.exists()), None)
    if archive is None:
        print(f"No {GENBANK_FILE} found. Run this script without --fixture first, or "
              f"python -m microbegraph.fetch --source mibig.")
        return 1
    with tarfile.open(archive, mode="r|*") as tar:
        for member in tar:
            if member.isfile() and Path(member.name).name == "BGC0000433.gbk":
                handle = tar.extractfile(member)
                text = handle.read().decode("utf-8") if handle else ""
                break
        else:
            print(f"BGC0000433.gbk isn't in {relative_to_repo(archive)}.")
            return 1
    target = Path(__file__).parent / "mibig" / "genbank" / "BGC0000433.gbk"
    target.parent.mkdir(parents=True, exist_ok=True)
    sample = cut_genbank(text)
    target.write_text(sample, encoding="utf-8", newline="\n")
    print(f"{relative_to_repo(target)}: {sample.count(chr(10))} of {text.count(chr(10))} lines "
          f"kept from {relative_to_repo(archive)}, SHA-256 "
          f"{hashlib.sha256(sample.encode('utf-8')).hexdigest()}")
    return 0


def survey_names(chosen: list[dict[str, Any]], answers: dict[str, Any],
                 properties: dict[str, dict[str, Any]], staging: Path) -> dict[str, Any]:
    """For each sampled compound: what the name search found, and how the formulas compare."""
    mibig = {r["node_id"]: r for r in read_csv(staging / "mibig_nodes.csv")
             if r["node_type"] == "Compound"}
    outcome: Counter[str] = Counter()
    by_group: dict[str, Counter[str]] = {}
    examples: dict[str, list[dict[str, Any]]] = {}
    for item in chosen:
        props = json.loads(mibig[item["compound"]]["properties"] or "{}")
        ours = props.get("formula", "")
        cids = cids_in(answers.get(item["compound"]))
        if not cids:
            result = "no number for this name"
        elif len(cids) > 1:
            agreeing = [c for c in cids if compare_formulas(
                ours, properties.get(str(c), {}).get("MolecularFormula")) == "agrees"]
            how_many = {0: "none", 1: "one"}.get(len(agreeing), str(len(agreeing)))
            result = (f"several numbers, {how_many} with MIBiG's formula" if ours
                      else "several numbers, no formula to compare")
        else:
            theirs = properties.get(str(cids[0]), {}).get("MolecularFormula")
            result = f"one number, formula {compare_formulas(ours, theirs)}"
            if f"pubchem.compound:{cids[0]}" == item.get("given"):
                result += ", the number MIBiG gives"
        outcome[result] += 1
        by_group.setdefault(item["why"], Counter())[result] += 1
        examples.setdefault(result, [])
        if len(examples[result]) < EXAMPLES:
            examples[result].append({"name": item["name"], "why": item["why"],
                                     "given": item.get("given", ""), "found": cids[:10],
                                     "mibig_formula": ours,
                                     "titles": [properties.get(str(c), {}).get("Title")
                                                for c in cids[:5]]})
    return {"asked": len(chosen), "outcome": dict(outcome.most_common()),
            "by_group": {k: dict(v.most_common()) for k, v in by_group.items()},
            "examples": examples}


def full_list_check(processed: Path, staging: Path,
                    pubchem_names: dict[str, list[str]]) -> dict[str, Any]:
    """The 325 formula-only joins against PubChem's full list of names."""
    mibig = {r["node_id"]: r for r in read_csv(staging / "mibig_nodes.csv")
             if r["node_type"] == "Compound"}
    found = missing = 0
    positions: list[int] = []
    examples: list[dict[str, Any]] = []
    for row in read_csv(processed / "resolution_ledger.csv"):
        if not (row["rule"] == "pubchem_number_confirmed" and row["decision"] == "merged"
                and "doesn't list the name" in row["grounds"]):
            continue
        cid = row["compared_with"].split(":", 1)[1]
        props = json.loads(mibig[row["identifier"]]["properties"] or "{}")
        ours = {name_key(n) for n in [mibig[row["identifier"]]["name"]]
                + split_list(props.get("synonyms")) + split_list(props.get("other_names"))} - {""}
        theirs = [name_key(n) for n in pubchem_names.get(cid, [])]
        hit = next((i for i, key in enumerate(theirs) if key in ours), None)
        if hit is None:
            missing += 1
            if len(examples) < EXAMPLES:
                examples.append({"compound": row["identifier"], "cid": cid,
                                 "names_listed": len(theirs)})
        else:
            found += 1
            positions.append(hit + 1)
    buckets = Counter("1-20" if p <= 20 else "21-50" if p <= 50 else "51-100" if p <= 100 else "101-500" if p <= 500
                      else "over 500" for p in positions)
    return {"formula_only_joins": found + missing, "name_found_in_full_list": found,
            "name_not_in_full_list": missing, "position_of_the_name": dict(buckets),
            "examples_not_found": examples}


def main() -> int:
    if "--fixture" in sys.argv[1:]:
        return write_fixture()
    processed, staging = PROCESSED_DIR, STAGING_DIR
    for needed in (processed / "resolution_ledger.csv", processed / "resolve_summary.json",
                   staging / "mibig_nodes.csv", RAW_DIR / "mibig" / PROTEIN_FILE):
        if not needed.exists():
            print(f"{relative_to_repo(needed)} is missing. Run Phases 1 to 4 first "
                  f"(the last step is: python -m microbegraph.resolve).")
            return 1
    from microbegraph.sources.pubchem import PubchemSource
    folder, manifest = PubchemSource().latest_snapshot()
    pubchem_names: dict[str, list[str]] = {}
    for answer in manifest["answers"]:
        if answer["file"].startswith("synonyms_"):
            data = json.loads((folder / answer["file"]).read_text(encoding="utf-8"))
            for entry in data.get("InformationList", {}).get("Information", []):
                pubchem_names[str(entry.get("CID"))] = list(entry.get("Synonym") or [])
    chosen = compounds_to_ask(processed, staging, pubchem_names)
    names_on_disk = RAW_DIR / "pubchem" / BULK_FILE
    if not names_on_disk.exists() and "--web" not in sys.argv[1:]:
        print(f"{relative_to_repo(names_on_disk)} isn't on this computer yet, so this survey\n"
              f"would send {len(chosen)} name searches to PubChem's web service. PubChem stops\n"
              f"answering after about 400 and can then refuse your computer for hours, the\n"
              f"PubChem fetch included. Run `python -m microbegraph.fetch --source pubchem`\n"
              f"first (it downloads that file), or add --web to ask the web service anyway.")
        return 1

    out_dir = DATA_DIR / "samples" / datetime.now(timezone.utc).strftime("%Y-%m-%d") / "gaps"
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    log: dict[str, Any] = {"captured_with": "tests/fixtures/capture_gap_samples.py",
                           "pubchem_snapshot": relative_to_repo(folder), "requests": []}
    print(f"Saving to {relative_to_repo(out_dir)}/")

    # 1a. the GenBank file
    print(f"\nPart 1a: MIBiG's GenBank file, from {SERVER}")
    target = out_dir / GENBANK_FILE
    record = download(session, SERVER + GENBANK_FILE, target)
    log["requests"].append(record)
    if "error" in record:
        print(f"    FAILED: {record['error']}")
        (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
        return 1
    print(f"    {record['bytes']:,} bytes, SHA-256 {record['sha256']}")

    # 1b. PubChem name searches
    groups = Counter(item["why"] for item in chosen)
    print(f"\nPart 1b: PubChem's name search for {len(chosen)} MIBiG compounds "
          f"({', '.join(f'{n} {w}' for w, n in groups.items())})")
    if names_on_disk.exists():
        print(f"    searching {relative_to_repo(names_on_disk)}, PubChem's file of every name, "
              f"on this computer (nothing is sent)")
        answers, statuses, mode = names_from_file(names_on_disk, chosen), Counter(), "names file"
        statuses.update("200" if cids_in(a) else "404" for a in answers.values())
        log["name_search_mode"] = mode
    else:
        answers, statuses, mode = web_name_search(session, chosen, out_dir, log)
    print(f"    answers by HTTP status: {dict(statuses)}")
    (out_dir / "pubchem_names.json").write_text(json.dumps(
        {"mode": mode, "asked": chosen, "answers": answers}, indent=1) + "\n", encoding="utf-8")

    found = sorted({c for a in answers.values() for c in cids_in(a)}
                   | {int(i["given"].split(":", 1)[1]) for i in chosen if i.get("given")
                      and "|" not in i["given"]})
    print(f"    {len(found)} PubChem numbers to describe; asking for their formulas and names")
    properties, names = pubchem_details(session, found, out_dir, log["requests"])

    # 1c. UniProt, for the tied protein numbers
    ledger = read_csv(processed / "resolution_ledger.csv")
    tied = [r for r in ledger if r["rule"] == "uniprot_cross_reference"
            and r["decision"] == "kept_apart"]
    accessions = sorted({e.split(":", 1)[1] for r in tied for e in split_list(r["compared_with"])})
    print(f"\nPart 1c: UniProt, {len(accessions)} entries behind {len(tied)} tied protein numbers")
    answer, record = ask(session, "GET", f"{UNIPROT}/accessions",
                         params={"accessions": ",".join(accessions), "fields": UNIPROT_FIELDS,
                                 "format": "tsv"})
    if record.get("status") != 200:
        answer, record = ask(session, "GET", f"{UNIPROT}/search",
                             params={"query": " OR ".join(f"accession:{a}" for a in accessions),
                                     "fields": UNIPROT_FIELDS, "format": "tsv", "size": "500"})
    log["requests"].append({k: v for k, v in record.items()})
    (out_dir / "uniprot_tied.tsv").write_text(answer if isinstance(answer, str) else "",
                                             encoding="utf-8")
    rows = (answer or "").count("\n") - 1 if isinstance(answer, str) else 0
    print(f"    {record.get('status', record.get('error'))}, {max(rows, 0)} entries described")

    # 1d. NCBI Gene, for the four maize genes
    summary = json.loads((processed / "resolve_summary.json").read_text(encoding="utf-8"))
    removals = (summary.get("for_phase_4b") or summary["still_open"])["curators_removals_not_found"]
    gene_ids = [r["to_delete"].removeprefix("LOC") for r in removals
                if r["to_delete"].startswith("LOC") and r["to_delete"][3:].isdigit()]
    print(f"\nPart 1d: NCBI Gene, {len(gene_ids)} genes: {', '.join(gene_ids)}")
    ncbi: dict[str, Any] = {}
    if gene_ids:
        answer, record = ask(session, "GET", f"{EUTILS}/esummary.fcgi",
                             params={"db": "gene", "id": ",".join(gene_ids), "retmode": "json",
                                     "tool": "microbegraph"})
        log["requests"].append(record)
        ncbi["esummary"] = answer
        time.sleep(0.4)
        answer, record = ask(session, "GET", f"{EUTILS}/elink.fcgi",
                             params=[("dbfrom", "gene"), ("db", "protein"),
                                     ("linkname", "gene_protein_refseq"), ("retmode", "json"),
                                     ("tool", "microbegraph")] + [("id", g) for g in gene_ids])
        log["requests"].append(record)
        ncbi["elink"] = answer
        print(f"    esummary and elink: {log['requests'][-2].get('status')}, "
              f"{log['requests'][-1].get('status')}")
    (out_dir / "ncbi_gene.json").write_text(json.dumps(ncbi, indent=1) + "\n", encoding="utf-8")

    # Part 2, offline
    print("\nPart 2: reading what arrived, with the files already in your locker (offline)")
    genbank, kept = survey_genbank(target, RAW_DIR / "mibig" / PROTEIN_FILE, staging, processed)
    for key in ("files_in_archive", "entries_with_cds", "records_per_file", "cds_total",
                "cds_without_protein_id", "protein_file_records_also_a_cds",
                "protein_file_records_not_a_cds"):
        print(f"    {key:<36} {genbank[key]}")
    placed = sum(1 for g in genbank["gene_records_left_by_phase_4"].values()
                 if any(f["in_protein_file"] for f in g["genbank"]))
    print(f"    {'leftover gene records placed':<36} {placed} of "
          f"{len(genbank['gene_records_left_by_phase_4'])}")
    placed = sum(1 for g in genbank["removals_left_by_phase_4"].values()
                 if any(f["in_protein_file"] for f in g))
    print(f"    {'leftover removals placed':<36} {placed} of "
          f"{len(genbank['removals_left_by_phase_4'])}")
    names_found = survey_names(chosen, answers, properties, staging)
    print("    PubChem name search, by outcome:")
    for outcome, n in names_found["outcome"].items():
        print(f"      {n:4d}  {outcome}")
    full = full_list_check(processed, staging, pubchem_names)
    print(f"    formula-only joins whose name is in PubChem's full list: "
          f"{full['name_found_in_full_list']} of {full['formula_only_joins']}")

    log.update({"genbank": {k: v for k, v in genbank.items()
                            if k not in ("gene_records_left_by_phase_4", "removals_left_by_phase_4")},
                "names": names_found, "full_list": full})
    (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    (out_dir / "capture_bundle.json").write_text(json.dumps(
        {"captured_with": log["captured_with"], "genbank": genbank, "names": names_found,
         "full_list": full, "pubchem_properties": properties,
         "pubchem_name_counts": {c: len(n) for c, n in names.items()},
         "ncbi_gene": ncbi, "cds_of_kept_entries": kept}, indent=1) + "\n", encoding="utf-8")
    print(f"\nDone. The one file to share: {relative_to_repo(out_dir / 'capture_bundle.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
