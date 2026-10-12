# Changelog

What changed in MicrobeGraph, with the newest changes at the top.

**How to read this.** Each release has a version number like `1.2.3`
(*major.minor.patch*). The first number changes when a release breaks something
on purpose or the project changes shape, the second when a capability is added,
and the third for fixes only. Work that hasn't been released yet sits under
*Unreleased*. There's a fuller explanation in
[`docs/GIT-WORKFLOW.md`, section 8](docs/GIT-WORKFLOW.md#8-tags-marking-a-release).

**How to update it.** Add a line under *Unreleased* in the same commit as the
change. When a release is tagged, rename *Unreleased* to the version and date,
and start a new, empty *Unreleased* above it. The
[Handbook](docs/HANDBOOK.md#how-this-handbook-is-maintained) lists the steps.

---

## Unreleased (toward 1.0.0)

### Phase 3b: every cluster's proteins, MIBiG's protein file

- **Added** MIBiG's protein file to the MIBiG adapter
  (`src/microbegraph/sources/mibig.py`): `mibig_prot_seqs_4.0.fasta`, from MIBiG's
  download server, fetched beside the archive and pinned by its SHA-256
  (`4b196343...0717e8b`) and size (31,833,799 bytes), measured on its first
  download because the server lists no checksum. The probe checks the size from
  the server's headers without downloading, and names newer MIBiG files on the
  server. A fetch now writes two provenance rows.
- **Added** `src/microbegraph/sources/mibig_proteins.py`, which reads the file
  (seven-part FASTA headers, refused in any other shape) and matches curators'
  names to proteins: by number or label, by one matching product, and for
  removals by a word inside the product.
- **Changed** the MIBiG tidy: every protein of every active entry becomes a
  `Protein` node with an `ENCODES` arrow; the curators' removals (`to_delete`)
  are left out and listed with their reasons in `mibig_summary.json`; each gene
  record is matched to its protein in the file, so a gene record named only by a
  locus tag or gene name is named after the file's protein number when there is
  one. Proteins gain `locations`, `locus_tags`, `sequence_length`,
  `sequence_md5`, `gene_record_id` and `found_in`. `CATALYZES` is unchanged.
  Fifteen new counts.
- **Changed** the UniProt adapter to 10,000 ids per job (UniProt allows 100,000),
  so about 39,000 protein numbers still take five jobs.
- **Added** to the socket (`sources/base.py`): a download can be checked against a
  SHA-256 this project pinned, with the same four safety rules as the MD5.
- **Added** 30 tests (213 in all), built from a sample of the protein file:
  surfactin's 23 real proteins copied line for line, and made-up proteins for
  each special case (`tests/fixtures/mibig/mibig_prot_seqs_sample.fasta`). The
  capture script `tests/fixtures/capture_mibig_protein_samples.py` downloads and
  surveys the real file.
- **Added** the Phase 3b guide (`docs/05b-all-cluster-proteins.md`), three
  pictures (`fasta_header.svg`, `protein_file_matching.svg`,
  `protein_file_coverage.svg`), the new terms in the glossary, and a
  *Watching the sources* section in the roadmap (MIBiG 4.0.1 on Zenodo, a MIBiG
  5.0 release candidate on the download server, the CI image change). The sources
  map, the ID mapping picture, the protein layer picture and the interactive
  explorers mention the protein file.
- **Measured on the first run** (2026-10-12, from `mibig_summary.json` and
  `uniprot_summary.json`):
  - *The file:* 46,987 proteins in 2,636 entries; 6,978 belong to 199 pending
    entries and are left out. The 40,009 in active entries are numbered 36,784 by
    INSDC, 2,300 by RefSeq and 925 otherwise. All 661 genes added by curators are
    in the file; 18 proteins removed by curators were left out (4 by number, 2 by
    gene name, 12 by NCBI gene number inside a product), and 4 removal names match
    nothing in the file (listed). 2 proteins appear twice in one cluster.
  - *Gene records:* 4,661 matched by number or label, 17 by product, 59 not in the
    file (listed, in 9 entries); 452 gene records named only by a locus tag or
    gene name gained a protein number.
  - *MIBiG's tables:* 40,037 `Protein` nodes (39,053 `ncbiprotein:`, 984
    `mg.protein:`) and 40,048 `ENCODES` arrows, up from 4,737 each; all 2,437
    active entries have proteins; 11 proteins sit in two clusters. MIBiG's arrows
    grow from 19,252 to 54,563. The Phase 1 and Phase 3 counts are unchanged.
  - *UniProt* (release `2026_03` of 02-September-2026, 10 answers, 6.6 MB,
    about 4 minutes): 39,053 protein ids asked about in 5 jobs (36,769 INSDC,
    2,284 RefSeq). 20,671 mapped and 18,382 didn't (16,965 INSDC, 1,417 RefSeq;
    all listed). That gives 20,507 UniProt entries, 2,692 of them reviewed, 5,081
    with an EC number and 3,848 with a description of function. 82 ids map to
    more than one entry, and 349 entries are reached from more than one id. All
    23 of surfactin's proteins map; the 1,640 ids Phase 3 couldn't map still
    don't.

### Phase 3: the proteomics layer, MIBiG's gene records and UniProt

- **Added** gene records to the MIBiG adapter (`src/microbegraph/sources/mibig.py`):
  every gene an entry lists becomes a `Protein` node, named `ncbiprotein:<id>`
  for an INSDC or RefSeq protein number and `mg.protein:<entry>-<id>` for a locus
  tag or gene name, with an `ENCODES` arrow from its cluster. Genes whose job
  builds the molecule (scaffold biosynthesis, precursor biosynthesis, tailoring)
  also get a `CATALYZES` arrow to each compound of the entry, at
  `curated_experimental` when MIBiG records an experiment for the job. Ten new
  counts in `mibig_summary.json`.
- **Added** the UniProt adapter (`src/microbegraph/sources/uniprot.py`): every
  INSDC and RefSeq protein number goes through UniProt's ID mapping service,
  1,000 per job, kept as a dated snapshot (each job's answer and its results
  table). Every UniProt entry found becomes a `uniprot:` node with its names,
  organism, length, EC numbers and function, and remembers the MIBiG protein
  number it was found through; every id that didn't map is listed in
  `uniprot_summary.json`.
- **Added** the `ncbiprotein` identifier prefix to the rulebook
  (`src/microbegraph/ontology.py`, `docs/02-ontology-and-data-model.md`).
- **Added** to the socket (`sources/base.py`): a GET can be told not to follow a
  redirect, which UniProt's job status needs.
- **Changed** the plan after a survey of the real data, made before any adapter
  code by `tests/fixtures/capture_uniprot_samples.py`: UniProt doesn't
  cross-reference MIBiG (the roadmap said it did), so the join goes through
  protein numbers; and only 452 of the 2,437 active entries have gene records, so
  Phase 3b (every cluster's proteins, from MIBiG's protein file) is added to the
  roadmap and the Handbook as the next phase.
- **Added** 39 tests (183 in all), built from seven real UniProt answers
  captured on 2026-10-12, with their real status codes and headers
  (`tests/fixtures/uniprot/`); the surfactin test record now keeps its real gene
  records, and two made-up records cover the other cases.
- **Added** the Phase 3 guide (`docs/05-proteomics-uniprot.md`), four pictures
  (`protein_layer.svg`, `gene_jobs.svg`, `idmapping_flow.svg`,
  `protein_coverage.svg`), UniProt in the
  data sources and licences table, srfAA in the interactive evidence chain, and
  the new terms in the glossary. The sources picture now shows six sources.
- **Measured on the first run** (2026-10-12, from `mibig_summary.json` and
  `uniprot_summary.json`):
  - *MIBiG gene records:* 452 of the 2,437 active entries have them, 4,737 in
    all: 3,994 named by an INSDC protein id, 95 by a RefSeq id and 648 by a locus
    tag or gene name, none without an id. 1,991 genes have a job that builds the
    molecule, 522 only other jobs and 2,224 no job recorded. That gives 4,737
    `Protein` nodes, 4,737 `ENCODES` arrows and 4,492 `CATALYZES` arrows (1,482
    `curated_experimental`, 3,010 `database_assertion`), of which 3,324 come from
    entries that list more than one compound. MIBiG's arrows grow from 10,023 to
    19,252; the Phase 1 counts are unchanged.
  - *UniProt* (release `2026_03` of 02-September-2026, 10 answers, 777.6 KB):
    4,089 protein ids asked about in 5 jobs (3,994 INSDC, 95 RefSeq). 2,449
    mapped and 1,640 didn't (1,574 INSDC, 66 RefSeq; all listed in the summary).
    That gives 2,442 UniProt entries, 360 of them reviewed, 683 with an EC number
    and 524 with a description of function. Five RefSeq ids map to two entries
    each, and twelve entries are each reached from two ids.
  - A second run the same day reused the snapshot and asked UniProt nothing.

### Phase 2: more sources, PubChem · NCBI Taxonomy · KEGG · the cited bridge

- **Added** the PubChem adapter (`src/microbegraph/sources/pubchem.py`): it asks
  about every CID MIBiG records, 100 at a time by POST, slows down when PubChem's
  traffic light turns, and writes `pubchem.compound` nodes with formula, weights,
  structure, synonyms, KEGG and ChEBI numbers, and the MIBiG compounds that gave
  each CID.
- **Added** the NCBI Taxonomy adapter (`src/microbegraph/sources/ncbi_taxonomy.py`):
  the family tree of every MIBiG organism and bridge pathogen, as `MEMBER_OF`
  arrows through the main ranks, with merged and deleted taxids handled and
  counted. Organisms get a `group` property (Bacteria, Fungi, Oomycetes...)
  instead of the `kingdom` the data model first planned, because NCBI now uses
  "kingdom" as a real rank for bacteria.
- **Added** the KEGG adapter (`src/microbegraph/sources/kegg.py`):
  `PARTICIPATES_IN` arrows from compounds to the pathway maps they appear on,
  leaving out maps of maps. KEGG is for academic use only, so its rows are never
  published.
- **Added** the curated bridge loader (`src/microbegraph/sources/curation.py`) and
  the first eight cited rows in `curation/compound_pathogen_crop.csv`, from six
  papers, with thirteen checks on every row. The file gained five columns
  (`pathogen_type`, `disease`, `crop_scientific_name`, `crop_category`,
  `added_on`); `curation/README.md` explains each column, the confidence scale,
  and how to add a row.
- **Added** snapshots for web APIs (`src/microbegraph/sources/api.py`): every fetch
  is a dated folder of answers saved byte for byte, a provenance row per answer,
  and a manifest written last; the same questions on the same day reuse the
  folder.
- **Added** private settings (`src/microbegraph/settings.py`): the optional NCBI
  key is read from `.env`, sent only in a POST body, and shown only as "set" or
  "not set".
- **Added** POST requests to the socket (`sources/base.py`); error messages name
  the address without anything sent with it.
- **Added** `src/microbegraph/staging.py`, which checks the twelve rules before
  writing any source's tables.
- **Changed** the safety gate to also catch keys written as `NAME_API_KEY=...`,
  in JSON, or in a web address, and its copy in `docs/01-setup.md` to match.
- **Changed** `--list` to show each licence on its own line, and the sources now
  run in dependency order: MIBiG, PubChem, NCBI Taxonomy, KEGG, the bridge.
- **Added** 71 tests (144 in all), built from ten real answers captured from
  PubChem, NCBI and KEGG on 2026-10-12 by `tests/fixtures/capture_samples.py`;
  `tests/fixtures/README.md` lists each with its fingerprint, and
  `.gitattributes` keeps their bytes exact on every system.
- **Changed** the running example to grey mould on jujube (Xiao et al. 2023),
  because no paper could be found that tested surfactin against grey mould on
  strawberry. The figures, the interactive evidence chain and the guides follow.
- **Added** the Phase 2 guide (`docs/04-more-sources-secrets.md`), a data sources
  and licences section in the README, three pictures (`sources_map.svg`,
  `secrets_env.svg`, `api_snapshot.svg`), and the new terms in the glossary.
- **Measured on the first run** (2026-10-12, from the four new `*_summary.json`
  files in `data/processed/staging/`):
  - *PubChem:* 1,176 CIDs asked about in 24 requests (2.1 MB). 1,171 found and 5
    not known to PubChem (listed in the summary, for Phase 4 to look into).
    Of those found, 1,072 have other names, 131 a KEGG number and 717 a ChEBI
    number. One request was answered `HTTP 502` and succeeded on the retry.
  - *NCBI Taxonomy* (build `Build261011-2030.1`, with a key, 9 requests,
    5.4 MB): 1,485 taxids asked about (1,480 organisms and 6 pathogens, one of
    them in both), all found, 7 of them under a newer number. That gives 2,441
    organism nodes joined by 2,433 `MEMBER_OF` arrows, and 4 pathogen nodes. Two
    pathogens are also organisms, *Fusarium graminearum* and *Botrytis
    cinerea*, left for Phase 4 to reconcile.
  - *KEGG* (pathway and compound releases of 2026/10/09, 4 requests, 528 KB):
    587 maps and 19,689 compound-to-map links. Of our 131 compounds with a KEGG
    number, the links give 85 `PARTICIPATES_IN` arrows to 39 maps; 104 links to
    maps of maps were left out, and 56 of our KEGG numbers are on no map.
  - *The bridge:* 8 rows, 7 `INHIBITS` and 7 `INFECTS` arrows from 6 papers;
    every row passed all thirteen checks, including NCBI's current names.
  - A second run the same day reused all three snapshots and asked the services
    nothing; the provenance log holds no key.

### After Phase 1: the test workflow

- **Changed** `.github/workflows/ci.yml` to use version 7 of `actions/checkout`
  and `actions/setup-python`. The first run warned that the versions it used
  (`checkout@v4`, `setup-python@v5`) are built for Node.js 20, which GitHub is
  retiring.
- **Changed** every CI job to stop after 20 minutes, and the code checkout to
  leave no login behind on the borrowed machine.
- **Added** a picture of what one test run does (`docs/img/ci_checks.svg`), and
  instructions for starting a run by hand and for keeping the workflow's actions
  current (`docs/03-ingestion-mibig.md`, section 13). The first push of Phase 1
  started no run by itself; it was started by hand and passed on all seven jobs.
- **Changed** the branch-model picture to say the tests run whenever `master`
  changes, which is what the workflow does.

### Phase 1: ingestion, the MIBiG backbone

- **Added** the source-adapter framework: one contract (`probe`, `fetch`, `tidy`)
  that every data source follows (`src/microbegraph/sources/base.py`).
- **Added** the MIBiG 4.0 adapter (`src/microbegraph/sources/mibig.py`), pinned to
  Zenodo record 14169073 and verified against its published MD5 checksum on every
  download.
- **Added** the evidence locker (`data/raw/`, never edited) and the append-only
  provenance log (`data/raw/provenance.csv`).
- **Added** the twelve rules of the ontology as code (`src/microbegraph/validate.py`);
  every adapter checks its own output before writing it.
- **Added** the command `python -m microbegraph.fetch` (`--list`, `--probe`,
  `--source`, `--all`, `--tidy-only`).
- **Added** offline tests with four MIBiG-layout test records (one cut down from
  the real archive, three invented and labelled as such) and a fake server, and
  continuous integration on Windows, macOS, Linux and RHEL 8.
- **Added** `pyproject.toml` and `src/microbegraph/__init__.py`; the project now
  installs with `pip install -e .`.
- **Removed** the unused top-level `sources/` and `figures/` placeholder folders,
  left over from an early version of the setup steps.
- **Added** `.gitattributes`, so shell scripts keep Linux line endings on every
  computer and the safety gate runs on Windows.
- **Decided** how MIBiG's evidence maps onto our evidence levels: organism and
  cluster arrows are `curated_experimental` only when MIBiG records an experiment
  for the cluster (knock-out, heterologous expression...), otherwise
  `database_assertion`; MIBiG's quality grade becomes the confidence.
- **Added** the Handbook (`docs/HANDBOOK.md`), the teaching diagrams
  (`docs/img/`), three interactive explorers (`docs/interactive/`), and the plan
  as data (`docs/phases.csv`).
- **Changed** `check-setup.py` to verify the package installation, to stop
  requiring `data/` and `app/` folders, which a fresh clone does not have, and to
  require Python 3.11 or newer (scikit-learn 1.9 no longer supports 3.10).
- **Changed** the lockfile command to `pip freeze --exclude-editable`.
- **Fixed** documentation: release numbering (Phase 19 cuts release 3.0, Phase 13
  cuts release 2.0), the effort table totals, edge examples with a missing column,
  stale phase references in the data model guide, and a stray `sources/` folder in
  the setup instructions.
- **Found on the first real run:** the published `mibig_json_4.0.tar.gz` is a
  plain, uncompressed tar archive, despite its name (its MD5 matches the one
  Zenodo lists, so it is the published file). Archives are now read by their
  contents, whatever the compression, and a fetch always writes its provenance
  row before anything else can stop it, so the locker never holds a file the log
  doesn't know about. Five new tests cover both.
- **Found on the first real run, too:** MIBiG 4.0 writes an activity's name either
  as an object (`{"activity": "antibacterial"}`, sometimes with a curator's
  comment) or as plain text. Only plain text was expected, which split one
  activity into two nodes. Both styles are now read into the same node,
  curators' comments are kept on the compound as `activity_notes`, and the
  surfactin test record is now a cut-down copy of the real record from the
  archive. Two new tests cover it.
- **Measured on the first run** (2026-10-10, from
  `data/processed/staging/mibig_summary.json`): 3,013 records in the archive
  (10,004,480 bytes); 2,437 active entries and 576 skipped as not active; of the
  active ones, 808 with experimental evidence and 1,629 predicted or unstated;
  4,294 compound records read; 2,937 observed bioactivities, and 66 negative
  results kept out of the graph; 4 compound-name collisions kept apart and 275
  property conflicts left for Phase 4. No unreadable or foreign files. The graph
  tables hold 74 activities and 10,023 arrows: 2,437 `HARBORS`, 4,283
  `PRODUCES`, 2,774 `HAS_ACTIVITY` and 529 `BELONGS_TO`.

### Phase 0: design

- **Added** the architecture, setup guide, ontology and data model, roadmap, git
  workflow, prior-art survey, R setup, container guides and glossary.
- **Added** the pre-push safety gate (`check-public-safe.sh`) and the setup check
  (`check-setup.py`).
