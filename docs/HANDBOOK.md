[← README](../README.md) · [Glossary](GLOSSARY.md) · [Architecture](00-architecture.md) · [Roadmap](ROADMAP.md) · [Git workflow](GIT-WORKFLOW.md) · [Changelog](../CHANGELOG.md)

# The MicrobeGraph Handbook: from day 0 to the finished product

![MicrobeGraph: from a microbe's genes to a crop's disease, with the evidence for every arrow](img/cover_microbegraph.svg)

**Handbook version:** 1.5 · **Last updated:** 2026-10-12 · **Repository state it
describes:** Phase 0 (design and setup), Phase 1 (MIBiG ingestion), Phase 2
(PubChem, NCBI Taxonomy, KEGG and the cited bridge), Phase 3 (the proteomics
layer: MIBiG's gene records and UniProt) and Phase 3b (every cluster's proteins,
from MIBiG's protein file) built and tested; Phase 4 (entity resolution and the
graph build) next.

**Read this document first, and come back to it whenever you lose your place.**
It follows the whole journey in order: understanding the project, setting up a
blank computer, building every phase, cutting each release, and running the
finished product. For each step it tells you what you are about to do, why that
step exists, which document has the detail, roughly how long it takes, and how
you'll know you are done. I wrote it so that nobody should have to hunt through
the repository to work out what comes next; if you ever find yourself doing that,
I count it as a defect in this handbook.

The intended reader is someone with no background in microbiology, chemistry,
databases, Python, Git or the command line who wants to end up able to build,
run, explain and extend the whole application. Every term is defined in
[`GLOSSARY.md`](GLOSSARY.md), and I'd keep that open in a second tab.

The stages are numbered and meant to be done in order. Each one ends with a
checkpoint, and you should pass it before moving on. In the tables, ✅ means built
and tested, ⏳ means next, and ⬜ means planned; the status column below describes
the repository exactly as it stood on the date at the top.

---

## Contents

- [The project in one minute](#the-project-in-one-minute)
- [The journey at a glance](#the-journey-at-a-glance)
- [Stage 0. Understand what you are building and why](#stage-0-understand-what-you-are-building-and-why)
- [Stage 1. Set up your workshop, once per computer](#stage-1-set-up-your-workshop-once-per-computer)
- [Stage 2. Version control and the end-of-phase ritual](#stage-2-version-control-and-the-end-of-phase-ritual)
- [Stage 3. The rulebook (Phase 0)](#stage-3-the-rulebook-phase-0)
- [Stage 4. Ingestion: the MIBiG backbone (Phase 1)](#stage-4-ingestion-the-mibig-backbone-phase-1)
- [Stages 5-12. Release 1.0, the science (Phases 2-9)](#release-10-the-science)
- [Stages 13-16. Release 2.0, the platform (Phases 10-13)](#release-20-the-platform)
- [Stages 17-22. Release 3.0, the product (Phases 14-19)](#release-30-the-product)
- [Stage 23. Running it as a product](#stage-23-running-it-as-a-product)
- [Every session, after setup](#every-session-after-setup)
- [When something goes wrong](#when-something-goes-wrong)
- [Where everything lives: the document map](#where-everything-lives-the-document-map)
- [How this handbook is maintained](#how-this-handbook-is-maintained)

---

## The project in one minute

**The scenario.** Picture a jujube grower who is losing harvested fruit to grey
mould, a fungus called *Botrytis cinerea*, and who would rather not spray more
synthetic fungicide. Some soil bacteria make natural molecules that suppress fungi, so the
grower's question is: which bacteria, making which molecules, have evidence behind
them for *this* disease?

**The problem.** The answer exists, but it's scattered. One public database knows
which bacterium carries which gene cluster and what molecule it makes, another
knows the molecule's chemistry, and another knows how organisms are related. The
last link, "this molecule suppresses that fungus", lives mostly in the text of
scientific papers, so there is no single place where you can walk from the
jujube back to the bacterium.

**The idea.** MicrobeGraph puts every piece into one **knowledge graph**, with dots
for things (microbes, gene clusters, enzymes, molecules, diseases, crops) and
arrows for relationships (*harbors*, *encodes*, *produces*, *inhibits*, *infects*),
and answers questions by walking the arrows. Once drawn, a fact checked by a
curator looks exactly like a fact guessed by software, so **every arrow carries its
evidence**: where it came from and how strongly it is known.

If that sounds abstract, think of a city transport map. It draws stations and
lines instead of writing facts out in sentences, and you find a route by following
the lines. MicrobeGraph is a transport map from microbes to crops in which every
line also says who surveyed it.

**What you end up with.** By the last stage you have a tested pipeline that
rebuilds the graph from public sources with one command, statistical checks that
the patterns are not chance, machine learning that suggests missing links (clearly
labelled as hypotheses), a public app, an API, a modern web frontend, an AI
assistant connection, and the whole thing runnable in containers with one command.
Since the repository is also the tutorial, you should come out of it able to
explain every one of those parts.

---

## The journey at a glance

![The journey: every phase from Phase 0 to Phase 19, grouped into three releases, with status and hours](img/journey_map.svg)

If you prefer a timeline you can hover over, open
[`interactive/roadmap_timeline.html`](interactive/roadmap_timeline.html) in a browser
for the same plan.

| Stage | What | Phase | Hands-on time | Status | Guide |
|---|---|---|---|---|---|
| 0 | Understand what you are building and why | 0 | 1.5 h reading | ✅ | [README](../README.md), [architecture](00-architecture.md), [roadmap](ROADMAP.md) |
| 1 | Set up your workshop, once per computer | 0 | 2-3 h | ✅ | [`01-setup.md`](01-setup.md) |
| 2 | Version control and the end-of-phase ritual | 0 | 30 min | ✅ | [`GIT-WORKFLOW.md`](GIT-WORKFLOW.md) |
| 3 | The rulebook: ontology and data model | 0 | 1 h | ✅ | [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md) |
| 4 | Ingestion: the MIBiG backbone | 1 | 7-9 h | ✅ | [`03-ingestion-mibig.md`](03-ingestion-mibig.md) |
| 5 | More sources: PubChem, NCBI Taxonomy, KEGG, the curated bridge | 2 | 6-8 h | ✅ | [`04-more-sources-secrets.md`](04-more-sources-secrets.md) |
| 6 | The proteomics layer: MIBiG's gene records and UniProt | 3 | 5-7 h | ✅ | [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md) |
| 6b | Every cluster's proteins: MIBiG's protein file | 3b | 4-5 h | ✅ | [`05b-all-cluster-proteins.md`](05b-all-cluster-proteins.md) |
| 7 | Entity resolution and the graph build | 4 | 10-12 h | ⏳ next | `06-entity-resolution-graph-build.md` |
| 8 | Graph analytics | 5 | 8-10 h | ⬜ | `07-graph-analytics.md` |
| 9 | Statistical validation in R | 6 | 6-8 h | ⬜ | `08-statistical-validation-r.md` |
| 10 | Graph machine learning | 7 | 12-14 h | ⬜ | `09-graph-machine-learning.md` |
| 11 | The Streamlit app (+ 11b, the same app in Shiny, optional) | 8, 8b | 10-12 h (+8-10 h) | ⬜ | `10-app-streamlit.md`, `10b-app-shiny.md` |
| 12 | Deployment, GraphRAG and **release 1.0** (+ 12b, one container, optional) | 9, 9b | 10-12 h (+4-5 h) | ⬜ | `11-deployment-graphrag.md`, `11b-one-container.md` |
| 13 | dbt: the ontology becomes tested SQL | 10 | 8-10 h | ⬜ | `12-dbt-transformations.md` |
| 14 | PostgreSQL + Apache AGE + pgvector | 11 | 10-12 h | ⬜ | `13-postgres-age-pgvector.md` |
| 15 | Airflow orchestration | 12 | 10-12 h | ⬜ | `14-airflow-orchestration.md` |
| 16 | Snowflake portability and **release 2.0** | 13 | 6-8 h | ⬜ | `15-snowflake-portability.md` |
| 17 | FastAPI service layer | 14 | 10-12 h | ⬜ | `16-fastapi-service-layer.md` |
| 18 | React + TypeScript frontend | 15 | 14-16 h | ⬜ | `17-react-frontend.md` |
| 19 | MCP server | 16 | 5-6 h | ⬜ | `18-mcp-server.md` |
| 20 | Databricks: literature mining at scale | 17 | 10-12 h | ⬜ | `19-databricks-literature-mining.md` |
| 21 | Containerize the whole application | 18 | 10-12 h | ⬜ | `20-containerize-the-stack.md` |
| 22 | Published images, CD and **release 3.0** | 19 | 6-8 h | ⬜ | `21-cicd-packaging.md` |
| 23 | Running it as a product | after 19 | reading + ongoing | ⬜ | this handbook, [roadmap](ROADMAP.md#what-finished-means-the-product-checklist) |

Guides listed without a link arrive with their phase, and I add the link here as
each one is written. The times are hands-on estimates for a beginner following the
guides. At four to five hours a week, Release 1.0 takes four to five months and
the whole product roughly a part-time year. Every stage ends at a natural stopping
point with everything committed, and **each release is complete on its own**, so
stopping after any of them still leaves you with something whole.

---

## Stage 0. Understand what you are building and why

**What.** Read, in this order:

1. [`README.md`](../README.md), *What is a knowledge graph?* and *The problem this
   project tackles*. Two everyday pictures (a transport map, and a contact list
   compared with a social network) show why the project uses a graph instead of a
   spreadsheet.
2. [`00-architecture.md`](00-architecture.md), every box of the system, what it
   does, why it exists, and the design decisions behind it.
3. [`ROADMAP.md`](ROADMAP.md), the phases you are about to follow, why each tool
   is there, and what I left out on purpose.
4. [`PRIOR-ART.md`](PRIOR-ART.md), what already exists, how this differs, and what
   the project does **not** claim.

After that, open [`interactive/ontology_explorer.html`](interactive/ontology_explorer.html)
in a browser and hover over the dots and arrows.

**Why.** Everything you type later makes more sense once you can say in one
sentence what the project is for: *an open, reproducible map from microbes' genes
to crop diseases, where every arrow says how it is known.* If you skip this stage,
the later ones tend to turn into copying commands without knowing why they are
there.

**Checkpoint.** You're ready to move on when you can explain to a friend, without
notes, what a node and an edge are, why the same molecule can have three names,
why a curated fact and a guessed fact must be kept apart, and what the three
releases are.

---

## Stage 1. Set up your workshop, once per computer

![Set up once per machine, then repeat a short loop](img/setup_flow.svg)

**What.** Work through [`01-setup.md`](01-setup.md) from Step 0 to the end. Every
step shows the commands for Windows, macOS and Linux / RHEL 8 side by side. Along
the way you install Python 3.11 or 3.12, VS Code and Git, create a GitHub account
and connect your computer to it, clone the repository, create the `.venv` toolbox,
install the packages and the project itself, and protect your secrets before you
have any.

**Why.** Setup is the long part, and you only do it once; after that, every session
is the same short loop (see [Every session](#every-session-after-setup)). The guide
has you prove each tool works before adding the next one, so if something breaks,
the problem is in the last thing you did.

**Platform note.** I wanted the project to behave the same on every system, so file
paths are built with Python's `pathlib` and every tool is cross-platform. From
Phase 1 onwards the tests also run automatically on Windows, macOS, Linux and
RHEL 8 at every push, which means a difference between systems can't go unnoticed.

Later in the journey you'll also set up R and RStudio
([`R-SETUP.md`](R-SETUP.md), at Stage 9) and, if you want one, a container engine
([`CONTAINERS.md`](CONTAINERS.md), at Stage 12b or 15).

**Checkpoint.** Your prompt shows `(.venv)`, and running `python check-setup.py`
ends with `All checks passed. Your workshop is ready.`

---

## Stage 2. Version control and the end-of-phase ritual

![Where your work goes: develop, then beta and master](img/git_branch_model.svg)

**What.** Read [`GIT-WORKFLOW.md`](GIT-WORKFLOW.md). You already created the
branches in [`01-setup.md`, Step 10](01-setup.md#12-step-10-the-three-branch-model).

**Why.** Git works like a save-game system for your work. With three branches,
anyone can find a working version while you are busy building the next phase:

| Branch | Holds | You... |
|---|---|---|
| `develop` | Daily work | work here, always |
| `beta` | Finished phases | never edit; the push updates it |
| `master` | What visitors see | never edit; the push updates it, then you sync your copy |

From here on you finish every stage with the **end-of-phase ritual** below. Each
stage tells you which commit message to use.

```bash
git switch develop
git add -A                    # stage first, so the gate sees the new files

pytest                        # from Phase 1 on: must end with "passed"
ruff check .                  # from Phase 1 on: must say "All checks passed!"
./check-public-safe.sh        # must print "SAFE TO PUSH" (Windows: bash check-public-safe.sh)

git commit -m "<the stage's commit message>"
git push origin develop develop:beta develop:master
## --tags is optional, only when a release tag was created in this stage

# bring local master in step with the remote master just updated
git switch master
git pull --ff-only origin master
git switch develop
```

Three stages (12, 16 and 22) also cut a release. For those, add a tag right after
the commit and **replace** the push line with one that sends the tag as well:

```bash
git tag -a v1.0.0 -m "Release 1.0, the science"            # after git commit
git push origin develop develop:beta develop:master --tags  # instead of the plain push
```

You need `--tags` because Git doesn't push tags unless you ask it to. Afterwards,
open **Releases** on GitHub and turn the tag into a release page by pasting in that
version's section of [`CHANGELOG.md`](../CHANGELOG.md).

**Checkpoint.** Running `git branch -a` lists `develop` and `master` locally, and
`origin/master`, `origin/beta` and `origin/develop` remotely.

---

## Stage 3. The rulebook (Phase 0)

![The nine node types, each with an identifier example and an everyday comparison](img/node_types.svg)

**What.** Read [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md):
nine kinds of node, ten kinds of edge, identifiers written as `prefix:number`
(CURIEs), four evidence levels, and the twelve rules every row must obey. The same
rulebook, written as code, lives in [`src/microbegraph/ontology.py`](../src/microbegraph/ontology.py).

![The rulebook as a picture: 9 node types, 10 edge types](img/ontology_map.svg)

**Why.** A graph assembled without a written contract turns into a tangle within
a week. Deciding its shape first is cheap, whereas changing it after thousands of
rows are loaded is expensive. It's the same as agreeing the rules of a board game
before anyone moves a piece.

![The four evidence levels, strongest first](img/evidence_ladder.svg)

**Checkpoint.** Make sure you can name the four-arrow chain from a microbe to a
crop, say which evidence level is a hypothesis, and explain why `326423` is a bad
identifier and `ncbitaxon:326423` a good one. The answers are at the end of the
guide.
**Commit message:** `feat: add the ontology and data model (nodes, edges, evidence)`
*(already done)*.

---

## Stage 4. Ingestion: the MIBiG backbone (Phase 1)

![Phase 1, end to end](img/ingestion_flow.svg)

**What.** Follow [`03-ingestion-mibig.md`](03-ingestion-mibig.md). In that guide
you make the project an installable package, build the "socket" every data source
plugs into, turn the twelve rules into code, write the MIBiG adapter, test
everything offline with labelled sample records and a fake server, switch on
automatic testing on four operating systems, and then download the real MIBiG 4.0
release.

```bash
pip install -e .                                   # once
python -m microbegraph.fetch --probe               # what is out there? (no download)
python -m microbegraph.fetch --source mibig        # download, verify, file, log, tidy
python -m microbegraph.fetch --tidy-only --all     # rebuild tables, offline
pytest                                             # the promises, checked
```

**Why.** Everything downstream needs data, and *how* the data arrives decides how
painful every later phase will be. This stage sets four habits that stay for the
rest of the project: ask servers politely, prove that a download is the file that
was published (checksums), never edit the original (the evidence locker), and
write down every fetch (provenance). It also adds a safety net in the form of
tests that run on every push.

**New ideas in this stage:** APIs and HTTP status codes, timeouts, retries with
backoff, tarballs, JSON, checksums, the evidence locker, provenance, staging tables,
abstract base classes, editable installs, tests and fixtures, continuous
integration.

**Checkpoint.** `pytest` passes; the locker holds `mibig_json_4.0.tar.gz`;
`data/raw/provenance.csv` has a `downloaded` row with MD5
`ce1736f4fac7168d85dae3b37c77d3d2`; `data/processed/staging/` holds the MIBiG
node and edge tables; the **Actions** tab on GitHub is green.
**What you should get:** 3,013 records read, 2,437 of them active, and 10,023
arrows (the counts are explained in
[`03-ingestion-mibig.md`, Step 8](03-ingestion-mibig.md#12-step-8-run-it-for-real)).
From Phase 3 the same tidy also reads gene records, and from Phase 3b MIBiG's
protein file (the fetch then downloads that file too), so it prints more counts
and writes more arrows; Stages 6 and 6b have those numbers.
**Commit message:** `feat: add MIBiG source adapter with evidence locker and provenance log`.
**Estimated time:** 7-9 hours.

**Looking after the automatic tests.** From this stage on, every change to
`master` is tested on seven borrowed machines, following
`.github/workflows/ci.yml`:

![What GitHub does with your code: the trigger, the seven jobs, and the five steps inside each](img/ci_checks.svg)

Between phases, two things can need a moment of attention, and neither means
your code is broken:

* **No run appears after a push.** Start one by hand from the Actions tab
  ([`03-ingestion-mibig.md`, *Starting a run by hand*](03-ingestion-mibig.md#starting-a-run-by-hand)).
* **A finished run lists yellow warnings that an action is being retired.** Move
  `ci.yml` to the newer version
  ([*Keeping the workflow current*](03-ingestion-mibig.md#keeping-the-workflow-current)).
  This happened once already, straight after Phase 1, and the fix was one small
  commit: `ci: move checkout and setup-python to v7`. From Phase 19, GitHub
  proposes these updates by itself.

---

<a id="release-10-the-science"></a>
# Release 1.0, the science (Stages 5-12)

*A working knowledge graph built from real public data, statistically validated,
with machine learning and a public app. This release is complete on its own.*

---

## Stage 5. More sources (Phase 2)

![The sources, one graph: what each needs first, its licence, and what it adds (the sixth, UniProt, arrives in Stage 6)](img/sources_map.svg)

**What.** Follow [`04-more-sources-secrets.md`](04-more-sources-secrets.md). Four
more sources plug into the socket from Phase 1:

* **PubChem** gives each compound MIBiG numbered a precise chemical identity:
  formula, weight, structure, its other names, and its numbers in KEGG and ChEBI.
* **NCBI Taxonomy** gives every organism its family tree, as `MEMBER_OF` arrows
  from strain to species to genus and on up.
* **KEGG** places compounds on its maps of metabolism (`PARTICIPATES_IN`).
* **The curated bridge**, [`curation/compound_pathogen_crop.csv`](../curation/compound_pathogen_crop.csv),
  holds the cited findings no database publishes: which compound acts against
  which crop pathogen. Its first eight rows, from six papers, add the
  `INHIBITS` and `INFECTS` arrows, so the chain finally reaches a crop.

This is also where the project meets its first **API key**: NCBI's free, optional
key, which lives in `.env` on your computer and never in the repository.

```bash
python -m microbegraph.fetch --list                # every source, each with its licence
python -m microbegraph.fetch --probe               # what is out there? (no download)
python -m microbegraph.fetch --all                 # fetch and tidy all five, in order
python -m microbegraph.fetch --tidy-only --all     # rebuild every table, offline
pytest                                             # 144 promises, checked
```

**Why.** The socket gets its first real test: four sources arrive and nothing
written in Phase 1 has to change. Three new habits join the four from Phase 1.
An answer from an API changes from day to day, so each fetch is kept as a dated
**snapshot**, with its own provenance rows. A key is a secret, so it is read from
`.env`, shown only as "set", and sent only inside a request's body. And a
licence is part of the data: KEGG is for academic use only, so its rows stay on
your machine and out of anything published.

![Where a key lives, and where it never goes](img/secrets_env.svg)

**New ideas in this stage:** web APIs, GET and POST, speed limits, API keys,
environment variables and `.env`, snapshots and manifests, sources that build on
each other, licence terms, taxonomy ranks and lineages, synonyms, test records
captured from real answers.

**Open:** [`04-more-sources-secrets.md`](04-more-sources-secrets.md);
[`curation/README.md`](../curation/README.md) for adding a bridge row;
[`01-setup.md`, Step 9](01-setup.md#11-step-9-protect-your-secrets-before-you-have-any) for how `.env` was protected.
**Checkpoint:** `pytest` passes; `data/raw/` holds one finished snapshot each
for PubChem, NCBI Taxonomy and KEGG; `data/processed/staging/` holds the tables of
all five sources; `git status` never lists `.env`; the **Actions** tab is green.
**What you should get:** on the first run (2026-10-12), PubChem knew 1,171 of
the 1,176 compounds asked about; NCBI answered for all 1,485 taxids, giving
2,441 organism nodes and 2,433 `MEMBER_OF` arrows; KEGG gave 85
`PARTICIPATES_IN` arrows to 39 maps. The bridge gives exactly 8 rows, 7
`INHIBITS` and 7 `INFECTS` arrows from 6 papers, every row confirmed against
NCBI. The live sources may give slightly different counts on another day; the
sanity checks are in
[`04-more-sources-secrets.md`, Step 10](04-more-sources-secrets.md#14-step-10-run-it-for-real).
**Commit message:** `feat: add PubChem, NCBI Taxonomy and KEGG adapters and the cited bridge`.
**Estimated time:** 6-8 hours.

---

## Stage 6. The proteomics layer (Phase 3)

![The protein layer: a cluster encodes its enzymes, the enzymes that build the molecule catalyze it, and UniProt says what each enzyme is](img/protein_layer.svg)

**What.** Follow [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md). The
enzymes each gene cluster codes for join the graph as `Protein` nodes, in two
steps:

* **MIBiG's gene records.** Some MIBiG entries list the cluster's genes, each
  with the number of the protein it makes and the job it does. The MIBiG adapter
  now reads them: every gene gives a `Protein` node and an `ENCODES` arrow from
  its cluster, and a gene whose job builds the molecule (scaffold, precursor or
  tailoring) also gives a `CATALYZES` arrow to the molecule.
* **UniProt**, the catalogue of proteins, says what each one is (names, organism,
  length, EC number, function). A sixth adapter asks it through its **ID
  mapping** service: hand in the protein numbers, get a job number, ask until the
  job is finished, collect the results.

```bash
python -m microbegraph.fetch --list                         # six sources now
python -m microbegraph.fetch --tidy-only --source mibig     # MIBiG's tables, now with proteins (offline)
python -m microbegraph.fetch --probe --source uniprot       # UniProt's release, proteins to ask about
python -m microbegraph.fetch --source mibig --source uniprot
pytest                                                      # 183 promises, checked
```

**Why.** The graph goes from two molecular layers to three (genes → proteins →
molecules → disease), so a single walk can now cross genomics, proteomics and
metabolomics. I kept MIBiG's direct `PRODUCES` shortcut because it answers a
different question: the shortcut says which cluster makes a molecule, and the
protein route shows how.

This stage also changed its own plan. A short survey of the real data, run before
any adapter code, showed that UniProt doesn't cross-reference MIBiG at all, so
the join goes through the protein's sequence number instead, and that only 452 of
the 2,437 active MIBiG entries have gene records. The second finding is why Stage
6b exists, and Stage 6b gives every cluster its proteins.

![Asking UniProt: a job with a ticket number](img/idmapping_flow.svg)

**New ideas in this stage:** genes, proteins and enzymes; the jobs genes do in a
cluster; joining two databases through a shared identifier; background jobs,
polling and HTTP redirects; identifiers that only mean something inside one
genome; reporting what a join didn't match.

**Open:** [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md);
[`tests/fixtures/README.md`](../tests/fixtures/README.md) for the captured
UniProt answers.
**Checkpoint:** `pytest` passes; MIBiG's tables include `Protein` nodes with
`ENCODES` and `CATALYZES` arrows, passing the twelve rules; `data/raw/uniprot/`
holds one finished snapshot; surfactin's cluster encodes nine proteins, three of
which catalyze surfactin; the **Actions** tab is green.
**What you should get:** on the first run (2026-10-12), MIBiG's 452 entries
with gene records gave 4,737 `Protein` nodes and `ENCODES` arrows, and 4,492
`CATALYZES` arrows from the 1,991 genes whose job builds the molecule (1,482 of
them backed by an experiment). UniProt (release `2026_03`) found 2,449 of the
4,089 protein numbers asked about, giving 2,442 entries, 360 of them reviewed; the
1,640 it didn't find are listed in `uniprot_summary.json`. The MIBiG counts are
fixed by the pinned release; UniProt's may move a little with each release. The
sanity checks are in
[`05-proteomics-uniprot.md`, Step 7](05-proteomics-uniprot.md#11-step-7-run-it-for-real).

![How far the protein layer reaches](img/protein_coverage.svg)

**Commit message:** `feat: add UniProt adapter and the protein layer`.
**Estimated time:** 5-7 hours.

---

## Stage 6b. Every cluster's proteins (Phase 3b)

![How far the protein layer reaches now: 452 entries with proteins become 2,437, 4,737 Protein nodes become 40,037, and 39,053 protein numbers go to UniProt](img/protein_file_coverage.svg)

**What.** Follow [`05b-all-cluster-proteins.md`](05b-all-cluster-proteins.md).
MIBiG's own download server publishes every protein of every cluster in one file,
`mibig_prot_seqs_4.0.fasta` (30.4 MB, in the FASTA format). You look at it first,
with a small capture script, the way Stage 6 looked at the JSON. The file has no
published checksum, so it's pinned by a SHA-256 measured on its first download.
Then the MIBiG adapter reads it: every protein of every active entry becomes a
`Protein` node with an `ENCODES` arrow, the curators' removals are left out and
listed, and each gene record is matched to its protein in the file. The protein
numbers, about 39,000 now, go through the same UniProt adapter, 10,000 per job.

```bash
python tests/fixtures/capture_mibig_protein_samples.py    # look at the real file first
python -m microbegraph.fetch --probe --source mibig        # both files, nothing downloaded
python -m microbegraph.fetch --source mibig                # downloads the protein file, rebuilds the tables
python -m microbegraph.fetch --source uniprot              # 39,053 numbers, 5 jobs
pytest                                                     # 213 promises, checked
```

![One protein from MIBiG's protein file, part by part](img/fasta_header.svg)

**Why.** A graph where four clusters in five have no proteins can't answer "which
enzymes do these clusters share?" fairly. The analytics in Stage 8 and the
machine learning in Stage 10 both lean on the protein layer, so it's complete
before them. The stage also teaches how to trust a file nobody gave you a
fingerprint for, and how to line up two lists that name the same things
differently without guessing.

![Every cluster's proteins, in three steps, with the real counts](img/protein_file_matching.svg)

**New ideas in this stage:** protein sequences and the FASTA format; isoforms;
pending entries; pinning a file by your own fingerprint; checking a remote file
by its headers; curators' corrections (`to_add`, `to_delete`); matching names
without guessing; keeping a fingerprint instead of the data; ID mapping at scale.

**Open:** [`05b-all-cluster-proteins.md`](05b-all-cluster-proteins.md);
[`tests/fixtures/README.md`](../tests/fixtures/README.md) for the protein file
sample.
**Checkpoint:** `pytest` passes; `data/raw/mibig/` holds the protein file, its
SHA-256 matching the pinned one; every active entry has `ENCODES` arrows;
`mibig_summary.json` lists every removal and every gene record the file doesn't
name; a new UniProt snapshot is in `data/raw/uniprot/`; the **Actions** tab is
green.
**What you should get:** on the first run (2026-10-12), the file held 46,987
proteins, 40,009 of them in the 2,437 active entries (the rest belong to 199
pending entries). After 18 removals by MIBiG's curators, MIBiG's tables hold
40,037 `Protein` nodes and 40,048 `ENCODES` arrows (from 4,737 each), and 452
gene records named only by a locus tag or gene name gained a protein number.
`CATALYZES` stays at 4,492. UniProt (release `2026_03`) found 20,671 of the
39,053 numbers asked about, giving 20,507 entries, 2,692 of them reviewed; the
18,382 it didn't find are listed. The MIBiG counts are fixed by the two pins;
UniProt's may move a little with each release. The sanity checks are in
[`05b-all-cluster-proteins.md`, Step 8](05b-all-cluster-proteins.md#12-step-8-run-it-for-real).
**Commit message:** `feat: add every cluster's proteins from MIBiG's protein file`.
**Estimated time:** 4-5 hours.

---

## Stage 7. Entity resolution and the graph build (Phase 4)

**What.** Decide when two names are one thing ("surfactin", "surfactin A",
`npatlas:NPA018495`), write every merge decision in a **resolution ledger**, join
MIBiG's compounds to the PubChem compounds from Phase 2 (each one records which
MIBiG compound gave its number) and look the rest up by name, move organisms whose
NCBI numbers were merged, then load the merged tables into DuckDB (the
single source of truth) and rebuild the NetworkX graph from it. The twelve rules
run on everything, and any failure stops the build. This stage also produces the
first `QUERY_COOKBOOK.md`, a collection of tested SQL recipes.

**Why.** This step decides whether you end up with a graph you can trust or one
that looks fine while being quietly wrong. A wrong merge does more harm than a
missed one, so the engine refuses to guess. Proteins join the same way compounds
do: each UniProt entry lists the MIBiG protein numbers it was found through
(Stages 6 and 6b), so an `ncbiprotein:` node and its `uniprot:` entry become one
node by an exact join. Stage 6b also hands over three short lists for the ledger:
59 gene records the protein file doesn't name, 4 curators' removals it doesn't
name, and a sequence fingerprint on every protein, so identical proteins can be
recognised ([`ROADMAP.md`, Phase 4](ROADMAP.md#phase-4-entity-resolution-and-the-graph-build)). It's also the stage where an organism
that is both a producer and a crop pathogen (*Botrytis cinerea* and some
*Fusarium* species are; Phase 2 counts them as `pathogens_also_organisms`) gets
caught by rule 1, and you resolve it on purpose.

**Open:** `06-entity-resolution-graph-build.md`; the rules in
[`02-ontology-and-data-model.md`, section 9](02-ontology-and-data-model.md#9-validation-rules-the-loader-enforces).
**Checkpoint:** DuckDB and NetworkX report the same row counts, and the ledger
explains every merge. **Commit message:** `feat: add entity resolution, resolution ledger, and graph build`.

---

## Stage 8. Graph analytics (Phase 5)

**What.** Find evidence paths (the jujube question, walked backwards), hubs
(centrality), bridges and communities, then draw the first interactive network
views.

**Why.** Until now you have been building the graph; from here on it starts
*answering*. Every path comes with its evidence chain, and a path is only as strong
as its weakest arrow.

**Open:** `07-graph-analytics.md`. If the weakest-link idea is new to you, try
[`interactive/evidence_chain.html`](interactive/evidence_chain.html) first.
**Checkpoint:** you can print a path from a crop back to candidate microbes, with
every arrow's evidence shown.
**Commit message:** `feat: add path finding, centrality, and community detection`.

---

## Stage 9. Statistical validation in R (Phase 6)

**What.** Set up R ([`R-SETUP.md`](R-SETUP.md)), read the same DuckDB file from R,
re-compute the main results with `igraph` as an independent cross-check, and run
**permutation tests**, which ask whether the structure is stronger than in
thousands of randomly rewired versions of the graph.

**Why.** Every network has hubs and clusters, even a random one, so "we found three
communities" means nothing until you compare it against a null model. Getting the
same answer from two different languages is a piece of evidence in its own right.

**Open:** `08-statistical-validation-r.md`, [`R-SETUP.md`](R-SETUP.md).
**Checkpoint:** Python and R agree on centrality, and the permutation results are
reported with their p-values. **Commit message:** `feat: add R null-model validation and igraph cross-check`.

---

## Stage 10. Graph machine learning (Phase 7)

**What.** Install the extras (`pip install -r requirements-ml.txt`), turn each node
into numbers (node2vec embeddings), and train a model that scores **missing**
arrows. The evaluation is the part to get right: proper negative sampling, a split
made *before* the embeddings (to avoid leakage), precision-recall, and a written
error analysis.

**Why.** The earlier phases describe what is already known, and this one suggests
where to look next. Because of that, every predicted arrow is stored as
`inferred`, drawn differently, and left out of evidence chains by default. Treat a
prediction as a reason to go and look, never as a finding.

**Open:** `09-graph-machine-learning.md`. **Checkpoint:** you have a ranked list of
candidate links and evaluation numbers you can defend.
**Commit message:** `feat: add node embeddings and link prediction with honest evaluation`.

---

## Stage 11. The Streamlit app (Phase 8), and 11b, the Shiny app (Phase 8b, optional)

**What.** Build a web app with four areas: **Explore** (filter by type, source,
evidence), **Trace** (evidence chains with every arrow's provenance), **Rank** (candidate
microbes for a pathogen), **Query** (a read-only SQL console, locked twice:
validated queries *and* a read-only connection). The optional 11b rebuilds the
core in R Shiny over the same database.

**Why.** In my view Streamlit is the quickest way to turn an analysis into something
a person can click on. The app reads small precomputed files, so it stays fast and
free to host.

**Open:** `10-app-streamlit.md`, `10b-app-shiny.md`.
**Checkpoint:** `streamlit run app/streamlit_app.py` serves all four areas locally.
**Commit messages:** `feat: add the Streamlit app with a read-only SQL console`;
`feat: add the Shiny frontend over the same database`.

---

## Stage 12. Deployment, GraphRAG and release 1.0 (Phase 9), and 12b, one container (Phase 9b, optional)

**What.** Deploy the app publicly for free and add the **GraphRAG** answer layer,
which walks the graph and then lets a language model phrase only those facts, with
citations (it hides itself when no API key is set). Then make the project easy to
pick up and put down: one-command setup scripts (`scripts/setup.sh` for macOS,
Linux and RHEL 8; `scripts/setup.ps1` for Windows), `docs/UNINSTALL.md`,
`docs/HOSTING.md`, `CONTRIBUTING.md`, `CITATION.cff`, and a versioned data release
of `nodes.csv` and `edges.csv` with its own DOI. The optional 12b packages the app
in one container image ([`CONTAINERS.md`](CONTAINERS.md), [`CONTAINERIZATION.md`](CONTAINERIZATION.md)).

**Why.** I don't consider a project finished while it only works on my own laptop.
Release 1.0 is meant to be complete, citable and public.

**Open:** `11-deployment-graphrag.md`, `11b-one-container.md`.
**Checkpoint:** the public link works, a fresh clone set up with the setup script
passes `check-setup.py` and `pytest`, and the v1.0.0 release page exists.
**Commit messages:** `feat: add the GraphRAG answer layer and deploy the app`;
then `chore: release v1.0.0` with
`git tag -a v1.0.0 -m "Release 1.0, the science"` and `--tags` (see Stage 2).

---

<a id="release-20-the-platform"></a>
# Release 2.0, the platform (Stages 13-16)

*The same system rebuilt on the tools a data team uses, each one introduced only
once the project has grown a need for it.*

---

## Stage 13. dbt: the ontology becomes tested SQL (Phase 10)

**What.** Move the transformations into **dbt** models, where the twelve rules
become dbt tests (`unique`, `relationships`, `accepted_values`, `not_null`).
**Why.** The rulebook turns into an actual `schema.yml` file that anyone who reads
SQL can follow, and dbt generates the lineage documentation for free.
**Open:** `12-dbt-transformations.md`. **Commit message:** `feat: move transformations into dbt with the ontology as tests`.

## Stage 14. PostgreSQL + Apache AGE + pgvector (Phase 11)

**What.** Add a server database that holds the graph (queried in Cypher through
AGE) and the GraphRAG embeddings (pgvector). DuckDB stays as the zero-setup local
option.
**Why.** PostgreSQL does three jobs here, and switching between local and server
comes down to a configuration change. Making that switch cleanly is the
portability skill this stage teaches.
**Open:** `13-postgres-age-pgvector.md`. **Commit message:** `feat: add PostgreSQL backend with Apache AGE and pgvector`.

## Stage 15. Airflow orchestration (Phase 12)

**What.** The whole pipeline becomes a scheduled Airflow DAG that runs monthly:
fetches in parallel, then resolve, build, dbt tests and artifact export, with
retries and alerts. A scheduled `--probe` notices when a source publishes a new
release. The container engine choices (Docker, Podman, or Prefect without
containers) are compared in [`CONTAINERS.md`](CONTAINERS.md).
**Why.** Five interdependent sources on a monthly refresh is exactly the kind of
problem Airflow was made for, and the exit codes from Phase 1 are how it tells
whether each step succeeded.
**Open:** `14-airflow-orchestration.md`. **Commit message:** `feat: orchestrate the pipeline with Airflow`.

## Stage 16. Snowflake portability and release 2.0 (Phase 13)

**What.** Point the same dbt models at a Snowflake trial warehouse, following
explicit steps to avoid costs, and document how to switch back to DuckDB.
**Why.** This stage shows one project running on two very different engines with
the same tests passing. At this size the warehouse itself is overkill, and the
guide says so.
**Open:** `15-snowflake-portability.md`.
**Commit messages:** `feat: add Snowflake as an alternative dbt target`; then
`chore: release v2.0.0` with `git tag -a v2.0.0 -m "Release 2.0, the platform"` and `--tags`.

---

<a id="release-30-the-product"></a>
# Release 3.0, the product (Stages 17-22)

*Turning a working system into something other people and other software can use.*

---

## Stage 17. FastAPI service layer (Phase 14)

**What.** Build a REST API for the core operations (paths, rankings, neighbourhoods,
validated read-only queries) with automatic interactive documentation, optional API
keys and rate limits for public use, structured logging, a health endpoint, and a
`SECURITY.md` saying how to report a problem.
**Why.** Streamlit, React and MCP all need the same logic. If it's written once,
behind an API, the three clients can't drift apart.
**Open:** `16-fastapi-service-layer.md`. **Commit message:** `feat: add the FastAPI service layer`.

## Stage 18. React + TypeScript frontend (Phase 15)

**What.** This is the public product: an interactive graph canvas, an
evidence-chain viewer and a ranking table, built against the API,
keyboard-accessible, and never using colour alone to show evidence.
**Why.** Streamlit remains the analyst's workbench, and the React app is the
polished version you share with other people. TypeScript's types act like
seatbelts, catching mistakes while you type.
**Open:** `17-react-frontend.md`. **Commit message:** `feat: add the React and TypeScript frontend`.

## Stage 19. MCP server (Phase 16)

**What.** Wrap the API in a Model Context Protocol server, so an AI assistant can
query the graph directly, read-only, with fixed, validated inputs.
**Why.** With the API already in place this is only a few hours of extra work. I
kept the scope narrow and read-only on purpose, and that restriction is the main
design decision of the stage.
**Open:** `18-mcp-server.md`. **Commit message:** `feat: add an MCP server over the graph`.

## Stage 20. Databricks: literature mining at scale (Phase 17)

**What.** A batch job reads thousands of abstracts and proposes candidate
compound → pathogen statements for **human review**; the accepted ones enter the
bridge with a citation at `curated_literature`. The guide also documents a local
Spark fallback.
**Why.** It goes after the same gap that the hand-curated bridge papers over. The
software only proposes, and a person decides what goes in. Of all the tools in the
plan this one has the weakest justification, so it's the first to cut if time is
short.
**Open:** `19-databricks-literature-mining.md`. **Commit message:** `feat: add literature mining with human review`.

## Stage 21. Containerize the whole application (Phase 18)

**What.** A single `compose.yaml` runs PostgreSQL, the API, Streamlit and React,
with health checks, named volumes, an internal network, secrets read at run time,
and a documented backup and restore of the database. It behaves identically under
Docker and Podman.
**Why.** Four cooperating services start with one command, even on a machine that
has no Python, R or PostgreSQL installed.
**Open:** `20-containerize-the-stack.md`, [`CONTAINERIZATION.md`](CONTAINERIZATION.md).
**Commit message:** `feat: containerize the full stack with compose`.

## Stage 22. Published images, CD and release 3.0 (Phase 19)

**What.** The tests have been running on every push since Phase 1, and this stage
adds **continuous delivery**: multi-platform images built and published to the GitHub
Container Registry, image vulnerability scanning, automatic dependency update
proposals, and release notes generated from the changelog.
**Why.** Once it's done, anyone can run the application with a single `docker run`
(or `podman run`), without cloning the repository or installing Python.
**Open:** `21-cicd-packaging.md`.
**Commit messages:** `ci: publish multi-platform images and automate releases`; then
`chore: release v3.0.0` with `git tag -a v3.0.0 -m "Release 3.0, the product"` and `--tags`.

---

## Stage 23. Running it as a product

**What.** A few habits keep a finished product alive: read the monthly refresh
results, upgrade a pinned source release only when you decide to (the MIBiG
procedure is in [`03-ingestion-mibig.md`, section 16](03-ingestion-mibig.md#16-upgrading-mibig-later),
and the releases already noticed are in
[`ROADMAP.md`, *Watching the sources*](ROADMAP.md#watching-the-sources)),
answer issues, keep the changelog, cut patch releases for fixes, and review the
product checklist in [`ROADMAP.md`](ROADMAP.md#what-finished-means-the-product-checklist),
which lists every piece of a finished product and the phase that delivers it.

**Why.** Software that nobody maintains decays as sources move, packages change and
links break. A small, regular routine costs far less than a rescue later on.

---

## Every session, after setup

macOS, Linux and RHEL 8:

```bash
cd ~/projects/microbegraph                    # or wherever you cloned it
source .venv/bin/activate
git switch develop
git pull --ff-only origin develop
python check-setup.py                         # quick health check
# ... work on the current stage ...
pytest && ruff check .
```

Windows PowerShell:

```powershell
cd $HOME\projects\microbegraph                 # or wherever you cloned it
.\.venv\Scripts\Activate.ps1
git switch develop
git pull --ff-only origin develop
python check-setup.py
# ... work on the current stage ...
pytest; ruff check .
```

When a stage (or a small tested change) is complete, finish with the end-of-phase
ritual from [Stage 2](#stage-2-version-control-and-the-end-of-phase-ritual).

---

## When something goes wrong

| Symptom | Look in |
|---|---|
| A command is "not found" | [`01-setup.md`](01-setup.md), Troubleshooting T1 and T3; is `.venv` active? |
| `ModuleNotFoundError: microbegraph` | [`03-ingestion-mibig.md`, section 17](03-ingestion-mibig.md#17-what-could-go-wrong). If `pip install -e .` itself prints it, `src/microbegraph/__init__.py` is missing; otherwise run `pip install -e .` |
| `pip` fails with compiler errors | [`01-setup.md`, T11](01-setup.md#t11-pip-fails-to-build-a-package-with-c-compiler-errors) (usually a too-new Python) |
| Behind a company proxy or firewall | [`01-setup.md`, T12](01-setup.md#t12-corporate-proxy--firewall-blocks-pip) |
| A download fails or a checksum does not match | [`03-ingestion-mibig.md`, section 17](03-ingestion-mibig.md#17-what-could-go-wrong) |
| "... is missing, and ... builds on it" | A source ran before the one it needs; [`04-more-sources-secrets.md`, section 17](04-more-sources-secrets.md#17-what-could-go-wrong) |
| PubChem, NCBI or KEGG refuses, is busy, or sends something odd | [`04-more-sources-secrets.md`, section 17](04-more-sources-secrets.md#17-what-could-go-wrong) |
| The probe says `API key : not set` although you made `.env` | [`04-more-sources-secrets.md`, Step 3](04-more-sources-secrets.md#7-step-3-your-first-api-key-optional) |
| A key was published by mistake | Replace it at the service first: [`04-more-sources-secrets.md`, Step 3](04-more-sources-secrets.md#7-step-3-your-first-api-key-optional) |
| The bridge refuses a row ("check ...") | [`curation/README.md`](../curation/README.md); the check numbers are in [`04-more-sources-secrets.md`, Step 8](04-more-sources-secrets.md#12-step-8-the-curated-bridge) |
| UniProt: "no proteins with an INSDC or RefSeq id", a job that fails or never finishes, an identifier type that disappeared | [`05-proteomics-uniprot.md`, section 15](05-proteomics-uniprot.md#15-what-could-go-wrong) |
| MIBiG's protein file: "not in the evidence locker yet", a SHA-256 that doesn't match the pinned one, a probe warning about its size, a header in another shape | [`05b-all-cluster-proteins.md`, section 16](05b-all-cluster-proteins.md#16-what-could-go-wrong) |
| The probe names a newer MIBiG release | Expected; [`ROADMAP.md`, *Watching the sources*](ROADMAP.md#watching-the-sources) says what the plan does about it |
| A test fails | The test's name says which promise broke; the phase guide's *What could go wrong* table |
| `$'\r': command not found` from the safety gate (Windows) | [`01-setup.md`, T14](01-setup.md#t14-bash-check-public-safesh-fails-with-r-command-not-found-windows) |
| The Actions tab shows no run after a push | [`03-ingestion-mibig.md`, *Starting a run by hand*](03-ingestion-mibig.md#starting-a-run-by-hand) |
| A run lists yellow warnings about Node.js or an action version | [`03-ingestion-mibig.md`, *Keeping the workflow current*](03-ingestion-mibig.md#keeping-the-workflow-current) |
| The Actions tab is red but your laptop is green | Click the red run, read the failing step; [`03-ingestion-mibig.md`, section 13](03-ingestion-mibig.md#13-step-9-continuous-integration-tests-on-four-systems) |
| Push refused about a "workflow" | [`01-setup.md`, T13](01-setup.md#t13-push-refused-refusing-to-allow-a-personal-access-token-to-create-or-update-workflow) |
| Push rejected, or `--ff-only` refuses | [`GIT-WORKFLOW.md`, section 9](GIT-WORKFLOW.md#9-when-something-goes-wrong) |
| The safety gate says NOT SAFE | [`GIT-WORKFLOW.md`, section 9](GIT-WORKFLOW.md#the-safety-gate-says-not-safe) |
| A word you don't know | [`GLOSSARY.md`](GLOSSARY.md) |
| Why a design choice was made | [`00-architecture.md`](00-architecture.md), *Design decisions*; each phase guide's reasoning |
| A figure looks wrong or out of date | `python docs/img/make_illustrations.py` and `python docs/interactive/make_interactive.py` |
| R does not find the database | [`R-SETUP.md`](R-SETUP.md) |
| Containers misbehave | [`CONTAINERS.md`](CONTAINERS.md), [`CONTAINERIZATION.md`](CONTAINERIZATION.md) |

---

## Where everything lives: the document map

| Document | What it is for | Read it |
|---|---|---|
| [`README.md`](../README.md) | The front page: what, why, results, how to run | Stage 0 |
| **[`HANDBOOK.md`](HANDBOOK.md)** | **This document: the whole journey, in order** | **First, and whenever unsure** |
| [`00-architecture.md`](00-architecture.md) | Every layer of the system and why it exists | Stage 0 |
| [`01-setup.md`](01-setup.md) | Blank computer to working workshop, three operating systems | Stage 1 |
| [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md) | The rulebook: nodes, edges, identifiers, evidence, twelve rules | Stage 3 |
| [`03-ingestion-mibig.md`](03-ingestion-mibig.md) | Phase 1: the evidence locker, provenance, tests, CI | Stage 4 |
| [`04-more-sources-secrets.md`](04-more-sources-secrets.md) | Phase 2: web APIs, snapshots, the first API key, licences, the curated bridge | Stage 5 |
| [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md) | Phase 3: genes, proteins and enzymes, MIBiG's gene records, UniProt's ID mapping, what didn't match | Stage 6 |
| [`05b-all-cluster-proteins.md`](05b-all-cluster-proteins.md) | Phase 3b: the FASTA format, pinning a file by your own fingerprint, curators' corrections, matching names without guessing, ID mapping at scale | Stage 6b |
| `06-...` to `21-...` | One guide per later phase | As each stage arrives |
| [`curation/README.md`](../curation/README.md) | The bridge file's columns, the confidence scale, how to add a row | Stage 5, and whenever you add a finding |
| [`tests/fixtures/README.md`](../tests/fixtures/README.md) | Where every test record came from, with fingerprints | Stages 5-6b, and when a source changes its format |
| [`ROADMAP.md`](ROADMAP.md) | The plan, the reasons for every tool, the product checklist, the source changes being watched | Stage 0, per release, and when a probe names something new |
| [`GIT-WORKFLOW.md`](GIT-WORKFLOW.md) | Commit messages, the branch flow, fixing git mistakes | Stage 2, and when stuck |
| [`PRIOR-ART.md`](PRIOR-ART.md) | Related work and what this project does not claim | Stage 0 |
| [`R-SETUP.md`](R-SETUP.md) | R, RStudio and renv beside Python | Stage 9 |
| [`CONTAINERS.md`](CONTAINERS.md) | Docker vs Podman vs Prefect | Stages 12b, 15 |
| [`CONTAINERIZATION.md`](CONTAINERIZATION.md) | The whole application in containers, from zero | Stages 12b, 21 |
| [`GLOSSARY.md`](GLOSSARY.md) | Every term, explained for a beginner | Always open |
| [`phases.csv`](phases.csv) | The plan as data: hours and status per phase | When updating status |
| [`CHANGELOG.md`](../CHANGELOG.md) | What changed in each version | Each release |
| [`img/`](img/) and [`interactive/`](interactive/) | The diagrams and open-in-browser explorers, plus the scripts that make them | Throughout |

---

## How this handbook is maintained

This handbook is a living document, and it's the first thing I update when the
project changes. If it ever falls behind the code, **treat that as a bug**.

**At the end of every phase**, do the following in this order, as part of the same
commit as the phase itself:

1. Flip the stage's status mark here (✅ for the finished stage, ⏳ for the next)
   and replace the estimated time with the measured one.
2. Link the phase guide that now exists, in the stage, the journey table and the
   document map.
3. Update the version, date and "repository state" line at the top, and add a line
   to the change log below.
4. Set the phase's `status` to `done` in [`phases.csv`](phases.csv) (edit it in VS
   Code, not a spreadsheet program, which may re-save it in another format) and re-run
   `python docs/img/make_illustrations.py` and `python docs/interactive/make_interactive.py`.
5. Make the same status change in the README build log and in
   [`ROADMAP.md`](ROADMAP.md).
6. Add the phase to [`CHANGELOG.md`](../CHANGELOG.md).

**Between phases**, when a small change is tested and committed (a fix, a renamed
command, a new troubleshooting answer), update every place in this handbook that
mentions it in that same commit, and add a change-log line.

### Handbook change log

| Version | Date | Change |
|---|---|---|
| 1.5 | 2026-10-12 | Phase 3b built and run: Stage 6b rewritten around the new guide, with three new pictures (one protein record part by part, the three steps for each cluster, and the protein layer before and after); a survey of the real file showed it already includes the genes curators added but not their removals, and that its headers carry the locus tags and products that give 452 gene records a protein number; Stage 7 is next and lists what Stage 6b hands it; Stage 4 notes that the MIBiG fetch now brings two files; new troubleshooting rows for the protein file and for a newer MIBiG release; the document map lists the Phase 3b guide; Stage 23 points at the roadmap's watch list |
| 1.4 | 2026-10-12 | Phase 3 built and run: Stage 6 rewritten around the new guide, with two new pictures (the protein layer, and asking UniProt); a survey of the real data showed UniProt doesn't cross-reference MIBiG and only 452 entries have gene records, so Stage 6b (every cluster's proteins, Phase 3b) is added to the plan and is next; Stage 4 notes that the MIBiG tidy now prints more counts; Stage 7 notes how proteins are joined; a troubleshooting row for UniProt; the document map lists the Phase 3 guide |
| 1.3 | 2026-10-12 | Phase 2 built and run against the live services: Stage 5 rewritten around the new guide, with the first run's counts and two new pictures (the five sources, and where a key lives); the running example now ends at grey mould on jujube, the crop for which a paper tested surfactin; Stage 7 notes what Phase 2 hands to entity resolution; new troubleshooting rows for missing tables, API trouble, keys and bridge checks; the document map lists the Phase 2 guide, `curation/README.md` and `tests/fixtures/README.md` |
| 1.2 | 2026-10-11 | After Phase 1: the test workflow moved to version 7 of `actions/checkout` and `actions/setup-python`, each job now stops after 20 minutes, and the code checkout leaves no login behind. Stage 4 gains "Looking after the automatic tests" with a new picture of what a run does; the troubleshooting map covers a push that starts no run and the version warnings |
| 1.1 | 2026-10-11 | Corrections from the first full run of Phase 1 on a Phase 0 checkout. `src/microbegraph/__init__.py` is new in Phase 1, not carried over from Phase 0. The unused top-level `sources/` and `figures/` folders are removed with `git rm`. New troubleshooting entry for `ModuleNotFoundError` during `pip install -e .`. The Phase 1 guide's probe output is now a real run against Zenodo, with the archive size as the program prints it (9.5 MB). The real MIBiG 4.0 archive is not gzip-compressed despite its name, so archives are now read by their contents, and a fetch logs the file it filed even if it then can't open it. MIBiG 4.0 writes activity names in two styles; both are now read, curators' comments are kept on the compound as `activity_notes`, and the surfactin test record is a cut-down copy of the real one. The Phase 1 checkpoint now gives the expected counts |
| 1.0 | 2026-10-10 | First edition: Stages 0-4 complete (design, setup, rulebook, MIBiG ingestion); Stages 5-23 described from the roadmap; journey map, setup loop, branch model, ontology and evidence pictures added |
