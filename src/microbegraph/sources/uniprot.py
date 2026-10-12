"""
MicrobeGraph, the UniProt adapter (Phase 3).

WHAT UNIPROT IS
    UniProt is the world's main catalogue of proteins, run jointly by the
    European Bioinformatics Institute (EMBL-EBI), the Swiss Institute of
    Bioinformatics and the Protein Information Resource. Each protein gets an
    entry with an accession (P27206, Q70KJ7), names, the organism it comes
    from, its length, and, where someone has worked it out, what it does and
    which reaction it carries out (its EC number).

    Entries come in two kinds:
        reviewed     (Swiss-Prot) a curator has read the papers and written
                     the entry by hand: about half a million proteins
        unreviewed   (TrEMBL) made automatically from sequence records:
                     everything else, hundreds of millions

    If a gene is a recipe, the protein is the machine the recipe builds, and
    UniProt is the catalogue of machines: each with a part number, a
    description and notes on what it does.

HOW MIBiG AND UNIPROT MEET
    UniProt doesn't cross-reference MIBiG (asking UniProt's list of linked
    databases for "mibig" returns nothing). The link runs through the
    sequence records instead. MIBiG's gene records name each protein by its
    INSDC protein id (the number GenBank, EMBL and DDBJ give a translated
    gene, such as CAE02630.1) or its RefSeq id (WP_...), and UniProt's ID
    MAPPING service translates those numbers into UniProt accessions:

        MIBiG gene record          ID mapping            UniProt entry
        CAE02630.1 (srfAA)  ---------------------->  Q70KJ7 (Surfactin synthetase A)

    The MIBiG adapter turns each gene record into a Protein node called
    ncbiprotein:<id> (src/microbegraph/sources/mibig.py). This adapter reads
    those nodes from MIBiG's staging table, so MIBiG must be tidied first.

HOW IT ASKS: A JOB WITH A TICKET NUMBER
    ID mapping works like ordering at a busy cafe counter. You place the
    order, get a number, and collect when your number is ready:

        1. POST /idmapping/run           "from" type, "to" UniProtKB, the ids
                                         -> {"jobId": "8Pr33gbOw8"}
        2. GET  /idmapping/status/<job>  asked every few seconds, WITHOUT
                                         following redirects:
                                         {"jobStatus": "RUNNING"} while working,
                                         HTTP 303 + {"jobStatus": "FINISHED"} when done
        3. GET  /idmapping/uniprotkb/results/stream/<job>?format=tsv&fields=...
                                         every result, as one table

    INSDC ids are asked with the "from" type EMBL-GenBank-DDBJ_CDS and RefSeq
    ids with RefSeq_Protein, 1,000 ids per job. The job answer (step 1) and
    the results (step 3) are kept in the snapshot. The "is it ready?"
    answers in between say nothing about proteins, so they aren't kept;
    the manifest records how many were needed. UniProt keeps a finished job
    for about a week, so a job number in an old manifest may no longer work.

    An id UniProt can't map doesn't appear in the results at all. The
    adapter works out which ones are missing (asked minus answered), counts
    them and lists them in the summary.

    Every answer carries the UniProt release in a header (X-UniProt-Release,
    for example 2026_03). That becomes the snapshot's source_version, so you
    can always tell which release a fetch saw.

WHAT tidy() TURNS THE ANSWERS INTO
    nodes  Protein   uniprot:<accession>   names, organism, length, EC numbers,
                                           function text, reviewed or not, and
                                           which MIBiG protein(s) it came from
                                           (mibig_protein_ids)
    edges  none. The ENCODES and CATALYZES arrows come from MIBiG's gene
           records. Phase 4 joins each ncbiprotein:<id> node to its UniProt
           entry through mibig_protein_ids, the same way PubChem's compounds
           are joined to MIBiG's.

PACING
    UniProt asks programs to be reasonable rather than publishing a fixed
    limit. This adapter makes one request a second and asks about a job
    every three seconds. The whole fetch is about twenty requests.

LICENCE AND CITATION
    UniProt is free to use under CC BY 4.0: credit UniProt when you use it.

    Cite: The UniProt Consortium (2025) UniProt: the Universal Protein
    Knowledgebase in 2025. Nucleic Acids Research 53(D1):D609-D617.
    doi:10.1093/nar/gkae1010
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import requests

from microbegraph.paths import relative_to_repo
from microbegraph.sources.api import ApiSource, Snapshot, batches_text, chunks
from microbegraph.sources.base import FetchResult, ProbeReport, SourceError, TidyResult
from microbegraph.staging import node_row, properties_of, read_table, write_tables

REST = "https://rest.uniprot.org"
FIELDS_URL = f"{REST}/configure/idmapping/fields"
RUN_URL = f"{REST}/idmapping/run"
STATUS_URL = REST + "/idmapping/status/{job}"
RESULTS_URL = REST + "/idmapping/uniprotkb/results/stream/{job}"

# The ID mapping names of the two identifier types MIBiG uses, read from
# UniProt's own list (FIELDS_URL), which probe() checks they are still on.
FROM_NAMES = {"insdc": "EMBL-GenBank-DDBJ_CDS", "refseq": "RefSeq_Protein"}
TO_NAME = "UniProtKB"
SHOWN_AS = {"insdc": "INSDC", "refseq": "RefSeq"}     # how each kind is named on screen

# The columns asked for in the results. Each name is on UniProt's list of
# result fields. The table comes back with readable headings instead, plus a
# first column, From, holding the id that was asked about:
#   From, Entry, Entry Name, Reviewed, Protein names, Gene Names, Organism,
#   Organism (ID), Length, EC number, Function [CC], Protein existence, Annotation
RETURN_FIELDS = ("accession,id,reviewed,protein_name,gene_names,organism_name,organism_id,"
                 "length,ec,cc_function,protein_existence,annotation_score")

BATCH_SIZE = 1000           # ids per job
POLL_FACTOR = 3             # ask about a job every 3 x pause_seconds
MAX_POLLS = 100             # about five minutes, far longer than a job of 1,000 ids takes

# How UniProt says "finished, look over there" when redirects aren't followed.
REDIRECTS = {301, 302, 303, 307, 308}


class UniprotSource(ApiSource):
    """UniProt: what each MIBiG protein is, through UniProt's ID mapping service."""

    name = "uniprot"
    licence = "CC-BY-4.0"
    homepage = "https://www.uniprot.org"
    pause_seconds = 1.0

    # ======================================================================
    # probe()
    # ======================================================================
    def probe(self) -> ProbeReport:
        report = ProbeReport(source=self.name, reachable=False)
        try:
            response = self.http_get(FIELDS_URL)
            offered = offered_from_names(response.content)
            report.reachable = True
            release = response.headers.get("X-UniProt-Release", "?")
            published = response.headers.get("X-UniProt-Release-Date", "?")
            report.facts.append(f"release        : {release} (published {published})")
            missing = [n for n in FROM_NAMES.values() if n not in offered]
            if missing:
                report.warnings.append(
                    f"UniProt's ID mapping no longer lists {', '.join(missing)}. Don't fetch "
                    f"until FROM_NAMES in src/microbegraph/sources/uniprot.py is updated.")
            else:
                report.facts.append(f"ID mapping     : offers both identifier types used here "
                                    f"({', '.join(FROM_NAMES.values())})")
        except (requests.RequestException, SourceError, ValueError) as error:
            report.warnings.append(f"Could not reach UniProt ({error}). Check your connection.")

        try:
            ids = self._ids_from_mibig()
            n_jobs = sum(len(chunks(ids[kind], BATCH_SIZE)) for kind in FROM_NAMES)
            report.facts.append(f"to ask about   : {len(ids['insdc']):,} INSDC and "
                                f"{len(ids['refseq']):,} RefSeq protein ids from MIBiG, "
                                f"{n_jobs} jobs")
        except SourceError as error:
            first_line = str(error).splitlines()[0]
            report.facts.append(f"to ask about   : unknown yet ({first_line})")
        facts, warnings = self.locker_facts()
        report.facts += facts
        report.warnings += warnings
        return report

    def _ids_from_mibig(self) -> dict[str, list[str]]:
        """The INSDC and RefSeq protein ids in MIBiG's staging table, sorted."""
        found: dict[str, set[str]] = {kind: set() for kind in FROM_NAMES}
        rows = read_table("mibig", "nodes", self.staging_dir, needed_by=self.name)
        for row in rows:
            if row["node_type"] != "Protein" or not row["node_id"].startswith("ncbiprotein:"):
                continue
            kind = properties_of(row).get("id_type")
            if kind in found:
                found[kind].add(row["node_id"].split(":", 1)[1])
        if not any(found.values()):
            raise SourceError(
                "mibig_nodes.csv has no proteins with an INSDC or RefSeq id. If it was "
                "written before Phase 3, re-tidy MIBiG so it reads the gene records.\n"
                "  Run:  python -m microbegraph.fetch --tidy-only --source mibig"
            )
        return {kind: sorted(ids) for kind, ids in found.items()}

    # ======================================================================
    # fetch()
    # ======================================================================
    def fetch(self) -> list[FetchResult]:
        ids = self._ids_from_mibig()
        asked_for = {"fields": RETURN_FIELDS, **ids}
        reused = self.reuse_today(asked_for)
        if reused:
            return reused

        snapshot = self.start_snapshot(asked_for, {"from_names": FROM_NAMES, "to": TO_NAME,
                                                   "batch_size": BATCH_SIZE})
        release, published = "unknown", ""
        jobs: list[dict[str, Any]] = []
        for kind in FROM_NAMES:
            batches = chunks(ids[kind], BATCH_SIZE)
            if batches:
                self.say(f"  [{self.name}] mapping {len(ids[kind]):,} {SHOWN_AS[kind]} protein ids "
                         f"in {batches_text(len(batches))} of up to {BATCH_SIZE:,}")
            for number, batch in enumerate(batches, start=1):
                job_id = self._start_job(snapshot, kind, number, batch)
                polls = self._wait_for(job_id)
                response = self.http_get(RESULTS_URL.format(job=job_id),
                                         params={"format": "tsv", "fields": RETURN_FIELDS})
                release = response.headers.get("X-UniProt-Release", release)
                published = response.headers.get("X-UniProt-Release-Date", published)
                n_rows = count_rows(response.content)
                path = snapshot.save(
                    f"{kind}_{number:03d}_results.tsv", response.content,
                    url=RESULTS_URL.format(job=job_id), method="GET",
                    sent={"format": "tsv", "fields": RETURN_FIELDS, "job": job_id},
                    n_records=n_rows, source_version=release)
                if n_rows == "":
                    raise SourceError(
                        f"{relative_to_repo(path)} arrived and is logged, but it isn't the "
                        f"results table expected. Open it to see UniProt's message, then run "
                        f"the fetch again; the unfinished folder is ignored by tidy."
                    )
                jobs.append({"file": path.name, "job": job_id, "ids": len(batch),
                             "rows": n_rows, "status_checks": polls})
                self.say(f"  [{self.name}] {relative_to_repo(path)} "
                         f"({n_rows:,} rows for {len(batch):,} ids)")
                self.pause()
        return snapshot.finish(release, {"release_date": published, "jobs": jobs})

    def _start_job(self, snapshot: Snapshot, kind: str, number: int, batch: list[str]) -> str:
        """Hand in one batch of ids (step 1) and return the job's ticket number."""
        form = {"from": FROM_NAMES[kind], "to": TO_NAME, "ids": ",".join(batch)}
        response = self.http_post(RUN_URL, form)
        job_id = job_id_in(response.content)
        path = snapshot.save(
            f"{kind}_{number:03d}_job.json", response.content, url=RUN_URL, method="POST",
            sent={"from": FROM_NAMES[kind], "to": TO_NAME, "ids": batch},
            n_records=1 if job_id else "",
            source_version=response.headers.get("X-UniProt-Release", "unknown"))
        if not job_id:
            raise SourceError(
                f"{relative_to_repo(path)} arrived and is logged, but it holds no job number "
                f"(UniProt said: {_preview(response.content)}). Run the fetch again later."
            )
        self.pause()
        return job_id

    def _wait_for(self, job_id: str) -> int:
        """Ask whether a job is finished (step 2) until it is. Returns how many times it asked."""
        url = STATUS_URL.format(job=job_id)
        for poll in range(1, MAX_POLLS + 1):
            response = self.http_get(url, allow_redirects=False)
            state = job_state(response.status_code, response.content)
            if state == "FINISHED":
                return poll
            if state not in ("NEW", "RUNNING"):
                raise SourceError(
                    f"UniProt stopped job {job_id} ({state}): {_preview(response.content)}\n"
                    f"  Run the fetch again; if it happens twice, check "
                    f"https://www.uniprot.org/help/id_mapping for changes."
                )
            self.pause(POLL_FACTOR)
        raise SourceError(
            f"UniProt job {job_id} was still running after {MAX_POLLS} checks. UniProt may be "
            f"busy; run the fetch again later."
        )

    # ======================================================================
    # tidy()
    # ======================================================================
    def tidy(self) -> TidyResult:
        folder, manifest = self.latest_snapshot()
        retrieved_at = manifest["started_at"][:10]
        asked = {kind: list(manifest["asked_for"].get(kind, [])) for kind in FROM_NAMES}

        rows: list[dict[str, str]] = []
        files_read = 0
        for answer in manifest["answers"]:
            if answer["file"].endswith("_results.tsv"):
                rows += read_results(folder / answer["file"])
                files_read += 1

        entries: dict[str, dict[str, Any]] = {}
        entries_for: dict[str, set[str]] = {}
        for row in rows:
            accession = row["Entry"].strip()
            from_id = row["From"].strip()
            if not accession or not from_id:
                continue
            entries_for.setdefault(from_id, set()).add(accession)
            entry = entries.setdefault(accession, {"row": row, "from": set()})
            entry["from"].add(from_id)

        nodes = [node_row(f"uniprot:{accession}", "Protein", short_name(entry["row"]),
                          entry_properties(entry["row"], entry["from"]), self.name, retrieved_at)
                 for accession, entry in entries.items()]

        not_mapped = {kind: [i for i in ids if i not in entries_for] for kind, ids in asked.items()}
        several = {i: sorted(a) for i, a in sorted(entries_for.items()) if len(a) > 1}
        counts = {
            "results_files_read": files_read,
            "ids_asked": sum(len(ids) for ids in asked.values()),
            "ids_asked_insdc": len(asked["insdc"]),
            "ids_asked_refseq": len(asked["refseq"]),
            "ids_mapped": sum(1 for ids in asked.values() for i in ids if i in entries_for),
            "ids_not_mapped": sum(len(ids) for ids in not_mapped.values()),
            "ids_with_several_entries": len(several),
            "uniprot_entries": len(entries),
            "entries_from_several_ids": sum(1 for e in entries.values() if len(e["from"]) > 1),
            "entries_reviewed": sum(1 for e in entries.values()
                                    if e["row"].get("Reviewed", "").strip() == "reviewed"),
            "entries_with_ec_number": sum(1 for e in entries.values()
                                          if e["row"].get("EC number", "").strip()),
            "entries_with_function": sum(1 for e in entries.values()
                                         if e["row"].get("Function [CC]", "").strip()),
        }
        summary = {
            "source": self.name,
            "source_version": manifest.get("source_version", ""),
            "release_date": manifest.get("notes", {}).get("release_date", ""),
            "snapshot": relative_to_repo(folder),
            "retrieved_at": retrieved_at,
            "counts": counts,
            "ids_not_mapped": not_mapped,
            "ids_with_several_entries": several,
        }
        return write_tables(self.name, nodes, [], summary, self.staging_dir)


# --------------------------------------------------------------------------
# Reading UniProt's answers (small functions, each tested on its own)
# --------------------------------------------------------------------------
def offered_from_names(body: bytes) -> set[str]:
    """The identifier types ID mapping accepts as "from", read from /configure/idmapping/fields."""
    data = json.loads(body)
    return {str(item.get("name")) for group in data.get("groups") or []
            for item in group.get("items") or [] if item.get("from") is True}


def job_id_in(body: bytes) -> str:
    """The ticket number in a /idmapping/run answer, or "" if there isn't one."""
    try:
        return str(json.loads(body).get("jobId") or "")
    except (ValueError, AttributeError):
        return ""


def job_state(status_code: int, body: bytes) -> str:
    """
    FINISHED, NEW, RUNNING, or whatever else UniProt reports (ERROR, say).

    A redirect means finished: UniProt points at the results once a job is
    done. The body says the same thing in words, and a body holding results
    (if a redirect was followed somewhere along the way) means finished too.
    """
    if status_code in REDIRECTS:
        return "FINISHED"
    try:
        data = json.loads(body)
    except ValueError:
        return "UNREADABLE"
    if not isinstance(data, dict):
        return "UNREADABLE"
    if data.get("jobStatus"):
        return str(data["jobStatus"]).upper()
    if "results" in data or "failedIds" in data:
        return "FINISHED"
    return "UNKNOWN"


def count_rows(body: bytes) -> int | str:
    """
    How many result rows a TSV answer holds, or "" if it isn't the table
    expected. An empty answer is a valid "nothing mapped".
    """
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 0
    if not lines[0].startswith("From\tEntry"):
        return ""
    return len(lines) - 1


def read_results(path: Path) -> list[dict[str, str]]:
    """Every row of one results table, as {heading: value}."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SourceError(f"{relative_to_repo(path)} can't be read ({error}). "
                          f"Run the fetch again.") from error
    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    missing = {"From", "Entry"} - set(reader.fieldnames or [])
    if missing:
        raise SourceError(f"{relative_to_repo(path)} has no {', '.join(sorted(missing))} "
                          f"column, so it isn't an ID mapping result. Run the fetch again.")
    return [dict(row) for row in reader]


def short_name(row: dict[str, str]) -> str:
    """
    The protein's main name. UniProt's "Protein names" column holds the
    recommended name first and every other name after it in brackets:
        "Glucose-1-phosphate thymidylyltransferase (EC 2.7.7.24) (dTDP-glucose synthase)"
    so the main name is everything before the first " (".
    """
    names = row.get("Protein names", "").strip()
    main = names.split(" (", 1)[0].strip()
    return main or row.get("Entry Name", "").strip() or row["Entry"].strip()


def entry_properties(row: dict[str, str], from_ids: set[str]) -> dict[str, Any]:
    """One results row as node properties. Several values in one cell are joined with "|"."""
    return {
        "uniprot_accession": row["Entry"].strip(),
        "entry_name": row.get("Entry Name", "").strip(),
        "reviewed": row.get("Reviewed", "").strip() == "reviewed",
        "protein_names": row.get("Protein names", "").strip(),
        "gene_names": "|".join(row.get("Gene Names", "").split()),
        "organism": row.get("Organism", "").strip(),
        "organism_taxid": _whole_number(row.get("Organism (ID)")),
        "length": _whole_number(row.get("Length")),
        "ec_numbers": "|".join(p.strip() for p in row.get("EC number", "").split(";")
                               if p.strip()),
        "function": row.get("Function [CC]", "").strip().removeprefix("FUNCTION: "),
        "protein_existence": row.get("Protein existence", "").strip(),
        "annotation_score": _decimal(row.get("Annotation")),
        "mibig_protein_ids": "|".join(f"ncbiprotein:{i}" for i in sorted(from_ids)),
    }


def _whole_number(text: Any) -> int | str:
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return ""


def _decimal(text: Any) -> float | str:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return ""


def _preview(body: bytes) -> str:
    """The start of an answer, for an error message."""
    text = body.decode("utf-8", errors="replace").strip()
    return text[:300] + ("..." if len(text) > 300 else "")
