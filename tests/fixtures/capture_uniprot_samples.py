"""
MicrobeGraph, look at MIBiG's gene records and capture real UniProt answers (Phase 3).

WHY THIS EXISTS
    Phase 3 adds the enzymes (proteins) each gene cluster encodes. Before any
    of that code is written, two things have to be seen with real eyes rather
    than read about:

      1. what MIBiG actually records about each gene: which identifier it
         uses for the protein, which job it gives the gene, and what evidence
         stands behind that job;
      2. what UniProt actually sends back when it is asked about those
         proteins, including when it doesn't know one.

    Phase 2's test records were cut from real answers captured the same way
    (tests/fixtures/capture_samples.py), after Phase 1 had twice been caught
    out by records written from documentation. This script does the same for
    Phase 3.

WHAT IT DOES
    Part 1 (offline): reads the MIBiG archive already in your evidence locker
    and counts what the gene records look like: how many there are, which
    identifier patterns they use, which jobs ("functions") and evidence
    methods appear. Nothing is sent anywhere in this part.

    Part 2 (about 12 requests, one or two a second): asks UniProt a few small
    questions and saves every answer exactly as it arrived:
        which identifier types the ID mapping service accepts,
        which fields a UniProt answer can contain,
        whether UniProt lists MIBiG among its cross-referenced databases,
        one small ID mapping job (about 30 protein identifiers, one of them
        made up on purpose), followed from start to finish,
        one small search, to see what a normal answer's headers look like.
    No key is needed and none is used.

USAGE (from the project folder, with .venv active, after Phase 1)
    python tests/fixtures/capture_uniprot_samples.py

    Everything lands in data/samples/<today>/uniprot/, which never goes to
    GitHub. capture_bundle.json holds the survey and every answer in one file
    (long answers cut to their first 500 lines, each with the fingerprint of
    exactly what it holds), so it is the one file to share.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import requests

from microbegraph.paths import DATA_DIR, RAW_DIR, relative_to_repo
from microbegraph.sources.base import TIMEOUT, USER_AGENT, iter_tar_json
from microbegraph.sources.mibig import FILENAME

UNIPROT = "https://rest.uniprot.org"

# Identifier patterns, as far as I know them, to be checked against the real data:
#   INSDC protein_id (EMBL, GenBank, DDBJ): three letters, five or seven digits, version
#   RefSeq protein: WP_, NP_, YP_ or XP_, digits, version
#   UniProtKB accession: the official pattern from UniProt's help pages
PATTERNS = {
    "insdc_protein": re.compile(r"^[A-Z]{3}\d{5}(\d{2})?\.\d+$"),
    "refseq_protein": re.compile(r"^(WP|NP|YP|XP)_\d+\.\d+$"),
    "uniprot_accession": re.compile(
        r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$"),
}

SURFACTIN = "BGC0000433"      # the worked example; all its genes are always included
MADE_UP_ID = "XYZ99999.99"    # shaped like a protein identifier, but no such protein exists
SPREAD = 20                   # INSDC identifiers picked evenly from the rest
RETURN_FIELDS = ("accession,id,reviewed,protein_name,gene_names,organism_name,organism_id,"
                 "length,ec,cc_function,protein_existence,annotation_score")
PAUSE_SECONDS = 1.0
FIRST_LINES = 500
KEEP_HEADERS = ("Content-Type", "Content-Length", "Date", "Location", "Link", "Retry-After",
                "X-UniProt-Release", "X-UniProt-Release-Date", "X-Total-Results",
                "x-uniprot-release", "x-uniprot-release-date", "x-total-results")


def names_in(answer: bytes) -> list[dict[str, Any]]:
    """Every dictionary with a "name" key anywhere in a JSON answer (empty if not JSON)."""
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("name"), str):
                found.append(value)
            for inner in value.values():
                walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)
    try:
        walk(json.loads(answer))
    except ValueError:
        pass
    return found


def from_name(fields_answer: bytes, words: tuple[str, ...], default: str) -> str:
    """
    The ID mapping name of an identifier type, read from UniProt's own list
    rather than typed from memory: the first "from" entry whose name and
    display name together contain every word. Falls back to `default`.
    """
    for item in names_in(fields_answer):
        label = f"{item.get('name', '')} {item.get('displayName', '')}".lower()
        if item.get("from") is not False and all(w.lower() in label for w in words):
            return str(item["name"])
    return default


def kind_of(identifier: str) -> str:
    for name, pattern in PATTERNS.items():
        if pattern.match(identifier):
            return name
    return "other"


def spread(values: list[str], count: int) -> list[str]:
    """`count` values spread evenly through a sorted list, first and last included."""
    if len(values) <= count:
        return values
    step = (len(values) - 1) / (count - 1)
    return [values[round(i * step)] for i in range(count)]


# ======================================================================
# Part 1: what MIBiG records about genes (offline)
# ======================================================================
def survey(archive: Any) -> tuple[dict[str, Any], dict[str, list[str]], dict[str, Any]]:
    entries = Counter()
    kinds: Counter[str] = Counter()
    gene_keys: Counter[str] = Counter()
    annotation_keys: Counter[str] = Counter()
    function_names: Counter[str] = Counter()
    function_shapes: Counter[str] = Counter()
    evidence_methods: Counter[str] = Counter()
    compounds_per_entry: Counter[int] = Counter()
    genes_per_entry: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    ids_by_kind: dict[str, set[str]] = {}
    seen_in: dict[str, set[str]] = {}
    gene_sections: dict[str, Any] = {}

    for _, payload in iter_tar_json(archive):
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            entries["unreadable"] += 1
            continue
        if not isinstance(raw, dict) or raw.get("status") != "active":
            entries["not_active"] += 1
            continue
        entries["active"] += 1
        accession = str(raw.get("accession", "?"))
        compounds_per_entry[len(raw.get("compounds") or [])] += 1
        genes = raw.get("genes")
        if not isinstance(genes, dict):
            entries["no_genes_section"] += 1
            genes_per_entry["0"] += 1
            continue
        gene_keys.update(genes.keys())
        annotations = genes.get("annotations") or []
        n = len(annotations)
        genes_per_entry["0" if n == 0 else "1-5" if n <= 5 else "6-20" if n <= 20
                        else "21-50" if n <= 50 else "over 50"] += 1
        if accession == SURFACTIN:
            gene_sections[accession] = genes
        for annotation in annotations:
            if not isinstance(annotation, dict):
                kinds["annotation_not_a_dict"] += 1
                continue
            annotation_keys.update(annotation.keys())
            identifier = str(annotation.get("id", "")).strip()
            kind = kind_of(identifier) if identifier else "missing"
            kinds[kind] += 1
            examples.setdefault(kind, [])
            if len(examples[kind]) < 8:
                examples[kind].append(f"{accession}: {identifier}")
            ids_by_kind.setdefault(kind, set()).add(identifier)
            seen_in.setdefault(identifier, set()).add(accession)
            for item in annotation.get("functions") or []:
                if not isinstance(item, dict):
                    function_shapes[type(item).__name__] += 1
                    continue
                function = item.get("function")
                function_shapes[type(function).__name__] += 1
                name = function.get("name") if isinstance(function, dict) else function
                function_names[str(name)] += 1
                for evidence in item.get("evidence") or []:
                    method = evidence.get("method") if isinstance(evidence, dict) else evidence
                    evidence_methods[str(method)] += 1
        # Keep the full gene section of a few entries that use other identifier styles.
        if len(gene_sections) < 6 and any(
                kind_of(str(a.get("id", ""))) != "insdc_protein"
                for a in annotations if isinstance(a, dict)):
            gene_sections.setdefault(accession, genes)

    shared = {i: sorted(a) for i, a in seen_in.items() if len(a) > 1}
    facts = {
        "entries": dict(entries),
        "annotations_by_identifier_kind": dict(kinds),
        "distinct_identifiers_by_kind": {k: len(v) for k, v in ids_by_kind.items()},
        "identifier_examples": examples,
        "identifiers_in_more_than_one_entry": len(shared),
        "shared_identifier_examples": dict(list(shared.items())[:8]),
        "keys_in_genes_section": dict(gene_keys),
        "keys_in_one_annotation": dict(annotation_keys),
        "function_names": dict(function_names.most_common()),
        "function_value_types": dict(function_shapes),
        "evidence_methods": dict(evidence_methods.most_common()),
        "compounds_per_active_entry": {str(k): v for k, v in sorted(compounds_per_entry.items())},
        "annotations_per_active_entry": dict(genes_per_entry),
    }
    return facts, {k: sorted(v) for k, v in ids_by_kind.items()}, gene_sections


def pick_identifiers(ids_by_kind: dict[str, list[str]],
                     gene_sections: dict[str, Any]) -> tuple[list[str], list[str]]:
    surfactin = [str(a.get("id")) for a in
                 (gene_sections.get(SURFACTIN) or {}).get("annotations", [])
                 if isinstance(a, dict) and a.get("id")]
    insdc = [i for i in ids_by_kind.get("insdc_protein", []) if i not in surfactin]
    chosen_insdc = [i for i in surfactin if kind_of(i) == "insdc_protein"]
    chosen_insdc += spread(insdc, SPREAD) + [MADE_UP_ID]
    chosen_refseq = spread(ids_by_kind.get("refseq_protein", []), 5)
    return chosen_insdc, chosen_refseq


# ======================================================================
# Part 2: real answers from UniProt
# ======================================================================
def ask(session: requests.Session, name: str, method: str, url: str,
        params: dict[str, str] | None = None, data: dict[str, str] | None = None,
        follow: bool = True) -> tuple[bytes, dict[str, Any]]:
    record: dict[str, Any] = {
        "name": name, "method": method, "url": url, "params": params or {},
        "sent": {k: (v if len(v) < 300 else v[:300] + "...") for k, v in (data or {}).items()},
        "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        response = session.request(method, url, params=params, data=data, timeout=TIMEOUT,
                                   allow_redirects=follow)
    except requests.RequestException as error:
        record["error"] = f"{type(error).__name__}: {error}"
        return b"", record
    body = response.content
    record.update({
        "final_url": response.url, "status": response.status_code,
        "headers": {k: v for k, v in response.headers.items() if k in KEEP_HEADERS},
        "bytes": len(body), "lines": body.count(b"\n"),
        "sha256": hashlib.sha256(body).hexdigest(),
    })
    return body, record


def main() -> int:
    archive = RAW_DIR / "mibig" / FILENAME
    if not archive.exists():
        print(f"{relative_to_repo(archive)} is missing. Run Phase 1 first:")
        print("    python -m microbegraph.fetch --source mibig")
        return 1

    print(f"Part 1: reading the gene records in {relative_to_repo(archive)} (offline)")
    facts, ids_by_kind, gene_sections = survey(archive)
    for key in ("entries", "annotations_by_identifier_kind", "distinct_identifiers_by_kind",
                "identifiers_in_more_than_one_entry", "compounds_per_active_entry"):
        print(f"    {key:<36} {facts[key]}")
    print(f"    {'function_names (top 8)':<36} "
          f"{dict(list(facts['function_names'].items())[:8])}")
    insdc, refseq = pick_identifiers(ids_by_kind, gene_sections)
    print(f"    identifiers chosen for UniProt     {len(insdc)} INSDC (one made up), "
          f"{len(refseq)} RefSeq")

    out_dir = DATA_DIR / "samples" / datetime.now(timezone.utc).strftime("%Y-%m-%d") / "uniprot"
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    log: dict[str, Any] = {"captured_with": "tests/fixtures/capture_uniprot_samples.py",
                           "survey": facts, "chosen": {"insdc": insdc, "refseq": refseq},
                           "requests": []}
    bundle: dict[str, Any] = {}

    def save(name: str, body: bytes, record: dict[str, Any]) -> None:
        log["requests"].append(record)
        if "error" in record:
            print(f"    {name:<36} FAILED, {record['error'][:90]}")
            return
        (out_dir / name).write_bytes(body)
        lines = body.splitlines(keepends=True)
        kept = b"".join(lines[:FIRST_LINES]) if len(lines) > FIRST_LINES else body
        bundle[name] = {"status": record["status"], "headers": record["headers"],
                        "complete": kept == body, "sha256": hashlib.sha256(kept).hexdigest(),
                        "text": kept.decode("utf-8", errors="replace")}
        print(f"    {name:<36} HTTP {record['status']}, {record['bytes']:,} bytes")
        time.sleep(PAUSE_SECONDS)

    print(f"\nPart 2: asking UniProt (about one request a second), saving to "
          f"{relative_to_repo(out_dir)}/")
    id_fields, record = ask(session, "idmapping_fields.json", "GET",
                            f"{UNIPROT}/configure/idmapping/fields")
    save("idmapping_fields.json", id_fields, record)
    result_fields, record = ask(session, "uniprotkb_result_fields.json", "GET",
                                f"{UNIPROT}/configure/uniprotkb/result-fields")
    save("uniprotkb_result_fields.json", result_fields, record)
    body, record = ask(session, "database_mibig.json", "GET", f"{UNIPROT}/database/search",
                       params={"query": "mibig", "format": "json"})
    save("database_mibig.json", body, record)

    # Use only field and identifier-type names that UniProt's own lists contain.
    known = {item["name"] for item in names_in(result_fields)}
    fields = [f for f in RETURN_FIELDS.split(",") if not known or f in known]
    log["return_fields"] = {"asked_for": fields,
                            "not_offered": [f for f in RETURN_FIELDS.split(",") if f not in fields]}
    insdc_from = from_name(id_fields, ("embl", "cds"), "EMBL-GenBank-DDBJ_CDS")
    refseq_from = from_name(id_fields, ("refseq", "protein"), "RefSeq_Protein")
    log["from_names"] = {"insdc": insdc_from, "refseq": refseq_from}
    print(f"    using identifier types {insdc_from!r} and {refseq_from!r}; "
          f"{len(fields)} fields")

    jobs = [("insdc", insdc_from, insdc)]
    if refseq:
        jobs.append(("refseq", refseq_from, refseq))
    for label, from_db, ids in jobs:
        name = f"idmapping_{label}_run.json"
        body, record = ask(session, name, "POST", f"{UNIPROT}/idmapping/run",
                           data={"from": from_db, "to": "UniProtKB", "ids": ",".join(ids)})
        save(name, body, record)
        try:
            job_id = json.loads(body)["jobId"]
        except (ValueError, KeyError):
            print(f"    no job number in the answer to {name}; skipping the rest of this job")
            continue
        # Ask for the status without following redirects, to see exactly what
        # UniProt sends while the job runs and once it has finished.
        for attempt in range(1, 31):
            body, record = ask(session, f"idmapping_{label}_status.json", "GET",
                               f"{UNIPROT}/idmapping/status/{job_id}", follow=False)
            record["attempt"] = attempt
            running = b'"RUNNING"' in body or b'"NEW"' in body
            if not running or attempt == 30:
                save(f"idmapping_{label}_status.json", body, record)
                break
            log["requests"].append(record)
            time.sleep(2)
        save(f"idmapping_{label}_details.json",
             *ask(session, f"idmapping_{label}_details.json", "GET",
                  f"{UNIPROT}/idmapping/details/{job_id}"))
        results = f"{UNIPROT}/idmapping/uniprotkb/results/stream/{job_id}"
        save(f"idmapping_{label}_results.tsv",
             *ask(session, f"idmapping_{label}_results.tsv", "GET", results,
                  params={"format": "tsv", "fields": ",".join(fields)}))
        save(f"idmapping_{label}_results.json",
             *ask(session, f"idmapping_{label}_results.json", "GET", results,
                  params={"format": "json", "fields": ",".join(fields)}))

    save("search_srfaa.tsv",
         *ask(session, "search_srfaa.tsv", "GET", f"{UNIPROT}/uniprotkb/search",
              params={"query": "gene:srfAA AND reviewed:true", "format": "tsv",
                      "fields": ",".join(fields), "size": "5"}))

    (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    (out_dir / "capture_bundle.json").write_text(
        json.dumps({"captured_with": log["captured_with"], "survey": facts,
                    "chosen": log["chosen"], "from_names": log["from_names"],
                    "return_fields": log["return_fields"], "gene_sections": gene_sections,
                    "answers": bundle}, indent=1) + "\n", encoding="utf-8")
    print(f"\nDone. The one file to share: {relative_to_repo(out_dir / 'capture_bundle.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
