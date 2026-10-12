[← Handbook](HANDBOOK.md) · [README](../README.md) · [Glossary](GLOSSARY.md) · [Architecture](00-architecture.md) · [Phase 1](03-ingestion-mibig.md)

# 02. The ontology and data model: the rulebook

**Prerequisites:** [`00-architecture.md`](00-architecture.md) (you should know
what a node and an edge are) and [`01-setup.md`](01-setup.md) (a working
repository on the `develop` branch). No biology or database background needed.

**Learning goal:** you will understand what an *ontology* is, why writing one
before any pipeline code is the single most important decision in a graph
project, and you will be able to read the complete MicrobeGraph schema, every
node type, every edge type, every column, and the evidence system that makes the
graph trustworthy.

**Time:** 30-40 minutes reading, ~15 minutes writing the two files at the end.

> Every term here is also in [`GLOSSARY.md`](GLOSSARY.md).

---

## Contents

1. [Why a rulebook, and why now](#1-why-a-rulebook-and-why-now)
2. [What an ontology actually is](#2-what-an-ontology-actually-is)
3. [Identifiers: the CURIE convention](#3-identifiers-the-curie-convention)
4. [The node types](#4-the-node-types-the-nouns)
5. [The edge types](#5-the-edge-types-the-verbs)
6. [Evidence: the column that makes the graph honest](#6-evidence-the-column-that-makes-the-graph-honest)
7. [The physical schema: two CSV files](#7-the-physical-schema-two-csv-files)
8. [How it becomes SQL tables and a graph](#8-how-it-becomes-sql-tables-and-a-graph)
9. [Validation rules the loader enforces](#9-validation-rules-the-loader-enforces)
10. [A worked example: one chain, end to end](#10-a-worked-example-one-chain-end-to-end)
11. [Design decisions and their reasons](#11-design-decisions-and-their-reasons)
12. [Write the files](#12-write-the-files)
13. [Checkpoint](#13-checkpoint)

---

## 1. Why a rulebook, and why now

This document exists to prevent a very common way for graph projects to fail.

You start collecting facts. MIBiG gives you organisms and compounds, so you add
those. PubChem gives you molecular weights, so you add a "weight" thing. A paper
mentions a pathogen, so you add pathogens. Somewhere along the way, one script
writes organism names as `Bacillus velezensis` and another writes
`bacillus_velezensis`. One writes the relationship as `produces`, another as
`makes`. Compounds are sometimes nodes and sometimes just a text column on
another node.

Three weeks in, nothing joins to anything. Your counts can't be trusted, and you
can't walk a path because half the arrows have the wrong name. A bug fix won't
help at that point, because the problem lives in the *shape* of the data rather
than in the code, so you end up rebuilding.

Picture a shared address book where one person writes phone numbers as
`+41 79 123 45 67`, another as `0791234567`, and a third as `079-123-45-67`.
Each entry is fine on its own, yet the book as a whole is unsearchable, and more
careful typing won't change that. What fixes it is agreeing on the format first.

**So: decide the shape first, write it down, and make the loader refuse anything
that doesn't fit.** That written agreement is called the ontology, and this
document is it.

I'd call this the most professional habit in the whole project. Deciding your
data model before writing any pipeline code is what turns a pile of scripts into
a system.

---

## 2. What an ontology actually is

The word sounds forbidding, but the idea behind it is simple.

An **ontology** is a written agreement about what kinds of things exist in your
world, and what kinds of relationships are allowed between them.

Take a family tree. Before you can draw one, you need to agree what kinds of
things appear (people) and what relationships are allowed (*parent-of*,
*married-to*, *sibling-of*). You'd never draw an arrow labelled
"borrowed-a-lawnmower-from". It may well be true, but it isn't what a family
tree is *for*. An ontology is that kind of decision, written down.

A restaurant menu works the same way. It has categories (starters, mains,
desserts) and rules (a dessert has a price, a main has a description, a wine has
a vintage), and you can't order a "starter" that is secretly a wine. Those
categories and their rules are the menu's ontology.

A library catalogue is a third example. Its things are Book, Author, Publisher
and Subject. Its relationships: an Author *wrote* a Book; a Publisher
*published* a Book; a Book *is-about* a Subject. That small set of nouns and
verbs is what lets you ask "which subjects does this author cover?", a question
no single book contains the answer to.

So an ontology has two halves:

- **Node types** are the *nouns*: the kinds of things that can be a dot.
- **Edge types** are the *verbs*: the kinds of arrows that are allowed, and
  which nouns each one may connect.

One rule does most of the work: **if a fact doesn't fit the nouns and verbs, it
doesn't go in.** Either you extend the ontology on purpose, in a commit with a
reason attached, or you leave the fact out. What you shouldn't ever do is quietly
bend an existing type to hold something it wasn't meant for.

### Ontology vs schema vs data model

You'll hear all three words. In practice, for a project this size:

- **Ontology**: the conceptual agreement about which nouns, verbs and rules
  exist. It doesn't depend on any programming language.
- **Schema**: the concrete implementation, meaning the actual columns, types and
  constraints.
- **Data model**: used loosely for either or both.

This document covers all of it, which is why the filename says
"ontology-and-data-model".

---

## 3. Identifiers: the CURIE convention

Every node needs an **identifier**, a name that is unique across the whole
graph and never changes.

### Why names won't do

"Surfactin" is not a safe identifier, because it gets written `surfactin`,
`Surfactin`, `surfactin A` and `Surfactin C15`. Text drifts, while a number
issued by an authority stays the same.

Raw numbers have the opposite problem, though: `326423` is unique in NCBI Taxonomy
and meaningless everywhere else. Taxon `1390` and PubChem compound `1390` are
completely different things.

### The fix: prefix the number with where it came from

A **CURIE** (*Compact URI*, pronounced "curie") is just `prefix:localid`:

```
ncbitaxon:326423             ← the organism Bacillus velezensis FZB42, in NCBI's numbering
mibig:BGC0000433             ← a gene cluster, in MIBiG's numbering
mg.compound:surfactin        ← a compound with no external id yet (see below)
```

International phone numbers solve the same problem. `079 123 45 67` is
ambiguous worldwide; `+41 79 123 45 67` is not, because the country code says
whose numbering system it belongs to. The CURIE prefix plays the part of the
country code.

I didn't invent this. CURIEs are a widely used standard, and the same convention
runs through biological and linked-data systems.

### The prefixes MicrobeGraph uses

| Prefix | Authority | Example | Used for |
|---|---|---|---|
| `ncbitaxon` | NCBI Taxonomy | `ncbitaxon:326423` | Organisms and pathogens |
| `mibig` | MIBiG | `mibig:BGC0000433` | Gene clusters |
| `pubchem.compound` | PubChem | `pubchem.compound:<CID>` | Compounds, once resolved |
| `kegg.pathway` | KEGG | `kegg.pathway:map00660` | Pathways |
| `ncbiprotein` | NCBI Protein (INSDC and RefSeq protein ids) | `ncbiprotein:CAE02630.1` | Proteins MIBiG numbers, in its gene records (from Phase 3) and its protein file (from Phase 3b) |
| `uniprot` | UniProt | `uniprot:Q70KJ7` | Proteins (enzymes), as UniProt describes them |
| `mg.class` | *this project* | `mg.class:lipopeptide` | Compound classes |
| `mg.activity` | *this project* | `mg.activity:antifungal` | Biological activities |
| `mg.crop` | *this project* | `mg.crop:jujube` | Crops |
| `mg.compound` | *this project* | `mg.compound:surfactin` | Compounds not (yet) matched to PubChem |
| `mg.organism` | *this project* | `mg.organism:<name>` | Strains with no NCBI number |
| `mg.protein` | *this project* | `mg.protein:bgc0000001-abyu` | Proteins MIBiG gives no INSDC or RefSeq number, named by a locus tag or gene name and scoped to their entry |

> **A measured fact that shapes the whole pipeline.** MIBiG does not supply
> PubChem identifiers for most of its compounds. Counting across the current
> release, only 1,410 of 4,594 compound entries carry one, which is 31%. The
> rest give a name and sometimes an identifier from another chemistry database.
>
> So a compound arriving from MIBiG cannot be given a `pubchem.compound` identifier
> at ingestion time. It enters as `mg.compound:<name>` and gets resolved against
> PubChem by name in a later phase, if a match can be confirmed.
>
> This is why entity resolution is a phase of its own rather than a footnote.
> The identifiers really are missing, and making them up is not an option.
>
> Phase 2 measured the same thing on the tidied tables: of the 3,842 compound
> nodes Phase 1 builds from MIBiG 4.0, 1,176 carry a PubChem number. Phase 2
> asks PubChem about exactly those 1,176 and writes them as
> `pubchem.compound:<CID>` nodes, each remembering which `mg.compound` it came
> from (`mibig_compound_ids`). Phase 4 joins the two where MIBiG's name or
> formula confirms the number, because some of the numbers turned out to belong
> to other molecules ([`06-entity-resolution-graph-build.md`, Step 5](06-entity-resolution-graph-build.md#9-step-5-compounds)).

The prefixes also make the graph open about its own sources. `mg.` marks the
things *this project* invented because no public authority numbers them, so
anyone reading the graph can tell at a glance which identifiers come from an
external authority and which are ours. That tells a reader how much external
weight each identifier carries.

**Rule:** prefer an authority prefix wherever one exists. Only mint an `mg.`
identifier when nothing external covers the concept, and keep those to a short,
controlled list defined in this document.

---

## 4. The node types (the nouns)

![The nine node types, each with an identifier example and an everyday comparison](img/node_types.svg)

There are nine node types. For each one you'll find a short definition, an
everyday comparison, its identifier scheme and its properties. The comparisons
all come from one picture, a factory, so they fit together as you read.

### 1. `Organism`

A microbe (a bacterium, fungus or yeast) that produces something interesting.
In the factory picture, this is *the factory* itself.

**Identifier:** `ncbitaxon:<taxid>`, or `mg.organism:<slug>` when a MIBiG record
names a strain that has no NCBI entry.

| Property | Type | Meaning |
|---|---|---|
| `name` | text | Scientific name, e.g. `Bacillus velezensis FZB42` |
| `rank` | text | NCBI's rank: `strain`, `species`, `genus`, `family`... |
| `lineage` | text | The full ladder as NCBI writes it, e.g. `cellular organisms; Bacteria; Bacillati; Bacillota; Bacilli; ...` |
| `group` | text | A broad group for colouring and filtering: `Bacteria`, `Archaea`, `Fungi`, `Oomycetes`, `Plants`, `Animals`, `Viruses` or `Other` |
| `division` | text | NCBI's own coarse label, e.g. `Bacteria`, `Plants and Fungi` |
| `synonyms` | text | Other names NCBI lists, pipe-separated |
| `merged_from` | text | Old taxids NCBI has merged into this one, if any |

The family tree itself is not a property: it's `MEMBER_OF` arrows from each
organism up through its species, genus, family and so on (section 5). Those
and every property except `name` arrive from NCBI Taxonomy in Phase 2.

**Why `group` and not `kingdom`?** In 2025 NCBI gave bacteria a real `kingdom`
rank (*Bacillus* sits in the kingdom *Bacillati*), so "kingdom" now means
something specific and would be confusing as a loose label. `group` is ours,
worked out from the names in the lineage, and only used to colour and filter.

### 2. `GeneCluster`

A run of neighbouring genes that together build one specialised molecule: *the
production line inside the factory*.

**Identifier:** `mibig:<accession>`

| Property | Type | Meaning |
|---|---|---|
| `name` | text | A readable label built from the compounds, e.g. `surfactin BGC` |
| `bgc_class` | text | The machinery type, as MIBiG writes it: `NRPS`, `PKS`, `ribosomal`, `saccharide`, `terpene`, `other`; hybrids joined with `\|`, e.g. `NRPS\|PKS` |
| `completeness` | text | `complete`, `partial` or `unknown`: how fully the cluster is characterised |
| `quality` | text | MIBiG's own grade for the entry: `high`, `medium`, `low` or `questionable` |
| `entry_version` | number | Which revision of the MIBiG entry was read |
| `loci` | text | The DNA record(s) the cluster sits in, e.g. `AJ575642.1` |

### 3. `Protein`

An enzyme encoded by the gene cluster. It's the actual molecular machine that
performs one chemical step, like *a machine standing on the production line*.

**Identifier:** three kinds, depending on where the protein was met (Phases 3
and 3b):

* `ncbiprotein:<protein id>` when MIBiG gives an INSDC or RefSeq protein number,
  in a gene record or in its protein file, e.g. `ncbiprotein:CAE02630.1`. These
  numbers are worldwide, so the same number in two entries is one node.
* `mg.protein:<entry>-<locus tag or gene name>` when MIBiG gives only a name that
  is unique inside its own genome, e.g. `mg.protein:bgc0000001-abyu`. The entry
  number keeps two genomes' names apart. (In Phase 3 the protein of locus tag
  `TSTA_117750` was `mg.protein:bgc0000154-tsta-117750`; from Phase 3b the
  protein file gives its number, so it's `ncbiprotein:EED18001.1`.)
* `uniprot:<accession>` for UniProt's description of a protein, e.g.
  `uniprot:Q70KJ7`. Phase 4 joins it to the `ncbiprotein:` node it was found
  through, so the finished graph has one node per protein, named by its UniProt
  entry where there is one, with the protein number kept as an alias
  ([`06-entity-resolution-graph-build.md`, Step 6](06-entity-resolution-graph-build.md#10-step-6-proteins)).

This node type matters because it turns MicrobeGraph from two molecular layers
into three. With `Protein` in place, the chain reads
genomics → proteomics → metabolomics → phenotype: three different kinds of
biological measurement, joined into one structure that a single query can walk.
That's what "multi-omics integration" means in practice, as opposed to three
tables sitting next to each other.

Properties from MIBiG (on `ncbiprotein:` and `mg.protein:` nodes), from its gene
records (Phase 3) and its protein file (Phase 3b):

| Property | Type | Meaning |
|---|---|---|
| `name` | text | The gene name, e.g. `srfAA` (or the product, or the id, when there's no gene name) |
| `protein_id`, `id_type` | text | The number that names the node, and its kind: `insdc`, `refseq` or `other` |
| `gene_name`, `product` | text | The gene's name and MIBiG's short product description, e.g. `surfactin synthetase A` (a gene record's product wins over the file's) |
| `functions` | text | The gene's jobs, joined with `\|`, e.g. `Scaffold biosynthesis` (gene records only) |
| `function_evidence` | text | How the jobs were shown, e.g. `Knock-out` (gene records only) |
| `comment`, `mutation_phenotype` | text | A curator's note, and what happened when the gene was switched off, when MIBiG gives them |
| `gene_record_id` | text | The id the gene record used, when it isn't the protein number (a locus tag or gene name) |
| `locus_tags` | text | The genome's label(s) for the gene, from the protein file, joined with `\|` |
| `locations` | text | Where the gene sits, one per place the protein file lists it, e.g. `BGC0000433:8558-19312:+` |
| `sequence_length`, `sequence_md5` | number, text | The sequence's length in amino acids and its MD5 fingerprint; the letters stay in the protein file |
| `found_in` | text | Where the node came from: `gene_records`, `protein_file`, or both |

Properties from UniProt (on `uniprot:` nodes):

| Property | Type | Meaning |
|---|---|---|
| `name` | text | UniProt's main name, e.g. `Surfactin synthetase A` |
| `entry_name`, `reviewed` | text, true/false | e.g. `Q70KJ7_BACAM`; whether a curator wrote the entry (Swiss-Prot) |
| `ec_numbers` | text | Enzyme Commission number(s), the standard code for the reaction it performs |
| `length` | number | Number of amino acids |
| `function` | text | UniProt's description of what it does |
| `organism`, `organism_taxid` | text, number | The organism as UniProt names it |
| `protein_existence`, `annotation_score` | text, number | How directly the protein is known to exist; how well the entry is described (1 to 5) |
| `mibig_protein_ids` | text | The `ncbiprotein:` node(s) it was found through, for the join in Phase 4 |

### 4. `Compound`

The molecule produced, or *the product coming off the line*.

**Identifier:** `pubchem.compound:<CID>`, or `mg.compound:<slug>` if PubChem has
no entry (so the gap stays visible instead of being hidden).

| Property | Type | Meaning |
|---|---|---|
| `name` | text | Preferred name, e.g. `surfactin` |
| `synonyms` | text | Pipe-separated alternatives, the raw material for resolution |
| `formula` | text | e.g. `C52H91N7O13` |
| `mass` | number | The mass MIBiG records. For surfactin it is 1021.667, which is the *monoisotopic* mass of C52H91N7O13 (each element counted by its most common isotope), not the average molecular weight (about 1022.3) |
| `database_ids` | text | Identifiers in other chemistry databases, pipe-separated, e.g. `npatlas:NPA018495` |
| `pubchem_cid` | text | The PubChem number when MIBiG gives one (only about a third of compounds have one) |
| `smiles` | text | The structure written as a line of text, when MIBiG gives one |
| `activity_notes` | text | Curators' comments on what this compound does, pipe-separated, each starting with the activity it describes (for example `antifungal: ...`). They stay on the compound because they describe this molecule, not the activity in general |

Compounds that come from PubChem (Phase 2) are `pubchem.compound:<CID>` nodes
with PubChem's own description:

| Property | Type | Meaning |
|---|---|---|
| `name` | text | PubChem's title, e.g. `Itaconic acid` |
| `pubchem_cid` | number | The CID itself |
| `formula` | text | e.g. `C5H6O4` |
| `molecular_weight` | number | The average mass, e.g. `130.1` |
| `monoisotopic_mass` | number | The mass counting each element's most common isotope |
| `iupac_name` | text | The systematic chemical name |
| `inchikey` | text | A fixed-length fingerprint of the structure, the same in every database |
| `smiles`, `connectivity_smiles` | text | The structure as text, with and without its 3D detail |
| `synonyms` | text | The first 20 other names PubChem lists, pipe-separated |
| `kegg_compound_ids`, `kegg_drug_ids`, `chebi_ids` | text | Numbers in KEGG and ChEBI, found among those names |
| `mibig_compound_ids` | text | The MIBiG compound(s) that recorded this CID, for Phase 4 |

### 5. `CompoundClass`

A family of chemically related compounds (*the product category*).

**Identifier:** `mg.class:<slug>`, e.g. `mg.class:lipopeptide`

In a supermarket, "surfactin" would be one product and "lipopeptide" the aisle
it sits in. Aisles let you ask "what else is like this?" without knowing every
product name.

| Property | Type | Meaning |
|---|---|---|
| `name` | text | e.g. `lipopeptide`, `polyketide`, `siderophore` |
| `description` | text | One plain-language line |

### 6. `Activity`

What a compound *does* biologically; in factory terms, *what the product is
for*.

**Identifier:** `mg.activity:<slug>`, e.g. `mg.activity:antifungal`

| Property | Type | Meaning |
|---|---|---|
| `name` | text | `antifungal`, `antibacterial`, `siderophore`, `surfactant` |
| `description` | text | One plain-language line |

### 7. `Pathogen`

An organism that causes plant disease. In the factory picture, this is *the
problem*.

**Identifier:** `ncbitaxon:<taxid>`

**Why separate from `Organism`?** Both are living things, and a purist would
model "pathogen" as a *role* rather than a *type*. I keep them as separate node
types for a practical reason: it makes every question in this project simpler to
ask and every diagram easier to read. The whole graph is oriented around
"helpful organism → molecule → harmful organism → crop", and collapsing the two
ends into one type would mean every query needs a role filter.

**A Pathogen is a kind of Organism (from Phase 4).** Some organisms are both:
*Fusarium graminearum* makes molecules MIBiG records *and* causes head blight on
wheat. Two separate types would need two dots with one identifier, which rule 1
below (unique `node_id`) forbids. So the rulebook says, in
[`ontology.py`](../src/microbegraph/ontology.py) (`SUBTYPE_OF`), that a Pathogen
is a **subtype** of Organism: anything an Organism may do in the graph, a
Pathogen may do too. An organism that is both becomes one Pathogen node that
harbours its clusters and sits in the family tree, and the resolution ledger
records why. The reverse doesn't hold: `INFECTS` still starts only at a Pathogen.

A sports car is a kind of car. It may park wherever a car may, but not every car
is allowed on the race track.

Queries that mean "every organism" include pathogens (the database's
`organisms` view does), and queries about pathogens filter on `Pathogen`. Phase 0
first wrote this down as a known cost of keeping two types; Phase 4 settled it,
and I've kept both halves of the story here so a future reader can see how the
decision was made.

| Property | Type | Meaning |
|---|---|---|
| `name` | text | NCBI's current scientific name, e.g. `Botrytis cinerea` |
| `pathogen_type` | text | `fungus`, `oomycete`, `bacterium`, `virus`, `nematode` or `other` |
| `diseases` | text | Each disease with its crop, pipe-separated, e.g. `grey mould (jujube)` |
| `rank`, `lineage`, `group`, `division`, `synonyms` | text | As for `Organism`, from NCBI Taxonomy |

The first three come from the curated bridge, the rest from NCBI Taxonomy, and
both arrive in Phase 2.

### 8. `Crop`

A cultivated plant that gets infected, which makes it *the one who suffers*.

**Identifier:** `mg.crop:<slug>`, e.g. `mg.crop:jujube`

| Property | Type | Meaning |
|---|---|---|
| `name` | text | Common name, e.g. `jujube` |
| `scientific_name` | text | e.g. `Ziziphus jujuba` |
| `category` | text | `cereal`, `fruit`, `vegetable`, `legume`, `fibre`, `oilseed` or `other` |

### 9. `Pathway`

A chain of biochemical reactions that a cell performs. Think of it as *the wider
production process the product belongs to*.

**Identifier:** `kegg.pathway:<id>`, e.g. `kegg.pathway:map00660`

| Property | Type | Meaning |
|---|---|---|
| `name` | text | Pathway name, e.g. `C5-Branched dibasic acid metabolism` |
| `category` | text | KEGG's top-level grouping, e.g. `Metabolism` |
| `subcategory` | text | The grouping below it, e.g. `Carbohydrate metabolism` |

---

## 5. The edge types (the verbs)

![The rulebook as a picture: 9 node types, 10 edge types](img/ontology_map.svg)

To explore it interactively, open
[`interactive/ontology_explorer.html`](interactive/ontology_explorer.html) in a
browser: hover any dot or arrow to see what it means and which phase brings it in.

There are ten edge types, and **every edge has a direction**:
`A --produces--> B` is a different statement from `B --produces--> A`, just as
"Anna is Ben's mother" differs from the reverse.

| Edge type | From → To | Reads as | Where it comes from |
|---|---|---|---|
| `HARBORS` | Organism → GeneCluster | *this microbe carries this production line* | MIBiG |
| `ENCODES` | GeneCluster → Protein | *this production line specifies this enzyme* | MIBiG's gene records (Phase 3) and protein file (Phase 3b) |
| `CATALYZES` | Protein → Compound | *this enzyme performs a step making this molecule* | MIBiG's gene records, for genes whose job builds the molecule (Phase 3) |
| `PRODUCES` | GeneCluster → Compound | *this production line makes this molecule* (the direct shortcut) | MIBiG |
| `BELONGS_TO` | Compound → CompoundClass | *this molecule is one of these* | MIBiG / curated |
| `HAS_ACTIVITY` | Compound → Activity | *this molecule does this* | MIBiG / curated |
| `INHIBITS` | Compound → Pathogen | *this molecule suppresses this pathogen* | **curated bridge** |
| `INFECTS` | Pathogen → Crop | *this pathogen attacks this crop* | **curated bridge** |
| `PARTICIPATES_IN` | Compound → Pathway | *this molecule takes part in this process* | KEGG |
| `MEMBER_OF` | Organism → Organism | *this species belongs to this genus* | NCBI Taxonomy |

Where a row says Organism, a Pathogen fits too, because a Pathogen is a kind of
Organism (from Phase 4; see `Pathogen` in section 4). So a pathogen may harbour a
gene cluster and has `MEMBER_OF` arrows up its family tree.

### The chain this is all built for

```
Organism --HARBORS--> GeneCluster --PRODUCES--> Compound --INHIBITS--> Pathogen --INFECTS--> Crop
                           |                       ^
                       ENCODES                 CATALYZES
                           v                       |
                        Protein --------------------
```

The top row is the fast path: MIBiG states directly that a cluster produces a
compound, so traversal is short. The lower branch is the mechanistic path
through the enzymes, added in Phase 3 from MIBiG's gene records and completed in
Phase 3b from MIBiG's protein file, with UniProt describing each enzyme.

I kept both because they answer different questions. The shortcut answers
"which microbe makes this?", and the protein path answers "*how*?". A redundant
shortcut comes with a cost (the two routes must stay consistent), so the
decision is written down here instead of being left for a future reader to
puzzle over.

Now take only the top row.

Read forwards, it says: *this microbe carries a production line that makes a
molecule that suppresses a pathogen that attacks this crop.*

Read **backwards**, which is the direction that makes the project useful, it
says: *start at a crop, find its diseases, find molecules that act on them, find
the production lines that make those molecules, find the microbes that carry
them.*

That walk covers four arrows from more than one source, and it is still a
single query.

### Why `MEMBER_OF` points organism → organism

This is the only edge whose two ends are the same type, and it's what makes
taxonomy work. *Bacillus velezensis* `MEMBER_OF` *Bacillus* (the genus). Chain
those and you get the full lineage as a walkable ladder, so "show me everything
from the genus *Bacillus*" becomes "walk down from the genus node". That needs no
special code and no lineage parsing, only the same arrow-following as everything
else.

Folders on a computer work the same way: a folder can contain a folder, and that
one rule gives you unlimited depth without any new concept.

---

## 6. Evidence: the column that makes the graph honest

**Every edge records where it came from and how strong that evidence is.** If I
had to defend only one part of the design, it would be this one.

### Why it's non-negotiable

A fact a curator verified from a published experiment, and a fact an algorithm
guessed from resemblance, look identical once they're arrows on a screen: both
are a line between two dots. If the graph doesn't distinguish them, it
*averages* them, and an average of "measured" and "guessed" is really "unknown"
dressed up with confidence.

A recipe has the same problem when it doesn't separate "I measured 200g" from "I
reckon about 200g". That's fine on the day you write it, but nobody else can
rely on it, and a year later you can't either.

### The four evidence levels

![The four evidence levels, strongest first](img/evidence_ladder.svg)

| Level | Meaning | Example | How to treat it |
|---|---|---|---|
| `curated_experimental` | A curator recorded a published experiment | A MIBiG entry whose cluster was tied to its compound by an experiment, such as a knock-out | Strongest available |
| `database_assertion` | A public database states it | PubChem's molecular formula; NCBI's lineage | Reliable reference data |
| `curated_literature` | **This project's own reading of a paper**, cited | An `INHIBITS` edge from the bridge layer | Trustworthy but ours, check the citation |
| `inferred` | Produced by an algorithm in this repo | A predicted link from Phase 7 | **A hypothesis. Never a finding.** |

### What the levels buy you

The level is stored in a column of its own (a footnote wouldn't do), and that
pays off in several ways:

- You can filter on it. "Show me only what is actually known" becomes a
  checkbox instead of a rewrite.
- Evidence chains can be audited. A path is only as strong as its weakest arrow,
  and the app can say which arrow that is.
- Predictions can never leak in. Inferred edges are excluded from evidence
  chains by default and drawn differently.
- You can measure your own graph. "62% of edges are `database_assertion`, 4%
  are `inferred`" is a real quality metric you can report and track over time.

### The other provenance columns

| Column | Why it exists |
|---|---|
| `source` | Which database or file this came from, `mibig`, `pubchem`, `curation` |
| `source_record_id` | The exact record, so anyone can go and look |
| `retrieved_at` | When. Databases change; "as of" is part of the fact |
| `confidence` | 0-1. Set by the source adapter; used for ranking, never for hiding |
| `citation` | For `curated_literature` edges: the DOI or reference. **Required** |

One rule here is strict: an edge with `evidence_level = curated_literature` and
an empty `citation` is **rejected by the loader**. It doesn't get a warning; the
loader refuses it. An uncited hand-added fact is exactly the thing that erodes
trust in a graph, so the schema makes it impossible instead of merely
discouraged.

---

## 7. The physical schema: two CSV files

The whole graph lives in two files. I chose that on purpose, because a graph you
can open in a text editor is a graph you can debug.

### `data/processed/nodes.csv`

One row per dot.

| Column | Type | Required | Meaning |
|---|---|---|---|
| `node_id` | text | ✅ | CURIE, unique across the entire file |
| `node_type` | text | ✅ | One of the nine types |
| `name` | text | ✅ | Human-readable label |
| `properties` | JSON text | | Type-specific extras, as `{"key": "value"}` |
| `source` | text | ✅ | Where this node came from |
| `retrieved_at` | date | ✅ | When |

Example rows:

```csv
node_id,node_type,name,properties,source,retrieved_at
ncbitaxon:326423,Organism,Bacillus velezensis FZB42,{},mibig,2026-10-10
mibig:BGC0000433,GeneCluster,surfactin BGC,"{""bgc_class"": ""NRPS"", ""completeness"": ""complete"", ""entry_version"": 5, ""loci"": ""AJ575642.1"", ""quality"": ""questionable""}",mibig,2026-10-10
mg.compound:surfactin,Compound,surfactin,"{""database_ids"": ""chemspider:391754|npatlas:NPA018495"", ""formula"": ""C52H91N7O13"", ""mass"": 1021.6674859720001, ""smiles"": ""[H][C@@]1(CCC(O)=O)NC(=O)CC(CCCCCCCCCCC)OC(=O)[C@]([H])(CC(C)C)NC(=O)[C@@]([H])(CC(C)C)NC(=O)[C@]([H])(CC(O)=O)NC(=O)[C@@]([H])(NC(=O)[C@@]([H])(CC(C)C)NC(=O)[C@]([H])(CC(C)C)NC1=O)C(C)C""}",mibig,2026-10-10
ncbitaxon:40559,Pathogen,Botrytis cinerea,"{""diseases"": ""grey mould (jujube)"", ""pathogen_type"": ""fungus""}",curation,2026-10-12
mg.crop:jujube,Crop,jujube,"{""category"": ""fruit"", ""scientific_name"": ""Ziziphus jujuba""}",curation,2026-10-12
```

The first three rows are copied from the first real Phase 1 run, on 2026-10-10
([`03-ingestion-mibig.md`](03-ingestion-mibig.md)); your own run will show the
date of your download instead. The long `smiles` value is surfactin's structure
written as one line of text. The organism's
properties are empty in MIBiG's table: its rank and family tree come from NCBI
Taxonomy's table in Phase 2, and Phase 4 merges the two into one node. The last two rows are
what the curated bridge writes in Phase 2, dated by the day each row was added.
The doubled quotes (`""`) are how a CSV file writes a quote mark inside a quoted
cell.

**Why a JSON blob for `properties` instead of a column per property?** Because
the nine node types need different properties, and one wide table with a column
for every property of every type would be mostly empty. A JSON column keeps the
file narrow and readable, and DuckDB can query inside JSON when you need it.
The downside is that querying inside JSON is slightly more awkward than querying
a plain column, so the database built in Phase 4 has a **view** for each node
type with properties worth showing (`organisms`, `compounds`, `proteins`...) with
the handful of properties we filter
on most as plain columns. Start simple, and promote a property once there's a
reason to.

**When a source disagrees with itself** (Phase 4b). Two MIBiG entries can give
one compound two different values: two formulas, two PubChem numbers. The
property keeps the first value under its usual name, so everything that reads
it keeps working, and a second property, named after the first with
`_by_entry` added, lists every value with the record that gave it:

```
pubchem_cid             9237955
pubchem_cid_by_entry    BGC0000657: 9237955|BGC0000658: 16913|BGC0000659: 16913
```

Nothing is thrown away, and anyone can see the disagreement and who said what.
The resolver reads these lists too: a formula the entries disagree about can't
confirm a join on its own ([`06b-closing-the-gaps.md`, Step 4](06b-closing-the-gaps.md#8-step-4-when-mibigs-entries-disagree-keep-every-value)).

### `data/processed/edges.csv`

One row per arrow.

| Column | Type | Required | Meaning |
|---|---|---|---|
| `source_id` | text | ✅ | CURIE of the node the arrow leaves |
| `target_id` | text | ✅ | CURIE of the node the arrow enters |
| `edge_type` | text | ✅ | One of the ten verbs |
| `evidence_level` | text | ✅ | One of the four levels |
| `source` | text | ✅ | Which database or file |
| `source_record_id` | text | | The exact record |
| `citation` | text | conditional | **Required** when `evidence_level = curated_literature` |
| `confidence` | number | | 0-1 |
| `retrieved_at` | date | ✅ | When |

Example rows:

```csv
source_id,target_id,edge_type,evidence_level,source,source_record_id,citation,confidence,retrieved_at
ncbitaxon:326423,mibig:BGC0000433,HARBORS,curated_experimental,mibig,BGC0000433,pubmed:14762003,0.50,2026-10-10
mibig:BGC0000433,mg.compound:surfactin,PRODUCES,curated_experimental,mibig,BGC0000433,pubmed:14762003,0.50,2026-10-10
mg.compound:surfactin,mg.activity:antibacterial,HAS_ACTIVITY,database_assertion,mibig,BGC0000433,,0.50,2026-10-10
mg.compound:surfactin,mg.activity:surfactant,HAS_ACTIVITY,database_assertion,mibig,BGC0000433,,0.50,2026-10-10
mg.compound:surfactin,ncbitaxon:40559,INHIBITS,curated_literature,curation,compound_pathogen_crop.csv,doi:10.1186/s13568-023-01543-w,0.90,2026-10-12
ncbitaxon:40559,mg.crop:jujube,INFECTS,curated_literature,curation,compound_pathogen_crop.csv,doi:10.1186/s13568-023-01543-w,0.90,2026-10-12
```

The first four rows are what Phase 1 writes from the surfactin entry on its own,
and two details in them are worth pointing out. The `HAS_ACTIVITY` rows have an
**empty citation** (the two commas side by side): MIBiG gives no reference for
those activities, so they enter as `database_assertion` rather than as
experiments. And every confidence is 0.50, because MIBiG itself grades this
entry "questionable" and the adapter carries that grade through instead of
inventing its own (the full rules are in
[`03-ingestion-mibig.md`, section 15](03-ingestion-mibig.md#15-how-evidence-and-confidence-are-decided)).

The last two rows are the curated bridge. Their citation is **required**, so you
can see it at a glance and filter on it in one clause.

These rows also hold the clearest illustration of why the evidence model exists.
MIBiG records surfactin as antibacterial and a surfactant, and says nothing
about antifungal activity. The claim that surfactin suppresses *Botrytis
cinerea*, a fungus, comes from published experiments rather than from the
database, so it enters as an `INHIBITS` edge at `curated_literature` with a
citation attached.

That gives the graph two facts about the same molecule, from two kinds of
source, carrying two different weights. If both were recorded as plain arrows,
the difference between them would be lost.

The citation is Xiao et al. (2023), who tested purified surfactin against
*Botrytis cinerea* on harvested winter jujube. Every row in
`curation/compound_pathogen_crop.csv` carries a real citation like this one, and
the loader rejects any row that doesn't.

---

## 8. How it becomes SQL tables and a graph

The same two files feed both stores, and neither store is written by hand.

```mermaid
flowchart LR
    N["nodes.csv"] --> DB[("DuckDB<br/>nodes table<br/>edges table")]
    E["edges.csv"] --> DB
    DB -->|"rebuilt, never edited directly"| G(["NetworkX<br/>DiGraph"])
    DB -->|SQL| Q1["counting · filtering · grouping"]
    G -->|graph algorithms| Q2["paths · centrality · communities"]

    classDef store fill:#FDE2E4,stroke:#D1495B,color:#4A0D14;
    classDef file fill:#EAECEF,stroke:#8A94A6,color:#1F2933;
    classDef use fill:#E8F0FE,stroke:#5B8DEF,color:#0B2545;
    class DB,G store
    class N,E file
    class Q1,Q2 use
```

**In DuckDB** the two CSVs become two tables, and SQL can then answer
table-shaped questions:

```sql
-- How many edges of each type, and how solid is the evidence?
SELECT edge_type, evidence_level, COUNT(*) AS n
FROM edges
GROUP BY edge_type, evidence_level
ORDER BY n DESC;
```

**In NetworkX** the same rows become a `DiGraph`, a *directed* graph, meaning
every arrow remembers which way it points. Node properties and edge properties
ride along, so a path result already carries its own evidence.

**One rule keeps the two in agreement:** DuckDB is the single source of truth,
and the NetworkX graph is *always* rebuilt from it, never edited in place. Facts
live in one place, and you get two shapes to ask questions in. If you could edit
the graph directly, the two would drift apart and you'd end up with two versions
of reality, which is the classic way projects like this rot.

**From Phase 4 this is real.** `python -m microbegraph.resolve` writes the merged
`nodes.csv` and `edges.csv`, and `python -m microbegraph.build_graph` loads them
into `data/processed/microbegraph.duckdb` (tables `nodes`, `edges`, `ledger`,
`sources` and `build_info`, views for the node types, and an `aliases` view),
rebuilds the NetworkX `DiGraph` and checks that both hold the same counts, type
by type, before the new database replaces the old one. [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md) has tested recipes for both
shapes.

---

## 9. Validation rules the loader enforces

An ontology that nothing enforces is only a suggestion. Phase 1 turns all twelve
rules into code, in [`src/microbegraph/validate.py`](../src/microbegraph/validate.py):
every source adapter checks its own rows before writing them, and from Phase 4
the resolver and the graph build run the same checks on every source merged and
**refuse to write anything** if any fail. The database repeats rules 1, 3, 6, 7
and 9 as database rules of its own (a primary key, foreign keys and CHECK lists
built from `ontology.py`), so a hand-edited row is refused there too.

**Node rules**

1. `node_id` is unique across the file. *(Duplicates mean resolution failed.)*
2. `node_id` matches `prefix:localid`.
3. `node_type` is one of the nine.
4. `name` is non-empty.
5. `source` and `retrieved_at` are present.

**Edge rules**

6. Both `source_id` and `target_id` exist in `nodes.csv`. *(An arrow to nowhere
   is the most common graph bug, and a silent one: the node just looks
   unconnected.)*
7. `edge_type` is one of the ten.
8. The types at each end are **allowed** for that edge type, or a kind of them.
   `PRODUCES` must go GeneCluster → Compound; a Compound → Compound `PRODUCES`
   edge is rejected. A Pathogen, a kind of Organism, may start `HARBORS` and
   `MEMBER_OF` (from Phase 4).
9. `evidence_level` is one of the four.
10. `citation` is non-empty whenever `evidence_level = curated_literature`.
11. `confidence`, if present, is between 0 and 1.
12. No duplicate edges: the same `(source_id, target_id, edge_type, source)`
    appearing twice is a bug rather than two facts.

> **Looking ahead (Release 2.0):** these twelve rules outlive Phase 1. In
> Phase 10 they move almost unchanged into dbt tests: rule 1 becomes `unique`,
> rule 6 becomes `relationships`, rules 3/7/9 become `accepted_values`, and
> rules 4/5 become `not_null`. The rulebook you are reading turns into a
> `schema.yml` file. The fit is close because dbt was built for exactly this
> kind of contract, and that's why it has a place in the roadmap
> ([`ROADMAP.md`](ROADMAP.md)).

**Why refuse rather than warn?** Because warnings get ignored. A build that
stops forces you to fix the data now, while you still remember what you were
doing, instead of discovering four phases later that 3% of your arrows point at
nothing and every centrality score is wrong.

Compare a spell-checker that highlights errors with a web form that won't submit
until the email address is valid. The form annoys you exactly once, while the
spell-checker's highlights annoy you forever.

---

## 10. A worked example: one chain, end to end

Follow one grower's question through the whole model.

**The question:** *Which microbes might help against grey mould on jujube fruit?*

(Jujube, *Ziziphus jujuba*, is a fruit tree grown widely in China. After
harvest the fruit rots easily, and grey mould is one of the causes.)

**Step 1, find the crop node.**
`mg.crop:jujube`

**Step 2, walk `INFECTS` backwards.** Which pathogens attack it?
→ `ncbitaxon:40559` (*Botrytis cinerea*, grey mould)
*Evidence: `curated_literature`, cited (`doi:10.1186/s13568-023-01543-w`).*

**Step 3, walk `INHIBITS` backwards.** Which compounds suppress it?
→ `mg.compound:surfactin`
*Evidence: `curated_literature`, cited (the same paper).*

**Step 4, walk `PRODUCES` backwards.** Which production lines make it?
→ `mibig:BGC0000433`
*Evidence: `curated_experimental`.*

**Step 4b, the protein route** (from Phase 3). Which enzymes make it? Walk
`CATALYZES` backwards from surfactin, then `ENCODES` backwards to the cluster:
→ `uniprot:Q70KJ7` (srfAA), `uniprot:Q70KJ6` (srfAB) and `uniprot:Q70KJ4`
(srfAC), the three parts of the surfactin synthetase, all encoded by
`mibig:BGC0000433`.
*Evidence: `curated_experimental` for srfAA, whose job a knock-out showed;
`database_assertion` for the other two.* Each node holds MIBiG's facts and
UniProt's together, since Phase 4 joined MIBiG's protein numbers
(`CAE02630.1` for srfAA) to their UniProt entries: `Q70KJ7` is "Surfactin
synthetase A", 3,584 amino acids long.

**Step 5, walk `HARBORS` backwards.** Which microbes carry it?
→ `ncbitaxon:326423` (*Bacillus velezensis* FZB42)
*Evidence: `curated_experimental`.*

**Step 6, walk `MEMBER_OF` upwards** (from Phase 2). What else is related?
→ `ncbitaxon:492670` (*Bacillus velezensis*, the species) → `ncbitaxon:1386`
(*Bacillus*, the genus) → and on up to `ncbitaxon:2` (Bacteria).
*Evidence: `database_assertion`, from NCBI Taxonomy.* This is the step that
turns "this one strain" into "and what about the rest of its genus?".

**The answer, assembled:**

> *Bacillus velezensis* FZB42 carries the surfactin gene cluster
> (MIBiG BGC0000433), which produces surfactin with its surfactin synthetase
> enzymes (SrfAA, SrfAB, SrfAC). Purified surfactin inhibited
> *Botrytis cinerea* and reduced grey mould on harvested winter jujube
> (Xiao et al. 2023).
>
> **Evidence chain:** experimental, experimental, literature (cited), literature
> (cited). **Weakest link: curated literature.** The two biological links come
> from this project's reading of a published paper, not from a database. MIBiG
> itself records surfactin only as antibacterial and a surfactant.

That last line is what makes the answer defensible instead of merely confident.
Along with the conclusion, the chain tells you how much weight to put on it and
where to look if you want to check. It also shows what the chain does *not*
say: the paper tested the molecule, so the arrow is about surfactin, not about
FZB42 on a jujube tree. Whether that strain makes enough surfactin on real fruit
is a different question, and the graph doesn't pretend to answer it.

No single database contains that sentence. It exists only because four arrows
from MIBiG and the cited bridge were joined, and that, in one example, is what the project is
for.

**A note on how I built this example.** I wrote an earlier version of it from
memory and got three things wrong. I had the organism as *Bacillus subtilis*
when MIBiG records *Bacillus velezensis* FZB42, I had the molecular formula
wrong, and I had surfactin listed as antifungal on the strength of the database.

MIBiG says no such thing. It records surfactin as antibacterial and a
surfactant, and nothing else. The antifungal claim is real, but it comes from
published experiments rather than from the database, which is exactly why it
sits in the curated layer with a citation attached instead of at
`database_assertion`.

I only found this by opening the actual record. Which is the argument for the
whole evidence model: a plausible fact and a checked fact look the same once
they are arrows on a screen.

The crop changed for the same reason. The first version of this example ended
at strawberries, but when the bridge was being filled in Phase 2, I couldn't
find a paper that tested surfactin against grey mould on strawberry. I did find
one for winter jujube, so the example now follows the study I can cite.

---

## 11. Design decisions and their reasons

| Decision | Reason | What it costs |
|---|---|---|
| CURIE identifiers everywhere | Unique across sources; `mg.` visibly marks what we invented | Slightly verbose to type |
| `Pathogen` separate from `Organism`, as a kind of it (Phase 4) | Every query in this project is oriented helpful → harmful; one type would mean a role filter in every query | Queries about every organism must include pathogens (the `organisms` view does) |
| Properties as a JSON column | Nine types with different properties; a wide table would be mostly empty | Querying inside JSON is more awkward; the most-used properties are plain columns in the database's views (Phase 4) |
| Join records only with independent confirmation (Phase 4) | A wrong merge silently attaches facts to the wrong thing; a missed one is a visible gap | Some true matches wait, listed, for more evidence or a person's review |
| A person's decisions in a file of their own, applied before the matching rules (Phase 4b) | Some questions need someone who has read the paper; a decision slipped in quietly would make the graph untrustworthy | Every decision needs a reason and a source, and it is visible in the ledger as `reviewed_by_hand` |
| Every value kept when a source disagrees with itself (Phase 4b) | Keeping only the first value hides the disagreement, and once hid the cause of two wrong joins | Some nodes carry an extra `<property>_by_entry` list |
| Evidence level on every edge, no default | Forces every adapter to state what it knows; no fact enters anonymously | Slightly more work per adapter, by design |
| Citation required for curated edges | An uncited hand-added fact is the thing that erodes trust fastest | Curation is slower; the bridge layer stays small and good rather than large and vague |
| Loader refuses instead of warns | Warnings get ignored; a broken graph is worse than no graph | Occasionally blocks you until you fix the data |
| DuckDB is truth, NetworkX is rebuilt | One source of truth; drift made structurally impossible | The graph must be rebuilt after every change (seconds) |
| Only ten edge types | A small, learnable vocabulary; every arrow means something specific | Some real-world facts don't fit and have to wait for a planned extension |

About that last row: every graph project tempts you to add an edge type
whenever a fact doesn't fit, and I'd resist it. Nobody can query a graph with
forty edge types, because nobody remembers the vocabulary. Adding a type should
be a decision with a paragraph of reasoning attached, made in a commit, and this
document is where that paragraph goes.

---

## 12. Write the files

There are two small files to write, and together they turn this document into
something the code can use.

### 1. `src/microbegraph/ontology.py`

This is the ontology written in Python, so the loader can check rows against it.

```python
"""
MicrobeGraph, the ontology, in code.

WHY THIS FILE EXISTS:
    docs/02-ontology-and-data-model.md is the rulebook written for people,
    and this file is the same rulebook written for the loader. Every
    validation rule imports its definitions from here, so the two can never
    drift apart.

    If you change the ontology, change it HERE and in the doc, in the
    same commit.
"""

from typing import Final

# --- The nine node types (the nouns) ---------------------------------
NODE_TYPES: Final[frozenset[str]] = frozenset({
    "Organism",       # a helpful microbe, the factory
    "GeneCluster",    # a run of genes that builds one molecule, the production line
    "Protein",        # an enzyme encoded by the cluster, the machine on the line
    "Compound",       # the molecule produced, the product
    "CompoundClass",  # a family of related molecules, the product category
    "Activity",       # what a molecule does, what it is for
    "Pathogen",       # an organism that causes plant disease, the problem
    "Crop",           # a cultivated plant, who suffers
    "Pathway",        # a chain of biochemical reactions, the wider process
})

# --- Kinds of a type --------------------------------------------------
# A Pathogen is a kind of Organism (from Phase 4). Anything an Organism may do
# in the graph, a Pathogen may do too: harbour a gene cluster, or sit in the
# family tree with MEMBER_OF arrows. The reverse isn't true: INFECTS starts at
# a Pathogen, and an ordinary Organism can't be its starting point.
#
# Without this, an organism that is both a producer and a crop pathogen
# (MIBiG records four gene clusters in Fusarium graminearum, which also causes
# head blight on wheat) would need two dots with one identifier, which rule 1
# forbids. With it, the graph has one Pathogen dot that also harbours clusters.
SUBTYPE_OF: Final[dict[str, str]] = {
    "Pathogen": "Organism",
}

# --- The ten edge types (the verbs) ---------------------------------
# Each maps to the (from_type, to_type) pair it is allowed to connect, or a
# kind of either (see SUBTYPE_OF above). The loader uses this to reject nonsense
# like Compound --PRODUCES--> Compound.
EDGE_TYPES: Final[dict[str, tuple[str, str]]] = {
    "HARBORS":         ("Organism", "GeneCluster"),
    "ENCODES":         ("GeneCluster", "Protein"),    # genomics -> proteomics
    "CATALYZES":       ("Protein", "Compound"),       # proteomics -> metabolomics
    "PRODUCES":        ("GeneCluster", "Compound"),   # the direct shortcut (MIBiG)
    "BELONGS_TO":      ("Compound", "CompoundClass"),
    "HAS_ACTIVITY":    ("Compound", "Activity"),
    "INHIBITS":        ("Compound", "Pathogen"),
    "INFECTS":         ("Pathogen", "Crop"),
    "PARTICIPATES_IN": ("Compound", "Pathway"),
    "MEMBER_OF":       ("Organism", "Organism"),   # species -> genus -> family ...
}

# --- The four evidence levels, strongest first ------------------------
# Order matters: a path's strength is the WEAKEST link in it, so the
# analytics code needs to know which of two levels is weaker.
EVIDENCE_LEVELS: Final[tuple[str,...]] = (
    "curated_experimental",   # a curator recorded a published experiment
    "database_assertion",     # a public database states it
    "curated_literature",     # this project's own cited reading of a paper
    "inferred",               # produced by an algorithm here, a HYPOTHESIS
)

# Levels that must carry a citation, or the loader rejects the row.
REQUIRES_CITATION: Final[frozenset[str]] = frozenset({"curated_literature"})

# Levels excluded from evidence chains unless the user explicitly opts in.
NOT_EVIDENCE: Final[frozenset[str]] = frozenset({"inferred"})

# --- Identifier prefixes ----------------------------------------------
# "mg." marks identifiers this project minted because no public authority
# numbers the concept. I keep them visibly separate so a reader can tell at a
# glance how much outside authority stands behind an identifier.
KNOWN_PREFIXES: Final[frozenset[str]] = frozenset({
    "ncbitaxon",          # NCBI Taxonomy
    "mibig",              # MIBiG gene clusters
    "pubchem.compound",   # PubChem compounds
    "kegg.pathway",       # KEGG pathways
    "ncbiprotein",        # NCBI protein sequence records (GenBank, EMBL, DDBJ, RefSeq)
    "uniprot",            # UniProt proteins
    "mg.class",           # ours: compound classes
    "mg.activity",        # ours: biological activities
    "mg.crop",            # ours: crops
    "mg.organism",        # ours: strains with no NCBI entry
    "mg.compound",        # ours: compounds with no PubChem entry
    "mg.protein",         # ours: proteins MIBiG names only by a gene name or locus tag
})


def is_a(node_type: str, wanted: str) -> bool:
    """
    True if node_type is the wanted type, or a kind of it.

    is_a("Pathogen", "Organism") is True; is_a("Organism", "Pathogen") is False.
    Rule 8 uses it, so a Pathogen may start a HARBORS or MEMBER_OF arrow.
    """
    seen = set()
    while node_type and node_type not in seen:
        if node_type == wanted:
            return True
        seen.add(node_type)
        node_type = SUBTYPE_OF.get(node_type, "")
    return False


def evidence_rank(level: str) -> int:
    """
    Return a level's position in EVIDENCE_LEVELS (0 = strongest).

    Used to find the weakest link in a path: the highest rank wins,
    because a chain is only as strong as its weakest arrow.
    """
    return EVIDENCE_LEVELS.index(level)


def is_valid_curie(node_id: str) -> bool:
    """
    Check that an identifier looks like 'prefix:localid' with a known prefix.

    The check is strict by design. An unknown prefix means either a typo or a
    new source that hasn't been registered above, and either one should fail
    loudly.
    """
    if ":" not in node_id:
        return False
    prefix, _, local = node_id.partition(":")
    return prefix in KNOWN_PREFIXES and bool(local)
```

### 2. `curation/compound_pathogen_crop.csv`

This file is where the bridge layer lives. Create it now with only its header,
so the shape is fixed before any rows arrive:

```csv
compound_name,compound_curie,pathogen_name,pathogen_curie,crop_name,crop_curie,relationship,citation,confidence,notes
```

It's correct to leave it empty at this stage. **Rows are only added when a real
citation is in hand.** That discipline is what makes this layer trustworthy, and
starting with an empty file makes it the default from the beginning instead of
something bolted on later.

> **Phase 2 widens this header.** Once real rows arrived, they needed five more
> columns: `pathogen_type`, `disease`, `crop_scientific_name`, `crop_category`
> and `added_on`. The current header, the first eight rows and how to add one are
> in [`04-more-sources-secrets.md`](04-more-sources-secrets.md) and
> [`curation/README.md`](../curation/README.md).

---

## 13. Checkpoint

You've finished this document when you can answer these without scrolling up:

1. What is an ontology, in one sentence, with an everyday example?
2. Why is `326423` a bad identifier and `ncbitaxon:326423` a good one?
3. Name the four-arrow chain from a microbe to a crop, and the branch beside it.
4. What do the four evidence levels mean, and which one is a hypothesis?
5. Why does the loader *refuse* rather than *warn* on a bad row?
6. Why is DuckDB the source of truth and NetworkX rebuilt from it?
7. What does the `mg.` prefix tell a reader?

<details>
<summary>Answers (open after you've tried)</summary>

1. A written agreement about what kinds of things exist and what relationships
   are allowed between them, like a family tree, which allows *parent-of* and
   *married-to* but not *borrowed-a-lawnmower-from*.
2. `326423` is only unique inside NCBI Taxonomy; PubChem compound 326423 would
   be a different thing entirely. The prefix says whose numbering system it
   belongs to, like a country code on a phone number.
3. `Organism --HARBORS--> GeneCluster --PRODUCES--> Compound --INHIBITS-->
   Pathogen --INFECTS--> Crop`, with the mechanistic branch
   `GeneCluster --ENCODES--> Protein --CATALYZES--> Compound` running alongside.
4. `curated_experimental` (curator recorded a published experiment),
   `database_assertion` (a public database states it), `curated_literature`
   (our own cited reading), `inferred` (algorithm output, the hypothesis).
5. Because warnings get ignored, and a graph with arrows pointing at
   non-existent nodes is silently wrong: every count and every centrality score
   would be off, with nothing visible to alert you.
6. One place facts live, two shapes to query them. If the graph could be edited
   directly, the two would drift and you'd have two versions of reality.
7. That the identifier was minted by this project because no public authority
   numbers that concept, so it carries no external authority.

</details>

**Files that should now exist:**

- [ ] `docs/02-ontology-and-data-model.md` (this document)
- [ ] `src/microbegraph/ontology.py`
- [ ] `curation/compound_pathogen_crop.csv` (header only)

---

## Committing this phase

```bash
git switch develop
git add -A                    # stage first, so the gate can see the new files

./check-public-safe.sh        # must print "SAFE TO PUSH"

git commit -m "feat: add the ontology and data model (nodes, edges, evidence)"
git push origin develop develop:beta develop:master

# bring local master in step with the remote master just updated
git switch master
git pull --ff-only origin master
git switch develop
```

---

**Next:** `03-ingestion-mibig.md`, which covers the evidence locker, the
provenance log and the first real records arriving from MIBiG.
