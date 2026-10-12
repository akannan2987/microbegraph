"""
MicrobeGraph, download MIBiG's protein file and look inside it (Phase 3b).

WHY THIS EXISTS
    Phase 3 gave proteins only to the 452 MIBiG entries that list their genes
    in the JSON release. MIBiG also publishes a file holding every protein of
    every cluster, mibig_prot_seqs_4.0.fasta, on its own download server.
    Before any code reads that file, I want to see what it really holds:

      1. how the line that starts each protein (its header) names the
         cluster and the protein, and whether every header follows one shape;
      2. how many proteins and clusters it covers, and how its proteins line
         up with the gene records Phase 3 already reads;
      3. whether MIBiG's corrections to a cluster's gene list ("to_add" and
         "to_delete" in the JSON) are already applied in the file.

    Phases 2 and 3 started the same way (capture_samples.py and
    capture_uniprot_samples.py): look at real data first, then write code.

WHAT IT DOES
    Part 1 (three requests): asks the download server about the file without
    downloading it (size and date), saves the folder listing the server
    shows (to see whether a checksum is published next to the file), and
    then downloads the file once, about 30 MB.

    Part 2 (offline): reads the downloaded file and the MIBiG archive already
    in your evidence locker, and counts everything listed above. Nothing is
    sent anywhere in this part.

USAGE (from the project folder, with .venv active, after Phase 1)
    python tests/fixtures/capture_mibig_protein_samples.py

    Everything lands in data/samples/<today>/mibig_proteins/, which never goes
    to GitHub. capture_bundle.json holds the survey, the server's answers and
    the full records of a few chosen clusters in one file, so it is the one
    file to share.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import DATA_DIR, RAW_DIR, relative_to_repo
from microbegraph.sources.base import TIMEOUT, USER_AGENT, iter_tar_json
from microbegraph.sources.mibig import FILENAME as JSON_ARCHIVE

SERVER = "https://dl.secondarymetabolites.org/mibig/"
PROTEIN_FILE = "mibig_prot_seqs_4.0.fasta"

SURFACTIN = "BGC0000433"     # the worked example in every guide
FIRST_HEADERS = 200          # headers kept from the top of the file
EXAMPLES = 6                 # examples kept for each kind of value

# What a value in a header might be, as far as I know the patterns. The
# survey counts which ones really turn up, and where.
KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("empty", re.compile(r"^$")),
    ("mibig_accession", re.compile(r"^BGC\d{7}(\.\d+)?$")),
    ("insdc_protein", re.compile(r"^[A-Z]{3}\d{5}(\d{2})?\.\d+$")),
    ("refseq_protein", re.compile(r"^(WP|NP|YP|XP)_\d+\.\d+$")),
    ("uniprot_accession", re.compile(
        r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2})$")),
    ("location", re.compile(r"^[<>]?\d+[-.]+[<>]?\d+$")),
    ("strand", re.compile(r"^([+-]|-?1)$")),
    ("short_code", re.compile(r"^[a-z]\d+$")),
    ("number", re.compile(r"^\d+$")),
)
ACCESSION_ANYWHERE = re.compile(r"BGC\d{7}")


def kind_of(value: str) -> str:
    for name, pattern in KINDS:
        if pattern.match(value):
            return name
    return "has_spaces" if " " in value else "other"


# ======================================================================
# Part 1: what the server says, and the file itself
# ======================================================================
def ask(session: requests.Session, method: str, url: str) -> tuple[bytes, dict[str, Any]]:
    """One request, recorded: status, the headers worth keeping, size and fingerprint."""
    record: dict[str, Any] = {"method": method, "url": url,
                              "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        response = session.request(method, url, timeout=TIMEOUT)
    except requests.RequestException as error:
        record["error"] = f"{type(error).__name__}: {error}"
        return b"", record
    body = response.content
    keep = ("Content-Type", "Content-Length", "Content-Encoding", "Last-Modified", "ETag",
            "Date", "Server", "Accept-Ranges")
    record.update({"status": response.status_code,
                   "headers": {k: v for k, v in response.headers.items() if k in keep},
                   "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    return body, record


def download(session: requests.Session, url: str, target: Path) -> dict[str, Any]:
    """Stream the file to disk, fingerprinting it on the way (MD5 and SHA-256)."""
    record: dict[str, Any] = {"method": "GET", "url": url,
                              "asked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    md5, sha256, n_bytes = hashlib.md5(), hashlib.sha256(), 0
    part = target.with_name(target.name + ".part")
    try:
        with session.get(url, stream=True, timeout=TIMEOUT) as response:
            record["status"] = response.status_code
            record["headers"] = {k: v for k, v in response.headers.items()
                                 if k in ("Content-Type", "Content-Length", "Content-Encoding",
                                          "Last-Modified", "ETag")}
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


# ======================================================================
# Part 2: what the file holds (offline)
# ======================================================================
def read_fasta(path: Path) -> tuple[list[tuple[str, str]], dict[str, Any]]:
    """
    Every (header, sequence) pair, plus facts about the layout: line widths,
    blank lines, text before the first header. Read as bytes first, so an
    odd character is counted instead of stopping the survey.
    """
    raw = path.read_bytes()
    layout: dict[str, Any] = {
        "bytes": len(raw),
        "line_endings": {"crlf": raw.count(b"\r\n"), "lf_only": raw.count(b"\n") - raw.count(b"\r\n")},
        "ends_with_newline": raw.endswith(b"\n"),
        "non_ascii_bytes": sum(1 for b in raw if b > 127),
    }
    text = raw.decode("utf-8", errors="replace")
    records: list[tuple[str, str]] = []
    header: str | None = None
    pieces: list[str] = []
    widths: Counter[int] = Counter()
    blank_lines = 0
    before_first = 0
    for line in text.splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(pieces)))
            header, pieces = line[1:], []
        elif not line.strip():
            blank_lines += 1
        elif header is None:
            before_first += 1
        else:
            pieces.append(line.strip())
            widths[len(line.strip())] += 1
    if header is not None:
        records.append((header, "".join(pieces)))
    layout.update({"blank_lines": blank_lines, "lines_before_first_header": before_first,
                   "most_common_sequence_line_widths": dict(widths.most_common(5))})
    return records, layout


def survey_fasta(records: list[tuple[str, str]]) -> tuple[dict[str, Any], dict[str, list[tuple[str, str]]]]:
    """Count the header shapes and the sequences, and group the records by cluster."""
    field_counts: Counter[int] = Counter()
    by_position: dict[int, Counter[str]] = {}
    examples: dict[str, list[str]] = {}
    lengths: list[int] = []
    letters: Counter[str] = Counter()
    by_entry: dict[str, list[tuple[str, str]]] = {}
    no_accession: list[str] = []
    headers_seen: Counter[str] = Counter()
    ends_with_stop = empty = whitespace_in_header = 0

    for header, sequence in records:
        headers_seen[header] += 1
        fields = header.split("|")
        field_counts[len(fields)] += 1
        if re.search(r"\s", header):
            whitespace_in_header += 1
        for position, value in enumerate(fields):
            kind = kind_of(value.strip())
            by_position.setdefault(position, Counter())[kind] += 1
            key = f"field {position}: {kind}"
            examples.setdefault(key, [])
            if len(examples[key]) < EXAMPLES:
                examples[key].append(value)
        match = ACCESSION_ANYWHERE.search(header)
        if match:
            by_entry.setdefault(match.group(0), []).append((header, sequence))
        elif len(no_accession) < EXAMPLES:
            no_accession.append(header)
        lengths.append(len(sequence))
        letters.update(sequence)
        if sequence.endswith("*"):
            ends_with_stop += 1
        if not sequence:
            empty += 1

    sizes = Counter(len(v) for v in by_entry.values())
    buckets: Counter[str] = Counter()
    for n, how_many in sizes.items():
        bucket = ("1" if n == 1 else "2-5" if n <= 5 else "6-20" if n <= 20
                  else "21-50" if n <= 50 else "51-100" if n <= 100 else "over 100")
        buckets[bucket] += how_many
    facts = {
        "records": len(records),
        "fields_per_header": dict(sorted(field_counts.items())),
        "kinds_by_field_position": {str(p): dict(c.most_common()) for p, c in sorted(by_position.items())},
        "examples_by_field_and_kind": examples,
        "headers_with_spaces_or_tabs": whitespace_in_header,
        "headers_repeated": sum(1 for n in headers_seen.values() if n > 1),
        "headers_without_a_bgc_accession": sum(1 for h, _ in records if not ACCESSION_ANYWHERE.search(h)),
        "examples_without_a_bgc_accession": no_accession,
        "clusters_in_file": len(by_entry),
        "proteins_per_cluster": dict(buckets),
        "largest_clusters": dict(sorted(((k, len(v)) for k, v in by_entry.items()),
                                        key=lambda kv: -kv[1])[:5]),
        "sequence_length": {"min": min(lengths, default=0), "median": statistics.median(lengths or [0]),
                            "max": max(lengths, default=0)},
        "sequences_empty": empty,
        "sequences_ending_in_star": ends_with_stop,
        "letters_in_sequences": dict(letters.most_common()),
    }
    return facts, by_entry


def entry_facts(archive: Path) -> dict[str, dict[str, Any]]:
    """For every entry in the MIBiG archive: status, version, loci, gene ids, to_add and to_delete."""
    found: dict[str, dict[str, Any]] = {}
    for _, payload in iter_tar_json(archive):
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict) or "accession" not in raw:
            continue
        genes = raw.get("genes") if isinstance(raw.get("genes"), dict) else {}
        found[str(raw["accession"])] = {
            "status": raw.get("status"),
            "version": raw.get("version"),
            "loci": [str(locus.get("accession")) for locus in raw.get("loci") or []
                     if isinstance(locus, dict)],
            "gene_ids": [str(g.get("id") or "") for g in genes.get("annotations") or []
                         if isinstance(g, dict)],
            "to_add": [g for g in genes.get("to_add") or [] if isinstance(g, dict)],
            "to_delete": [g for g in genes.get("to_delete") or [] if isinstance(g, dict)],
            "genes_keys": sorted(genes.keys()),
        }
    return found


def compare(by_entry: dict[str, list[tuple[str, str]]],
            entries: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Line the file up against the archive. Returns the facts and a few clusters worth keeping whole."""
    active = {a for a, e in entries.items() if e["status"] == "active"}
    in_file = set(by_entry)
    statuses = Counter(str(entries.get(a, {}).get("status", "not in the archive")) for a in in_file)

    def values_in(accession: str) -> set[str]:
        return {f.strip() for header, _ in by_entry.get(accession, []) for f in header.split("|")}

    gene_found = gene_missing = 0
    missing_examples: list[str] = []
    count_match = Counter()
    for accession in sorted(active & in_file):
        ids = [i for i in entries[accession]["gene_ids"] if i]
        if not ids:
            continue
        values = values_in(accession)
        for identifier in ids:
            if identifier in values:
                gene_found += 1
            else:
                gene_missing += 1
                if len(missing_examples) < EXAMPLES * 2:
                    missing_examples.append(f"{accession}: {identifier}")
        n_file, n_genes = len(by_entry[accession]), len(ids)
        count_match["same" if n_file == n_genes else "file has more" if n_file > n_genes
                    else "file has fewer"] += 1

    add_keys: Counter[str] = Counter()
    delete_keys: Counter[str] = Counter()
    add_in_file = add_not_in_file = delete_in_file = delete_not_in_file = 0
    add_examples: list[dict[str, Any]] = []
    delete_examples: list[dict[str, Any]] = []
    keep: list[str] = [SURFACTIN]
    for accession in sorted(active):
        entry = entries[accession]
        values = values_in(accession)
        for gene in entry["to_add"]:
            add_keys.update(gene.keys())
            identifier = str(gene.get("id") or gene.get("protein_id") or "")
            if identifier and identifier in values:
                add_in_file += 1
            else:
                add_not_in_file += 1
            if len(add_examples) < 3:
                add_examples.append({"entry": accession, **{k: (v[:80] + "..." if isinstance(v, str)
                                                                and len(v) > 80 else v)
                                                            for k, v in gene.items()}})
        for gene in entry["to_delete"]:
            delete_keys.update(gene.keys())
            identifier = str(gene.get("id") or "")
            if identifier and identifier in values:
                delete_in_file += 1
            else:
                delete_not_in_file += 1
            if len(delete_examples) < 3:
                delete_examples.append({"entry": accession, **gene})
        if (entry["to_add"] or entry["to_delete"]) and len(keep) < 5 and accession in in_file:
            keep.append(accession)

    other_ids = [a for a in sorted(active & in_file)
                 if any(kind_of(v) in ("other", "has_spaces") for h, _ in by_entry[a]
                        for v in h.split("|")[:1])]
    keep += other_ids[:2]
    loci_seen = sum(1 for a in active & in_file
                    if set(entries[a]["loci"]) & values_in(a))

    facts = {
        "entries_in_archive": len(entries),
        "active_entries": len(active),
        "active_entries_in_file": len(active & in_file),
        "active_entries_not_in_file": len(active - in_file),
        "examples_active_not_in_file": sorted(active - in_file)[:EXAMPLES * 2],
        "clusters_in_file_by_archive_status": dict(statuses),
        "active_entries_whose_locus_accession_is_in_a_header": loci_seen,
        "gene_record_ids_found_in_file": gene_found,
        "gene_record_ids_not_found_in_file": gene_missing,
        "examples_gene_record_ids_not_found": missing_examples,
        "entries_with_gene_records_file_vs_records": dict(count_match),
        "entries_with_to_add": sum(1 for a in active if entries[a]["to_add"]),
        "to_add_genes": sum(len(entries[a]["to_add"]) for a in active),
        "to_add_keys": dict(add_keys),
        "to_add_ids_in_file": add_in_file,
        "to_add_ids_not_in_file": add_not_in_file,
        "to_add_examples": add_examples,
        "entries_with_to_delete": sum(1 for a in active if entries[a]["to_delete"]),
        "to_delete_genes": sum(len(entries[a]["to_delete"]) for a in active),
        "to_delete_keys": dict(delete_keys),
        "to_delete_ids_still_in_file": delete_in_file,
        "to_delete_ids_not_in_file": delete_not_in_file,
        "to_delete_examples": delete_examples,
        "keys_in_genes_section": dict(Counter(k for e in entries.values() for k in e["genes_keys"])),
    }
    return facts, list(dict.fromkeys(keep))


def main() -> int:
    archive = RAW_DIR / "mibig" / JSON_ARCHIVE
    if not archive.exists():
        print(f"{relative_to_repo(archive)} is missing. Run Phase 1 first:")
        print("    python -m microbegraph.fetch --source mibig")
        return 1

    out_dir = DATA_DIR / "samples" / datetime.now(timezone.utc).strftime("%Y-%m-%d") / "mibig_proteins"
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    log: dict[str, Any] = {"captured_with": "tests/fixtures/capture_mibig_protein_samples.py",
                           "requests": []}

    print(f"Part 1: asking {SERVER} (three requests), saving to {relative_to_repo(out_dir)}/")
    _, record = ask(session, "HEAD", SERVER + PROTEIN_FILE)
    log["requests"].append(record)
    print(f"    HEAD {PROTEIN_FILE:<28} {record.get('status', 'FAILED')} "
          f"{record.get('headers', {}).get('Content-Length', '')} bytes, "
          f"{record.get('headers', {}).get('Last-Modified', record.get('error', ''))}")
    listing, record = ask(session, "GET", SERVER)
    log["requests"].append(record)
    if listing:
        (out_dir / "listing.html").write_bytes(listing)
    names = sorted(set(re.findall(r'href="([^"?/][^"]*)"', listing.decode("utf-8", "replace"))))
    log["listing_files"] = names
    log["checksum_files_listed"] = [n for n in names if re.search(r"(md5|sha|checksum)", n, re.I)]
    print(f"    GET  listing{'':<24} {record.get('status', 'FAILED')}, {len(names)} files listed, "
          f"checksum files: {log['checksum_files_listed'] or 'none'}")

    target = out_dir / PROTEIN_FILE
    if target.exists():
        print(f"    {PROTEIN_FILE} is already here from an earlier run; not downloading again")
        n_bytes = target.stat().st_size
        data = target.read_bytes()
        record = {"method": "GET", "url": SERVER + PROTEIN_FILE, "reused": True, "bytes": n_bytes,
                  "md5": hashlib.md5(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest()}
    else:
        print(f"    GET  {PROTEIN_FILE}")
        record = download(session, SERVER + PROTEIN_FILE, target)
    log["requests"].append(record)
    if "error" in record:
        print(f"    FAILED: {record['error']}")
        (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
        return 1
    print(f"    {record['bytes']:,} bytes, SHA-256 {record['sha256']}")

    print(f"\nPart 2: reading {PROTEIN_FILE} and {relative_to_repo(archive)} (offline)")
    records, layout = read_fasta(target)
    fasta_facts, by_entry = survey_fasta(records)
    entries = entry_facts(archive)
    joined, keep = compare(by_entry, entries)
    for key in ("records", "fields_per_header", "clusters_in_file", "headers_without_a_bgc_accession",
                "sequences_ending_in_star"):
        print(f"    {key:<44} {fasta_facts[key]}")
    for key in ("active_entries", "active_entries_in_file", "active_entries_not_in_file",
                "clusters_in_file_by_archive_status", "gene_record_ids_found_in_file",
                "gene_record_ids_not_found_in_file", "entries_with_gene_records_file_vs_records",
                "to_add_genes", "to_add_ids_in_file", "to_delete_genes",
                "to_delete_ids_still_in_file"):
        print(f"    {key:<44} {joined[key]}")
    for position, kinds in fasta_facts["kinds_by_field_position"].items():
        print(f"    header field {position:<31} {kinds}")

    log.update({"layout": layout, "fasta": fasta_facts, "against_archive": joined,
                "kept_whole": keep})
    (out_dir / "capture_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    whole = {accession: [f">{h}\n{s}" for h, s in by_entry.get(accession, [])] for accession in keep}
    (out_dir / "capture_bundle.json").write_text(
        json.dumps({"captured_with": log["captured_with"], "requests": log["requests"],
                    "listing_files": log["listing_files"], "layout": layout, "fasta": fasta_facts,
                    "against_archive": joined,
                    "first_headers": [h for h, _ in records[:FIRST_HEADERS]],
                    "clusters_kept_whole": whole}, indent=1) + "\n", encoding="utf-8")
    print(f"\nDone. The one file to share: {relative_to_repo(out_dir / 'capture_bundle.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
