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
