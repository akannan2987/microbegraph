# Glossary — every term, in plain words

**The rule for this repository:** every term used anywhere in MicrobeGraph —
biological or technical — is defined here in plain language, with an everyday
example wherever one helps. **If a word isn't here, that's a documentation
bug** — open an issue and it gets added.

Terms are grouped by where you first meet them, so you can read a section before
its phase and skim the rest. Within each section they're alphabetical.

---

## Contents

- [Biology and agriculture](#biology-and-agriculture)
- [Graphs and knowledge](#graphs-and-knowledge)
- [Computers, terminals, and files](#computers-terminals-and-files)
- [Python and programming](#python-and-programming)
- [Git and GitHub](#git-and-github)
- [Data, databases, and SQL](#data-databases-and-sql)
- [Getting data from the internet](#getting-data-from-the-internet)
- [The data sources used here](#the-data-sources-used-here)
- [Analysis and statistics](#analysis-and-statistics)
- [Apps and deployment](#apps-and-deployment)
- [Containers, orchestration, and the modern data stack](#containers-orchestration-and-the-modern-data-stack)
- [AI and language models](#ai-and-language-models)
- [Quality, testing, and honesty](#quality-testing-and-honesty)

---

## Biology and agriculture

**Bacterium** (plural *bacteria*) — a single-celled living thing far too small
to see. Most are harmless, many are useful, a few cause disease. *Bacillus
subtilis*, common in soil, is one of the useful ones and appears throughout this
project.

**Biocontrol** — using a living organism to control a pest or disease, instead
of a synthetic chemical. *Everyday example:* releasing ladybirds to eat aphids
rather than spraying. MicrobeGraph is about the microbial version.

**Biological (crop protection)** — a crop-protection product based on a living
organism or a natural molecule, as opposed to a synthetic pesticide. The
commercial field this project's domain belongs to.

**Biosynthetic gene cluster (BGC)** — a run of neighbouring genes in a microbe's
DNA that together build one specific molecule. *Everyday example:* if the genome
is a cookbook, a BGC is several consecutive pages that together describe one
complicated recipe. Abbreviated BGC throughout.

**Compound** — see *Metabolite*. Used interchangeably here; "compound" is the
chemistry word, "metabolite" the biology word.

**Crop** — a cultivated plant grown for food or material. In this project, the
end of the chain: who ultimately suffers from the disease.

**Fungus** (plural *fungi*) — a kingdom of life including moulds, yeasts, and
mushrooms. Some fungi attack crops; others protect them.

**Gene** — one instruction in an organism's DNA, usually the recipe for one
protein.

**Genome** — the complete set of an organism's DNA. *Everyday example:* the
entire cookbook, not one recipe.

**Grey mould** — a common name for the disease caused by the fungus *Botrytis
cinerea*, which rots soft fruit including strawberries and grapes. Used as the
running example throughout the docs.

**Kingdom** — a very broad grouping of life: Bacteria, Fungi, Plants, Animals.
The top rung of the taxonomy ladder used here.

**Lipopeptide** — a class of molecules that are part fat, part protein-fragment.
Many are soapy, which is how they damage the membranes of other microbes.
Surfactin is one.

**Metabolite** — a small chemical an organism makes and often releases.
*Everyday example:* if the microbe is a factory, metabolites are its products.
Some products happen to be poisonous to plant diseases, which is the whole
premise of this project.

**Microbe** — any organism too small to see: bacteria, fungi, yeasts. The
umbrella term.

**Pathogen** — an organism that causes disease. In this project, specifically a
*plant* pathogen — something that attacks crops.

**Pathway (biochemical)** — a chain of chemical reactions a cell performs in
sequence. *Everyday example:* a production line with named stations, where each
station's output feeds the next.

**Protein** — a molecular machine built from an organism's genetic instructions.
*Everyday example:* if the genome is a cookbook and a gene is a recipe, the
protein is the finished dish that then does a job. In this project, the enzymes
encoded by a gene cluster.

**Enzyme** — a protein that speeds up one specific chemical reaction. *Everyday
example:* a specialised machine on a production line — it does one step, very
fast, over and over.

**EC number** — Enzyme Commission number, the standard code describing what
reaction an enzyme performs. Like a job title with a fixed vocabulary.

**Proteomics** — the study of the full set of proteins in a sample. One of the
three molecular layers this project joins together.

**Multi-omics integration** — combining several kinds of biological measurement
(genomics, proteomics, metabolomics) into a single analysis, rather than looking at
each in isolation. Hard because each layer has different units, scales, and
identifiers — which is precisely why the ontology and entity resolution phases
exist.

**Secondary metabolite** — a molecule an organism makes that isn't needed for
basic survival, but gives it an advantage — a weapon, a signal, a defence. Most
antibiotics are secondary metabolites. Also called a *specialised metabolite* or
*natural product*.

**Siderophore** — a molecule a microbe releases to grab iron from its
surroundings. Since iron is scarce and everyone needs it, a good siderophore is
a way of starving your competitors. A common biocontrol mechanism.

**Species / genus / family** — rungs on the ladder that classifies life, from
specific to general. *Bacillus subtilis* is a species; *Bacillus* is its genus.
*Everyday example:* street → city → region → country.

**Strain** — one specific isolate within a species. *Everyday example:* if
"species" is a car model, a strain is one particular car with its own history
and quirks. Two strains of the same species can behave quite differently.

**Surfactin** — a lipopeptide made by *Bacillus* bacteria. Used as the running
example in these docs because it's real, well-studied, and appears in every
source database this project touches.

**Taxonomy** — the system for naming and classifying organisms, and the
hierarchy it produces.

**Yeast** — a single-celled fungus.

---

## Graphs and knowledge

**Betweenness centrality** — a measure of how often a node sits *on the shortest
route between other nodes*. The "bridge" score. *Everyday example:* a junction
that isn't busy itself but breaks half the city's journeys if it closes. Often
more interesting than raw popularity.

**Centrality** — any measure of how important a node is within a graph. There
are several kinds because "important" means different things.

**Community detection** — automatically finding clumps of nodes more connected
to each other than to the rest. *Everyday example:* in a social network, your
school friends and your colleagues form visible clusters without anyone
labelling them.

**CURIE** ("Compact URI", say *curie*) — an identifier written as
`prefix:localid`, e.g. `pubchem.compound:443324`. The prefix says whose
numbering system the number belongs to. *Everyday example:* the country code on
a phone number.

**Degree** — how many arrows touch a node. Its "popularity" score.

**Directed graph (DiGraph)** — a graph where arrows have a direction. *A
produces B* is not the same statement as *B produces A*. MicrobeGraph is
directed throughout.

**Edge** — a connection between two nodes, with a direction and a name
(*produces*, *inhibits*). Also called a *relationship* or *link*. One arrow on
the map.

**Entity resolution** — deciding that several records refer to the same
real-world thing and merging them into one node. *Everyday example:* realising
"Robert Smith", "Bob Smith", and "R. Smith (work)" are one person.

**Graph** — information stored as dots connected by arrows. Nothing to do with
bar charts. *Everyday example:* a transport map; a social network.

**GraphRAG** — answering a question by first *walking a knowledge graph* to
collect relevant facts, then giving those facts to a language model to phrase the
answer. See also *RAG*.

**Embedding** — turning a node's position in a graph into a list of numbers, so
that nodes with similar connection patterns get similar numbers. Once every node
is a vector, ordinary machine learning applies. *Everyday example:* describing a
person by which social circles they move in, then finding people with similar
descriptions.

**node2vec** — the specific method this project uses to compute embeddings. It
takes many random walks through the graph and learns numbers that predict what a
node's neighbours tend to be.

**Cypher** — the query language for graph databases, as SQL is for tables. Its
patterns look like little drawings: `(a)-[:PRODUCES]->(b)`. Introduced with Apache
AGE in Release 2.0.

**Hop** — one step along one arrow. A "three-hop path" crosses three arrows.

**Knowledge graph** — a graph whose nodes are real-world concepts and whose
edges are meaningful relationships between them, usually with provenance
attached. What this project builds.

**Link prediction** — scoring arrows that *don't* exist yet, to guess which ones
probably should. *Everyday example:* "People you may know". In this project the
output is always a hypothesis, never a finding.

**Node** — one thing in a graph: a microbe, a compound, a crop. Also called a
*vertex*. One dot on the map.

**Ontology** — a written agreement about what kinds of things exist in your
world and what relationships are allowed between them. *Everyday example:* a
family tree allows *parent-of* and *married-to*, but not
*borrowed-a-lawnmower-from* — the ontology is that decision, made explicitly.

**Path** — a sequence of arrows leading from one node to another. The core
output of this project: an evidence chain.

**Property** — a piece of information attached to a node or edge, e.g. a
compound's molecular weight.

**Schema** — the concrete implementation of an ontology: these columns, these
types, these constraints.

**Shortest path** — the route between two nodes crossing the fewest arrows. The
graph equivalent of "fastest route".

---

## Computers, terminals, and files

**CSV** ("comma-separated values") — a plain-text table where columns are
separated by commas. Openable by Excel, by any text editor, and by every
programming language. Deliberately used here for the graph files, because a file
you can open in a text editor is a file you can debug.

**Directory** — another word for folder.

**Executable bit** — a file permission on macOS/Linux marking a file as "allowed
to run as a program". Set with `chmod +x`. Windows doesn't use it.

**JSON** ("JavaScript Object Notation") — a text format for structured data,
using `{ }` for records and `[ ]` for lists. The format most web services reply
in. *Everyday example:* a nested bullet list a computer can read reliably.

**PATH** — a list of folders your computer searches when you type a command
name. If a program isn't on the PATH, typing its name gets "command not found"
even though it's installed.

**Path (file)** — the address of a file, e.g. `data/raw/provenance.csv`. A
*relative* path starts from where you are; an *absolute* path starts from the
root of the disk. **Always prefer relative paths in a shared project** — an
absolute path that works on your machine breaks on everyone else's.

**Terminal** — a window where you type text commands instead of clicking. Also
called shell, console, or command line.

**Working directory** — the folder your terminal is currently "in". `pwd` prints
it.

---

## Python and programming

**Argument** — a value you hand to a function. In `round(3.7)`, `3.7` is the
argument.

**Function** — a named, reusable block of instructions. *Everyday example:* a
recipe you can follow whenever you want that dish, rather than re-deriving it
each time.

**Import** — bringing code from another file or package into the one you're
writing. `import pandas` means "give me the pandas toolkit".

**Library / package** — code someone else wrote and published so you don't have
to write it yourself. *Everyday example:* buying flour instead of growing wheat.

**Module** — one Python file containing code you can import.

**pandas** — the standard Python library for working with tables. *Everyday
example:* programmable Excel that never gets tired and never mis-clicks.

**pip** — Python's package installer. The command that fetches and installs
libraries.

**Python** — the programming language this project is written in. Chosen for
readability and because every library needed already exists in it.

**requirements.txt** — a text file listing exactly which packages the project
needs. The project's *receipt* — it lets anyone rebuild an identical toolbox.

**Script** — a file of code you run from start to finish, as opposed to a
library you import.

**Variable** — a name attached to a value, so you can refer to it later.

**Virtual environment (`venv`)** — a folder holding a private copy of Python and
its libraries, belonging to one project only. *Everyday example:* your own
kitchen cupboard in a shared kitchen, so nobody else's substitutions break your
recipe. Must be *activated* in each new terminal session.

---

## Git and GitHub

**Branch** — an independent line of work in the same repository. This project
uses three: `master` (stable), `beta` (release candidate), `develop` (daily
work).

**Clone** — download a copy of a repository including its whole history, wired
up to talk to the original.

**Commit** — one saved snapshot of your project, with a message explaining what
changed. *Everyday example:* clicking "save a named version" in a document.

**Fast-forward** — updating a branch by simply moving its pointer along an
existing line, with nothing to merge. The clean case. `--ff-only` means "only do
it if it's this clean; otherwise stop and tell me".

**Git** — the program on your computer that records snapshots of your project.
*Everyday example:* a save-game system for your work.

**GitHub** — a website that stores copies of Git repositories online. Git and
GitHub are different things; you can use Git without GitHub.

**.gitignore** — a file listing things Git must never track: secrets,
rebuildable data, huge folders.

**Origin** — Git's default nickname for "the repository I cloned from". Usually
your GitHub copy.

**Personal Access Token (PAT)** — a long, generated password used by programs
instead of your account password. Can be scoped narrowly and revoked
individually.

**Pull** — fetch changes from the remote and apply them to your local branch.

**Push** — send your local commits up to the remote.

**Remote** — a copy of the repository somewhere else, usually GitHub.

**Repository ("repo")** — a project folder Git is watching, plus its entire
history.

**SSH key** — a matched pair of files proving your identity without sending a
password. *Everyday example:* a physical key (private, yours) and the lock it
fits (public, given to GitHub).

**Staging** — marking changes for inclusion in the next commit. *Everyday
example:* putting items in a shopping basket — nothing's bought yet.

**Tag** — a permanent label on a specific commit, used to mark releases (`v1.0`).

**Untracked** — a file Git can see but isn't watching yet.

---

## Data, databases, and SQL

**Column** — one field in a table; one attribute of every row.

**Constraint** — a rule the data must obey, enforced by the database or the
loader. "This value must be unique" is a constraint.

**Database** — a program whose job is to store information in an organised way
and answer questions about it quickly. *Everyday example:* a library with a
catalogue and a fast librarian, versus a pile of books in a garage.

**DuckDB** — the database used here. A complete analytics database that lives in
a single file on your laptop: no server, no account, no cost. Also the standard
local stand-in for cloud warehouses, so the SQL you write transfers directly.

**Foreign key** — a column whose values must exist in another table. In our
graph, every `source_id` in `edges.csv` must exist in `nodes.csv`.

**Join** — combining two tables by matching a shared column. The table-shaped
equivalent of following one arrow.

**Primary key** — the column that uniquely identifies each row. Ours is
`node_id`.

**Query** — a question asked of a database, usually written in SQL.

**Read-only** — able to look but not change. The app's SQL console is read-only
*by construction*, meaning it's enforced in code, not promised in the docs.

**Row** — one record in a table; one thing.

**Schema** — the structure of a database: which tables exist, which columns they
have, which rules apply.

**SQL** (say "sequel" or "ess-cue-ell") — the language for asking databases
questions. Reads close to English: `SELECT name FROM compounds WHERE activity =
'antifungal'`. Invented in the 1970s and still everywhere.

**Table** — a grid of rows and columns. Excellent at counting and filtering; bad
at chains of unknown length, which is why this project also builds a graph.

---

## Getting data from the internet

**API** ("Application Programming Interface") — a way for one program to ask
another program for data, designed for machines rather than humans. *Everyday
example:* a restaurant's takeaway hatch — a defined way to place an order and
collect it, without wandering into the kitchen.

**API key** — a string identifying who is making requests, so a service can
apply limits fairly. Sometimes optional (a courtesy that raises your rate
limit), sometimes required. **Always a secret.**

**Endpoint** — one specific address within an API that answers one kind of
question.

**Evidence locker** — this project's name for `data/raw/`: the untouched
original responses from every source, kept forever. *Everyday example:* the
original receipts behind a tax return.

**HTTP** — the protocol web browsers and programs use to request things from
servers.

**Ingestion** — the act of getting data into your system. The first pipeline
stage.

**Provenance** — the recorded origin of a piece of information: where it came
from, when, and under what terms. Written to `data/raw/provenance.csv` on every
fetch.

**Rate limit** — a cap on how many requests you may make per second. Exceeding
it gets you blocked. Respecting it is basic politeness to a free service.

**Retry with backoff** — when a request fails, waiting a moment and trying
again, waiting longer each time. *Everyday example:* the phone is engaged; you
don't redial forty times a second.

**Status code** — a number a server returns describing the outcome. 200 = fine.
404 = not found. 403 = refused. 429 = you're going too fast. 500 = the server
broke.

**User agent** — a short line a program sends identifying itself. Sending a
polite, honest one (naming the project and a contact) is expected etiquette when
using public scientific APIs.

---

## The data sources used here

**KEGG** — a database mapping compounds to the biochemical pathways they take
part in. Free for academic use, requires attribution, must not be bulk-scraped.

**MIBiG** — *Minimum Information about a Biosynthetic Gene Cluster*. A
community-curated public repository of gene clusters that have been
experimentally shown to produce a particular molecule. Published under CC-BY on
Zenodo with a permanent DOI. **This project's backbone**, because it supplies
the organism → cluster → compound arrows.

**NCBI** — the US National Center for Biotechnology Information. Runs Taxonomy
(the classification of life) and Datasets (genome records), among much else.
Public domain.

**PubChem** — the US National Institutes of Health's chemistry database. Given a
compound name it returns a stable numeric ID (a CID), a formula, a weight, and a
synonym list. Free, no account. Its synonym lists are the raw material for
entity resolution here.

**The curated bridge** — this project's own small, hand-assembled CSV linking
compounds to pathogens to crops, because no public database publishes those
links as a downloadable table. Every row carries a citation; every edge is
labelled `curated_literature`; the whole layer can be filtered out.

---

## Analysis and statistics

**Aggregate** — to summarise many rows into one number: a count, a sum, an
average.

**Confidence** — in this project, a 0–1 number a source adapter attaches to an
edge. Used for ranking, never for hiding.

**Deduplicate** — remove repeated records that describe the same thing.

**Hypothesis** — a proposed explanation worth testing, not yet a finding. Every
predicted link in this project is a hypothesis, and is labelled as one.

**Normalise (text)** — put text into a consistent form before comparing:
lowercase, trimmed, punctuation stripped. Prevents `Surfactin ` and `surfactin`
from being treated as different things.

---

## Apps and deployment

**Backend** — the part of software that does the work, out of the user's sight.
*Everyday example:* a restaurant kitchen.

**Deployment** — putting your app somewhere on the internet so other people can
use it.

**Frontend** — the part the user sees and touches. *Everyday example:* the
dining room and the menu.

**Graceful degradation** — designing so that when an optional piece is missing,
that one feature disappears quietly and everything else still works. Applied
here to the AI layer: no API key means no chatbot, not a broken app.

**Localhost** — your own computer, acting as a server for you only. When an app
prints `http://localhost:8501`, that page exists on your machine and nobody else
can reach it.

**Secret** — any value that must never be published: API keys, tokens,
passwords. Kept in `.env` or `secrets.toml`, both gitignored.

**Streamlit** — a Python library that turns a plain script into a web app with
buttons and charts, without web development. *Everyday example:* an automatic
gearbox — less control than manual, driving today rather than in three months.

---

## Containers, orchestration, and the modern data stack

**Airflow** — an orchestrator: it runs pipeline steps in the right order, on a
schedule, with retries and alerts. *Everyday example:* an alarm clock combined
with a checklist that knows which tasks must finish before others can start.

**Apache AGE** — a PostgreSQL extension that adds graph storage and Cypher queries
to an ordinary Postgres database. Lets this project get graph-database skills
without running a second server.

**Astro CLI** — a free command-line tool that runs Apache Airflow locally in
containers. Works with Docker or Podman.

**Backfill** — re-running a scheduled pipeline for dates in the past, usually
after fixing a bug.

**Container** — a sealed, lightweight box holding a program plus everything it
needs to run, so it behaves identically on any machine. *Everyday example:* a
recipe shipped together with the kitchen. See [`CONTAINERS.md`](CONTAINERS.md).

**Containerfile / Dockerfile** — the text file describing how to build an image.
The two names are the same format; Podman prefers the first, Docker the second.

**Base image** — the image your image is built on top of. *Everyday example:* you
don't build a kitchen from raw ore; you start with a room that already has
plumbing and power.

**Bind mount** — attaching a folder from your own machine into a container, so
edits appear inside instantly. Used in development; never for code in production.

**Compose** — a file describing several services, how they connect, what storage
they keep, and in what order they start — plus the command that runs them all.
*Everyday example:* a Containerfile is a recipe for one dish; a compose file is
the menu plus the kitchen rota.

**Containerfile / Dockerfile** — the text file describing how to build an image.
Same format, two names; both engines read both. This project uses `Containerfile`
because it is the vendor-neutral name.

**DAG** ("Directed Acyclic Graph") — in orchestration, the map of which tasks
depend on which. *Directed* because dependencies point one way; *acyclic* because
a task can't ultimately depend on itself.

**Databricks** — a cloud platform for large-scale data processing built on Spark.
Used in this project for one genuinely compute-heavy job (mining paper abstracts)
and honestly flagged as the weakest-fit tool in the plan.

**dbt** — a tool that turns a folder of SQL files into a tested, documented,
version-controlled transformation pipeline. It works out which model depends on
which, runs them in order, and tests the results.

**Docker** — the best-known container platform. Free for personal use; requires a
paid subscription in larger companies, which is often why it's unavailable on work
machines.

**ELT / ETL** — Extract, Load, Transform (or Extract, Transform, Load). Whether
you clean the data before or after loading it into the warehouse. Modern practice
usually loads first and transforms in SQL — which is dbt's whole premise.

**FastAPI** — a Python framework for building web APIs. Generates interactive
documentation automatically and validates every request against declared types.

**Health check** — a command run periodically inside a container to answer "is
this service actually *working*?", which is a different question from "is the
process running?". *Everyday example:* waiting for the kettle's click, not just
for the switch to be on.

**Idempotent** — safe to run more than once with the same result. A pipeline step
that appends rows every run is *not* idempotent; one that replaces a day's data is.
Essential for retries to be safe.

**Image** — the packaged blueprint a container is started from. Static, where a
container is running.

**Layer** — a saved snapshot of the filesystem after one Containerfile
instruction. Images are layers stacked, and the engine caches them — which is why
instruction order changes rebuild times dramatically. *Everyday example:* packing
a suitcase; changing the item on top is easy, changing the shoes at the bottom
means unpacking everything.

**Lakehouse** — a storage design combining a cheap data lake with warehouse-style
querying. The concept behind Databricks.

**Multi-stage build** — using one image to *build* and a second, minimal one to
*run*, copying only the finished output across. *Everyday example:* baking needs
mixing bowls and a messy worktop; serving needs a plate. You don't deliver the
kitchen with the cake.

**Named volume** — storage managed by the container engine that survives a
container being deleted. *Everyday example:* a container is a hotel room, cleaned
between guests; the volume is your suitcase, which leaves with you.

**nginx** — a small, very fast web server. Here it hands finished HTML, CSS and
JavaScript files to browsers.

**Orchestration** — running the steps of a pipeline in the right order, on
schedule, handling failures. The problem Airflow and Prefect solve.

**pgvector** — a PostgreSQL extension adding vector similarity search, used here
to store embeddings for the RAG layer.

**Podman** — a container engine that runs without a background daemon and without
root privileges. Red Hat's default on RHEL, and usually the right choice on shared
or locked-down machines.

**Prefect** — a Python orchestration library that needs no containers. The
container-free route through this project's orchestration phase.

**React** — a JavaScript library for building user interfaces from reusable
components.

**REST API** — a convention for how programs ask each other for things over the
web, using URLs and HTTP verbs.

**Publishing a port** — making a port inside a container reachable from your
machine, with `-p outside:inside`. *Everyday example:* the hotel front desk
connecting an outside call to a room's phone. Anything not published stays
invisible from outside — which is why this project's database has no published
port.

**Registry** — a place images are stored so others can download them. *Everyday
example:* an app store for images. This project publishes to GitHub Container
Registry (GHCR).

**Rootless** — running containers as an ordinary user rather than as root. If
something misbehaves it has your permissions, not the machine's.

**SELinux** — an extra security layer in Red Hat Linux that labels every file and
controls which processes may touch which labels. *Everyday example:* a building
where every room has a colour-coded badge reader. It causes the classic RHEL
container symptom: `Permission denied` on a mounted folder despite correct file
permissions. Fixed by adding `:Z` to the mount.

**Service discovery** — how containers find each other. Under compose, each
service is reachable by its **name** (`postgres:5432`) rather than an IP address,
which changes on every restart. *Everyday example:* dialling "Accounts" on an
office phone system instead of a full external number.

**Snowflake** — a cloud data warehouse that separates storage from compute. Used
here as a portability demonstration, not because the data volume needs it.

**Spark** — a framework for processing data across many machines at once.

**TypeScript** — JavaScript with types added. *Everyday example:* seatbelts —
they catch the mistake of passing a number where text was expected while you're
typing, rather than in front of a user.

**Warehouse (data)** — a database built for analytical questions over large
volumes, as opposed to running an application.

**WSL2** — Windows Subsystem for Linux: a real Linux kernel inside Windows.
Containers need it, since containers are Linux technology.

---

## AI and language models

**Agent** — an AI that *takes actions* rather than only answering: it plans
steps, calls tools, checks results, and loops until the task is done. *Chatbot
vs agent:* a chatbot tells you which query would answer your question; an agent
runs it, reads the result, and decides what to do next.

**Context** — the information given to a language model along with your question.
The whole point of RAG is controlling what goes in here.

**Hallucination** — when a language model produces a confident, fluent, entirely
invented answer. The reason a scientific project must ground answers in real,
retrieved facts rather than the model's memory.

**Large language model (LLM)** — the technology behind chat assistants. Excellent
at language, unreliable at specific facts on its own.

**MCP (Model Context Protocol)** — an open standard letting an AI assistant plug
into an external tool or data source. *Everyday example:* USB — one agreed shape,
so any device works with any computer.

**Prompt** — the instructions and question given to a language model.

**RAG (Retrieval-Augmented Generation)** — fetching the relevant real information
*first*, handing it to the model, and instructing it to answer only from what it
was given. *Everyday example:* handing a well-read friend the exact page from the
manual instead of asking them from memory.

**Tool (in AI)** — a function an AI is allowed to call, with defined inputs and
outputs. This project's MCP tools will be read-only by design.

---

## Quality, testing, and honesty

**Assertion** — a statement in a test that must be true, or the test fails.

**Checkpoint** — in this tutorial, a verification step: run this, expect that. If
it doesn't match, stop and fix before continuing.

**Evidence level** — the label on every edge saying what kind of knowledge it is:
`curated_experimental`, `database_assertion`, `curated_literature`, or
`inferred`. See [`02-ontology-and-data-model.md`](02-ontology-and-data-model.md).

**Fixture** — a small, controlled piece of test data. **Must be built from the
same code or schema as the real thing, never from memory** — a fixture that has
drifted from reality produces tests that pass while the system fails.

**Ledger** — a written record of what a step did: what was merged, removed, or
changed, and why. The resolution ledger and the provenance log are both ledgers.
*Everyday example:* a bank statement — not the money, but the account of what
happened to it.

**Pipeline** — a series of stages where each one's output is the next one's
input, flowing one way. *Everyday example:* beans → grinder → espresso machine →
cup. Each stage has one job and can be tested alone.

**pytest** — the tool that runs this project's automated tests.

**Reproducibility** — the property that someone else, on a different machine, can
run your work and get the same result. The reason for `requirements.txt`, the
evidence locker, and the provenance log.

**Test (unit test)** — a small automated check proving one function does what you
claim. *Everyday example:* tasting the sauce before serving, rather than hoping.

**Validation** — checking data against rules before accepting it. This project's
loader *refuses* invalid rows rather than warning about them, because warnings
get ignored.

---

*Missing a term? That's a documentation bug — please open an issue.*
