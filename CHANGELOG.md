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
