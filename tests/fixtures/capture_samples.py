"""
MicrobeGraph, capture real sample answers from the Phase 2 sources.

WHY THIS EXISTS
    Phase 1 taught this project the same lesson twice. Test records written
    by hand from documentation drift away from what a server really sends:
    the MIBiG archive turned out not to be gzip-compressed, and activity
    names arrived in a second style that no documentation had mentioned.
    Both times every test had passed.

    So the Phase 2 test records are cut from real answers, and this script
    is how those answers were captured. Run it again whenever a source
    changes its format, and the tests can be refreshed from the new answers.

WHAT IT DOES
    It reads the MIBiG tables you built in Phase 1 to pick a handful of real
    identifiers, then asks each Phase 2 source a few small questions and
    saves every answer exactly as it arrived, byte for byte:

        PubChem          properties and synonyms of five compounds, a batch
                         that mixes real and missing identifiers, one missing
                         identifier on its own, and a well-known compound
        NCBI Taxonomy    facts about the database, five organisms' family
                         trees, the plant pathogens used by the curated
                         bridge, and identifiers that were merged or deleted
        KEGG             update dates, the pathway list, the links between
                         compounds and pathways, and the pathway categories

    That's about 15 requests, one per second, which is well inside every
    source's limits. No API key is used or needed.

    It's like photographing a few real parcels at the sorting office
    before designing the shelves: the shelves then fit the parcels that
    actually arrive, not the ones in the brochure.

USAGE (from the project folder, with .venv active, after Phase 1)
    python tests/fixtures/capture_samples.py

    The answers land in data/samples/<today>/. data/ never goes to GitHub,
    so nothing captured here can be published by accident.
    capture_log.json, next to them, records what was asked, when, and what
    came back (status, size, fingerprint). capture_bundle.json holds every
    answer in one file, which is easier to share than fourteen: the biggest
    answer is cut to its first 500 lines there, and each entry keeps the
    fingerprint of exactly what it holds.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from microbegraph.paths import DATA_DIR, STAGING_DIR, relative_to_repo
from microbegraph.sources.base import TIMEOUT, USER_AGENT

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
KEGG = "https://rest.kegg.jp"

# The properties MicrobeGraph plans to read from PubChem. SMILES and
# ConnectivitySMILES are the names PubChem has used since 2025.
PUBCHEM_PROPERTIES = ("Title,MolecularFormula,MolecularWeight,MonoisotopicMass,"
                      "IUPACName,InChIKey,SMILES,ConnectivitySMILES")

# A compound identifier far beyond any real one, to see what "not found" looks like.
MISSING_CID = "999999999"

# Caffeine: a compound everyone has heard of, used to see which outside
# identifiers (KEGG, ChEBI) PubChem lists among its synonyms.
CAFFEINE_CID = "2519"

# The surfactin cluster's organism from Phase 1, always included.
FZB42_TAXID = "326423"

# The plant pathogens the curated bridge refers to. Capturing them now
# checks each number against NCBI before any bridge row relies on it.
#   40559 Botrytis cinerea, 5518 Fusarium graminearum, 36779 Gaeumannomyces
#   tritici, 456999 Rhizoctonia solani, 62727 Podosphaera fusca,
#   2052682 Globisporangium ultimum (Pythium ultimum)
PATHOGEN_TAXIDS = ["40559", "5518", "36779", "456999", "62727", "2052682"]

# 2056260 was merged into 435890, and 3897929 was deleted (both reported
# publicly in 2026). They show how NCBI answers for retired numbers.
RETIRED_TAXIDS = ["2056260", "3897929"]

PAUSE_SECONDS = 1.0           # between requests: polite to every source
FIRST_LINES = 500             # length of the exact excerpt kept of a big answer
BIG_ANSWER_BYTES = 200_000    # answers bigger than this also get an excerpt


def spread(values: list[str], count: int) -> list[str]:
    """Pick `count` values spread evenly through a sorted list (first and last included)."""
    if len(values) <= count:
        return values
    step = (len(values) - 1) / (count - 1)
    return [values[round(i * step)] for i in range(count)]


def pick_identifiers(nodes_path: Path) -> tuple[list[str], list[str], dict[str, int]]:
    """Real PubChem compound numbers and NCBI organism numbers from the MIBiG tables."""
    cids: set[str] = set()
    taxids: set[str] = set()
    compounds = 0
    with nodes_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["node_type"] == "Compound":
                compounds += 1
                cid = json.loads(row["properties"] or "{}").get("pubchem_cid")
                if cid:
                    cids.add(str(cid))
            elif row["node_type"] == "Organism" and row["node_id"].startswith("ncbitaxon:"):
                taxids.add(row["node_id"].split(":", 1)[1])
    by_number = sorted(cids, key=int)
    organisms = sorted(taxids - {FZB42_TAXID}, key=int)
    facts = {"compounds": compounds, "compounds_with_pubchem_cid": len(cids),
             "organisms_with_ncbi_taxid": len(taxids)}
    return spread(by_number, 5), [FZB42_TAXID] + spread(organisms, 4), facts


def plan_requests(cids: list[str], taxids: list[str]) -> list[dict]:
    """Every question this script asks, in order. Nothing secret is ever sent."""
    tool = {"tool": "microbegraph"}
    return [
        {"file": "pubchem_properties.json", "method": "POST",
         "url": f"{PUBCHEM}/compound/cid/property/{PUBCHEM_PROPERTIES}/JSON",
         "data": {"cid": ",".join(cids)}},
        {"file": "pubchem_synonyms.json", "method": "POST",
         "url": f"{PUBCHEM}/compound/cid/synonyms/JSON", "data": {"cid": ",".join(cids)}},
        {"file": "pubchem_properties_mixed.json", "method": "POST",
         "url": f"{PUBCHEM}/compound/cid/property/{PUBCHEM_PROPERTIES}/JSON",
         "data": {"cid": ",".join(cids[:2] + [MISSING_CID])}},
        {"file": "pubchem_missing.json", "method": "GET",
         "url": f"{PUBCHEM}/compound/cid/{MISSING_CID}/property/Title/JSON"},
        {"file": "pubchem_synonyms_caffeine.json", "method": "GET",
         "url": f"{PUBCHEM}/compound/cid/{CAFFEINE_CID}/synonyms/JSON"},
        {"file": "ncbi_einfo.json", "method": "GET", "url": f"{EUTILS}/einfo.fcgi",
         "params": {"db": "taxonomy", "retmode": "json", **tool}},
        {"file": "ncbi_efetch_organisms.xml", "method": "POST", "url": f"{EUTILS}/efetch.fcgi",
         "data": {"db": "taxonomy", "id": ",".join(taxids), "retmode": "xml", **tool}},
        {"file": "ncbi_efetch_pathogens.xml", "method": "POST", "url": f"{EUTILS}/efetch.fcgi",
         "data": {"db": "taxonomy", "id": ",".join(PATHOGEN_TAXIDS), "retmode": "xml", **tool}},
        {"file": "ncbi_efetch_retired.xml", "method": "POST", "url": f"{EUTILS}/efetch.fcgi",
         "data": {"db": "taxonomy", "id": ",".join(RETIRED_TAXIDS + [FZB42_TAXID]),
                  "retmode": "xml", **tool}},
        {"file": "kegg_info_kegg.txt", "method": "GET", "url": f"{KEGG}/info/kegg"},
        {"file": "kegg_info_pathway.txt", "method": "GET", "url": f"{KEGG}/info/pathway"},
        {"file": "kegg_list_pathway.txt", "method": "GET", "url": f"{KEGG}/list/pathway"},
        {"file": "kegg_link_pathway_compound.txt", "method": "GET",
         "url": f"{KEGG}/link/pathway/compound"},
        {"file": "kegg_br08901.txt", "method": "GET", "url": f"{KEGG}/get/br:br08901"},
    ]


def ask(session: requests.Session, request: dict) -> tuple[bytes, dict]:
    """Send one request; return the raw answer and a record of what happened."""
    record = {"file": request["file"], "method": request["method"], "url": request["url"],
              "sent": request.get("data") or request.get("params") or {},
              "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        response = session.request(request["method"], request["url"],
                                   params=request.get("params"), data=request.get("data"),
                                   timeout=TIMEOUT)
    except requests.RequestException as error:
        record["error"] = f"{type(error).__name__}: {error}"
        return b"", record
    body = response.content
    keep = ("Content-Type", "Content-Length", "Date", "X-Throttling-Control", "Retry-After")
    record.update({
        "status": response.status_code,
        "headers": {k: v for k, v in response.headers.items() if k in keep},
        "bytes": len(body),
        "lines": body.count(b"\n"),
        "sha256": hashlib.sha256(body).hexdigest(),
    })
    return body, record


def main() -> int:
    nodes_path = STAGING_DIR / "mibig_nodes.csv"
    if not nodes_path.exists():
        print(f"{relative_to_repo(nodes_path)} is missing. Run Phase 1 first:")
        print("    python -m microbegraph.fetch --source mibig")
        return 1

    cids, taxids, facts = pick_identifiers(nodes_path)
    print("From your MIBiG tables:")
    for key, value in facts.items():
        print(f"    {key:<28} {value}")
    print(f"    compounds chosen             {', '.join(cids)}")
    print(f"    organisms chosen             {', '.join(taxids)}")

    out_dir = DATA_DIR / "samples" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    log = {"captured_with": "tests/fixtures/capture_samples.py", "mibig_facts": facts,
           "requests": []}
    bundle: dict[str, dict] = {}
    print(f"\nAsking the sources (one request per second), saving to {relative_to_repo(out_dir)}/")
    for request in plan_requests(cids, taxids):
        body, record = ask(session, request)
        if "error" not in record:
            (out_dir / request["file"]).write_bytes(body)
        kept, complete = body, True
        if record.get("bytes", 0) > BIG_ANSWER_BYTES:
            # A big answer also gets an exact excerpt: the same bytes, first lines only.
            kept, complete = b"".join(body.splitlines(keepends=True)[:FIRST_LINES]), False
            name = Path(request["file"])
            excerpt_name = f"{name.stem}.first{FIRST_LINES}{name.suffix}"
            (out_dir / excerpt_name).write_bytes(kept)
            record["excerpt"] = excerpt_name
        if "error" not in record:
            bundle[request["file"]] = {"status": record["status"], "complete": complete,
                                       "sha256": hashlib.sha256(kept).hexdigest(),
                                       "text": kept.decode("utf-8")}
        log["requests"].append(record)
        if "error" in record:
            outcome = "FAILED, " + record["error"][:90] + "..."
        else:
            outcome = f"HTTP {record['status']}, {record['bytes']:,} bytes"
        print(f"    {request['file']:<36} {outcome}")
        time.sleep(PAUSE_SECONDS)

    (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    (out_dir / "capture_bundle.json").write_text(
        json.dumps({"captured_with": log["captured_with"], "answers": bundle}, indent=1) + "\n",
        encoding="utf-8")
    print(f"\nDone. The log is {relative_to_repo(out_dir / 'capture_log.json')}")
    print(f"Every answer, in one file: {relative_to_repo(out_dir / 'capture_bundle.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
