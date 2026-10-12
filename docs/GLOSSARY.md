[← Handbook](HANDBOOK.md) · [README](../README.md) · [Architecture](00-architecture.md) · [Roadmap](ROADMAP.md)

# Glossary, every term, in plain words

Every term used anywhere in MicrobeGraph, biological or technical, is defined
here in plain language, with an everyday comparison wherever one helps. **If a
word isn't here, that's a documentation bug**: open an issue and I'll add it.

Terms are grouped by where you first meet them, so you can read a section before
its phase and skim the rest. Within each section they're alphabetical.

---

## Contents

- [Biology and agriculture](#biology-and-agriculture)
- [Graphs and knowledge](#graphs-and-knowledge)
- [Computers, terminals, and files](#computers-terminals-and-files)
- [Python and programming](#python-and-programming)
- [R and its ecosystem](#r-and-its-ecosystem)
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

**Bacterium** (plural *bacteria*): a single-celled living thing far too small to
see. Most are harmless and many are useful, though a few cause disease.
*Bacillus subtilis*, common in soil, is one of the useful ones and appears
throughout this project.

**Biocontrol**: using a living organism to control a pest or disease instead of
a synthetic chemical, the way a gardener might release ladybirds to eat aphids
rather than spray them. MicrobeGraph is about the microbial version.

**Biological (crop protection)**: a crop-protection product based on a living
organism or a natural molecule, as opposed to a synthetic pesticide. This is the
commercial field this project's domain belongs to.

**Biosynthetic gene cluster (BGC)**: a run of neighbouring genes in a microbe's
DNA that together build one specific molecule. If the genome is a cookbook, a
BGC is several consecutive pages describing one complicated recipe. Abbreviated
BGC throughout.

**Compound**: see *Metabolite*. The two words are used interchangeably here;
"compound" is the chemistry word and "metabolite" the biology word.

**Crop**: a cultivated plant grown for food or material. In this project it sits
at the end of the chain, as the one who ultimately suffers from the disease.

**Damping-off**: seedlings rotting at the soil line and collapsing, just before
or after they come up. Soil organisms such as *Globisporangium ultimum* (long
called *Pythium ultimum*) and *Rhizoctonia solani* cause it. Two bridge rows are
about damping-off of cotton.

**Domain**: the top rank of NCBI's ladder of life: Bacteria, Archaea and
Eukaryota (living things whose cells have a nucleus, which includes fungi,
plants and animals). NCBI called this rank "superkingdom" until 2025.

**EC number**: Enzyme Commission number, the standard code describing what
reaction an enzyme performs. You can think of it as a job title chosen from a
fixed vocabulary.

**Enzyme**: a protein that speeds up one specific chemical reaction, rather like
a specialised machine on a production line that does one step, very fast, over
and over.

**Fungus** (plural *fungi*): a kingdom of life including moulds, yeasts and
mushrooms. Some fungi attack crops; others protect them.

**Fusarium head blight**: a disease of wheat and barley ears, caused mainly by
the fungus *Fusarium graminearum*. It shrivels the grain and can leave toxins in
it. The same fungus causes **Gibberella ear rot** on maize, a pink to red mould
on the ear (Gibberella was the older name of the fungus's sexual stage).

**Gene**: one instruction in an organism's DNA, usually the recipe for one
protein.

**Genome**: the complete set of an organism's DNA. In the cookbook comparison,
it's the entire book rather than any one recipe.

**Grey mould**: a common name for the disease caused by the fungus *Botrytis
cinerea*, which rots many fruits after harvest, including grapes, strawberries
and jujubes. The docs use grey mould on jujube as their running example, because
that's where a paper tested surfactin against it (Xiao et al. 2023).

**Group**: MicrobeGraph's own broad label for an organism (`Bacteria`,
`Archaea`, `Fungi`, `Oomycetes`, `Plants`, `Animals`, `Viruses` or `Other`),
worked out from the names in its NCBI lineage. It's used for colouring and
filtering and isn't an official rank (see **Kingdom** for why it isn't called
that).

**Jujube** (*Ziziphus jujuba*): a fruit tree grown widely in China, whose fruit
rots easily after harvest. It's the crop in the running example, because Xiao
and colleagues (2023) showed that purified surfactin reduced grey mould on
harvested winter jujube.

**Kingdom**: a very broad rank in the taxonomy ladder, just below domain. Fungi,
plants (Viridiplantae) and animals (Metazoa) are kingdoms; since 2025 NCBI also
gives bacteria kingdoms, such as *Bacillati*, which holds *Bacillus*. Because the
word now has that exact meaning, MicrobeGraph's own broad label is called
`group` (see **Group**).

**Lineage**: the full list of groups an organism belongs to, from the top of the
tree down, as NCBI writes it. For *Bacillus velezensis* FZB42 it starts
`cellular organisms; Bacteria; Bacillati; Bacillota; Bacilli; ...`. MicrobeGraph
keeps it as text on the node, and turns the main ranks into `MEMBER_OF` arrows.

**Lipopeptide**: a class of molecules that are part fat, part protein-fragment.
Many are soapy, which is how they damage the membranes of other microbes.
Surfactin is one.

**Metabolite**: a small chemical an organism makes and often releases. Picture
the microbe as a factory and its metabolites as the products. Some of those
products happen to be poisonous to plant diseases, and this project is built on
that premise.

**Microbe**: the umbrella term for any organism too small to see, including
bacteria, fungi and yeasts.

**Monoisotopic mass**: a molecule's mass counting each element by its most
common isotope (carbon-12, hydrogen-1...). This is the value a mass spectrometer
measures for the main peak. Surfactin's is 1021.667; its average molecular
weight, which mixes in the heavier isotopes, is about 1022.3.

**Multi-omics integration**: combining several kinds of biological measurement
(genomics, proteomics, metabolomics) into a single analysis, rather than looking
at each in isolation. The difficulty is that each layer has different units,
scales and identifiers, and that is exactly why the ontology and entity
resolution phases exist.

**Oomycete**: a fungus-like organism that belongs to a different branch of life
from true fungi (it's closer to brown seaweeds). Oomycetes look like moulds and
cause serious plant diseases, so the bridge records them as their own
`pathogen_type`. *Globisporangium ultimum* is one.

**Pathogen**: an organism that causes disease. In this project, specifically a
*plant* pathogen, something that attacks crops.

**Pathway (biochemical)**: a chain of chemical reactions a cell performs in
sequence. Think of a production line with named stations, where each station's
output feeds the next.

**Powdery mildew**: a white, powdery fungal growth on leaves. On melons and
cucumbers one cause is *Podosphaera fusca*, also called *Podosphaera xanthii*.

**Protein**: a molecular machine built from an organism's genetic instructions.
To carry on with the cookbook: if the genome is the book and a gene is a recipe,
the protein is the finished dish, which then goes off and does a job. In this
project the proteins that matter are the enzymes encoded by a gene cluster.

**Proteomics**: the study of the full set of proteins in a sample. One of the
three molecular layers this project joins together.

**Rank**: one rung on the taxonomy ladder: strain, species, genus, family,
order, class, phylum, kingdom, domain. NCBI also uses in-between ranks such as
"species group" and "clade"; MicrobeGraph makes nodes only for the main ones.

**Secondary metabolite**: a molecule an organism makes that isn't needed for
basic survival but gives it an advantage, such as a weapon, a signal or a
defence. Most antibiotics are secondary metabolites. Also called a *specialised
metabolite* or *natural product*.

**Siderophore**: a molecule a microbe releases to grab iron from its
surroundings. Iron is scarce and everyone needs it, so a good siderophore is a
way of starving your competitors. Siderophores are a common biocontrol
mechanism.

**Species / genus / family**: rungs on the ladder that classifies life, from
specific to general. *Bacillus subtilis* is a species; *Bacillus* is its genus.
A postal address climbs the same way: street → city → region → country.

**Strain**: one specific isolate within a species. If "species" is a car model,
a strain is one particular car with its own history and quirks, and two strains
of the same species can behave quite differently.

**Surfactin**: a lipopeptide made by *Bacillus* bacteria. I use it as the
running example in these docs because it's real and well studied, and its whole
chain, from microbe to crop, can be backed by a citation.

**Take-all**: a root disease of wheat caused by the fungus *Gaeumannomyces
tritici* (in older papers, *G. graminis* var. *tritici*). It blackens the roots
and leaves white, empty heads.

**Taxid** (taxon ID): NCBI Taxonomy's number for an organism or a group, for
example `326423` for *Bacillus velezensis* FZB42, written `ncbitaxon:326423`
in this project. NCBI sometimes **merges** two numbers (asking for the old one
returns the record under the new one) or **deletes** one.

**Taxonomy**: the system for naming and classifying organisms, and the
hierarchy it produces.

**Yeast**: a single-celled fungus.

---

## Graphs and knowledge

**Betweenness centrality**: a measure of how often a node sits *on the shortest
route between other nodes*, which makes it a kind of "bridge" score. A road
junction can be quiet itself and still break half the city's journeys if it
closes; that junction has high betweenness. This often tells you more than raw
popularity does.

**Centrality**: any measure of how important a node is within a graph. There
are several kinds because "important" means different things.

**Community detection**: automatically finding clumps of nodes that are more
connected to each other than to the rest. Your own social network has them:
school friends and colleagues form visible clusters without anyone labelling
them.

**CURIE** ("Compact URI", pronounced *curie*): an identifier written as
`prefix:localid`, e.g. `ncbitaxon:326423`. The prefix says whose numbering
system the number belongs to, much as the country code on a phone number does.

**Cypher**: the query language for graph databases, doing for graphs what SQL
does for tables. Its patterns look like little drawings: `(a)-[:PRODUCES]->(b)`.
It arrives in Release 2.0, together with Apache AGE.

**Degree**: how many arrows touch a node, which you can read as its "popularity"
score.

**Directed graph (DiGraph)**: a graph where arrows have a direction. *A
produces B* is not the same statement as *B produces A*. MicrobeGraph is
directed throughout.

**Edge**: a connection between two nodes, with a direction and a name
(*produces*, *inhibits*). Also called a *relationship* or *link*. On the map,
it's one arrow.

**Embedding**: turning a node's position in a graph into a list of numbers, so
that nodes with similar connection patterns get similar numbers. Once every node
is a vector, ordinary machine learning applies. Describing a person by the
social circles they move in, then looking for people with similar descriptions,
works on the same principle.

**Entity resolution**: deciding that several records refer to the same
real-world thing and merging them into one node, as when you realise that
"Robert Smith", "Bob Smith" and "R. Smith (work)" are one person.

**Graph**: information stored as dots connected by arrows (nothing to do with
bar charts). A transport map is a graph, and so is a social network.

**GraphRAG**: answering a question by first *walking a knowledge graph* to
collect relevant facts, then giving those facts to a language model to phrase
the answer. See also *RAG*.

**Hop**: one step along one arrow. A "three-hop path" crosses three arrows.

**Knowledge graph**: a graph whose nodes are real-world concepts and whose edges
are meaningful relationships between them, usually with provenance attached.
MicrobeGraph is one.

**Link prediction**: scoring arrows that *don't* exist yet, to guess which ones
probably should. Social networks do this when they suggest "People you may
know". In this project the output is always a hypothesis, never a finding.

**Node**: one thing in a graph: a microbe, a compound, a crop. Also called a
*vertex*. One dot on the map.

**node2vec**: the specific method this project uses to compute embeddings. It
takes many random walks through the graph and learns numbers that predict what a
node's neighbours tend to be.

**Ontology**: a written agreement about what kinds of things exist in your world
and what relationships are allowed between them. A family tree has one built in:
it allows *parent-of* and *married-to*, but not *borrowed-a-lawnmower-from*. An
ontology is that kind of decision, made explicitly.

**Path**: a sequence of arrows leading from one node to another. Paths are the
core output of this project, because each one is an evidence chain.

**Property**: a piece of information attached to a node or edge, e.g. a
compound's molecular weight.

**Schema**: the concrete implementation of an ontology: these columns, these
types, these constraints.

**Shortest path**: the route between two nodes crossing the fewest arrows. The
graph equivalent of "fastest route".

---

## Computers, terminals, and files

**CSV** ("comma-separated values"): a plain-text table where columns are
separated by commas. Excel, any text editor and every programming language can
open one. I chose CSV for the graph files on purpose: when you can open a file
in a text editor, you can debug it.

**Directory**: another word for folder.

**Executable bit**: a file permission on macOS/Linux marking a file as "allowed
to run as a program". Set with `chmod +x`. Windows doesn't use it.

**JSON** ("JavaScript Object Notation"): a text format for structured data,
using `{ }` for records and `[ ]` for lists. Most web services reply in it.
Think of it as a nested bullet list that a computer can read reliably.

**PATH**: a list of folders your computer searches when you type a command
name. If a program isn't on the PATH, typing its name gets "command not found"
even though it's installed.

**Path (file)**: the address of a file, e.g. `data/raw/provenance.csv`. A
*relative* path starts from where you are; an *absolute* path starts from the
root of the disk. **Always prefer relative paths in a shared project**, because
an absolute path that works on your machine breaks on everyone else's.

**Terminal**: a window where you type text commands instead of clicking. Also
called shell, console, or command line.

**Working directory**: the folder your terminal is currently "in". `pwd` prints
it.

---

## Python and programming

**Abstract base class**: a template class that lists the functions every
subclass *must* provide, without providing them itself. Python refuses to create
an object that forgets one. MicrobeGraph's `Source` is one: every data source
must have `probe`, `fetch` and `tidy`.

**Argument**: a value you hand to a function. In `round(3.7)`, `3.7` is the
argument.

**Editable install** (`pip install -e .`): installing your own project into the
virtual environment as a *pointer* to its source folder rather than a copy, so
every edit is live immediately. Compare a library card that says "shelf 4" with
a photocopy of the book.

**Exit code**: a number a program hands back when it finishes. `0` means
success; anything else means a problem. People rarely see it, but schedulers
like Airflow read it to decide whether to retry.

**Function**: a named, reusable block of instructions, like a recipe you can
follow whenever you want that dish instead of working it out again each time.

**Import**: bringing code from another file or package into the one you're
writing. `import pandas` means "give me the pandas toolkit".

**Library / package**: code someone else wrote and published so you don't have
to write it yourself. Using one is like buying flour instead of growing wheat.

**Module**: one Python file containing code you can import.

**pandas**: the standard Python library for working with tables. If you know
Excel, imagine a programmable version that never gets tired and never
mis-clicks.

**pip**: Python's package installer, the command that fetches and installs
libraries.

**pyproject.toml**: the standard file describing a Python project: its name,
where its code lives, and how its tools (pytest, ruff) are set up. If the
project is a box, this is the label on it.

**Python**: the programming language this project is written in. I chose it for
readability, and because every library the project needs already exists in it.

**requirements.txt**: a text file listing exactly which packages the project
needs. It acts as the project's *receipt*: with it, anyone can rebuild an
identical toolbox.

**Script**: a file of code you run from start to finish, as opposed to a
library you import.

**Slug**: a name turned into identifier-safe text: lowercase, letters and
digits, words joined by hyphens. `Bacillomycin D` becomes `bacillomycin-d`.

**Variable**: a name attached to a value, so you can refer to it later.

**Virtual environment (`venv`)**: a folder holding a private copy of Python and
its libraries, belonging to one project only. Picture your own cupboard in a
shared kitchen, where nobody else's substitutions can break your recipe. It must
be *activated* in each new terminal session.

---

## R and its ecosystem

**CRAN** ("Comprehensive R Archive Network"): the official home of R and its
packages, run by the R Foundation. Think of it as R's app store, except that a
non-profit runs it and everything is free.

**DBI**: the standard R interface for talking to any database. You use the same
commands whether the database underneath is DuckDB, PostgreSQL or something
else, the way a universal remote gives you one set of buttons for many devices.

**ggplot2**: R's main plotting library, known for publication-quality static
figures. It builds a chart in layers: data, then how values map to position and
colour, then what marks to draw.

**igraph**: a library for building and analysing graphs. It exists for both R
and Python, and this project uses the R version to cross-check the Python
results independently.

**Positron**: a newer IDE from the makers of RStudio, built on the same
foundation as VS Code, supporting R and Python in one window. It's worth
considering for bilingual projects like this one.

**R**: a programming language designed by statisticians for statistics. Where
Python is a general language that grew statistics libraries, R started there. A
Swiss Army knife has a screwdriver and it works, but a proper screwdriver is
still better at screws.

**`.RData`**: a saved snapshot of your entire R workspace. R offers to write one
when you quit and reload it when you start. **Turn both off.** It makes scripts
appear to work when they only work on your machine, because an object is still
sitting in memory from last time: a recipe that only works because there's
already stock in your fridge that isn't on the ingredients list.

**Reactive programming**: a style where outputs recompute automatically when the
inputs they depend on change, and *only* those outputs. Shiny is built on this
model. *Everyday example:* a spreadsheet; change cell B2 and only the formulas
referencing B2 update.

**`renv`**: R's per-project package library, the exact counterpart of Python's
`.venv`. `renv.lock` plays the role of `requirements.lock.txt`. Unlike `.venv`,
it activates automatically when you open the project.

**`.Rproj`**: a small file marking a folder as an RStudio project. Opening it
sets the working directory correctly, which prevents the most common R beginner
error: scripts that only run if you happen to be in the right folder.

**Rscript**: the command that runs an R script from the terminal, R's equivalent
of `python script.py`. That's what makes R scripts automatable, with no IDE
involved.

**RStudio**: the free, open-source application most people write R in. Keep in
mind that it is *not* R: R is the engine and RStudio the dashboard, the same
relationship Python has with VS Code.

**Shiny**: R's equivalent of Streamlit: it turns R code into a web app with
controls and charts, and splits every app into `ui` (what the page looks like)
and `server` (what it does). If Shiny is a restaurant with a printed menu and a
kitchen, Streamlit is a food truck where you watch your order being made.

**The pipe (`|>`)**: passes a result into the next function so code reads left
to right instead of inside out. `edges |> filter(...) |> count(...)` reads as
"take edges, then filter, then count". Python's method chaining is the same
idea.

**tidyverse**: a family of R packages sharing a common style, including `dplyr`
(data manipulation), `ggplot2` (plots), `readr` (reading files) and `tidyr`
(reshaping). Learning one makes the others easier.

**Vector**: R's basic unit, an ordered list of values. Even a single number is a
vector of one, which is why R prints `[1] 2` rather than `2`. *(R also counts
from 1, not 0, which is the single most common stumble for anyone arriving from
Python.)*

---

## Git and GitHub

**Branch**: an independent line of work in the same repository. This project
uses three: `master` (stable), `beta` (release candidate), `develop` (daily
work).

**Clone**: download a copy of a repository including its whole history, wired
up to talk to the original.

**Commit**: one saved snapshot of your project, with a message explaining what
changed. Clicking "save a named version" in a document is the nearest everyday
equivalent.

**Fast-forward**: updating a branch by moving its pointer along an existing
line, with nothing to merge. This is the clean case, and `--ff-only` means "only
do it if it's this clean; otherwise stop and tell me".

**Git**: the program on your computer that records snapshots of your project, a
save-game system for your work.

**GitHub**: a website that stores copies of Git repositories online. Git and
GitHub are different things; you can use Git without GitHub.

**.gitignore**: a file listing things Git must never track: secrets,
rebuildable data, huge folders.

**Origin**: Git's default nickname for "the repository I cloned from". Usually
your GitHub copy.

**Personal Access Token (PAT)**: a long, generated password used by programs
instead of your account password. It can be scoped narrowly and revoked
individually.

**Pull**: fetch changes from the remote and apply them to your local branch.

**Push**: send your local commits up to the remote.

**Remote**: a copy of the repository somewhere else, usually GitHub.

**Repository ("repo")**: a project folder Git is watching, plus its entire
history.

**SSH key**: a matched pair of files proving your identity without sending a
password. The pair works like a physical key (private, yours) and the lock it
fits (public, given to GitHub).

**Staging**: marking changes for inclusion in the next commit. *Everyday
example:* putting items in a shopping basket, where nothing's bought yet.

**Tag**: a permanent label on a specific commit, used to mark releases (`v1.0`).

**Untracked**: a file Git can see but isn't watching yet.

---

## Data, databases, and SQL

**Column**: one field in a table; one attribute of every row.

**Constraint**: a rule the data must obey, enforced by the database or the
loader. "This value must be unique" is a constraint.

**Database**: a program whose job is to store information in an organised way
and answer questions about it quickly. Compare a library with a catalogue and a
fast librarian to a pile of books in a garage.

**DuckDB**: the database used here, a complete analytics database that lives in
a single file on your laptop, with no server, no account and no cost. DuckDB is
also the standard local stand-in for cloud warehouses, so the SQL you write
transfers directly.

**Foreign key**: a column whose values must exist in another table. In our
graph, every `source_id` in `edges.csv` must exist in `nodes.csv`.

**Join**: combining two tables by matching a shared column. The table-shaped
equivalent of following one arrow.

**Primary key**: the column that uniquely identifies each row. Ours is
`node_id`.

**Query**: a question asked of a database, usually written in SQL.

**Read-only**: able to look but not change. The app's SQL console is read-only
*by construction*, meaning the code enforces it rather than the docs promising
it.

**Row**: one record in a table; one thing.

**Schema**: the structure of a database: which tables exist, which columns they
have, which rules apply.

**SQL** (pronounced "sequel" or "ess-cue-ell"): the language for asking
databases questions. It reads close to English:
`SELECT name FROM compounds WHERE activity = 'antifungal'`. It was invented in
the 1970s and is still everywhere.

**Table**: a grid of rows and columns. Tables are excellent at counting and
filtering but bad at chains of unknown length, which is why this project also
builds a graph.

---

## Getting data from the internet

**API** ("Application Programming Interface"): a way for one program to ask
another program for data, designed for machines rather than humans. A
restaurant's takeaway hatch is a good picture of one: a defined way to place an
order and collect it, without wandering into the kitchen.

**API key**: a string identifying who is making requests, so a service can apply
limits fairly. Sometimes it's optional (a courtesy that raises your rate limit)
and sometimes required. **It is always a secret.** In this project keys live in
`.env`, are shown on screen only as "set" or "not set", and travel only inside a
request's body. See [`img/secrets_env.svg`](img/secrets_env.svg).

**Archive (tarball)**: many files bundled into one. A `.tar.gz` file is normally
bundled with `tar` and then compressed with `gzip`. MIBiG 4.0 arrives as one, and
this project reads the files straight out of it without unpacking. A suitcase
packed with vacuum bags is the same idea: one thing to carry, with everything
inside intact. The name is only a label, though: MIBiG 4.0's `.tar.gz` turned out
not to be gzip-compressed at all, so the code works out the compression from the
file's first bytes instead of trusting the name.

**Checksum**: a short fingerprint calculated from every byte of a file; change
one byte and the fingerprint changes completely. Publishers list it beside a
download so you can prove you received exactly their file. **MD5** and
**SHA-256** are two common kinds; SHA-256 is longer and stronger. Checking one
is like counting a parcel's contents against its packing slip. See
[`img/checksum_fingerprint.svg`](img/checksum_fingerprint.svg).

**DOI** (Digital Object Identifier): a permanent link to a published thing (a
paper or a dataset), written like `10.1093/nar/gkae1115`. It keeps working even
when websites move, so a citation with a DOI can always be found again.

**Endpoint**: one specific address within an API that answers one kind of
question.

**`.env` file**: a plain-text file in the project folder holding your private
settings, one `NAME=value` per line, such as an API key. It's listed in
`.gitignore` so Git never sees it; the repository holds `.env.example`, the same
names with every value empty. See [`04-more-sources-secrets.md`](04-more-sources-secrets.md), Step 3.

**Environment variable**: a named setting your computer hands to a program when
it starts, kept outside the program's own files. It's how programs usually
receive secrets; `.env` is a convenient way to set them for one project.

**E-utilities** (Entrez Programming Utilities): NCBI's API. MicrobeGraph uses two
of its programs: `einfo` (facts about a database) and `efetch` (full records).

**Evidence locker**: this project's name for `data/raw/`, the untouched original
responses from every source, kept forever. They play the same part as the
original receipts kept behind a tax return.

**GET and POST**: the two common kinds of web request. A GET puts everything in
the web address, like a postcard anyone handling it can read; a POST carries its
details in the request **body**, like a sealed envelope. MicrobeGraph sends long
lists and any key by POST.

**HTTP**: the protocol web browsers and programs use to request things from
servers.

**Ingestion**: the act of getting data into your system, and the first pipeline
stage.

**Manifest**: the file `manifest.json` in each API snapshot, listing what was
asked and what came back. It's written last, so its presence means the fetch
finished.

**`.part` file**: a download in progress, saved under a temporary name and
renamed only once it is complete and verified, so a dropped connection never
leaves a half-file that looks finished.

**Provenance**: the recorded origin of a piece of information: where it came
from, when, and under what terms. Written to `data/raw/provenance.csv` on every
fetch.

**PUG REST**: PubChem's API. You put what you want in the address (compounds by
CID, their properties or synonyms) and the CIDs themselves in a POST body.

**Rate limit**: a cap on how many requests you may make per second. Exceed it
and you get blocked; respecting it is basic politeness to a free service.
PubChem allows 5 a second, NCBI 3 (10 with a key) and KEGG 3.

**Request body**: the part of a request that carries its details separately from
the web address. Error messages, logs and browser histories show addresses, not
bodies, which is why a key belongs in the body.

**Retry with backoff**: when a request fails, waiting a moment and trying
again, waiting longer each time. *Everyday example:* the phone is engaged; you
don't redial forty times a second.

**Snapshot**: one fetch from a web API, kept as a dated folder in the evidence
locker: every answer exactly as it arrived, plus a manifest. A new day or a new
set of questions makes a new snapshot; older ones are kept for comparison. See
[`img/api_snapshot.svg`](img/api_snapshot.svg).

**Source adapter**: the small piece of code that connects one data source to the
project, by providing the three functions of the **contract**: `probe()` (what
is out there?), `fetch()` (bring it home, untouched) and `tidy()` (make it fit
the rulebook). If the contract is a wall socket, each adapter is the plug on an
appliance. See [`03-ingestion-mibig.md`](03-ingestion-mibig.md).

**Staging table**: one source's data, already reshaped into the project's
standard columns but not yet merged with the others. Written by `tidy()` to
`data/processed/staging/`. dbt (Phase 10) uses the same word for the same idea.

**Status code**: a number a server returns describing the outcome. 200 = fine.
404 = not found. 403 = refused. 429 = you're going too fast. 500 = the server
broke.

**Throttling**: a service slowing down or refusing requests that arrive too fast.
PubChem reports how close you are with a traffic light in each answer's
`X-Throttling-Control` header: Green, Yellow, Red or Black.

**Timeout**: how long a program waits for an answer before giving up. Without
one, a silent server can make a program hang forever.

**User agent**: a short line a program sends identifying itself. Sending a
polite, truthful one (naming the project and a contact) is expected etiquette
when using public scientific APIs.

---

## The data sources used here

**ChEBI** (Chemical Entities of Biological Interest): a free dictionary of small
molecules, run by EMBL-EBI. Phase 2 reads ChEBI numbers from PubChem's synonyms
(`CHEBI:30838` is itaconic acid).

**CID** (compound identifier): PubChem's number for one chemical structure, for
example `811` for itaconic acid, written `pubchem.compound:811` here.

**InChIKey**: a 27-character fingerprint of a chemical structure, the same in
every database, which makes it handy for matching compounds across sources.

**KEGG**: the Kyoto Encyclopedia of Genes and Genomes, a set of hand-drawn maps
of cell chemistry (pathway maps such as `map00660`) with the compounds on them
(`C00490`). **Not open data:** its API is for academic use by academic users,
other use needs a commercial licence, and serving its data to others needs a
licence too. MicrobeGraph fetches it locally and never publishes KEGG rows.

**MIBiG**: *Minimum Information about a Biosynthetic Gene Cluster*. A
community-curated public repository of gene clusters that have been
experimentally shown to produce a particular molecule, published under CC-BY on
Zenodo with a permanent DOI. It's **this project's backbone**, because it
supplies the organism → cluster → compound arrows.

**MIBiG quality grade**: MIBiG's own rating of each entry: `high`, `medium`,
`low` or `questionable`. MicrobeGraph carries it through as the `confidence` of
every arrow from that entry (0.95, 0.85, 0.70, 0.50).

**NCBI**: the US National Center for Biotechnology Information. It runs Taxonomy
(the classification of life) and Datasets (genome records), among much else.
NCBI places no restrictions on using its data, although some people who submit
data to it claim rights in what they submitted.

**Negative result**: a test that looked for something and did not find it. MIBiG
records some bioactivities as `"observed": false`. MicrobeGraph counts them but
never turns them into a `HAS_ACTIVITY` arrow, which would say the opposite.

**PubChem**: the US National Institutes of Health's chemistry database. Given a
CID it returns a formula, weights, the structure and a synonym list; given a name
it can find the CID. Access is free and needs no account. Its synonym lists are
the raw material for entity resolution here.

**SMILES**: a way of writing a molecule's structure as one line of text, for
example `C=C(CC(=O)O)C(=O)O` for itaconic acid.

**Synonym**: another name for the same thing. One molecule can have dozens
(itaconic acid has about ninety in PubChem), which is why names alone can't be
trusted to match records.

**The curated bridge**: this project's own small, hand-assembled CSV linking
compounds to pathogens to crops, because no public database publishes those
links as a downloadable table. Every row carries a citation and every edge is
labelled `curated_literature`, and the whole layer can be filtered out. Every
row passes thirteen checks before it's loaded; how to add one is in
[`curation/README.md`](../curation/README.md).

**Zenodo**: a free, permanent archive for research outputs, run by CERN. Each
upload gets a DOI and a checksum for every file. MIBiG publishes its releases
there.

---

## Analysis and statistics

**Aggregate**: to summarise many rows into one number: a count, a sum, an
average.

**Confidence**: in this project, a 0-1 number a source adapter attaches to an
edge. The project uses it to rank edges, never to hide them.

**Deduplicate**: remove repeated records that describe the same thing.

**Hypothesis**: a proposed explanation worth testing, not yet a finding. Every
predicted link in this project is a hypothesis, and is labelled as one.

**Normalise (text)**: put text into a consistent form before comparing:
lowercase, trimmed, punctuation stripped. It stops `Surfactin ` and `surfactin`
from being treated as different things.

**Null model**: a random version of your data, built on purpose as a comparison.
Any network has *some* clustering, so "we found three communities" means nothing
until you know what a random network of the same size and shape would have
produced. You'd reason the same way about a coin: before calling it biased, you
need to know what a fair coin looks like over the same number of throws.

**Permutation test**: shuffling your data many times, keeping certain properties
fixed, and asking how often the shuffled version is as extreme as the real one.
If the real result beats 999 of 1,000 shuffles, chance is an unlikely
explanation. Card players will recognise the idea: deal the same cards thousands
of times and see how often a hand as good as yours turns up.

---

## Apps and deployment

**Backend**: the part of software that does the work, out of the user's sight.
If the app were a restaurant, this would be the kitchen.

**Deployment**: putting your app somewhere on the internet so other people can
use it.

**Frontend**: the part the user sees and touches. In the same restaurant, it's
the dining room and the menu.

**Graceful degradation**: designing so that when an optional piece is missing,
that one feature disappears quietly and everything else still works. This
project applies it to the AI layer: with no API key there's no chatbot, but the
app isn't broken.

**Localhost**: your own computer, acting as a server for you only. When an app
prints `http://localhost:8501`, that page exists on your machine and nobody else
can reach it.

**Secret**: any value that must never be published: API keys, tokens,
passwords. Kept in `.env` or `secrets.toml`, both gitignored.

**Streamlit**: a Python library that turns an ordinary script into a web app
with buttons and charts, without any web development. In car terms, Streamlit is
an automatic gearbox: less control than a manual, but you're driving today
rather than in three months.

---

## Containers, orchestration, and the modern data stack

**Airflow**: an orchestrator. It runs pipeline steps in the right order, on a
schedule, with retries and alerts. You can picture it as an alarm clock combined
with a checklist that knows which tasks must finish before others can start.

**Apache AGE**: a PostgreSQL extension that adds graph storage and Cypher
queries to an ordinary Postgres database. It lets this project cover
graph-database skills without running a second server.

**Astro CLI**: a free command-line tool that runs Apache Airflow locally in
containers. It works with Docker or Podman.

**Backfill**: re-running a scheduled pipeline for dates in the past, usually
after fixing a bug.

**Base image**: the image your image is built on top of. Nobody builds a kitchen
from raw ore; you start with a room that already has plumbing and power, and the
base image is that room.

**Bind mount**: attaching a folder from your own machine into a container, so
edits appear inside instantly. Bind mounts are for development, never for code
in production.

**Compose**: a file describing several services, how they connect, what storage
they keep and in what order they start, plus the command that runs them all. If
a Containerfile is the recipe for one dish, a compose file is the menu plus the
kitchen rota.

**Container**: a sealed, lightweight box holding a program plus everything it
needs to run, so it behaves identically on any machine. Imagine a recipe shipped
together with its kitchen. See [`CONTAINERS.md`](CONTAINERS.md).

**Containerfile / Dockerfile**: the text file describing how to build an image.
The two names are the same format, and both engines read both, although Podman
prefers the first name and Docker the second. This project uses `Containerfile`
because it is the vendor-neutral name.

**DAG** ("Directed Acyclic Graph"): in orchestration, the map of which tasks
depend on which. It's *directed* because dependencies point one way, and
*acyclic* because a task can't ultimately depend on itself.

**Databricks**: a cloud platform for large-scale data processing built on Spark.
This project uses it for one job that really is compute-heavy (mining paper
abstracts), and I've flagged it as the weakest-fit tool in the plan.

**dbt**: a tool that turns a folder of SQL files into a tested, documented,
version-controlled transformation pipeline. It works out which model depends on
which, runs them in order, and tests the results.

**Docker**: the best-known container platform. Free for personal use, it
requires a paid subscription in larger companies, which is often why it's
unavailable on work machines.

**ELT / ETL**: Extract, Load, Transform (or Extract, Transform, Load). The
difference is whether you clean the data before or after loading it into the
warehouse. Modern practice usually loads first and transforms in SQL, and dbt is
built on that premise.

**FastAPI**: a Python framework for building web APIs. It generates interactive
documentation automatically and validates every request against declared types.

**Health check**: a command run periodically inside a container to answer "is
this service actually *working*?", which is a different question from "is the
process running?". With a kettle, you'd wait for the click rather than trusting
that the switch is on.

**Idempotent**: safe to run more than once with the same result. A pipeline step
that appends rows every run is *not* idempotent; one that replaces a day's data
is. Retries are only safe when steps are idempotent.

**Image**: the packaged blueprint a container is started from. An image is
static, whereas a container is running.

**Lakehouse**: a storage design combining a cheap data lake with warehouse-style
querying. Databricks is built around this idea.

**Layer**: a saved snapshot of the filesystem after one Containerfile
instruction. Images are layers stacked, and the engine caches them, which is why
instruction order changes rebuild times dramatically. Packing a suitcase works
the same way: changing the item on top is easy, but changing the shoes at the
bottom means unpacking everything.

**Multi-stage build**: using one image to *build* and a second, minimal one to
*run*, copying only the finished output across. *Everyday example:* baking needs
mixing bowls and a messy worktop, while serving needs a plate, and you don't
deliver the kitchen with the cake.

**Named volume**: storage managed by the container engine that survives a
container being deleted. If the container is a hotel room, cleaned between
guests, the volume is your suitcase, which leaves with you.

**nginx**: a small, very fast web server. Here it hands finished HTML, CSS and
JavaScript files to browsers.

**Orchestration**: running the steps of a pipeline in the right order, on
schedule, handling failures. This is the problem Airflow and Prefect solve.

**pgvector**: a PostgreSQL extension adding vector similarity search, used here
to store embeddings for the RAG layer.

**Podman**: a container engine that runs without a background daemon and without
root privileges. Red Hat's default on RHEL, and usually the right choice on
shared or locked-down machines.

**Prefect**: a Python orchestration library that needs no containers, which
makes it the container-free route through this project's orchestration phase.

**Publishing a port**: making a port inside a container reachable from your
machine, with `-p outside:inside`, much as a hotel front desk connects an
outside call to a room's phone. Anything not published stays invisible from
outside, which is why this project's database has no published port.

**React**: a JavaScript library for building user interfaces from reusable
components.

**Registry**: a place images are stored so others can download them, a sort of
app store for images. This project publishes to GitHub Container Registry
(GHCR).

**REST API**: a convention for how programs ask each other for things over the
web, using URLs and HTTP verbs.

**Rootless**: running containers as an ordinary user rather than as root. If
something misbehaves it has your permissions, not the machine's.

**SELinux**: an extra security layer in Red Hat Linux that labels every file and
controls which processes may touch which labels. Picture a building where every
room has a colour-coded badge reader. It causes the classic RHEL container
symptom, `Permission denied` on a mounted folder despite correct file
permissions, and the fix is to add `:Z` to the mount.

**Service discovery**: how containers find each other. Under compose, each
service is reachable by its **name** (`postgres:5432`) rather than an IP
address, which changes on every restart. In an office, you'd dial "Accounts" on
the phone system instead of a full external number.

**Snowflake**: a cloud data warehouse that separates storage from compute. It's
used here to demonstrate portability; the data volume doesn't need it.

**Spark**: a framework for processing data across many machines at once.

**TypeScript**: JavaScript with types added. Types work like seatbelts: they
catch the mistake of passing a number where text was expected while you're
typing, rather than in front of a user.

**Warehouse (data)**: a database built for analytical questions over large
volumes, as opposed to running an application.

**WSL2**: Windows Subsystem for Linux, a real Linux kernel inside Windows.
Containers need it, because containers are Linux technology.

---

## AI and language models

**Agent**: an AI that *takes actions* rather than only answering: it plans
steps, calls tools, checks results, and loops until the task is done. The
difference from a chatbot is easiest to see with a query: a chatbot tells you
which query would answer your question, while an agent runs it, reads the result
and decides what to do next.

**Context**: the information given to a language model along with your question.
RAG exists to control what goes in here.

**Hallucination**: when a language model produces a confident, fluent, entirely
invented answer. Hallucination is the reason a scientific project must ground
answers in real, retrieved facts rather than the model's memory.

**Large language model (LLM)**: the technology behind chat assistants. It's
excellent at language and, on its own, unreliable at specific facts.

**MCP (Model Context Protocol)**: an open standard letting an AI assistant plug
into an external tool or data source. It plays the role USB plays for hardware:
one agreed shape, so any device works with any computer.

**Prompt**: the instructions and question given to a language model.

**RAG (Retrieval-Augmented Generation)**: fetching the relevant real information
*first*, handing it to the model, and instructing it to answer only from what it
was given. It's like handing a well-read friend the exact page from the manual
instead of asking them to answer from memory.

**Tool (in AI)**: a function an AI is allowed to call, with defined inputs and
outputs. This project's MCP tools will be read-only by design.

---

## Quality, testing, and honesty

**Action (in GitHub Actions)**: a ready-made step that someone publishes for
workflows to borrow, named by owner, name and major version, like
`actions/checkout@v7` (fetch the code) or `actions/setup-python@v7` (install
Python). Borrowing one is like using a standard plug instead of wiring your own.
The version number matters: GitHub retires old versions from time to time, and
[`03-ingestion-mibig.md`, section 13](03-ingestion-mibig.md#13-step-9-continuous-integration-tests-on-four-systems)
shows how to move to a newer one.

**Annotation (on a GitHub run)**: a note GitHub pins to a finished run. A yellow
**warning** means something still works but should change soon, such as an
action version being retired. A grey **notice** is information only. Neither is
a failure: a failed job has a red cross instead.

**Assertion**: a statement in a test that must be true, or the test fails.

**Changelog**: a file (`CHANGELOG.md`) listing what changed in each version,
newest first, in plain language. Its sections become the release notes on
GitHub.

**Checkpoint**: in this tutorial, a verification step: run this, expect that. If
it doesn't match, stop and fix it before continuing.

**Continuous integration (CI)**: every time `master` changes (which your
end-of-phase push always does), the project is installed automatically on fresh
computers and the tests are run. Here that means Windows, macOS, Linux and a
RHEL 8 container, through **GitHub Actions** (GitHub's free service for running
such jobs, configured by files in `.github/workflows/`). Think of a recipe tested
in other people's kitchens as well as your own. A run can also be started by
hand with the **Run workflow** button on the Actions tab.

**Evidence level**: the label on every edge saying what kind of knowledge it is:
`curated_experimental`, `database_assertion`, `curated_literature`, or
`inferred`. See
[`02-ontology-and-data-model.md`](02-ontology-and-data-model.md).

**Fake server (test double)**: a stand-in that answers like a real server but
from a script in memory, so tests run offline, fast, and the same every time.
MicrobeGraph's is `FakeSession` in `tests/conftest.py`.

**Fixture**: a small, controlled piece of test data. **It must be built from the
same code or schema as the real thing, never from memory**: a fixture that has
drifted from reality produces tests that pass while the system fails. Where you
can, cut it down from a real record. Phase 1 learned this twice: the real MIBiG
archive turned out not to be gzip-compressed, and it wrote activity names in a
style the hand-made test record didn't use. Both times, every test had passed.

**Handbook**: [`HANDBOOK.md`](HANDBOOK.md), the one document to read first: the
whole build, day 0 to the finished product, in order, linking to every guide.
Updated in the same commit as any change it describes.

**Ledger**: a written record of what a step did: what was merged, removed, or
changed, and why. The resolution ledger and the provenance log are both ledgers.
A bank statement is one in this sense; it records what happened to the money
rather than holding the money itself.

**Pipeline**: a series of stages where each one's output is the next one's
input, flowing one way. *Everyday example:* beans → grinder → espresso machine →
cup. Each stage has one job and can be tested alone.

**pytest**: the tool that runs this project's automated tests.

**Reproducibility**: the property that someone else, on a different machine, can
run your work and get the same result. That's why this project has
`requirements.txt`, the evidence locker and the provenance log.

**Test (unit test)**: a small automated check proving one function does what you
claim. A cook tastes the sauce before serving instead of hoping; a test does the
same for code.

**Validation**: checking data against rules before accepting it. This project's
loader *refuses* invalid rows rather than warning about them, because warnings
get ignored.

---

*Missing a term? Please open an issue; I treat that as a documentation bug.*
