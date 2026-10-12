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

### Phase 4b: closing the gaps, with GenBank, PubChem names and a review file

- **Added** MIBiG's GenBank file to the MIBiG adapter: `mibig_gbk_4.0.tar.gz`
  (2,636 records, 79.8 MB) from MIBiG's download server, pinned by its SHA-256
  (`43543f9c...e834b`) and size (83,652,126 bytes) like the protein file, probed
  by its size, and read by a new reader, `src/microbegraph/sources/mibig_genbank.py`
  (CDS features only, and only the qualifiers that name a gene or its protein;
  about four seconds for the whole file). A gene record or a curators' removal
  that neither the protein number nor the product finds is now looked up among
  the names each CDS goes by (gene name, locus tag, old locus tag, gene
  synonyms, NCBI gene number). A fetch now writes three provenance rows.
- **Changed** the MIBiG adapter to keep every value when entries disagree: the
  first stays under the property's name, and `<property>_by_entry` lists each
  value with its entry.
- **Changed** the PubChem adapter to ask in three rounds: every number MIBiG
  gives (including the second numbers in `pubchem_cid_by_entry`) and every
  number in the review file; a name search for compounds whose own numbers
  don't list their name, and for those with no number but a formula; then the
  numbers the search found. When PubChem stops answering in round 2 (round 3
  then waits) or round 3, the snapshot is finished incomplete with every
  name-search answer, tidy leaves out answers whose numbers round 3 hadn't
  described, and the next run carries round 1 and the answers over; a refusal
  in the first round says so in plain words. PubChem nodes gain
  `found_by_name`, `names_matching_mibig` (from PubChem's full list of names)
  and `synonym_count`.
- **Added** PubChem's names file to the name search. PubChem refuses a computer
  after about 400 web name searches, whatever their pace, so with more than 300
  names, or once the file is in the locker, the search reads
  `CID-Synonym-filtered.gz` from PubChem's download area instead: downloaded
  once into `data/raw/pubchem/` and logged, then searched line by line on your
  computer by a new module, `src/microbegraph/sources/pubchem_names.py` (exact
  match, ignoring the capitals A to Z and spaces at either end; the first 1,000 lines must
  look like a number, a tab and a name). The answers are saved 500 to a file
  (`names_from_file_NNN.json`), each marked with the file and the start of its
  SHA-256, and are carried over after a stop in round 3 only while that same
  file is in the locker. A short list (300 names or fewer, no file yet) still
  goes to PubChem's web search (`POST .../compound/name/cids/JSON`), one name a
  second. The provenance log gains a third outcome, `derived`, for answers
  worked out on your computer from a downloaded file, and the probe shows the
  size and date of PubChem's copy of the file and whether the locker has it.
- **Changed** the compound rules (`src/microbegraph/resolution/compounds.py`)
  to judge every candidate number on four clues: the name under MIBiG's own
  number; the name under another record of the same structure (the first block
  of the InChIKey); the name search with an agreeing formula; the formula alone,
  which no longer counts when the name search points at another molecule or
  MIBiG's entries disagree about the formula. New ledger rules
  `pubchem_numbers_differ` and `pubchem_name_search`; every PubChem join's
  grounds now name the clue that decided it ("Confirmed by name.", "Confirmed
  by the formula alone." and so on). The NPAtlas rule refuses a
  disputed formula too.
- **Added** the review file, `curation/resolution_decisions.csv`, read by
  `src/microbegraph/resolution/reviewed.py`: decisions a person made (`join` or
  `keep_apart`), each with a reason, a citation and a date, checked line by line,
  applied before the rules that join compounds and proteins, and recorded in
  the ledger as `reviewed_by_hand`. A pair kept apart can never meet through a
  chain of joins (`Groups.forbid`), and keeping apart two records already
  joined by rows above is refused. The
  first five rows keep 2-methylisoborneol and desosamine apart from the records
  they were wrongly joined to, and CBF82293.1 apart from UniProt's P0CU77 and
  P0CU78.
- **Added** `curation/activity_synonyms.csv`, read by
  `src/microbegraph/resolution/activities.py`: four activity words folded into
  the word they mean the same as (ledger rule `activity_synonym`).
- **Fixed** the gene-name rule's reading of UniProt's gene names: it split
  them on spaces and semicolons, but the UniProt adapter joins them with `|`,
  so an entry with more than one gene name never matched (baeI's entry Q1RS74
  lists "baeI|PV946_13250"). Some of Phase 4's 21 leftover gene records were
  left over for that reason; the rule has nothing left to match now, since the
  GenBank file places all of them.
- **Fixed** a circular import: `import microbegraph.staging` failed on its own.
  The table shapes, safe writers and `SourceError` moved to
  `src/microbegraph/tables.py`; `sources/base.py` still offers them, and the
  resolver no longer loads any source adapter.
- **Added** `python tests/fixtures/capture_gap_samples.py`, the look at the
  evidence before the code, with a `--fixture` mode that cuts surfactin's
  GenBank record into `tests/fixtures/mibig/genbank/`; the resolver's test slice
  gains 12 clusters and its own `curation/` folder; two real PubChem name-search
  answers join the fixtures. The survey looks names up in PubChem's names file
  once the fetch has downloaded it; before that it stops and says why, unless
  `--web` asks PubChem's web service anyway.
- **Added** 60 tests (356 in all), mostly in `tests/test_closing_the_gaps.py`;
  the Phase 4b guide (`docs/06b-closing-the-gaps.md`); cookbook recipes R20 to
  R22; four pictures (`gaps_closed.svg`, `genbank_record.svg`,
  `clue_ladder.svg`, `review_row.svg`) and an interactive page of real cases
  (`resolution_cases.html`); new glossary terms; the Handbook's Stage 7b.
- **Measured** (2026-10-12):
  - *MIBiG:* the GenBank file's 46,987 CDS match the protein file's 46,987
    proteins; 59 gene records found through it (21 that no rule had placed and
    38 that UniProt's gene names had), so 511 gene records now carry a protein
    number and none is left without; 4 removals found through it (22 in all,
    none left); 278 disagreements kept, as 194 `_by_entry` properties on 120
    nodes (structures 109, masses 49, PubChem numbers 17, formulas 16, two
    proteins' gene names and one product). 29 of the 49 masses differ by less
    than 0.01, often only in the last digits.
  - *PubChem:* round 1, 1,193 numbers in 24 requests (5 not in PubChem); the
    names file, 931 MB (976,534,762 bytes, last changed by PubChem on
    27 September 2026), downloaded once; 1,655 names searched in a few
    minutes: 1,201 found under one number, 47 under several, 2 under more than
    10, 405 not found; round 3, 1,320 numbers in 28 requests. 2,508 compounds
    in all (2,409 with other names, 214 with a KEGG number, 1,772 with a ChEBI
    number). On the 673 names both had answered, the names file and PubChem's
    web search gave the same answer every time.
  - *KEGG:* 214 of our compounds have a KEGG number (131 before), giving 142
    `PARTICIPATES_IN` arrows to 53 maps.
  - *Resolver:* 71,901 identifiers in; 4 activity words folded; 5 decisions by
    hand; PubChem joins by MIBiG's own numbers 1,029 (82 by the formula alone),
    by the name search 928, for shared numbers 9, and where entries give
    different numbers 11; refused 116, 385, 13 and 19 respectively; 1 NPAtlas
    pair; 20,626 protein numbers joined to UniProt and 40 left with tied
    entries; 220 identical sequences; the gene-name rule found nothing left to
    do.
  - *Out:* 48,239 nodes (Activity 70, Compound 3,826, Pathway 53, Protein
    39,354) and 57,014 arrows (66 combined, 25 dropped with entries left out);
    827 entries left out; a ledger of 25,741 rows. DuckDB and NetworkX agree on
    every count. 1,978 of MIBiG's 3,842 compounds share a node with a PubChem
    record.
  - *Before the name search* (the day's first build, with the PubChem snapshot
    from Phase 2): 70,550 identifiers, 48,236 nodes, 56,987 arrows, 353 left
    out, a ledger of 23,937 rows, 1,102 compounds with a PubChem record and 322
    joins on the formula alone.
- **The PubChem run took four runs on 2026-10-12.** The web name search was
  refused (HTTP 429) after 372 of 1,655 names, at one name a second, after an
  earlier survey at four a second had been refused after about 400; that's
  what moved the search into the names file. The next run downloaded the file
  and searched every name, then PubChem refused round 3, still blocking the
  computer. A third run got two round-3 answers and was stopped by hand, so it
  left an unfinished folder that fetch and tidy ignore. Four hours after the
  refusal the same command carried round 1 and the search over and PubChem
  answered all of round 3.
- **Known limits:** ferrichrome joined PubChem's 644246, "[55Fe] Ferrichrome",
  through the same-structure clue, which compares the first block of the
  InChIKey and so can't see isotopes (PubChem files the name under 121489511);
  82 joins still rest on the formula alone, because PubChem's names file
  doesn't know those names; 34 compounds' names are filed under several
  equally good records, and 129 compounds were refused by the clues, each for
  a person to read; pyrrolomycin, a general name, shares pyrrolomycin A's
  record on the formula alone; 5 KEGG maps are left without an arrow; the
  ledger's sentence for the 409 PubChem records only the name search found
  lists no compounds ("(; see their pubchem_number rows)"); the names file is
  PubChem's "filtered" selection, so a name only the web search knows would be
  missed (none was, on the 673 names compared), and its search folds only the
  capitals A to Z.
- **Planned, from what this phase found:** ferrichrome's record, every
  PubChem number an entry lists as a candidate (17 compounds list two in one
  entry, and only the first is used today), the ledger's sentence for records
  only the name search found, and the maps left without an arrow, all before
  Phase 5; NPAtlas as a
  second, independent witness for the 82 joins the name search can't settle;
  gene names from the GenBank file as protein labels (Phase 5).

### Phase 4: entity resolution, the resolution ledger, and the graph build

- **Added** the resolver, `python -m microbegraph.resolve`
  (`src/microbegraph/resolve.py` and the `src/microbegraph/resolution/`
  package). It reads all six sources' staging tables and applies ten rules in a
  fixed order: one node for one identifier from several sources; organisms moved
  from NCBI's merged numbers; an Organism that is also a Pathogen becomes one
  Pathogen node; MIBiG's PubChem numbers joined only where the name or formula
  confirms them, and a number shared by several MIBiG names only where each name
  is confirmed; MIBiG compounds with the same NPAtlas number and formula joined;
  protein numbers joined to their UniProt entry (organism, then sequence length,
  then review status choosing between several); identical sequences in one
  organism joined; gene records named only by a gene name joined through
  UniProt's gene names. Records are grouped with union-find, a group never holds
  two PubChem or two UniProt entries, and the identifier from the most specific
  authority names each node, with the others kept as aliases. Every arrow is
  re-pointed, and arrows that become one are combined, keeping the strongest
  evidence. The twelve rules run on the merged tables, and nothing is written if
  any fails, or if any identifier that disappeared lacks a ledger row.
- **Added** the resolution ledger (`data/processed/resolution_ledger.csv`): one
  row per decision, merged, moved, combined, kept apart or left out, with its
  rule and its grounds in a sentence. A refused PubChem number moves to
  `pubchem_cid_not_confirmed`, and the node notes why.
- **Added** the graph build, `python -m microbegraph.build_graph`
  (`src/microbegraph/build_graph.py`): DuckDB
  (`data/processed/microbegraph.duckdb`) with `nodes`, `edges`, `ledger`,
  `sources` and `build_info` tables, the ontology as database rules (primary key,
  foreign keys, CHECK lists built from `ontology.py`), one view per node type and
  an `aliases` view; the NetworkX graph rebuilt from it (`load_graph()`) and
  compared type by type. All of it happens in a temporary file, swapped in only
  when the counts agree, so a failed build leaves the previous database as it
  was.
- **Added** `python -m microbegraph.query` (`src/microbegraph/query.py`), which
  runs a cookbook recipe or your own SQL on the database, read-only, and
  `docs/QUERY_COOKBOOK.md`: SQL in ten minutes, 19 SQL recipes and 5 NetworkX
  recipes, each run by the tests (the Python ones also pasted into an
  interactive prompt, the way the cookbook says to run them).
- **Changed** the ontology: a Pathogen is a kind of Organism (`SUBTYPE_OF` and
  `is_a()` in `src/microbegraph/ontology.py`; rule 8 in `validate.py` accepts a
  kind of a type). The NCBI Taxonomy adapter gives every pathogen its family tree
  (12 more ancestors and 16 more `MEMBER_OF` arrows on the real data).
- **Added** 83 tests (296 in all): `tests/test_resolve.py`,
  `tests/test_build_graph.py`, `tests/test_query.py`, built from a real slice of
  all six sources around 22 chosen clusters (`tests/fixtures/resolve/`, cut by
  `tests/fixtures/capture_resolution_samples.py`, which also has a `--survey`
  mode that counts the duplicates in your own tables).
- **Added** the Phase 4 guide (`docs/06-entity-resolution-graph-build.md`), five
  pictures (`resolution_flow.svg`, `pubchem_check.svg`, `uniprot_choice.svg`,
  `ledger_row.svg`, `two_shapes.svg`), the new terms in the glossary, and Phase
  4b in the roadmap and the Handbook (Stage 7b). The ontology map shows that a
  Pathogen is a kind of Organism, and the interactive explorers name srfAA's node
  by its UniProt entry.
- **Measured on the first run** (2026-10-12, from `resolve_summary.json` and the
  build's output):
  - *In:* 72,092 node rows for 70,613 identifiers from the six sources (MIBiG
    47,907, PubChem 1,171, NCBI Taxonomy 2,457, KEGG 39, UniProt 20,507, the
    bridge 11), and 57,111 arrows.
  - *Organisms:* 1,478 identifiers described by more than one source; 7 moved to
    NCBI's current number (3 of them onto a number MIBiG also uses); 2 given both
    roles (*Fusarium graminearum*, *Botrytis cinerea*). 130 organisms take NCBI's
    current name, with MIBiG's kept as another name.
  - *Compounds:* of 1,186 PubChem numbers MIBiG gives, 1,097 confirmed (637 by
    name and formula, 135 by name, 325 by formula) and 64 refused; of 10 numbers
    shared by two MIBiG names, 8 names confirmed and 12 not; 5 numbers PubChem
    doesn't have. 3 pairs joined by NPAtlas number and formula, 7 kept apart.
  - *Proteins:* 20,629 protein numbers joined to a UniProt entry (20,589 with one
    entry; of 82 with several, 33 decided by organism, 2 by length, 5 by review
    status) and 42 left with tied entries; 220 identical sequences in one organism
    joined and 9 kept apart because UniProt keeps them separate; 38 gene records
    joined through UniProt's gene names, 21 listed for Phase 4b.
  - *Out:* 48,264 nodes (Activity 74, Compound 3,836, CompoundClass 37, Crop 5,
    GeneCluster 2,437, Organism 2,451, Pathogen 6, Pathway 39, Protein 39,379)
    and 57,012 arrows (96 combined, 3 dropped with left-out entries); 347 PubChem
    and UniProt entries left out; a ledger of 23,989 rows. DuckDB and NetworkX
    agree on every count.
- **Known limit, for Phase 4b:** 325 of the PubChem joins rest on the formula
  alone, and a formula only confirms a number when MIBiG didn't copy it from
  that same PubChem record. Most are right; a few aren't (MIBiG's
  "2-methylisoborneol" carries a bromine compound's formula). Recipe R19 lists
  them; Phase 4b, above, takes them up.

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
