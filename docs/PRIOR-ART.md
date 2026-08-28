# Prior art: what exists already, and where this project sits

**Prerequisites:** [`00-architecture.md`](00-architecture.md) — you should know what
a knowledge graph is and what MicrobeGraph builds. No specialist background
needed; every tool and term below is explained.

**Learning goal:** you will know what already exists in this field, how
MicrobeGraph differs, and — just as importantly — **what it does not claim**. You
will also understand why naming the related work makes a project *more* credible
rather than less.

**Time:** 25–30 minutes of reading. Nothing to run.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [Why a document like this exists](#1-why-a-document-like-this-exists)
2. [The landscape, layer by layer](#2-the-landscape-layer-by-layer)
3. [The closest prior art](#3-the-closest-prior-art-socialgene)
4. [The pattern borrowed from biomedicine](#4-the-pattern-borrowed-from-biomedicine)
5. [The gap: where the knowledge stops being machine-readable](#5-the-gap-where-the-knowledge-stops-being-machine-readable)
6. [Commercial platforms](#6-commercial-platforms)
7. [Where MicrobeGraph sits](#7-where-microbegraph-sits)
8. [What is genuinely uncommon here](#8-what-is-genuinely-uncommon-here)
9. [What this project does not claim](#9-what-this-project-does-not-claim)
10. [What would make it more novel](#10-what-would-make-it-more-novel)
11. [References](#11-references)

---

## 1. Why a document like this exists

### What "prior art" means

**Prior art** is everything already published or built that relates to what you're
making. The term comes from patent law: before an invention can be patented,
someone checks whether it already exists.

*Everyday example:* before spending a year designing a better umbrella, you spend
an afternoon finding out what umbrellas already exist. Not to be discouraged — to
find out which specific problem is still unsolved, and to avoid loudly announcing
something invented in 1962.

### Why publishing it makes a project stronger

This is counter-intuitive, so it's worth being explicit.

A repository that says *"here is the related work, here is precisely where mine
differs, and here is what mine is not"* reads as work by someone who knows the
field. A repository silent about related work reads as someone who didn't look —
and in a specialised area, the people most likely to read it are exactly the
people who will know.

*Everyday example:* two people describe a restaurant idea. One says "a place that
sells food". The other says "there are four Italian places on this street; three
do pizza, one does pasta, none opens for lunch — I'd open for lunch." The second
person has obviously done the work, and their idea is more believable *because*
they named the competition.

**The rule this document follows:** state what exists, state what's different,
state what isn't claimed. All three, plainly.

---

## 2. The landscape, layer by layer

MicrobeGraph sits on top of a mature ecosystem. Here is that ecosystem, from the
raw biology upward.

### Layer 1 — The curated databases

**MIBiG** — *Minimum Information about a Biosynthetic Gene Cluster*. A
community-curated repository of gene clusters experimentally shown to produce a
particular molecule. Version 2.0 held 2,021 entries; 3.0 added 661 more with
re-validation of existing ones; 4.0 continues that work through international
collaboration.

**What it is, in plain terms:** a hand-checked list of "this microbe's DNA
contains this production line, and it makes this molecule", each entry signed off
by a human against published experiments.

**This is MicrobeGraph's backbone.** The project does not compete with MIBiG — it
consumes it, with attribution.

### Layer 2 — The prediction tools

**antiSMASH** — scans a genome and predicts where the biosynthetic gene clusters
are. Where MIBiG holds clusters that were *proven*, antiSMASH finds clusters that
are *probable*, at enormous scale.

*Everyday example:* MIBiG is a list of restaurants someone has actually eaten at
and reviewed. antiSMASH is an algorithm scanning satellite images for buildings
that look like restaurants. Both useful, very different confidence.

### Layer 3 — The analysis tools

**BiG-SCAPE** and **CORASON** — build *similarity networks* of gene clusters:
which clusters resemble which others, grouped into families. Widely used; a
typical study might network a thousand clusters from a few dozen genomes and find
that most have no close match to anything characterised.

**Note what kind of network this is.** The nodes are all the *same type* — gene
clusters — and the edges mean "these two resemble each other". That is a
**similarity network**.

MicrobeGraph is a different shape: nodes of nine *different* types, edges that are
named relationships (*produces*, *inhibits*, *infects*). That is a **knowledge
graph**.

*Everyday example:* a similarity network is a chart of which songs sound alike. A
knowledge graph is a chart of who wrote which song, for which film, in which year.
Both are networks; they answer completely different questions.

### Layer 4 — Machine learning on clusters

An active, crowded area. Recent work includes transformer models trained on
22,258 Actinomycete clusters to predict what compound class a cluster produces,
and deep networks classifying cluster products at fine structural resolution using
roughly 3,800 cluster–product pairs from MIBiG.

**Be clear-eyed about this:** applying machine learning to BGC data is not novel.
Phase 7 of this project is *learning* an established technique on a small graph,
not advancing the state of the art. The docs say so.

---

## 3. The closest prior art: SocialGene

If you read one thing in this document, read this section.

**SocialGene** builds large-scale knowledge graphs in Neo4j for comparative
genomics and natural-product discovery. It links MIBiG clusters to chemical
structures in NPAtlas, connects genomes to mass-spectrometry features and GNPS
molecular-networking clusters, and ships precomputed databases — including one
spanning over 343,000 reference genomes and another holding more than two million
antiSMASH-predicted clusters.

**Say plainly what that means: the first half of MicrobeGraph already exists, is
published, is open source, and is enormously larger.**

| | SocialGene | MicrobeGraph |
|---|---|---|
| Graph store | Neo4j | DuckDB + NetworkX *(Postgres + AGE in Release 2.0)* |
| Scale | Hundreds of thousands of genomes, millions of clusters | Thousands of nodes |
| Chain covered | genome → cluster → protein → compound → mass spec | organism → cluster → protein → compound → **pathogen → crop** |
| Audience | Working bioinformaticians | Anyone, from zero |
| Evidence model | Provenance by source | Evidence *level* on every edge, filterable |
| Documentation | Reference documentation | The repository **is** a tutorial |

**Two honest conclusions:**

1. **On scale and on the genomics half, SocialGene is simply better.** It is the
   right tool if you want to mine biosynthetic potential across all of RefSeq.
   Nothing here competes with that.
2. **The chain is different at the end.** SocialGene connects clusters to
   *chemistry and analytical measurement*. MicrobeGraph connects them to *disease
   outcomes in crops* — which is a different question and requires data that isn't
   in any of these systems (see [section 5](#5-the-gap-where-the-knowledge-stops-being-machine-readable)).

**If you want the state of the art in BGC knowledge graphs, use SocialGene.** This
project is a smaller, differently-aimed, fully-taught system that extends the
chain past the point the others stop.

Saying that clearly costs nothing and buys a great deal of credibility.

---

## 4. The pattern borrowed from biomedicine

Building a heterogeneous knowledge graph and using it to suggest untested links is
**a well-established pattern in biomedicine**, not an invention of this project.

Drug-repurposing knowledge graphs — Hetionet is the best-known early example, with
several larger successors — integrate genes, compounds, diseases, symptoms and
side effects into one graph, then use path-based and embedding methods to rank
plausible drug–disease pairs for testing.

**MicrobeGraph applies that established pattern to agriculture.** The structure of
the question is the same:

| Biomedical version | This project |
|---|---|
| Which existing drug might treat this disease? | Which microbe might suppress this crop disease? |
| compound → target → pathway → disease | organism → cluster → protein → compound → pathogen → crop |
| Rank candidates for a clinical trial | Rank candidates for a greenhouse trial |

**That transfer is the honest description of the idea:** a proven pattern moved to
a domain where it is much less common. Applying a known method in a new domain is
legitimate, useful work — and it is *not* the same as inventing the method.

---

## 5. The gap: where the knowledge stops being machine-readable

Here is the one place where something is genuinely missing, and it is the reason
this project exists.

**The biocontrol literature is enormous.** Reviews consolidate which microbial
lipopeptides and polyketides act against which crop pathogens — *Fusarium*,
*Botrytis*, *Magnaporthe*, *Colletotrichum*, *Phytophthora*, *Rhizoctonia* — from
genera such as *Bacillus*, *Pseudomonas*, *Streptomyces* and *Trichoderma*. The
economic stakes are well documented: crop losses to disease are routinely
estimated at 20–40% of global production.

**And essentially none of it is downloadable as structured data.**

It exists as prose: sentences in papers, written for humans. There is no public
table you can query with *"which compounds have reported activity against
Botrytis cinerea on strawberry, and which organisms produce them?"*

*Everyday example:* imagine every restaurant review ever written existing only as
flowing paragraphs, with no ratings, no cuisine tags, no price fields. All the
knowledge is there. None of it is sortable.

**This is the gap MicrobeGraph addresses**, and it addresses it in a deliberately
modest, honest way:

- A small hand-curated CSV — **dozens of rows, not thousands**
- **A literature citation required on every row**, enforced by the loader
- Every such edge stamped `evidence_level = curated_literature`, visually distinct
  in the app, and filterable out entirely
- Version-controlled, so its history is public

**What this is:** a transparent, auditable, tiny bridge across a real gap.

**What this is not:** a comprehensive biocontrol database. Building one properly
would take a funded team years, and the project says so everywhere the layer
appears.

---

## 6. Commercial platforms

Several well-funded companies work on the same underlying problem — finding
microbes that protect crops.

- **AgBiome** — its GENESIS platform runs environmental sampling through genomics,
  bioinformatics and high-throughput screening to identify useful microbes.
- **Lavie Bio** — uses computational predictive biology, originally developed for
  plant breeding, to design microbial products from genetic signals.
- **Indigo Ag** — a large genomic microbe database matching beneficial microbes to
  crops and regions.
- **Biome Makers** — a soil-microbiome platform built on thousands of soil samples
  across many countries, producing disease-risk and soil-health metrics.
- **IFF Crop Biologicals** — an integrated discovery-to-field pipeline inside a
  large ingredients company.

**What their platforms have that this project does not, and never will:**

1. **Physical strain collections** — tens of thousands of isolates, owned.
2. **Proprietary screening results** — their own assay data on their own strains.
3. **Field trial data** — the expensive, slow, decisive evidence.
4. **Regulatory and commercial infrastructure.**

**Their moat is the data, not the graph.** Any competent team can build a
knowledge graph. Nobody else has their strain library.

**Which points at where public value actually lies.** These platforms are closed —
you cannot inspect their reasoning, check their sources, or reproduce their
conclusions. An open, evidence-labelled, reproducible graph is a *different kind
of object*: not a competitor to a commercial pipeline, but a public, auditable
starting point that anyone can extend.

### Could this become a product?

An honest answer, since it's a fair question to ask of any project.

**Selling the data would not work.** The valuable layer is hand-curated from
published papers, so anyone can rebuild it; it is small; and it lacks the
proprietary experimental evidence that gives the commercial platforms their value.
There is no data moat here.

**The more credible direction is the opposite: the machinery, not the facts.**
Many research organisations have the same underlying problem — scattered internal
and public data, no provenance, no way to ask questions that cross several
sources. What they cannot easily buy is a *system* for building an
evidence-graph over **their own private data**, with the ontology, entity
resolution, evidence model and query layer already designed.

In that framing the product is the framework — ingestion contract, ontology,
resolution ledger, evidence discipline, GraphRAG, MCP server — and the customer
supplies the data. The graph is the product; the facts stay theirs.

**Stated as honestly as possible:** that is a plausible direction, not a plan.
This repository is a working demonstration and a teaching resource. Anyone
considering the commercial path would need to talk to people actually working in
that field first.

---

## 7. Where MicrobeGraph sits

| Question | Best existing answer | Does MicrobeGraph help? |
|---|---|---|
| Which clusters exist in this genome? | antiSMASH | No — use antiSMASH |
| Which clusters are experimentally proven? | MIBiG | No — MicrobeGraph reads MIBiG |
| Which clusters resemble each other? | BiG-SCAPE | No — different network shape |
| Mine biosynthetic potential across all of RefSeq | SocialGene | No — SocialGene is far larger |
| What is this compound's chemistry? | PubChem | No — MicrobeGraph reads PubChem |
| Which compounds act on this crop pathogen? | **Scattered across papers** | **Yes — this is the gap** |
| Show the full chain from crop back to microbe, with evidence for every step | **Nothing public** | **Yes — this is the point** |
| How confident is each link in that chain? | Rarely modelled anywhere | **Yes — evidence level on every edge** |
| Learn how such a system is built, from zero | Rarely documented | **Yes — the repo is the tutorial** |

**The pattern:** for every question a mature tool answers well, use that tool. The
last four rows are where this project contributes.

---

## 8. What is genuinely uncommon here

Three things. Each is real; none is a scientific breakthrough.

### 1. The chain continues past the compound

Every system surveyed above stops at chemistry. MicrobeGraph continues to
*pathogen* and *crop* — which is only possible because of the curated bridge, and
which is exactly why nobody else's system does it.

**Why that matters practically:** it turns a literature-review-shaped task into a
query. Starting at a crop disease and walking backwards to candidate organisms, in
one step, is not something the existing tools can do.

### 2. Evidence level as a first-class, filterable property

Most knowledge graphs record *that* a relationship exists. Recording **how
strongly it is known**, on every single edge, and making "show me only what is
actually measured" a checkbox — that is rarer than it should be.

Concretely, this project:

- assigns one of four evidence levels to every edge, with no default
- **refuses to build** if a curated edge lacks a citation
- keeps algorithm-predicted edges in a separate layer, excluded from evidence
  chains by default
- reports the graph's own evidence composition as a quality metric

*Everyday example:* a recipe that distinguishes "I measured 200g" from "I reckon
about 200g". Obvious once stated; almost nobody does it.

### 3. Reproducible, open, and taught

The commercial platforms are closed. The academic tools are open but assume you
already are a bioinformatician.

A system that is simultaneously **open**, **reproducible from raw responses**, and
**documented so a complete beginner can rebuild every step** is unusual — and that
combination is a deliberate goal here rather than a by-product.

---

## 9. What this project does not claim

Stated plainly, because the boundary matters more than the achievement.

- ❌ **Not a new scientific method.** Knowledge graphs, entity resolution, link
  prediction and GraphRAG are all established. This project applies them.
- ❌ **Not a discovery.** No claim that any suggested microbe controls any disease.
  Predictions are hypotheses generated from structural resemblance, labelled
  `inferred`, and excluded from evidence chains by default.
- ❌ **Not a comprehensive biocontrol database.** The bridge layer is dozens of
  hand-curated rows. A real one needs a funded team and years.
- ❌ **Not a replacement for MIBiG, antiSMASH, BiG-SCAPE or SocialGene.** It
  consumes some of them and is smaller than all of them.
- ❌ **Not validated against field outcomes.** Nothing here has been tested in a
  greenhouse, let alone a field.
- ❌ **Not production-scale.** Release 1.0 runs on a laptop, by design.

### What it does claim — in one sentence

This is the claim to make when you have one line: in a README opener, a summary, a
conversation. Every clause is defensible, and each is doing work.

> **An open, reproducible knowledge graph that connects curated biosynthetic gene
> cluster data to crop disease outcomes, with evidence provenance on every
> relationship — including a transparently hand-curated bridge for the
> literature-derived links that no public database provides.**

Read it clause by clause and notice that nothing is decorative:

| Clause | Why it's there |
|---|---|
| *open, reproducible* | Distinguishes it from the closed commercial platforms |
| *curated biosynthetic gene cluster data* | Says the source is MIBiG — proven entries, not predictions. Claims no credit for the underlying data |
| *to crop disease outcomes* | The part no other system reaches. This is the whole contribution |
| *evidence provenance on every relationship* | The design decision that makes the graph auditable |
| *transparently hand-curated bridge* | Volunteers the weakest part before anyone has to ask |
| *no public database provides* | States the gap as fact, and it is checkable |

**Notice what the sentence does not say.** No "novel", no "breakthrough", no "first
of its kind", no "AI-powered". Those words invite exactly the question you cannot
answer, and their absence is what makes the rest believable.

*Everyday parallel:* a builder who says "I extended the kitchen, kept the original
brickwork, and here's where the new join is" is more trustworthy than one who says
"I transformed the property." The first one you can walk round and check.

**The longer version**, when there's room for a paragraph: a correct, honest,
end-to-end workflow — ingestion with provenance, an ontology-governed graph,
entity resolution with a written ledger, statistically validated analytics,
machine learning with honest evaluation, and a public application — extending the
chain to crop outcomes, with evidence provenance throughout, documented so that
anyone can reproduce and learn from it.

**That is a smaller claim than "novel", and it is entirely defensible.** A smaller
true claim is worth more than a larger one that doesn't survive a question.

---

## 10. What would make it more novel

If this were to become genuinely new work rather than a well-built integration,
these are the honest directions — recorded so the ambition is on the record even
where the work isn't done.

| Direction | What it would take | Why it would matter |
|---|---|---|
| **Systematic literature extraction** | Language models reading thousands of abstracts to propose compound → pathogen edges, with human review (Phase 17) | Turns the tiny bridge into a real resource. This is the single highest-value extension |
| **Quantitative activity, not binary** | Recording measured inhibition values rather than "inhibits yes/no" | Lets you rank by strength, not just presence |
| **Strain-level resolution** | Modelling strains rather than species | Two strains of one species genuinely differ; the current model cannot express that |
| **Experimental validation** | A lab testing a handful of top predictions | Would convert "plausible" into evidence. Requires a lab |
| **Formal ontology alignment** | Mapping onto established ontologies and publishing as linked data | Would let this graph merge with others rather than stand alone |
| **Negative results** | Recording where a compound was tested and *failed* | Absence of evidence and evidence of absence are different, and almost nobody records the second |

**That last row is worth dwelling on.** Failed tests are rarely published, so every
graph in this field silently over-represents success. Modelling negative results
explicitly would be a genuinely uncommon contribution — and it costs nothing but
discipline.

---

## 11. References

Everything cited above, so any claim can be checked.

**Databases and tools**

- **MIBiG** — Minimum Information about a Biosynthetic Gene Cluster.
  <https://mibig.secondarymetabolites.org/> · MIBiG 3.0: *Nucleic Acids Research*
  51(D1):D603 · MIBiG 4.0: <https://doi.org/10.5281/zenodo.14169073> (CC-BY)
- **antiSMASH** — biosynthetic gene cluster prediction.
  <https://antismash.secondarymetabolites.org/>
- **BiG-SCAPE / CORASON** — gene cluster similarity networks and phylogenies.
- **SocialGene** — bespoke large-scale knowledge graphs for comparative genomics
  and multi-omics natural product discovery.
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11370487/>
- **PubChem** — <https://pubchem.ncbi.nlm.nih.gov/> (public domain)
- **NCBI Taxonomy / Datasets** — <https://www.ncbi.nlm.nih.gov/> (public domain)
- **UniProt** — <https://www.uniprot.org/>
- **KEGG** — <https://www.genome.jp/kegg/> (academic use, attribution required)

**Knowledge-graph methodology**

- **Hetionet** and successor biomedical knowledge graphs — the established pattern
  of heterogeneous graphs plus path-based and embedding methods for candidate
  ranking, which this project applies to agriculture.

**Biocontrol context**

- *Bacterial and Fungal Biocontrol Agents for Plant Disease Protection*,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC10537577/>
- *Antifungal Biocontrol in Sustainable Crop Protection: Microbial Lipopeptides,
  Polyketides, and Plant-Derived Agents*, <https://doi.org/10.3390/jof12010022>

**Commercial platforms** (context only; none is a data source here)

- AgBiome · Lavie Bio · Indigo Ag · Biome Makers · IFF Crop Biologicals

> **On keeping this current.** This survey reflects the landscape at the time of
> writing. Fields move. If you find work that overlaps more closely than anything
> listed here, that is worth an issue and an update — a prior-art document that is
> never revised is a prior-art document nobody should trust.

---

## Checkpoint

You've understood this document when you can answer:

1. What is prior art, and why does publishing it make a project more credible?
2. What does SocialGene do, and in what two ways is it better than this project?
3. What is the difference between a similarity network and a knowledge graph?
4. Why is the compound → pathogen → crop link not available as downloadable data?
5. Name three things this project explicitly does not claim.
6. Why is the commercial platforms' moat their data rather than their software?

<details>
<summary>Answers (open after you've tried)</summary>

1. Everything already published or built in the same area. Naming it shows you
   surveyed the field; silence suggests you didn't look — and specialists will
   know.
2. It builds large-scale Neo4j knowledge graphs linking clusters, genomes,
   chemicals and mass-spectrometry data. It is far larger and stronger on the
   genomics half. It stops at chemistry rather than continuing to crop outcomes.
3. A similarity network connects nodes of one type by resemblance ("these two
   clusters are alike"). A knowledge graph connects nodes of many types by named
   relationships ("this organism *produces* this compound").
4. Because it lives in the prose of scientific papers, written for humans. No
   public database publishes it as a queryable table.
5. Any three of: not a new method; not a discovery; not comprehensive; not a
   replacement for existing tools; not field-validated; not production-scale.
6. Anyone competent can build a graph. Nobody else owns their strain collections,
   proprietary screening results, or field trial data.

</details>

---

## Committing this document

```bash
git switch develop
git add -A                    # stage first, so the gate can see the new files

./check-public-safe.sh        # must print "SAFE TO PUSH"

git commit -m "docs: add a prior-art survey and state what this project does not claim"
git push origin develop develop:beta develop:master

## --tags is optional, and only when cutting a new version
## then switch back to local master and pull in the changes from the remote

git switch master
git pull --ff-only origin master
git switch develop
```

---

**Related:** [`00-architecture.md`](00-architecture.md) (what this project builds) ·
[`ROADMAP.md`](ROADMAP.md) (where the extensions sit) ·
[`02-ontology-and-data-model.md`](02-ontology-and-data-model.md) (the evidence model)
