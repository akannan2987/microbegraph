[← Handbook](HANDBOOK.md) · [README](../README.md) · [Glossary](GLOSSARY.md) · [Roadmap](ROADMAP.md) · [Git workflow](GIT-WORKFLOW.md)

# 05b. Every cluster's proteins: MIBiG's protein file (Phase 3b)

**Prerequisites:** [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md)
finished: `pytest` passes, the MIBiG archive is in `data/raw/mibig/`, and
`data/processed/staging/` holds the tables of all six sources. Section 14 of that
guide, *What the protein layer doesn't cover yet*, is the reason this phase
exists, so it's worth reading again first. No biology background is needed.

**Learning goal:** after this phase you will understand what a protein sequence
and the FASTA file format are; how to pin a file whose publisher lists no
checksum, and how to notice that it changed without downloading it again; how
curators' corrections to a list are applied and written down; how to match names
from two lists without guessing; why the project keeps a fingerprint of each
sequence instead of the sequence itself; and how a background service is asked
about tens of thousands of identifiers at once. You will also see, for the second
phase running, how a look at the real data before any code was written shaped
the design.

**Time:** about 4 to 5 hours, in two sessions. The real run downloads one file of
30.4 MB and runs five UniProt jobs, about four minutes in all.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md). The overview of this
> phase is in [`HANDBOOK.md`](HANDBOOK.md), Stage 6b.

---

## Contents

1. [What this phase builds, in one picture](#1-what-this-phase-builds-in-one-picture)
2. [The science, in plain words](#2-the-science-in-plain-words)
3. [The engineering ideas, in plain words](#3-the-engineering-ideas-in-plain-words)
4. [Step 0. Get into position](#4-step-0-get-into-position)
5. [Step 1. Put the new files in place](#5-step-1-put-the-new-files-in-place)
6. [Step 2. Look at the real file first](#6-step-2-look-at-the-real-file-first)
7. [Step 3. Pin a file that has no published checksum](#7-step-3-pin-a-file-that-has-no-published-checksum)
8. [Step 4. Read the protein file](#8-step-4-read-the-protein-file)
9. [Step 5. MIBiG builds every cluster's proteins](#9-step-5-mibig-builds-every-clusters-proteins)
10. [Step 6. ID mapping at scale](#10-step-6-id-mapping-at-scale)
11. [Step 7. Tests built from real records](#11-step-7-tests-built-from-real-records)
12. [Step 8. Run it for real](#12-step-8-run-it-for-real)
13. [Step 9. Pictures, the Handbook and the records](#13-step-9-pictures-the-handbook-and-the-records)
14. [How evidence and confidence are decided for the new arrows](#14-how-evidence-and-confidence-are-decided-for-the-new-arrows)
15. [What the protein layer still doesn't cover](#15-what-the-protein-layer-still-doesnt-cover)
16. [What could go wrong](#16-what-could-go-wrong)
17. [Checkpoint](#17-checkpoint)
18. [Committing this phase](#18-committing-this-phase)

---

## 1. What this phase builds, in one picture

![How far the protein layer reaches now: active entries with proteins go from 452 to 2,437, Protein nodes from 4,737 to 40,037, ENCODES arrows from 4,737 to 40,048, numbers sent to UniProt from 4,089 to 39,053; CATALYZES stays at 4,492](img/protein_file_coverage.svg)

Phase 3 gave the graph its protein layer, but only for the 452 MIBiG entries that
list their genes in the JSON release. Four clusters in five had no proteins at
all. MIBiG also publishes every protein of every cluster in one file on its
own download server, and this phase reads it. Afterwards every one of the 2,437
active entries has its proteins, each a `Protein` node with an `ENCODES` arrow
from its cluster, and the protein numbers among them (about 39,000) go to UniProt
through the same adapter as before.

Nothing about the shape of the graph changes. No node type, edge type or
identifier prefix is new; there are just many more `Protein` nodes and
`ENCODES` arrows. `CATALYZES` doesn't grow, because only MIBiG's gene records say
what job a gene does, and the protein file only says that the gene is there.

The commands, starting with the capture script from Step 2:

| Command | What it does | Touches the internet? |
|---|---|---|
| `python tests/fixtures/capture_mibig_protein_samples.py` | Downloads the file once into `data/samples/` and surveys it (Step 2) | Yes, three requests |
| `python -m microbegraph.fetch --probe --source mibig` | Asks Zenodo about the archive and MIBiG's server about the protein file, without downloading either | Yes, a few small questions |
| `python -m microbegraph.fetch --source mibig` | Downloads the protein file into the locker (the archive is already there), then tidies both | Yes, one 30 MB download |
| `python -m microbegraph.fetch --source uniprot` | Maps every protein number to UniProt, 10,000 per job | Yes, five jobs, about 90 requests (most are quick "is it ready?" questions) |
| `python -m microbegraph.fetch --tidy-only --all` | Rebuilds every table from what is on your machine | **No** |

**Files this phase creates or changes** (paths relative to the project folder):

| Path | New or changed | What it is |
|---|---|---|
| `src/microbegraph/sources/mibig_proteins.py` | new | Reads MIBiG's protein file and matches curators' names to its proteins |
| `src/microbegraph/sources/mibig.py` | changed | Fetches and probes the protein file; builds every cluster's proteins; lists every decision in its summary |
| `src/microbegraph/sources/base.py` | changed | A download can be checked against a SHA-256 this project pinned |
| `src/microbegraph/sources/uniprot.py` | changed | 10,000 ids per job instead of 1,000 |
| `src/microbegraph/sources/__init__.py`, `src/microbegraph/staging.py`, `src/microbegraph/provenance.py` | changed | Notes only |
| `tests/fixtures/capture_mibig_protein_samples.py` | new | Downloads the protein file once and surveys it against the archive |
| `tests/fixtures/mibig/mibig_prot_seqs_sample.fasta` | new | Surfactin's 23 real proteins, plus made-up ones for the made-up entries |
| `tests/fixtures/mibig/BGC9999901.json`, `BGC9999903.json` | changed | Made-up gene records, a curator-added gene and four removals for the new cases |
| `tests/fixtures/README.md` | changed | Where the sample came from, record by record |
| `tests/conftest.py` | changed | Puts the sample next to the test archive; the fake server records which requests stream |
| `tests/test_mibig_protein_file.py` | new | The promises the new code makes |
| `tests/test_mibig_fetch_probe.py`, `tests/test_mibig_genes.py` | changed | A fetch brings two files; three more gene records in the counts |
| `docs/05b-all-cluster-proteins.md` | new | This guide |
| `docs/img/fasta_header.svg`, `docs/img/protein_file_matching.svg`, `docs/img/protein_file_coverage.svg` | new | Three new pictures |
| `docs/img/make_illustrations.py`, `docs/interactive/make_interactive.py` and the files they draw | changed | The new pictures; the sources map, the ID mapping picture, the protein layer and the explorers mention the protein file |
| `docs/phases.csv` | changed | Phase 3b done |
| `README.md`, `CHANGELOG.md`, `docs/HANDBOOK.md`, `docs/ROADMAP.md`, `docs/GLOSSARY.md`, `docs/GIT-WORKFLOW.md`, `docs/00-architecture.md`, `docs/02-ontology-and-data-model.md`, `docs/03-ingestion-mibig.md`, `docs/05-proteomics-uniprot.md` | changed | Updated for this phase |

**Files this phase writes on your computer that never go to GitHub:**

| Path | What it is |
|---|---|
| `data/raw/mibig/mibig_prot_seqs_4.0.fasta` | MIBiG's protein file, checked against its pinned SHA-256 |
| `data/raw/uniprot/<moment>/` | A new UniProt snapshot: five jobs and their results, plus `manifest.json` |
| `data/raw/provenance.csv` | Gains a row for the protein file (and an `already_present` row for the archive) and one for every UniProt answer |
| `data/processed/staging/mibig_*`, `uniprot_*` | Rewritten, now with every cluster's proteins |
| `data/samples/<date>/mibig_proteins/` | The survey and the downloaded file from Step 2 |

---

## 2. The science, in plain words

### A protein's sequence

A protein is a chain of building blocks called **amino acids**, and there are
twenty kinds. Write each kind as one capital letter (M for methionine, A for
alanine, and so on) and the whole protein becomes a line of text: its
**sequence**. srfAA, the first part of the surfactin synthetase, is 3,584 letters
long and starts

```
MEITFYPLTNAQKRIWYTEKFYPNTSISNLAGFGKLISEDGVQAHYVEKAIQEFVRRYES...
```

Most proteins in the file are a few hundred letters long: the median is 344,
which means half are shorter and half longer. The longest are the giant
assembly-line enzymes, at up to 18,447. A handful are only a few letters long,
which may be a fragment, or a gene the sequence record only partly describes. Now
and then a letter is **X**, meaning "an amino acid is
here, but the sequencing couldn't tell which one": 139 proteins in the file have
at least one.

### Two lists of a cluster's genes

MIBiG describes a cluster's genes in two places, and they do different jobs:

| | Gene records (Phase 3) | The protein file (this phase) |
|---|---|---|
| Where | The `genes` part of each JSON entry | One FASTA file for the whole release |
| Covers | 452 of the 2,437 active entries, 4,737 genes | All 2,437 active entries, 40,009 proteins |
| Says | The protein's number, often the gene's job and the experiment that showed it | The protein's number, label, product, position and sequence |
| Gives | `ENCODES`, and `CATALYZES` for genes that build the molecule | `ENCODES` only |

Think of a school class. The gene records are a teacher's notes on some of the
pupils (who is good at what, and how we know), while the protein file is the full
class register, every pupil with no notes.

### The curators' corrections: "to_add" and "to_delete"

A MIBiG entry points at a stretch of a public **sequence record** (a GenBank or
EMBL record of the DNA). That record's list of genes isn't always right for the
cluster, so MIBiG's curators can correct it, much as a publisher prints an
errata slip:

* **`to_add`**: genes the record doesn't list but the cluster has. 60 active
  entries add 661 genes this way, usually with a name made up for the purpose
  (`ctg1_orf7`, `abyU`) because the record gives them no number.
* **`to_delete`**: genes the record lists but the curators say are not part of
  the cluster, each with a reason. 2 active entries remove 14 genes.

The capture in Step 2 found that the protein file **already includes** every gene
added with `to_add`, sequence and all (the JSON has a sequence for only 5 of the
661), but **still lists** genes removed with `to_delete`. So this phase applies the
removals itself. Two real examples:

* **BGC0000966, caerulomycin A.** Six genes removed, with reasons such as "Gene
  encodes function not relevant to caerulomycin A". Four are named by protein
  number (`AFD30968.1`); two by gene name (`CrmK`, `CrmF`).
* **BGC0002390, zealexins in maize.** Eight genes removed because "cluster only
  contains zx5, zx6 and zx7 as shown in in-vivo expression assay". They're named
  by NCBI gene numbers such as `LOC100273419`, which never appear on their own in
  the file: they appear inside product names, as in "uncharacterized protein
  LOC100273419 isoform X5".

### Isoforms: one gene, several proteins

That last example shows something new. In plants and animals one gene can be read
in more than one way, giving slightly different proteins called **isoforms**. One
recipe card with optional steps is close: leave out the nuts, or bake it longer,
and you get variations of the same cake. Gene `LOC100273419` has eight isoforms
in the file, each with its own protein number, and removing the gene removes all
eight.

### Entries that aren't released yet

The file holds proteins for 2,636 entries, while the archive has 2,437 active
ones. The other 199 are **pending**: submitted to MIBiG but not yet reviewed and
released. Between them they hold 6,978 proteins, and one of them alone
(BGC0002977) has 4,117, about as many proteins as a whole bacterial genome has.
The project reads only active
entries, as it has since Phase 1, so these proteins are counted and left out.

### The worked example: surfactin's 23 proteins

In Phase 3 the surfactin cluster, BGC0000433, encoded the nine proteins of its
gene records. The protein file lists 23 for it, `CAE02619.1` to
`CAE02641.1` in one unbroken run along the DNA. The nine from the gene records are
among them, and keep everything Phase 3 gave them (gene name, job, the
knock-out). The other 14 arrive from the file with what the file knows: product
names such as "YciC protein", "Nin" or "amino transferase", their position, and
their length. None of the 14 gets a `CATALYZES` arrow, because nobody recorded a
job for them.

![The protein layer: FZB42 harbors BGC0000433, which encodes srfAA, which catalyzes surfactin; from Phase 3b the protein file adds the cluster's other 14 proteins](img/protein_layer.svg)

---

## 3. The engineering ideas, in plain words

### Looking at real data first, again

Phase 3 changed its plan after a short survey of the real data. This phase did the
same before any adapter code existed:
[`tests/fixtures/capture_mibig_protein_samples.py`](../tests/fixtures/capture_mibig_protein_samples.py)
downloads the file once and lines every protein up with the archive. What it
found, and what each finding changed:

| Expected before looking | What the file showed | What the code does |
|---|---|---|
| A header naming the cluster and the protein | Seven parts separated by `\|`, the same shape in all 46,987 headers | Reads exactly that shape and refuses anything else |
| Proteins for active entries | Also 6,978 for 199 pending entries | Reads active entries only, counts the rest |
| The protein number in one place | A label (often a locus tag, a genome's own label for a gene) in part 4 and the number in part 6 | Matches gene records on either, so 435 locus tags gain a number |
| Gene records use protein numbers | 76 use other names, mostly gene names such as `nisA`; 17 of those equal a product once capitals are ignored (`NisA`) | A second rule: one product, ignoring capitals, only if unique |
| `to_add` and `to_delete` both to be applied | `to_add` is already in the file; `to_delete` isn't | Applies removals only, and lists each one |
| Removals named by protein number | Also by gene name and by NCBI gene number inside a product | Three rules for removals, each recorded |

### The FASTA format

**FASTA** is a very plain text format for sequences, used since the 1980s and
read by almost every biology tool. A record has two parts: a header line that
starts with `>`, and the sequence on the following line or lines. MIBiG puts each
sequence on a single line.

A stack of index cards works as a picture: the top line of each card is its label,
the rest is the content, and the stack is the file. MIBiG writes its labels in
seven parts:

![One protein from MIBiG's protein file: a header with seven parts (entry and version, record, position, strand, label, product, protein number) and its sequence, and what MicrobeGraph keeps of each](img/fasta_header.svg)

| Part | Example | What it is |
|---|---|---|
| 0 | `BGC0000433.5` | The entry and its version (5, the same as in the JSON) |
| 1 | `c1` | Which sequence record of the entry; always `c1` in MIBiG 4.0 |
| 2 | `8558-19312` | Where the gene sits in that record |
| 3 | `+` | Which strand of the DNA it's read from (`+` or `-`; DNA has two strands, and a gene can sit on either) |
| 4 | `CAE02630.1` | The gene's label: a locus tag such as `TSTA_117750` when the record has one, otherwise the same as part 6 |
| 5 | `surfactin_synthetase_A` | The product, with spaces written as `_`; empty for 1,260 proteins (1,253 in active entries) |
| 6 | `CAE02630.1` | The protein's number: INSDC or RefSeq (the two worldwide protein numbering systems from Phase 3) when there is one, otherwise a gene name or MIBiG's own label |

### Pinning a file with no published checksum

Zenodo lists an MD5 next to MIBiG's archive, and Phase 1 checks every download
against it. MIBiG's download server lists nothing next to the protein file, so
there's no publisher's fingerprint to compare with.

The answer is to take one yourself. The first download (on 2026-10-12) was looked
at in full, and its **SHA-256** fingerprint and its exact size went into the code
as constants, the way the archive's MD5 did. From then on every download must
produce the same fingerprint or it is thrown away, and the locker never
overwrites a file that doesn't match. Weighing a parcel on the day it arrives and
writing the weight on the shelf label does the same job: next time, you can tell
whether the parcel on the shelf is the same one.

Two numbers are pinned, for two different checks:

| Constant in `mibig.py` | Value | Checked by |
|---|---|---|
| `PROTEIN_FILE_SHA256` | `4b196343ed82d49f2b8f3babe89d512b92f0e026040fa50b15eeb97950717e8b` | Every fetch, after downloading |
| `PROTEIN_FILE_BYTES` | `31833799` | The probe, without downloading |

### Noticing a change without downloading

The probe has to stay cheap, so it can't download 30 MB to check a fingerprint.
Instead it asks for the file and **hangs up as soon as the reply's headers
arrive**. Every reply from a web server starts with headers, short lines that
describe what follows, including its size (`Content-Length`) and when it last
changed (`Last-Modified`). If MIBiG replaced the file, the size would almost
certainly change, and the probe warns before anyone fetches. (In code this is a
GET with `stream=True`, closed before the body is read.)

The same probe also reads the server's list of files and reports anything from a
newer release. On 2026-10-12 that's `mibig_json_5.0rc1.tar.bz2`, a release
candidate of MIBiG 5.0 (a test version published just before the final one). The project stays on 4.0 until an upgrade is made on
purpose ([`03-ingestion-mibig.md`, section 16](03-ingestion-mibig.md#16-upgrading-mibig-later)).

### Matching names from two lists without guessing

The gene records and the removals name genes in their own ways, and the file in
its own. Lining them up is like seating guests from a list: check the ticket
number first, and if there's no ticket, look for the name, seating someone by name
only when exactly one guest has it.

![Every cluster's proteins in three steps: leave out the curators' removals, match each gene record, add every other protein; with the real counts](img/protein_file_matching.svg)

Each name is looked up only among the proteins of its own entry:

1. **By number or label.** The name equals part 6 or part 4 exactly.
   `TSTA_117750` finds the protein whose label it is, numbered `EED18001.1`.
2. **By product.** The name equals part 5, ignoring capitals: `nisA` and `NisA`.
   For a gene record this counts only when exactly one protein in the entry has
   that product.
3. **By word in the product** (removals only). The name appears as a whole word
   inside the product, which is how NCBI names a protein nobody has characterised:
   "uncharacterized protein LOC100273419 isoform X5". A removal may match several
   proteins this way, one per isoform.

Rule 3 isn't used for gene records. A gene name found inside a longer product
could belong to a neighbouring gene, and a wrong match would quietly merge two
proteins, which is worse than leaving one unmatched. Everything that isn't
matched is kept as it was and listed in `mibig_summary.json`.

### One protein, one node

A protein can now reach the graph from two directions, a gene record and the file.
It must still be one node. The node is named after the file's protein number
whenever the gene record is found in the file, so:

* a gene record that gave `CAE02630.1` and the file's `CAE02630.1` are the same
  node, `ncbiprotein:CAE02630.1`, with the gene record's details and the file's
  details together;
* a gene record that gave only the locus tag `TSTA_117750` (in Phase 3,
  `mg.protein:bgc0000154-tsta-117750`) becomes `ncbiprotein:EED18001.1`, a
  worldwide number UniProt can look up. 452 gene records gain a number this way
  (435 by label, 17 by product);
* a gene record that can't be found keeps its Phase 3 node and is listed.

Each node remembers where it came from in `found_in`: `gene_records`,
`protein_file`, or both.

### A fingerprint instead of the sequence

The staging tables don't hold the sequences. The 40,009 sequences of active
entries add up to about 25 million letters, the tables are read again and again,
and no phase so far needs them. Instead each node keeps `sequence_length` and `sequence_md5`, an MD5
fingerprint of the letters. Two proteins with the same fingerprint have exactly the
same sequence, which Phase 4 can use when deciding whether two nodes are one
protein. The sequences themselves stay in the file in the locker, where any later
phase can read them.

MD5 is fine here because it's only used to compare sequences; the file as a
whole is guarded by its SHA-256.

---

## 4. Step 0. Get into position

1. Open your terminal and go to the project folder:

   ```bash
   cd ~/projects/microbegraph      # or wherever you cloned it
   ```

   Windows PowerShell: `cd $HOME\projects\microbegraph`
2. Make sure you're on the working branch and up to date:

   ```bash
   git switch develop
   git pull --ff-only origin develop
   ```

3. Activate the toolbox:

   ```bash
   source .venv/bin/activate          # macOS / Linux / RHEL 8
   ```

   Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
4. Check that the MIBiG archive is in the locker, because the capture compares
   the protein file with it:

   ```bash
   ls data/raw/mibig
   ```

   Windows PowerShell: `dir data\raw\mibig`. You should see
   `mibig_json_4.0.tar.gz`. If not, run
   `python -m microbegraph.fetch --source mibig` first.

✅ **Checkpoint.** Your prompt starts with `(.venv)`, `git branch` shows
`* develop`, and the archive is there.

---

## 5. Step 1. Put the new files in place

If you cloned the repository after this phase was committed, every file is
already there and you can read along. If you're building it yourself, put each
file from the table in section 1 at the path shown. Then:

1. **No new packages are needed.** The FASTA reader uses only Python's own
   `hashlib` and `re`, and everything else was installed in earlier phases.
2. **No reinstall is needed either.** The package is installed in editable mode
   (`pip install -e .`), so Python reads the new module,
   `src/microbegraph/sources/mibig_proteins.py`, straight from the folder.
3. **The list of sources doesn't change.** `python -m microbegraph.fetch --list`
   still shows six. The protein file belongs to MIBiG's release, so the MIBiG
   adapter reads it rather than a seventh source.

✅ **Checkpoint.** `python -m microbegraph.fetch --list` shows the same six
sources as in Phase 3.

---

## 6. Step 2. Look at the real file first

Before writing any code, download the file once and see what's in it:

```bash
python tests/fixtures/capture_mibig_protein_samples.py
```

The script makes three requests: one asks for the file's headers only, one reads
the server's file list, and one downloads the file. It then reads the file and the
archive in your locker, offline, and prints what it found. Everything lands in
`data/samples/<today>/mibig_proteins/`, which never goes to GitHub.

This is the real output from 2026-10-12 (the download counter, which climbs to
30.4 MB, is shown at its end):

```
Part 1: asking https://dl.secondarymetabolites.org/mibig/ (three requests), saving to data/samples/2026-10-12/mibig_proteins/
    HEAD mibig_prot_seqs_4.0.fasta    200 31833799 bytes, Fri, 15 Nov 2024 12:35:03 GMT
    GET  listing                         200, 38 files listed, checksum files: none
    GET  mibig_prot_seqs_4.0.fasta
      30.4 MB
    31,833,799 bytes, SHA-256 4b196343ed82d49f2b8f3babe89d512b92f0e026040fa50b15eeb97950717e8b

Part 2: reading mibig_prot_seqs_4.0.fasta and data/raw/mibig/mibig_json_4.0.tar.gz (offline)
    records                                      46987
    fields_per_header                            {7: 46987}
    clusters_in_file                             2636
    headers_without_a_bgc_accession              0
    sequences_ending_in_star                     0
    active_entries                               2437
    active_entries_in_file                       2437
    active_entries_not_in_file                   0
    clusters_in_file_by_archive_status           {'active': 2437, 'pending': 199}
    gene_record_ids_found_in_file                4661
    gene_record_ids_not_found_in_file            76
    entries_with_gene_records_file_vs_records    {'file has more': 275, 'same': 177}
    to_add_genes                                 661
    to_add_ids_in_file                           661
    to_delete_genes                              14
    to_delete_ids_still_in_file                  6
    header field 0                               {'mibig_accession': 46987}
    header field 1                               {'short_code': 46987}
    header field 2                               {'location': 46987}
    header field 3                               {'strand': 46987}
    header field 4                               {'insdc_protein': 28025, 'other': 18841, 'refseq_protein': 79, 'short_code': 29, 'number': 13}
    header field 5                               {'other': 45727, 'empty': 1260}
    header field 6                               {'insdc_protein': 43213, 'refseq_protein': 2703, 'other': 1071}

Done. The one file to share: data/samples/2026-10-12/mibig_proteins/capture_bundle.json
```

How to read it:

* One shape: every header has 7 parts, every part 0 is a BGC accession, and no
  sequence ends in `*` (some files mark the end of a protein that way).
* Every active entry is there, plus 199 pending ones.
* 4,661 of the 4,737 gene records appear in the file by their own id (in part
  4 or part 6). The 76 that don't are mostly gene names such as `nisA`, `baeB`
  or `mscA`, plus a few locus tags (`SCO6265`) and NCBI gene numbers
  (`LOC100274356`).
* For 275 entries the file lists more proteins than the gene records, for 177
  the same number. The gene records describe a selection of genes; the file
  describes them all.
* All 661 genes added with `to_add` are in the file, and so are at least 6 of
  the 14 removed with `to_delete`. The survey only looks for each name as a
  whole part of a header. The adapter's own rules (Step 5) also look inside
  product names, and find 18 proteins behind 10 of the 14 names.
* Part 4 is mostly a protein number (28,025) or a locus tag ("other",
  18,841). Part 6 is mostly an INSDC number (43,213) or a RefSeq number
  (2,703); the 1,071 "other" are names such as `abyU` and MIBiG's labels for
  curator-added genes. Part 5 is empty 1,260 times across the whole file (1,253
  of them in active entries).

✅ **Checkpoint.** The output ends with `Done.`, and
`data/samples/<today>/mibig_proteins/` holds the file and `capture_bundle.json`.

---

## 7. Step 3. Pin a file that has no published checksum

[`src/microbegraph/sources/mibig.py`](../src/microbegraph/sources/mibig.py) gains
the protein file's pins next to the archive's:

```python
DOWNLOAD_SERVER = "https://dl.secondarymetabolites.org/mibig/"
PROTEIN_FILE = "mibig_prot_seqs_4.0.fasta"
PROTEIN_FILE_URL = DOWNLOAD_SERVER + PROTEIN_FILE
PROTEIN_FILE_SHA256 = "4b196343ed82d49f2b8f3babe89d512b92f0e026040fa50b15eeb97950717e8b"
PROTEIN_FILE_BYTES = 31_833_799
```

The two numbers are the ones the capture in Step 2 printed. They belong to MIBiG
4.0 like the archive's constants, so an upgrade changes all of them together.

**The download rules don't change.**
[`src/microbegraph/sources/base.py`](../src/microbegraph/sources/base.py):
`download_to_locker()` gains one option, `expected_sha256`, used exactly like the
MD5 it already checked. The four safety rules from Phase 1 apply to the protein
file unchanged: a verified file already in the locker costs no download; a
different file with the same name is never overwritten; a download goes into a
`.part` file and is renamed only once complete; and a download that doesn't match
its fingerprint is thrown away. The message for a mismatch says "this project
pinned" rather than "the publisher lists", so you can tell which kind of
fingerprint failed.

**fetch()** now brings two files and writes one provenance row for each: the
archive from Zenodo, then the protein file from MIBiG's server. The protein file's
row records its URL, its MD5 and SHA-256, the number of proteins (lines starting
with `>`), and the licence. MIBiG's data is released under CC BY 4.0, and the file
is part of the same release.

**probe()** adds four lines about the protein file: where it comes from, its size
and date from the server's headers (compared with the pinned size), anything newer
in the server's file list, and whether the copy in your locker matches the pinned
SHA-256.

**tidy()** now needs both files. If the protein file is missing (say you updated
the code and ran `--tidy-only` before fetching), it stops before writing anything
and says which command fetches it:

```
[mibig] tidy

[mibig] FAILED: data/raw/mibig/mibig_prot_seqs_4.0.fasta is not in the evidence locker yet (the tidy reads it from Phase 3b).
  Run:  python -m microbegraph.fetch --source mibig
  The JSON archive is already there, so only the protein file is downloaded.
  (add --debug to see the full error)
```

---

## 8. Step 4. Read the protein file

[`src/microbegraph/sources/mibig_proteins.py`](../src/microbegraph/sources/mibig_proteins.py)
is a new module with one job: turn the file into a list of proteins per entry,
and answer "which protein does this name mean?". It's a module of its own, beside
the adapter, so it can be tested on its own and read in one sitting.

| Function | What it does |
|---|---|
| `parse_header(header)` | Splits a header into its seven parts, or returns `None` if it has another shape (another number of parts, no BGC accession, no protein number) |
| `read_protein_file(path)` | Every protein, grouped by entry, in file order: the parts of its header, the product with `_` turned back into spaces, the sequence's length and its MD5. Refuses the whole file if any header can't be read, naming the first few |
| `count_records(path)` | How many proteins the file holds: the lines that start with `>` |
| `find_gene(name, records)` | The protein a gene record means, by rule 1 or 2 (section 3), or none |
| `find_removed(name, records)` | The protein(s) a removal means, by rule 1, 2 or 3, or none |

Each protein becomes a small record (a Python **dataclass**, a class whose only job
is to hold a few named values) called `ProteinRecord`. The whole file, 46,987 of
them, takes about a second to read.

**Why refuse a whole file over one odd header?** Because an odd header means the
format isn't what the code thinks it is, and every number after that would be
quietly wrong. The file is pinned, so this can only happen when someone moves the
pin to a different file, and then the code should stop and say so.

---

## 9. Step 5. MIBiG builds every cluster's proteins

The MIBiG adapter's tidy now works through each active entry's proteins in three
steps, in this order (the picture in section 3 shows them):

1. **Leave out the curators' removals.** Each `to_delete` name is looked up among
   the entry's proteins (rules 1 to 3). Every protein found is left out and listed
   in `mibig_summary.json`, under `removed_by_curators`, with the rule that found
   it and the curators' reason. A name that finds nothing is listed under
   `to_delete_not_found`.
2. **Match each gene record** (rules 1 and 2). Found: the node is named after the
   file's protein number. Not found: the node is named as in Phase 3, and the gene
   record is listed under `genes_not_in_protein_file`.
3. **Add every other protein.** Each remaining protein of the entry becomes a
   `Protein` node with an `ENCODES` arrow from its cluster. A protein a gene
   record already gave is the same node and the same arrow.

One case the order leaves open: a gene record that names a protein the curators
removed. The gene record is still matched to it, so that protein would keep a
node and an `ENCODES` arrow from the gene record. MIBiG 4.0 has no such case (no
removed gene has a gene record), and the counts in Step 8 would show one, because
the arrows would no longer add up.

**What a `Protein` node holds now** (only the properties that have a value are
written):

| Property | From | Example (srfAA) |
|---|---|---|
| `protein_id` | the number that names the node | `CAE02630.1` |
| `id_type` | `insdc`, `refseq` or `other` | `insdc` |
| `gene_name`, `functions`, `function_evidence`, `comment`, `mutation_phenotype` | gene record (Phase 3) | `srfAA`, `Scaffold biosynthesis`, `Knock-out` |
| `product` | gene record if it has one, else the file | `surfactin synthetase A` |
| `gene_record_id` | gene record, when its id isn't the protein number | (for tropA: `TSTA_117750`) |
| `locus_tags` | the file's part 4, when it isn't the protein number; a list, because one RefSeq number can stand for the same protein in several genomes | (for tropA: `TSTA_117750`) |
| `locations` | the file's parts 0, 2 and 3, one per place the file lists the protein (a repeat in one cluster gives two) | `BGC0000433:8558-19312:+` |
| `sequence_length`, `sequence_md5` | the file's sequence | `3584`, `f8ecefd278c1a5e646f54a819dedd2ae` |
| `found_in` | where the node came from | `gene_records\|protein_file` |

**The new counts,** which `tidy` prints along with the old ones (alphabetically,
so they're mixed in):

| Count | Meaning |
|---|---|
| `protein_file_records` | Proteins in the file |
| `protein_file_records_not_active` | Of those, proteins of entries that aren't active (left out) |
| `protein_file_insdc_id`, `protein_file_refseq_id`, `protein_file_other_id` | Proteins of active entries, by the kind of their number (part 6) |
| `protein_file_repeats_in_entry` | The same protein listed twice in one cluster: one node, both positions |
| `protein_file_version_differs` | Entries whose version in the file differs from the JSON; should be 0 |
| `proteins_added_by_curators` | Proteins that are in the file because of `to_add` |
| `proteins_removed_by_curators` | Proteins left out because of `to_delete` |
| `to_delete_not_found` | Removal names that matched no protein (listed) |
| `genes_found_by_id`, `genes_found_by_product` | Gene records matched by rule 1, by rule 2 |
| `genes_not_in_protein_file` | Gene records not matched (listed) |
| `genes_given_a_protein_number` | Gene records named by a locus tag or name that now have an INSDC or RefSeq number |
| `entries_with_proteins` | Active entries with at least one `ENCODES` arrow |

You'll run it in Step 8, after the tests.

---

## 10. Step 6. ID mapping at scale

[`src/microbegraph/sources/uniprot.py`](../src/microbegraph/sources/uniprot.py)
needs no new logic: it reads every `ncbiprotein:` node from MIBiG's table, so the
new proteins are asked about automatically. What changes is how many there are:
about 39,000 instead of 4,089.

At 1,000 ids per job that would be 40 jobs and well over a hundred requests.
Posting a big pile of letters works the same way: if the post office takes sacks
of up to 100,000 letters, you don't send forty small bags. UniProt's ID mapping
accepts up to 100,000 ids in one job (<https://www.uniprot.org/help/id_mapping>),
so `BATCH_SIZE` goes from 1,000 to 10,000. That's five jobs, the same number
Phase 3 used: four for the INSDC numbers and one for the RefSeq ones. Each results
table is at most a few megabytes.

Why not one job of 100,000? A job that fails costs the whole job, so five moderate
jobs lose less when one goes wrong, and each one still finishes in about a
minute. The adapter's other limits stay as they were: one request a second, a status
question every three seconds, at most 100 questions per job.

---

## 11. Step 7. Tests built from real records

1. **The sample protein file.**
   [`tests/fixtures/mibig/mibig_prot_seqs_sample.fasta`](../tests/fixtures/mibig/mibig_prot_seqs_sample.fasta)
   starts with surfactin's 23 proteins, copied line for line from the real file,
   then made-up proteins for the made-up entries. Each made-up protein exists for
   one case the real ones don't cover:

   | Made-up protein(s) | The case |
   |---|---|
   | `XYZ99960.1`, label `TESTI_00060` | A gene record named only by its locus tag gains a protein number |
   | `XYZ99980.1`, product `TstQ` | A gene record named `tstQ` matches one product |
   | `XYZ99981.1`, `XYZ99982.1`, both `TstY` | A gene record named `tstY` matches two, so stays unmatched |
   | `XYZ99990.1`, `XYZ99991.1` (`TstD`), `XYZ99992.1` and `XYZ99993.1` (`LOC999001` isoforms) | Removals by number, by product, by word in the product |
   | (no protein) | A removal, `tstZ`, that names a gene the file doesn't show, so it's listed as not found |
   | `WP_999999970.1`, twice | The same protein at two positions in one cluster |
   | `XYZ99970.1`, in BGC9999901 and BGC9999903 | One protein in two clusters |
   | `ctg1_orf7` | A gene the curators added |
   | `XYZ99902.1`, in BGC9999902 | A protein of an entry that isn't active |

   BGC9999901 gained three gene records and the `to_add` and `to_delete` lists to
   go with them, and says so in its `comment` field.
   [`tests/fixtures/README.md`](../tests/fixtures/README.md) lists every record.
2. **The test archive comes with the sample.** `build_archive()` in
   [`tests/conftest.py`](../tests/conftest.py) now puts the sample next to the
   archive under the real file's name, because the tidy reads both.
3. **Run the tests:**

   ```bash
   pytest
   ```

   ```
   .............................................................................. [ 36%]
   .............................................................................. [ 73%]
   .........................................................                      [100%]
   213 passed in 1.74s
   ```

   (The time varies by computer, and the number of dots on a line depends on how
   wide your terminal window is.)
4. **Run the style checker:**

   ```bash
   ruff check .
   ```

   Expected: `All checks passed!`

**What the new tests promise** (in
[`tests/test_mibig_protein_file.py`](../tests/test_mibig_protein_file.py)):

* a header in the seven-part shape is read part by part, and one in any other
  shape is refused, never guessed at;
* the product gets its spaces back, and the fingerprint is the MD5 of the letters;
* a gene is found by number or label, or by one matching product, and two matching
  products are ambiguous; a removal is found by number, product or word in the
  product, and part of a word isn't a word;
* surfactin's cluster encodes all 23 proteins, keeping the gene records' details,
  and `CATALYZES` still comes only from gene records;
* a locus tag gains its protein number, a name matching one product becomes that
  protein, and an ambiguous one stays its own node and is listed;
* the curators' removals are left out and listed with their reasons, and a gene
  they added arrives from the file;
* one protein twice in a cluster is one node with both positions; one protein in
  two clusters is one node with two arrows;
* proteins of an entry that isn't active are left out and counted;
* the counts add up, and the tidy refuses to run without the protein file;
* a fetch brings both files, checks the protein file against the pinned SHA-256,
  throws away one that doesn't match and never overwrites a different one;
* the probe checks the size without reading the file, warns if it changed, and
  names newer files on the server;
* UniProt is now asked about every numbered protein, and the batch size stays
  inside UniProt's limit.

✅ **Checkpoint.** `pytest` ends with `213 passed` and no `failed`; `ruff check .`
says `All checks passed!`.

---

## 12. Step 8. Run it for real

1. **Probe MIBiG.** Nothing is downloaded:

   ```bash
   python -m microbegraph.fetch --probe --source mibig
   ```

   The real output from a run on 2026-10-12, after the fetch in item 2 (so the
   protein file is already in the locker). Zenodo was busy for a moment, so this
   run also shows one automatic retry:

   ```
   [mibig] probe
     [mibig] attempt 1 of 5 failed (https://zenodo.org/api/records/14169073 answered HTTP 504 (busy or temporarily broken)); trying again in 2 s
     pinned release : MIBiG 4.0, Zenodo record 14169073
     record page    : https://zenodo.org/records/14169073
     title          : The Minimum Information about a Biosynthetic Gene Cluster (MIBiG) data repository
     version        : 4.0
     published      : 2024-11-15
     licence        : cc-by-4.0
     file           : mibig_json_4.0.tar.gz (9.5 MB)
     checksum       : matches the pinned MD5
     in your locker : yes, 9.5 MB, verified
     protein file   : mibig_prot_seqs_4.0.fasta from https://dl.secondarymetabolites.org/mibig/
     size           : 31,833,799 bytes, the pinned size (last changed Fri, 15 Nov 2024 12:35:03 GMT)
     newer files    : the server also offers mibig_json_5.0rc1.tar.bz2 (not used until an upgrade is made on purpose)
     in your locker : yes, 30.4 MB, verified
     WARNING: A newer MIBiG release exists on Zenodo: version 4.0.1, https://zenodo.org/records/14835872
       This project stays on 4.0 until an upgrade is made on purpose (docs/03-ingestion-mibig.md, section 16, 'Upgrading MIBiG later').
   ```

   The `attempt 1 of 5 failed ... HTTP 504` line is Zenodo saying "busy, try
   later". The probe waited 2 seconds and asked again, the retry rule from Phase 1,
   so you only see it when a server has a bad moment. Most runs don't have it.

   The nine lines after it and the warning are Phase 1's: it's the same 4.0.1
   warning Phase 1 showed, and [`ROADMAP.md`](ROADMAP.md#watching-the-sources) says
   why the project stays on 4.0. Warnings are printed after all the facts, so it
   now comes last. The four lines from `protein file` on describe the protein
   file. `the pinned size` is the check that matters: if MIBiG ever replaces the
   file, this line becomes a warning. `newer files` is the MIBiG 5.0 release
   candidate. The second `in your locker` line is about the protein file: before
   the fetch in item 2 it says `not yet (run the fetch)`, and afterwards
   `yes, 30.4 MB, verified`.
2. **Fetch and tidy MIBiG:**

   ```bash
   python -m microbegraph.fetch --source mibig
   ```

   The archive is already in the locker; the protein file is downloaded once
   (the counter climbs to 30.4 MB). The real output:

   ```
   [mibig] fetch
     [mibig] mibig_json_4.0.tar.gz is already in the locker and verified, nothing to download
     [mibig] already_present: data/raw/mibig/mibig_json_4.0.tar.gz (9.5 MB, 3013 records), provenance logged
     [mibig] downloading mibig_prot_seqs_4.0.fasta
         30.4 MB of 30.4 MB (100%)
     [mibig] downloaded: data/raw/mibig/mibig_prot_seqs_4.0.fasta (30.4 MB, 46987 proteins), provenance logged
   [mibig] tidy
     [mibig] wrote mibig_nodes.csv and mibig_edges.csv
       bioactivities_not_observed              66
       bioactivities_observed                2937
       catalyzes_in_multi_compound_entries   3324
       compound_name_collisions                 4
       compounds_read                        4294
       entries_active                        2437
       entries_predicted_or_unstated         1629
       entries_skipped_status                 576
       entries_with_experimental_evidence     808
       entries_with_gene_records              452
       entries_with_proteins                 2437
       files_not_mibig4                         0
       files_read                            3013
       files_unreadable                         0
       genes_found_by_id                     4661
       genes_found_by_product                  17
       genes_given_a_protein_number           452
       genes_in_biosynthesis                 1991
       genes_insdc_id                        3994
       genes_not_in_protein_file               59
       genes_other_id                         648
       genes_other_roles                      522
       genes_read                            4737
       genes_refseq_id                         95
       genes_role_not_stated                 2224
       genes_without_id                         0
       property_conflicts                     275
       protein_file_insdc_id                36784
       protein_file_other_id                  925
       protein_file_records                 46987
       protein_file_records_not_active       6978
       protein_file_refseq_id                2300
       protein_file_repeats_in_entry            2
       protein_file_version_differs             0
       proteins_added_by_curators             661
       proteins_removed_by_curators            18
       to_delete_not_found                      4
   ```

   MIBiG 4.0 and the protein file are both pinned, so your numbers should be
   exactly these.

   **Sanity checks on your numbers:**

   * the file's proteins split into the four kinds:
     `protein_file_records = protein_file_records_not_active + protein_file_insdc_id + protein_file_refseq_id + protein_file_other_id`
     (46,987 = 6,978 + 36,784 + 2,300 + 925);
   * every gene record with an id is matched once or listed:
     `genes_found_by_id + genes_found_by_product + genes_not_in_protein_file = genes_read - genes_without_id`
     (4,661 + 17 + 59 = 4,737);
   * every active entry has proteins: `entries_with_proteins` equals
     `entries_active` (2,437);
   * the Phase 3 counts haven't moved: `genes_read` is still 4,737,
     `genes_in_biosynthesis` still 1,991, `property_conflicts` still 275.

   Across the release that gives:

   | | Phase 3 | Phase 3b |
   |---|---|---|
   | `Protein` nodes | 4,737 | 40,037 (39,053 `ncbiprotein:`, 984 `mg.protein:`) |
   | `ENCODES` arrows | 4,737 | 40,048, all `database_assertion` |
   | `CATALYZES` arrows | 4,492 | 4,492 |
   | All MIBiG arrows | 19,252 | 54,563 |

   The arithmetic behind the arrows: 46,987 proteins in the file, less 6,978 in
   pending entries, less 18 removed by the curators, less 2 repeats, gives 39,989;
   the 59 gene records that aren't in the file add theirs, making 40,048. There
   are 11 fewer nodes than arrows because 11 proteins sit in two clusters each.
   `mibig_nodes.csv` grows to about 15 MB and `mibig_edges.csv` to about 7 MB.

3. **Where each protein came from:**

   ```bash
   python -c "import json, pandas as pd; n = pd.read_csv('data/processed/staging/mibig_nodes.csv', dtype=str, keep_default_na=False); p = n[n.node_type == 'Protein']; print(len(p), 'Protein nodes'); print(p.properties.map(lambda s: json.loads(s)['found_in']).value_counts().to_string())"
   ```

   ```
   40037 Protein nodes
   properties
   protein_file                 35300
   gene_records|protein_file     4678
   gene_records                    59
   ```

   35,300 come from the file alone, 4,678 from both (4,661 + 17), and 59 from gene
   records alone.
4. **Surfactin's cluster:**

   ```bash
   python -c "import json, pandas as pd; n = pd.read_csv('data/processed/staging/mibig_nodes.csv', dtype=str, keep_default_na=False); e = pd.read_csv('data/processed/staging/mibig_edges.csv', dtype=str, keep_default_na=False); ids = e[(e.source_id == 'mibig:BGC0000433') & (e.edge_type == 'ENCODES')].target_id; p = n[n.node_id.isin(ids)].copy(); p['found_in'] = p.properties.map(lambda s: json.loads(s)['found_in']); print(p[['node_id', 'name', 'found_in']].to_string(index=False))"
   ```

   ```
                  node_id                      name                  found_in
   ncbiprotein:CAE02619.1              YciC protein              protein_file
   ncbiprotein:CAE02620.1              Yx01 protein              protein_file
   ncbiprotein:CAE02621.1              YckC protein              protein_file
   ncbiprotein:CAE02622.1              YckD protein              protein_file
   ncbiprotein:CAE02623.1              YckE protein              protein_file
   ncbiprotein:CAE02624.1                       Nin              protein_file
   ncbiprotein:CAE02625.1                      NucA              protein_file
   ncbiprotein:CAE02626.1              HxlB protein              protein_file
   ncbiprotein:CAE02627.1              HxlA protein              protein_file
   ncbiprotein:CAE02628.1 transcriptional regulator              protein_file
   ncbiprotein:CAE02629.1              Xy02 protein              protein_file
   ncbiprotein:CAE02630.1                     srfAA gene_records|protein_file
   ncbiprotein:CAE02631.1                     srfAB gene_records|protein_file
   ncbiprotein:CAE02632.1                      comS gene_records|protein_file
   ncbiprotein:CAE02633.1                     srfAC gene_records|protein_file
   ncbiprotein:CAE02634.1                     srfAD gene_records|protein_file
   ncbiprotein:CAE02635.1         amino transferase              protein_file
   ncbiprotein:CAE02636.1                      ycxc gene_records|protein_file
   ncbiprotein:CAE02637.1                      ycxD gene_records|protein_file
   ncbiprotein:CAE02638.1                       sfp gene_records|protein_file
   ncbiprotein:CAE02639.1                      yczE gene_records|protein_file
   ncbiprotein:CAE02640.1              YckI protein              protein_file
   ncbiprotein:CAE02641.1              YckJ protein              protein_file
   ```

   23 proteins in a row along the DNA. The nine gene records keep their gene
   names; the other 14 are named by their product. (`CAE02635.1`, "amino
   transferase", sits between srfAD and ycxc and has no gene record.)
5. **The curators' removals:**

   ```bash
   python -c "import json; s = json.load(open('data/processed/staging/mibig_summary.json')); print('\n'.join(r['entry'] + '  ' + r['to_delete'] + ' -> ' + r['protein'] + ' (' + r['matched_by'] + ')' for r in s['removed_by_curators'])); print('not found:', ', '.join(r['to_delete'] for r in s['to_delete_not_found']))"
   ```

   ```
   BGC0000966  AFD30968.1 -> AFD30968.1 (id)
   BGC0000966  AFD30967.1 -> AFD30967.1 (id)
   BGC0000966  AFD30966.1 -> AFD30966.1 (id)
   BGC0000966  CrmK -> AFD30946.1 (product)
   BGC0000966  AFD30945.1 -> AFD30945.1 (id)
   BGC0000966  CrmF -> AFD30958.1 (product)
   BGC0002390  LOC100382880 -> NP_001314933.1 (word in product)
   BGC0002390  LOC100193898 -> XP_008681210.1 (word in product)
   BGC0002390  LOC100193898 -> NP_001346253.1 (word in product)
   BGC0002390  LOC100273419 -> NP_001141328.1 (word in product)
   BGC0002390  LOC100273419 -> XP_035823698.1 (word in product)
   BGC0002390  LOC100273419 -> XP_020408751.1 (word in product)
   BGC0002390  LOC100273419 -> XP_035823699.1 (word in product)
   BGC0002390  LOC100273419 -> XP_035823697.1 (word in product)
   BGC0002390  LOC100273419 -> XP_008681441.1 (word in product)
   BGC0002390  LOC100273419 -> XP_008681439.1 (word in product)
   BGC0002390  LOC100273419 -> NP_001347178.1 (word in product)
   BGC0002390  LOC100502279 -> NP_001183685.1 (word in product)
   not found: LOC100272490, LOC103626198, LOC103626199, LOC103626200
   ```

   18 proteins behind 10 of the 14 names. The four names not found are maize genes
   whose numbers don't appear anywhere in the zealexin entry's headers, so the
   file alone can't say which proteins they are (section 15).
6. **A locus tag that gained a number:**

   ```bash
   python -c "import json, pandas as pd; n = pd.read_csv('data/processed/staging/mibig_nodes.csv', dtype=str, keep_default_na=False).set_index('node_id'); r = n.loc['ncbiprotein:EED18001.1']; p = json.loads(r.properties); print(r['name'], '|', {k: p[k] for k in ['protein_id', 'gene_record_id', 'locus_tags', 'product', 'functions', 'found_in']})"
   ```

   ```
   tropA | {'protein_id': 'EED18001.1', 'gene_record_id': 'TSTA_117750', 'locus_tags': 'TSTA_117750', 'product': 'NR-PKS', 'functions': 'Scaffold biosynthesis', 'found_in': 'gene_records|protein_file'}
   ```

   In Phase 3 this was `mg.protein:bgc0000154-tsta-117750`. The gene record's
   product ("NR-PKS") is kept, rather than the file's ("polyketide synthase,
   putative").
7. **Probe UniProt:**

   ```bash
   python -m microbegraph.fetch --probe --source uniprot
   ```

   ```
   [uniprot] probe
     release        : 2026_03 (published 02-September-2026)
     ID mapping     : offers both identifier types used here (EMBL-GenBank-DDBJ_CDS, RefSeq_Protein)
     to ask about   : 36,769 INSDC and 2,284 RefSeq protein ids from MIBiG, 5 jobs
     in your locker : 1 finished fetch(es), newest 2026-10-12T090322Z (2026_03)
   ```

   `5 jobs` is four jobs for the INSDC numbers (10,000 each, the last one
   shorter) and one for the RefSeq numbers.
8. **Fetch UniProt.** This is the slow one: each job of 10,000 ids takes UniProt
   from a few seconds to a little over a minute.

   ```bash
   python -m microbegraph.fetch --source uniprot
   ```

   The real output from 2026-10-12. The folder name is the moment the fetch
   started, so yours will differ, and UniProt is a live database, so your counts
   may differ slightly:

   ```
   [uniprot] fetch
     [uniprot] mapping 36,769 INSDC protein ids in 4 batches of up to 10,000
     [uniprot] data/raw/uniprot/2026-10-12T101526Z/insdc_001_results.tsv (8,029 rows for 10,000 ids)
     [uniprot] data/raw/uniprot/2026-10-12T101526Z/insdc_002_results.tsv (4,433 rows for 10,000 ids)
     [uniprot] data/raw/uniprot/2026-10-12T101526Z/insdc_003_results.tsv (5,307 rows for 10,000 ids)
     [uniprot] data/raw/uniprot/2026-10-12T101526Z/insdc_004_results.tsv (2,041 rows for 6,769 ids)
     [uniprot] mapping 2,284 RefSeq protein ids in 1 batch of up to 10,000
     [uniprot] data/raw/uniprot/2026-10-12T101526Z/refseq_001_results.tsv (1,103 rows for 2,284 ids)
     [uniprot] downloaded: data/raw/uniprot/2026-10-12T101526Z/ (10 answers, 6.6 MB), provenance logged
   [uniprot] tidy
     [uniprot] wrote uniprot_nodes.csv and uniprot_edges.csv
       results_files_read            5
       ids_asked                 39053
       ids_asked_insdc           36769
       ids_asked_refseq           2284
       ids_mapped                20671
       ids_not_mapped            18382
       ids_with_several_entries     82
       uniprot_entries           20507
       entries_from_several_ids    349
       entries_reviewed           2692
       entries_with_ec_number     5081
       entries_with_function      3848
   ```

   The rows per job are uneven (8,029, 4,433, 5,307, then 2,041) because the ids
   are sorted, so each job holds a different stretch of numbers, and some
   stretches map far better than others. As in Phase 3, the project doesn't guess
   why a given number is missing; it lists them all. Each status check is three
   seconds apart, so the longest job (26 checks) took UniProt a little over a
   minute; the whole fetch took about four
   minutes. All 23 of surfactin's proteins map: `CAE02619.1`, "YciC protein", for
   example, is `uniprot:Q70KK8`, 425 amino acids, the same length the protein file
   gives.

   **What the counts mean** is the same as in Phase 3
   ([`05-proteomics-uniprot.md`, Step 7](05-proteomics-uniprot.md#11-step-7-run-it-for-real)).

   **Sanity checks on your numbers:**
   * `ids_asked` equals the total in the probe's `to ask about` line
     (36,769 + 2,284 = 39,053);
   * `ids_mapped + ids_not_mapped` equals `ids_asked` (20,671 + 18,382 = 39,053);
   * the 4,089 numbers from Phase 3 are among those asked, so `ids_mapped` is at
     least as large as Phase 3's 2,449, unless UniProt removed entries in between
     (it didn't: the 1,640 numbers Phase 3 couldn't map are still unmapped, and the
     rest still map);
   * `uniprot_entries` is `ids_mapped`, plus the extra entries of numbers with
     several, minus the extra numbers of entries reached from several
     (20,671 + 242 - 406 = 20,507). This prints the two extras:

     ```bash
     python -c "import json, pandas as pd; s = json.load(open('data/processed/staging/uniprot_summary.json')); n = pd.read_csv('data/processed/staging/uniprot_nodes.csv', dtype=str, keep_default_na=False); print('extra entries:', sum(len(v) - 1 for v in s['ids_with_several_entries'].values()), '| extra ids:', sum(len(json.loads(p)['mibig_protein_ids'].split('|')) - 1 for p in n.properties))"
     ```

     ```
     extra entries: 242 | extra ids: 406
     ```

9. **Rebuild every table offline**, to make sure all six sources still tidy
   together:

   ```bash
   python -m microbegraph.fetch --tidy-only --all
   ```

   Every source prints its counts again and nothing is downloaded.
10. **Write your numbers down.** Copy the counts from `mibig_summary.json` and
    `uniprot_summary.json` into the Phase 3b entry of
    [`CHANGELOG.md`](../CHANGELOG.md). The changelog only states numbers that a
    real run produced.

✅ **Checkpoint.** `data/raw/mibig/` holds both files; `data/raw/uniprot/` holds
a new finished snapshot; `data/processed/staging/` holds the tables of all six
sources; the sanity checks add up.

---

## 13. Step 9. Pictures, the Handbook and the records

**The pictures.** Three new diagrams, all drawn by
`docs/img/make_illustrations.py`: one protein record part by part
(`fasta_header.svg`), the three steps for each cluster with the real counts
(`protein_file_matching.svg`), and the protein layer before and after this phase
(`protein_file_coverage.svg`, in section 1). The sources map, the ID mapping
picture and the protein layer picture mention the protein file, and the
interactive explorers say where `Protein` nodes and `ENCODES` arrows now come
from.

**At the end of this phase,** as at the end of every phase:

1. In `docs/phases.csv` (in VS Code), Phase 3b's `status` is `done`.
2. Re-run both picture scripts:

   ```bash
   python docs/img/make_illustrations.py
   python docs/interactive/make_interactive.py
   ```

   The first prints `Done: 22 figures in docs/img/`.
3. In `docs/HANDBOOK.md`: Stage 6b is ✅ and Stage 7 is ⏳, with the version,
   date and repository state at the top updated, and a change-log line.
4. The same status change is in the README build log and `docs/ROADMAP.md`.
5. Add the Phase 3b entry to `CHANGELOG.md`, with your numbers from Step 8.
6. Commit all of it in the phase commit (section 18).

---

## 14. How evidence and confidence are decided for the new arrows

![The four evidence levels, strongest first](img/evidence_ladder.svg)

| Arrow | Source | Evidence level | Confidence | Why |
|---|---|---|---|---|
| `ENCODES` | MIBiG's protein file | `database_assertion` | the entry's grade | MIBiG states which proteins the cluster has; nobody recorded an experiment on each one |
| `ENCODES` | MIBiG gene record (Phase 3) | `database_assertion` | the entry's grade | The same statement, from the other list; for the same protein it's the same arrow |
| `CATALYZES` | MIBiG gene record only | as in Phase 3 | the entry's grade | Only a gene record says what job a gene does |

The arrow's `citation` is the references MIBiG gives for the cluster, and its
`source_record_id` is the entry's accession, exactly as for the gene records'
arrows. When one protein sits in two clusters, it gets two `ENCODES` arrows, one
from each cluster, each with its own entry's grade and references.

A removal never becomes a negative arrow. MIBiG's curators say the gene isn't part
of the cluster, so there's no arrow, and the summary keeps the reason. That's the
same choice Phase 1 made for activities that were tested and not seen.

---

## 15. What the protein layer still doesn't cover

| Gap | How big | What happens to it |
|---|---|---|
| Gene records the file doesn't name | 59, in 9 entries (for example `baeB` in the bacillaene cluster BGC0001089, `mscA` in BGC0001019, and the three zealexin genes in BGC0002390); listed in `mibig_summary.json` | They keep their Phase 3 `mg.protein:` nodes, so in those 9 entries a protein can appear twice (once by gene name, once by number). Phase 4's ledger matches them using UniProt's gene names for the cluster's proteins, or MIBiG's GenBank file, and records each merge |
| Removals the file doesn't name | 4, all maize genes in BGC0002390; listed | The zealexin cluster keeps 7 of the file's proteins (the 4 unresolved removals among them), plus zx5, zx6 and zx7 as gene-record nodes (row above), where the curators describe 3. Phase 4 resolves the four names through NCBI's gene records |
| Protein numbers UniProt can't map | 18,382 of the 39,053 numbers asked about (16,965 INSDC, 1,417 RefSeq), on UniProt release `2026_03` | Listed in `uniprot_summary.json`; their `ncbiprotein:` nodes stay, with MIBiG's product and the sequence fingerprint |
| Proteins of pending entries | 6,978, in 199 entries | Left out on purpose, as for every pending entry; they would arrive only through a planned upgrade to a release in which those entries are active |
| Sequences | 40,009 sequences of active entries (46,987 in the file) | Kept in the locker, not in the tables; each node has its length and MD5 |
| MIBiG's GenBank file (`mibig_gbk_4.0.tar.gz`, 79.8 MB) | Not read | Not needed for the protein layer; Phase 4 may read it for the 59 unmatched gene records and 4 removals above |
| Jobs for the new proteins | 35,300 proteins come from the file alone | `ENCODES` only. A job needs a gene record (or, later, a cited source) |

**MIBiG 5.0 is in testing.** The download server already offers
`mibig_json_5.0rc1.tar.bz2`, a release candidate of MIBiG 5.0, dated 21 September
2026. The project stays on 4.0. When 5.0 is final and on Zenodo, the upgrade is a
planned change of its own, archive and protein file together, following
[`03-ingestion-mibig.md`, section 16](03-ingestion-mibig.md#16-upgrading-mibig-later)
([`ROADMAP.md`](ROADMAP.md#watching-the-sources) keeps the note).

---

## 16. What could go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Tidy: `... mibig_prot_seqs_4.0.fasta is not in the evidence locker yet` | The protein file hasn't been fetched | `python -m microbegraph.fetch --source mibig` (only the protein file is downloaded) |
| Fetch: `... arrived with SHA-256 ..., but this project pinned ...` | The download was damaged, or MIBiG replaced the file | Run it again. If it repeats, run `--probe`: a size different from the pinned one means the file changed. Look at the new file before moving the pin |
| Probe: `The download server lists mibig_prot_seqs_4.0.fasta at ... bytes, but this project pinned 31,833,799` | MIBiG replaced the file | Don't fetch. Run the capture (Step 2) on the new file and compare before changing anything |
| Fetch: `... exists but its SHA-256 is ..., not the pinned ...` | A different file with the same name is in `data/raw/mibig/` | Move it somewhere else yourself (the locker never overwrites), then fetch again |
| Tidy: `... has N header(s) that aren't in the seven-part shape` | The file isn't the pinned one, or it was edited | Move the file out of `data/raw/mibig/` yourself, then run `python -m microbegraph.fetch --source mibig`. Never edit files in the locker |
| Probe: `Could not ask MIBiG's download server about the protein file` | Offline, or a network that blocks the server | Check your connection; at work, try another network |
| `capture_mibig_protein_samples.py` stops with `FAILED: ... 403` | A proxy or allowlist blocks `dl.secondarymetabolites.org` | Run it on a network that reaches the server |
| `UniProt job ... was still running after 100 checks` | UniProt is very busy with a large job | Run the fetch again later; the unfinished folder is ignored |
| `pytest` fails in `test_mibig_protein_file.py` with a count one higher or lower | A fixture file was changed by hand | Restore the fixtures from Git: `git checkout -- tests/fixtures` |
| The sample's fingerprint doesn't match the README on Windows | The file was written with Windows line endings | Delete it (`Remove-Item tests\fixtures\mibig\mibig_prot_seqs_sample.fasta`), restore it from Git (`git checkout -- tests/fixtures/mibig/mibig_prot_seqs_sample.fasta`), and check the SHA-256 again; `.gitattributes` keeps it byte for byte from then on |
| VS Code is slow on `mibig_nodes.csv`, or turns off its colouring | It's 15 MB now | Look at it with the commands in Step 8 instead |

---

## 17. Checkpoint

You have finished this phase when you can answer these without scrolling up:

1. What's the difference between MIBiG's gene records and its protein file, and
   which arrows does each give?
2. Why does the protein file give no `CATALYZES` arrows?
3. The download server lists no checksum. How is the protein file still pinned,
   and how does the probe notice a change without downloading it?
4. Which of the curators' corrections had to be applied by the code, and why not
   the other?
5. Why is a gene record matched by product only when exactly one protein has it,
   while a removal may match several?
6. In Phase 3, `TSTA_117750` became `mg.protein:bgc0000154-tsta-117750`. What is
   it now, and why does that matter for UniProt?
7. Why keep an MD5 of each sequence instead of the sequence?
8. Why did the batch size for UniProt go up, and why not to the maximum?

<details>
<summary>Answers (open after you've tried)</summary>

1. Gene records are notes on some genes (452 entries), with their jobs; they give
   `ENCODES` and, for building jobs, `CATALYZES`. The protein file lists every
   protein of every active cluster (2,437 entries), with no jobs; it gives `ENCODES`.
2. It says which proteins a cluster has, not what any of them does.
3. Its SHA-256 and size were measured on the first download and written into the
   code. Every fetch must match the SHA-256. The probe asks for the file, reads
   only the reply's headers (`Content-Length`, `Last-Modified`) and compares the
   size with the pinned one.
4. `to_delete`: the file still lists the removed genes. `to_add` is already in the
   file, sequences included.
5. A gene record is one protein, so two candidates mean the code can't tell which;
   guessing could merge two proteins. A removal names a gene, and one gene can have
   several proteins (isoforms), all of which go.
6. `ncbiprotein:EED18001.1`, because the file gives the protein number for that
   locus tag. A worldwide number can be sent to UniProt; a locus tag can't.
7. The tables stay small (the sequences add up to about 25 million letters),
   and two proteins with the same fingerprint have the same sequence, which is what
   Phase 4 needs. The sequences stay in the locker.
8. About 39,000 numbers at 1,000 a job would mean 40 jobs. UniProt allows up to
   100,000; 10,000 keeps it to five jobs, and a failed job costs less than one huge
   one would.

</details>

**Files that should now exist:** every file in the table in
[section 1](#1-what-this-phase-builds-in-one-picture), plus, on your machine only,
the files under `data/`.

---

## 18. Committing this phase

Run the tests and the safety gate, then commit, push, and sync. Each phase goes
into a single commit; the second `-m` adds a short description under the title
line.

```bash
git switch develop
git add -A                    # stage first, so the gate can see the new files

git status --short            # .env must NOT be listed
pytest                        # must end with "passed" and no "failed"
ruff check .                  # must say "All checks passed!"
./check-public-safe.sh        # must print "SAFE TO PUSH"
                              # Windows: bash check-public-safe.sh

git commit -m "feat: add every cluster's proteins from MIBiG's protein file" -m "MIBiG's protein FASTA pinned by its own SHA-256 and read for every active cluster: Protein nodes and ENCODES arrows, the curators' removals applied and listed, gene records matched to protein numbers, UniProt ID mapping at 10,000 ids per job, tests from real records, and the guide, Handbook and pictures for Phase 3b."
git push origin develop develop:beta develop:master
## --tags is optional, only when a release tag was created (not in this phase)

# bring local master in step with the remote master just updated
git switch master
git pull --ff-only origin master
git switch develop
```

Then open the **Actions** tab on GitHub and wait for the green ticks (about five
minutes).

---

**Next:** Phase 4, `06-entity-resolution-graph-build.md`: entity resolution and
the graph build. The proteins arrive there with everything it needs: the UniProt
entries each `ncbiprotein:` node maps to, the sequence fingerprints, and the lists
of gene records and removals this phase couldn't match. The plan is in the
[Handbook, Stage 7](HANDBOOK.md#stage-7-entity-resolution-and-the-graph-build-phase-4).
