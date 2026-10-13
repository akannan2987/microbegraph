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

**Alpha carbon**: the carbon in an amino acid that carries the amino group, the
acid group and the side chain. In every amino acid but glycine it is a
**chiral centre**, so it decides whether the amino acid is the D or the L form.
Echinomycin's two PubChem records differ at the alpha carbons of its two
alanines (Phase 4c).

**Amino acid**: one of the twenty or so small building blocks that proteins are
made of. A protein is a chain of them, folded into shape, and its length is
counted in amino acids: surfactin synthetase A is 3,584 long.

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

**CDS (coding sequence)**: the stretch of DNA that is read to make one protein.
In a GenBank record each one is a feature of its own, followed by qualifiers
that give the gene's names and the protein's number (Phase 4b). See
[`img/genbank_record.svg`](img/genbank_record.svg).

**Chiral centre**: an atom, usually a carbon, with four different groups
attached, which can sit around it in two mirror-image ways. A molecule with several has a
left-or-right choice at each one. A PubChem record "drawn with its 3D shape"
says which way every chiral centre goes; a record drawn flat leaves them open.
Epoxomicin has eight (Phase 4b). The two ways are named **R and S**, and a
SMILES string marks them with `@` and `@@` (Phase 4c).

**Charge (of a molecule)**: a molecule with an electric charge is an **ion**,
and its formula ends in a sign: `C10H16NO4-` has one negative charge. Databases
don't always write the sign, so the same atoms can appear as `C10H16NO4` in one
record and `C10H16NO4-` in another (MIBiG and PubChem for prekainic acid).
Phase 4's formula check ignores a sign at the end, but not a difference in the
atoms: an acid and its ion usually differ by a hydrogen, and stay different.

**Compound**: see *Metabolite*. The two words are used interchangeably here;
"compound" is the chemistry word and "metabolite" the biology word.

**Crop**: a cultivated plant grown for food or material. In this project it sits
at the end of the chain, as the one who ultimately suffers from the disease.

**D and L (amino acids)**: the older names for the two mirror-image forms of an
amino acid, given by how its **alpha carbon** is arranged. Proteins are built
from L amino acids, but microbes often put D forms into the small molecules
they make. For most amino acids L is S and D is R (cysteine is the usual
exception), so "N-myristoyl-D-asparagine" means the record with R at that
carbon (Phase 4c).

**Damping-off**: seedlings rotting at the soil line and collapsing, just before
or after they come up. Soil organisms such as *Globisporangium ultimum* (long
called *Pythium ultimum*) and *Rhizoctonia solani* cause it. Two bridge rows are
about damping-off of cotton.

**Diastereomers**: stereoisomers that aren't mirror images of each other: some
of their chiral centres (or double bonds) point the same way and some don't.
Echinomycin's two PubChem records are diastereomers, agreeing at 6 of the 8
chiral centres both describe (Phase 4c).

**Domain**: the top rank of NCBI's ladder of life: Bacteria, Archaea and
Eukaryota (living things whose cells have a nucleus, which includes fungi,
plants and animals). NCBI called this rank "superkingdom" until 2025.

**E and Z**: the two names for the arrangement around a double bond that can't
rotate. When the more important group at each end sits on the same side, it's
Z (German *zusammen*, together); on opposite sides, E (*entgegen*, against). A
SMILES string shows it with `/` and `\` next to the double bond: `F/C=C/F` is
E, `F/C=C\F` is Z. Macbecin II's two PubChem records draw three double bonds
opposite ways (Phase 4c).

**EC number**: Enzyme Commission number, the standard code describing what
reaction an enzyme performs. You can think of it as a job title chosen from a
fixed vocabulary.

**Enantiomers**: two stereoisomers that are mirror images, with every chiral
centre the other way round. Brevione E's two PubChem records are drawn as
enantiomers (Phase 4c).

**Enzyme**: a protein that speeds up one specific chemical reaction, rather like
a specialised machine on a production line that does one step, very fast, over
and over.

**Epimer**: a stereoisomer that differs from another at exactly one of its two
or more chiral centres, the closest kind of diastereomer. Colistin A's two PubChem records are
epimers (Phase 4c).

**Fungus** (plural *fungi*): a kingdom of life including moulds, yeasts and
mushrooms. Some fungi attack crops; others protect them.

**Fusarium head blight**: a disease of wheat and barley ears, caused mainly by
the fungus *Fusarium graminearum*. It shrivels the grain and can leave toxins in
it. The same fungus causes **Gibberella ear rot** on maize, a pink to red mould
on the ear (Gibberella was the older name of the fungus's sexual stage).

**Gene**: one instruction in an organism's DNA, usually the recipe for one
protein.

**Gene job (function)**: what MIBiG says a gene does for its cluster. There are
seven: scaffold biosynthesis (builds the molecule's backbone), precursor
biosynthesis (makes a building block), tailoring (changes the backbone once it
exists), regulation, transport, activation / processing, and
resistance/immunity. Only the first three carry out a step in making the
molecule, so only they give a `CATALYZES` arrow. See
[`img/gene_jobs.svg`](img/gene_jobs.svg).

**Gene name**: the short name the scientists who described a gene gave it, such
as `srfAA` or `baeI`. Meaningful within one paper or genome, not worldwide; the
same protein can have a gene name, a **locus tag**, an **NCBI gene number** and
a **protein id**, and a GenBank record lists them side by side.

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

**Isoform**: one of several slightly different proteins made from the same gene,
because the gene can be read in more than one way (common in plants and
animals). One recipe card with optional steps gives several versions of the same
cake. In MIBiG's protein file each isoform has its own protein number, so
removing a gene (`to_delete`) removes all of them (Phase 3b).

**Isomers**: molecules made of exactly the same atoms joined in different ways,
so they share a molecular formula and can still behave completely differently,
like two models built from the same box of bricks. Minutissamides B, C and D are
isomers, which is why a matching formula alone never proves that two records
are one molecule.

**Isotope**: a version of an atom with a different weight. Most iron is iron-56;
iron-55 is a radioactive isotope. A molecule built with a radioactive isotope
is a **tracer**: chemists make it so they can follow where the molecule goes,
much as a drop of dye shows where water flows. PubChem keeps a separate record for
each, such as "[55Fe] Ferrichrome", which is why a matching formula can point
at the wrong record (Phase 4b). A matching first InChIKey block can too,
because that block leaves isotopes out, and that's how ferrichrome first ended
up joined to the iron-55 record. Since the Phase 4b follow-ups the resolver
reads the isotope label in the record's SMILES (`[55Fe+3]`: the mass number,
the count of particles in the atom's core, in front of the element), and the
same-structure clue no longer confirms a tracer.

**Jujube** (*Ziziphus jujuba*): a fruit tree grown widely in China, whose fruit
rots easily after harvest. It's the crop in the running example, because Xiao
and colleagues (2023) showed that purified surfactin reduced grey mould on
harvested winter jujube.

**Kingdom**: a very broad rank in the taxonomy ladder, just below domain. Fungi,
plants (Viridiplantae) and animals (Metazoa) are kingdoms; since 2025 NCBI also
gives bacteria kingdoms, such as *Bacillati*, which holds *Bacillus*. Because the
word now has that exact meaning, MicrobeGraph's own broad label is called
`group` (see **Group**).

**Knock-out**: switching one gene off (or removing it) and seeing what changes.
If the molecule disappears, the gene is needed to make it. It's one of the
experiments MIBiG records, both for whole clusters and for single genes.

**Lineage**: the full list of groups an organism belongs to, from the top of the
tree down, as NCBI writes it. For *Bacillus velezensis* FZB42 it starts
`cellular organisms; Bacteria; Bacillati; Bacillota; Bacilli; ...`. MicrobeGraph
keeps it as text on the node, and turns the main ranks into `MEMBER_OF` arrows.

**Lipopeptide**: a class of molecules that are part fat, part protein-fragment.
Many are soapy, which is how they damage the membranes of other microbes.
Surfactin is one.

**Locus tag**: a label a genome project gives each gene, such as `TSTA_117750`.
It's unique inside that one genome only, rather like a staff badge number, so
this project scopes it to its MIBiG entry (`mg.protein:bgc0000154-tsta-117750`).
From Phase 3b, when MIBiG's protein file pairs a locus tag with a protein number
(`TSTA_117750` with `EED18001.1`), the protein is named by the number instead and
the locus tag is kept as a property, `locus_tags`.

**Metabolite**: a small chemical an organism makes and often releases. Picture
the microbe as a factory and its metabolites as the products. Some of those
products happen to be poisonous to plant diseases, and this project is built on
that premise.

**Microbe**: the umbrella term for any organism too small to see, including
bacteria, fungi and yeasts.

**Molecular formula**: the atoms in one molecule, element by element with their
counts: surfactin is `C52H91N7O13`, meaning 52 carbon, 91 hydrogen, 7 nitrogen
and 13 oxygen atoms. It says which atoms there are, not how they're joined (see
*Isomers*). Phase 4 uses it as a check that two records describe the same
molecule.

**Monoisotopic mass**: a molecule's mass counting each element by its most
common isotope (carbon-12, hydrogen-1...). This is the value a mass spectrometer
measures for the main peak. Surfactin's is 1021.667; its average molecular
weight, which mixes in the heavier isotopes, is about 1022.3.

**Multi-omics integration**: combining several kinds of biological measurement
(genomics, proteomics, metabolomics) into a single analysis, rather than looking
at each in isolation. The difficulty is that each layer has different units,
scales and identifiers, and that is exactly why the ontology and entity
resolution phases exist.

**NRPS** (nonribosomal peptide synthetase): a giant enzyme that strings amino
acids together like an assembly line, each section adding one. Surfactin is made
by one, split across three proteins (srfAA, srfAB and srfAC). MIBiG also uses
`NRPS` as the name of a class of gene cluster.

**Oomycete**: a fungus-like organism that belongs to a different branch of life
from true fungi (it's closer to brown seaweeds). Oomycetes look like moulds and
cause serious plant diseases, so the bridge records them as their own
`pathogen_type`. *Globisporangium ultimum* is one.

**Pathogen**: an organism that causes disease. In this project, specifically a
*plant* pathogen, something that attacks crops.

**Pathway (biochemical)**: a chain of chemical reactions a cell performs in
sequence. Think of a production line with named stations, where each station's
output feeds the next.

**Place (in the 3D check)**: one spot in a molecule where the atoms can sit in
two ways: a chiral centre (R or S) or a double bond whose ends can be E or Z.
The ledger counts places when it compares two records' 3D detail: "their 3D
detail agrees at the 8 places both describe" (Phase 4c).

**Powdery mildew**: a white, powdery fungal growth on leaves. On melons and
cucumbers one cause is *Podosphaera fusca*, also called *Podosphaera xanthii*.

**Protein**: a molecular machine built from an organism's genetic instructions.
To carry on with the cookbook: if the genome is the book and a gene is a recipe,
the protein is the finished dish, which then goes off and does a job. In this
project the proteins that matter are the enzymes encoded by a gene cluster.

**Proteomics**: the study of the full set of proteins in a sample. One of the
three molecular layers this project joins together.

**R and S**: the two names for the arrangement of a chiral centre, from the CIP
rules (after Cahn, Ingold and Prelog). Rank the four groups by the atomic number
of the atom attached (roughly, by weight), turn the lowest one away from you,
and follow the other three from highest to lowest: clockwise is R (*rectus*),
anticlockwise S (*sinister*). The alanine in proteins is S. RDKit names every
centre a SMILES describes, but the resolver compares the arrangement itself,
because a name can change between **tautomers** while nothing moves in space
(Phase 4c).

**Rank**: one rung on the taxonomy ladder: strain, species, genus, family,
order, class, phylum, kingdom, domain. NCBI also uses in-between ranks such as
"species group" and "clade"; MicrobeGraph makes nodes only for the main ones.

**Ring form and open chain (of a sugar)**: in water, a sugar molecule keeps
switching between a straight chain and a closed ring, two shapes of one sugar.
PubChem can hold a record for each, and their InChIKeys differ in the first
block, because the ring adds a bond. Desosamine's name is filed under the open
chain (168997), while one MIBiG entry gives the ring's number (419813).

**Salt (of a molecule)**: an acid with its hydrogen swapped for a metal, such as
the sodium salt of lasalocid (C34H53NaO8, against C34H54O8 for the acid).
Chemically it's the same active molecule, but PubChem keeps it as a separate
record, its InChIKey has a first block of its own (that block also encodes the
formula, sodium included), and MIBiG's entries don't always agree on which one
they describe.

**Secondary metabolite**: a molecule an organism makes that isn't needed for
basic survival but gives it an advantage, such as a weapon, a signal or a
defence. Most antibiotics are secondary metabolites. Also called a *specialised
metabolite* or *natural product*.

**Sequence (protein)**: a protein written as text, one capital letter per amino
acid in the order they're joined: srfAA starts `MEITFYPLTNAQ...` and runs to 3,584
letters. `X` stands for "some amino acid, but the sequencing couldn't tell
which". MicrobeGraph keeps each protein's sequence length and an MD5 fingerprint
of its letters (`sequence_length`, `sequence_md5`), and leaves the letters
themselves in MIBiG's protein file in the evidence locker.

**Siderophore**: a molecule a microbe releases to grab iron from its
surroundings. Iron is scarce and everyone needs it, so a good siderophore is a
way of starving your competitors. Siderophores are a common biocontrol
mechanism.

**Strand (DNA)**: DNA is two long strands wound together, and a gene can be
written on either one. MIBiG's protein file marks which with `+` or `-`, and
MicrobeGraph keeps it in a protein's `locations` (Phase 3b).

**Species / genus / family**: rungs on the ladder that classifies life, from
specific to general. *Bacillus subtilis* is a species; *Bacillus* is its genus.
A postal address climbs the same way: street → city → region → country.

**Stereochemistry**: how a molecule's atoms are arranged in space, not just
which are connected to which. Your left and right hands show the idea: the same
parts, connected the same way, yet a left glove won't go on a right hand. PubChem
often has one record with the 3D arrangement spelled out and one without; the
first block of the **InChIKey** is the same for both.

**Stereoisomers**: two molecules with the same atoms, connected the same way,
whose **chiral centres** point different ways. They share a formula and the
first InChIKey block, yet a cell can treat them as two different things (one
may work as a medicine while its mirror form does nothing). That's why Phase 4c
compares the chiral centres and double bonds of two records before clue 2
treats them as one compound ([`06c-checking-3d-detail.md`](06c-checking-3d-detail.md)).
See also **enantiomers**, **diastereomers** and **epimer**.

**Strain**: one specific isolate within a species. If "species" is a car model,
a strain is one particular car with its own history and quirks, and two strains
of the same species can behave quite differently.

**Surfactin**: a lipopeptide made by *Bacillus* bacteria. I use it as the
running example in these docs because it's real and well studied, and its whole
chain, from microbe to crop, can be backed by a citation.

**Synthetase**: an enzyme that joins smaller molecules into a bigger one. The
surfactin synthetase joins seven amino acids and a fatty acid.

**Take-all**: a root disease of wheat caused by the fungus *Gaeumannomyces
tritici* (in older papers, *G. graminis* var. *tritici*). It blackens the roots
and leaves white, empty heads.

**Tautomers**: two forms of one compound that turn into each other on their own,
a hydrogen atom moving to a neighbouring atom and a double bond moving with
it. They count as one compound. For the common kind, where the hydrogen moves
between nitrogen or oxygen atoms, the first InChIKey block is the same for
both. Saxitoxin has two PubChem records that are tautomers (Phase 4c). Moving
the hydrogen can change the name R or S of a centre nearby, though nothing
moved in space.

**Taxid** (taxon ID): NCBI Taxonomy's number for an organism or a group, for
example `326423` for *Bacillus velezensis* FZB42, written `ncbitaxon:326423`
in this project. NCBI sometimes **merges** two numbers (asking for the old one
returns the record under the new one) or **deletes** one.

**Taxonomy**: the system for naming and classifying organisms, and the
hierarchy it produces.

**Yeast**: a single-celled fungus.

---

## Graphs and knowledge

**Activity synonym**: two activity words that mean the same thing, such as
"antitumor" and "anticancer". Since Phase 4b they're listed, each with a reason
and a source, in `curation/activity_synonyms.csv`, and the resolver folds one
word's node into the other's, keeping the old word as another name.

**Alias**: another identifier for the same node. Since Phase 4,
`ncbiprotein:CAE02630.1` is an alias of `uniprot:Q70KJ7`: the node lists its
aliases, and the database's `aliases` view finds the node from any of them, the
way a forwarding address still reaches you after a move.

**Betweenness centrality**: a measure of how often a node sits *on the shortest
route between other nodes*, which makes it a kind of "bridge" score. A road
junction can be quiet itself and still break half the city's journeys if it
closes; that junction has high betweenness. This often tells you more than raw
popularity does.

**Canonical numbering**: a fixed way of numbering the atoms of a molecule (or
the nodes of any graph) that gives the same numbers to the same structure
however it was written down. Two drawings of one skeleton numbered this way can
be matched atom for atom. RDKit's version is `CanonicalRankAtoms` (Phase 4c).

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

**Decision by hand**: a join or a refusal that a person made, after reading the
source, because no rule could make it correctly. Since Phase 4b it goes in the
**review file**, with a reason and a citation, and the ledger records it under
its own rule, `reviewed_by_hand`, so it's never mistaken for a rule's decision.

**Degree**: how many arrows touch a node, which you can read as its "popularity"
score.

**Directed graph (DiGraph)**: a graph where arrows have a direction. *A
produces B* is not the same statement as *B produces A*. MicrobeGraph is
directed throughout. NetworkX's `DiGraph` holds at most one arrow from one node
to another, which the graph build checks.

**Edge**: a connection between two nodes, with a direction and a name
(*produces*, *inhibits*). Also called a *relationship* or *link*. On the map,
it's one arrow.

**Embedding**: turning a node's position in a graph into a list of numbers, so
that nodes with similar connection patterns get similar numbers. Once every node
is a vector, ordinary machine learning applies. Describing a person by the
social circles they move in, then looking for people with similar descriptions,
works on the same principle.

**Entity resolution** (also *record linkage* or *deduplication*): deciding that
several records refer to the same real-world thing and merging them into one
node, as when you realise that "Robert Smith", "Bob Smith" and "R. Smith (work)"
are one person. MicrobeGraph's resolver (Phase 4) does it with ten rules and
writes every decision, joins and refusals alike, in the resolution ledger.

**Graph**: information stored as dots connected by arrows (nothing to do with
bar charts). A transport map is a graph, and so is a social network.

**GraphRAG**: answering a question by first *walking a knowledge graph* to
collect relevant facts, then giving those facts to a language model to phrase
the answer. See also *RAG*.

**Hop**: one step along one arrow. A "three-hop path" crosses three arrows.

**Isolated node**: a node with no arrow to or from anything (degree 0). In a
knowledge graph it says nothing, since every fact is an arrow. MicrobeGraph's
resolver takes out KEGG maps that end up isolated, because every compound KEGG
placed on them was left out, and writes a ledger row for each (Phase 4b
follow-ups).

**Knowledge graph**: a graph whose nodes are real-world concepts and whose edges
are meaningful relationships between them, usually with provenance attached.
MicrobeGraph is one.

**Link prediction**: scoring arrows that *don't* exist yet, to guess which ones
probably should. Social networks do this when they suggest "People you may
know". In this project the output is always a hypothesis, never a finding.

**Naming identifier**: the one identifier a merged node keeps, taken from the most
specific public authority: a PubChem compound before MIBiG's own compound name,
a UniProt entry before a protein record number. The others become its aliases.

**Node**: one thing in a graph: a microbe, a compound, a crop. Also called a
*vertex*. One dot on the map.

**node2vec**: the specific method this project uses to compute embeddings. It
takes many random walks through the graph and learns numbers that predict what a
node's neighbours tend to be.

**Ontology**: a written agreement about what kinds of things exist in your world
and what relationships are allowed between them. A family tree has one built in:
it allows *parent-of* and *married-to*, but not *borrowed-a-lawnmower-from*. An
ontology is that kind of decision, made explicitly.

**Override**: a decision that wins over the normal rule. An override nobody can
see is a hidden fault; one written down with its reason, like a referee's
decision with the replay attached, can be checked. The review file is this
project's only override, and every use of it is in the ledger.

**Path**: a sequence of arrows leading from one node to another. Paths are the
core output of this project, because each one is an evidence chain.

**Property**: a piece of information attached to a node or edge, e.g. a
compound's molecular weight.

**Schema**: the concrete implementation of an ontology: these columns, these
types, these constraints.

**Shortest path**: the route between two nodes crossing the fewest arrows. The
graph equivalent of "fastest route".

**Subtype (a kind of)**: a node type that is a special case of another, and may do
anything the other may. In MicrobeGraph a Pathogen is a kind of Organism (since
Phase 4), so a pathogen may harbour gene clusters and sit in the family tree,
while an ordinary Organism still can't infect a crop. A sports car is a kind of
car: it may park wherever cars may, but not every car is allowed on the track.

**Union-find** (also *disjoint-set forest*): a small data structure that keeps
track of which items belong together while groups are joined one pair at a
time. If A joins B and later B joins C, it knows that A and C are in one group
without anyone comparing them. Phase 4's resolver groups records of the same
thing with it (`src/microbegraph/resolution/groups.py`).

**Values by entry** (`<property>_by_entry`): when two records of one source give
one node different values, the node keeps the first under the property's name
and lists every value with the record that gave it, e.g.
`pubchem_cid_by_entry` = `BGC0000657: 9237955|BGC0000658: 16913`. Like signed
witness statements: the disagreement stays visible (Phase 4b).

**Weakest link**: the least certain arrow along a path. A chain of evidence is only
as strong as its weakest arrow, so the cookbook's recipe R9, and the analytics
from Phase 5, name it for every path.

---

## Computers, terminals, and files

**CSV** ("comma-separated values"): a plain-text table where columns are
separated by commas. Excel, any text editor and every programming language can
open one. I chose CSV for the graph files on purpose: when you can open a file
in a text editor, you can debug it.

**Directory**: another word for folder.

**Executable bit**: a file permission on macOS/Linux marking a file as "allowed
to run as a program". Set with `chmod +x`. Windows doesn't use it.

**FASTA**: a plain text format for sequences, read by almost every biology tool.
Each record is a header line starting with `>`, then the sequence. MIBiG's
protein file is a FASTA file with a seven-part header (`BGC0000433.5|c1|...`);
[`img/fasta_header.svg`](img/fasta_header.svg) shows it part by part.

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

**TSV** ("tab-separated values"): a CSV that separates columns with tabs
instead of commas. UniProt sends its result tables this way, and Python, VS Code
and any spreadsheet program can open them.

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

**Circular import**: two Python files that each need the other before they can
finish loading, so neither can, like two people at a door each waiting for the
other to go first. The fix is to move what both need into a third file that
needs neither (Phase 4b moved the shared table helpers into
`src/microbegraph/tables.py`).

**Dataclass**: a Python class whose only job is to hold a few named values
together, like a printed form with labelled boxes. `ProteinRecord` in
`mibig_proteins.py` is one: a protein's entry, position, label, product, number,
length and fingerprint (Phase 3b).

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

**NetworkX**: the Python library this project uses to hold the graph in memory and
walk it: neighbours, shortest paths, centrality. In MicrobeGraph it's always
rebuilt from the DuckDB database (`load_graph()`), never edited on its own.

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

**RDKit**: the free chemistry library for Python (BSD licence) this project uses
to read SMILES strings and compare how molecules sit in 3D (Phase 4c). It is
the one package pinned to an exact version, `rdkit==2025.9.3`, because newer
versions have no ready-made install for Intel Macs and because its answers
decide the resolver's counts.

**requirements.txt**: a text file listing exactly which packages the project
needs. It acts as the project's *receipt*: with it, anyone can rebuild an
identical toolbox. Most lines give a range of versions; RDKit's gives one exact
version (Phase 4c).

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

**CHECK constraint**: a rule a database checks on every row before accepting it,
such as "`evidence_level` must be one of these four words". MicrobeGraph's
database builds its CHECK lists from `ontology.py`, so the Python rules and the
database rules can't disagree.

**Column**: one field in a table; one attribute of every row.

**Constraint**: a rule the data must obey, enforced by the database or the
loader. "This value must be unique" is a constraint.

**Crosswalk**: a table of matched identifiers between two databases, such as
"INSDC protein `CAE02630.1` is UniProt entry `Q70KJ7`". Two databases that never
mention each other can be joined through one, as long as both know some shared
number.

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

**NULL**: "no value" in a database. It isn't zero and it isn't empty text, so SQL
tests for it with `IS NULL` or `IS NOT NULL`, never with `=`.

**Primary key**: the column that uniquely identifies each row. Ours is
`node_id`.

**Query**: a question asked of a database, usually written in SQL.

**Query cookbook**: [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md), a collection of
questions for the database, each with the SQL (or Python) that answers it and
the answer it gave on the real data. Every recipe is run by the tests, so none of
them quietly stops working.

**Read-only**: able to look but not change. The query command
(`python -m microbegraph.query`), `load_graph()` and the app's SQL console open
the database read-only *by construction*, meaning the database itself refuses
any change, rather than the docs promising it.

**Recursive query**: a SQL query that feeds its own result back in, step by step,
until nothing new turns up (`WITH RECURSIVE`). It's how SQL walks a family tree of
any depth; the cookbook's recipe R12 finds every cluster under the genus
*Bacillus* this way.

**Row**: one record in a table; one thing.

**Schema**: the structure of a database: which tables exist, which columns they
have, which rules apply.

**Single source of truth**: the one place a fact is kept, from which every other
copy is rebuilt. Here it's the DuckDB database: the NetworkX graph is rebuilt
from it every time, so the two can't drift apart.

**SQL** (pronounced "sequel" or "ess-cue-ell"): the language for asking
databases questions. It reads close to English:
`SELECT name FROM compounds WHERE activity = 'antifungal'`. It was invented in
the 1970s and is still everywhere.

**Table**: a grid of rows and columns. Tables are excellent at counting and
filtering but bad at chains of unknown length, which is why this project also
builds a graph.

**View**: a saved query that looks and behaves like a table. MicrobeGraph's
database has one for each node type with properties worth showing (`organisms`,
`compounds`, `proteins`...), with the most-used properties as plain columns, and
an `aliases` view.

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

**Batch (of ids)**: a group of identifiers sent in one request or job, because
sending them one at a time would take thousands of requests. From Phase 3b the
UniProt adapter sends 10,000 ids per job (UniProt allows up to 100,000), so about
39,000 numbers take five jobs.

**Bulk download**: a whole database, or a slice of it, published as one file
to download instead of answered one question at a time. When the list of
questions is long and the service limits how many it answers, one big file can
be both kinder to the service and faster. From Phase 4b, MicrobeGraph takes
PubChem's names this way (see *Names file (PubChem)*): one 931 MB download in
place of 1,653 questions.

**Checksum**: a short fingerprint calculated from every byte of a file; change
one byte and the fingerprint changes completely. Publishers list it beside a
download so you can prove you received exactly their file. **MD5** and
**SHA-256** are two common kinds; SHA-256 is longer and stronger. Checking one
is like counting a parcel's contents against its packing slip. See
[`img/checksum_fingerprint.svg`](img/checksum_fingerprint.svg). When a publisher
lists none, this project records its own from the first download and pins it
(see *Pin*).

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

**Headers (HTTP)**: the short lines at the start of every web answer that
describe what follows, such as its size (`Content-Length`), its type and when it
last changed (`Last-Modified`). Reading only the headers and then hanging up is
how the MIBiG probe checks the protein file without downloading it (Phase 3b).

**HTTP**: the protocol web browsers and programs use to request things from
servers.

**Ingestion**: the act of getting data into your system, and the first pipeline
stage.

**Job (on a web service)**: a request that runs in the background because it may
take a while. You hand in the work, get a job number back, ask about it until it
is finished, then collect the result, much like ordering at a busy cafe counter.
UniProt's ID mapping works this way.

**Manifest**: the file `manifest.json` in each API snapshot, listing what was
asked and what came back. It's written last, so its presence means the fetch
finished.

**`.part` file**: a download in progress, saved under a temporary name and
renamed only once it is complete and verified, so a dropped connection never
leaves a half-file that looks finished.

**Pin**: to fix exactly which version of something the project uses, by writing
its name and fingerprint into the code, so a newer or altered file can't slip in
unnoticed. MIBiG's archive is pinned by the MD5 Zenodo publishes; MIBiG's protein
file, whose server publishes no checksum, by the SHA-256 and size of its first
download (Phase 3b). A package can be pinned too, by giving one exact version
instead of a range, as `requirements.txt` does for RDKit (Phase 4c). Changing a
pin is an upgrade made on purpose.

**Polling**: asking the same question again and again, a few seconds apart,
until the answer changes ("is my job finished yet?").

**Provenance**: the recorded origin of a piece of information: where it came
from, when, and under what terms. Written to `data/raw/provenance.csv` on every
fetch. Each row also says what happened to the file: `downloaded`,
`already_present` (it was in the locker already) or, from Phase 4b, `derived`
(worked out on your computer from a downloaded file, such as the name search
done in PubChem's names file).

**PUG REST**: PubChem's API. You put what you want in the address (compounds by
CID, their properties or synonyms) and the CIDs themselves in a POST body.

**Rate limit**: a cap on how many requests you may make per second. Exceed it
and you get blocked; respecting it is basic politeness to a free service.
PubChem allows 5 a second and 400 a minute, NCBI 3 a second (10 with a key) and
KEGG 3. A block can outlast the burst that caused it: in Phase 4b, a survey
asking PubChem four names a second was answered **429 Too Many Requests** after
about 400 names, and PubChem went on refusing for hours. Asking one name a
second was refused after 372 names too, so the name search now reads PubChem's
names file instead (see *Names file (PubChem)*).

**Redirect**: an answer that says "what you want is over there", with the new
address in a header called `Location`. HTTP 303 is one kind. Programs usually
follow redirects automatically; the UniProt adapter turns that off when it asks
whether a job is finished, because the redirect itself is the answer it needs.

**Release candidate (rc)**: a version published for testing just before the
final release, such as `mibig_json_5.0rc1.tar.bz2`. Things can still change
before the final version, so this project waits for the final one before
upgrading ([`ROADMAP.md`, *Watching the sources*](ROADMAP.md#watching-the-sources)).

**Request body**: the part of a request that carries its details separately from
the web address. Error messages, logs and browser histories show addresses, not
bodies, which is why a key belongs in the body.

**Resume (a search)**: carry on from where an interrupted run stopped instead of
starting again. When PubChem stops answering partway through the name search,
the adapter keeps what arrived in a snapshot marked incomplete, and the next run
carries those answers over and asks only the rest, like a long trip with rest
stops where you pick up from the last stop, not from home.

**Retry with backoff**: when a request fails, waiting a moment and trying
again, waiting longer each time. *Everyday example:* the phone is engaged; you
don't redial forty times a second.

**Snapshot**: one fetch from a web API, kept as a dated folder in the evidence
locker: every answer exactly as it arrived, plus a manifest. A new day or a new
set of questions makes a new snapshot; older ones are kept for comparison. From
Phase 4b a snapshot can be finished incomplete (the manifest says
`"complete": false`) when the service stopped answering, so the next run can
resume it. See
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
404 = not found. 403 = refused. 429 = Too Many Requests: you're going too fast,
so wait, longer each time, and never retry in a quick loop. 500 = the server
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

**Annotation score**: UniProt's rating, from 1 to 5, of how well an entry is
described. It measures how much is written about the protein, not how certain
any one statement is.

**ChEBI** (Chemical Entities of Biological Interest): a free dictionary of small
molecules, run by EMBL-EBI. Phase 2 reads ChEBI numbers from PubChem's synonyms
(`CHEBI:30838` is itaconic acid).

**CID** (compound identifier): PubChem's number for one chemical structure, for
example `811` for itaconic acid, written `pubchem.compound:811` here.

**Curators' corrections (`to_add`, `to_delete`)**: changes MIBiG's curators make
to the gene list of the sequence record an entry points at, like an errata slip
for a printed book. `to_add` lists genes the record misses (661 in active
entries, all already in MIBiG's protein file); `to_delete` lists genes that
aren't part of the cluster, each with a reason (14 names, 18 proteins). From
Phase 3b the removals are applied and each one is listed in
`mibig_summary.json`.

**GenBank record**: the text format NCBI and its partners have used since the
1980s to describe a piece of DNA: a header, a **FEATURES** table saying what sits
where (each gene that codes for a protein is a **CDS**), and the DNA itself.
MIBiG publishes one per entry, in its GenBank file.

**ID mapping**: UniProt's service for translating identifiers from another
database (an INSDC or RefSeq protein number, for example) into UniProt
accessions. It runs as a job. An id it can't translate doesn't appear in
the results, so this project compares what it asked with what came back.

**InChI**: the text form of a structure that an **InChIKey** is made from, built
of layers separated by `/`. The `/t` layer lists each chiral centre by atom
number with `+` or `-`, `/b` each double bond, and `/m` says whether the signs
are written for the mirror image. Phase 4c's survey compares two records'
layers number by number as a second check on `stereo.py`'s answers.

**InChIKey**: a 27-character fingerprint of a chemical structure, the same in
every database, which makes it handy for matching compounds across sources. It
has three blocks: the **first** encodes the atoms and how they connect, the
second the 3D arrangement and isotopes, the third the charge. Two PubChem records
with the same first block are usually the same molecule drawn in different ways,
but they can also be a molecule and its isotope-labelled tracer, or two
**stereoisomers** (Phase 4b uses the first block to tell "another record of
the same molecule" from "another molecule"; ferrichrome's iron-55 record and
the stereoisomer question show where that stops working). A drawing without
3D detail or isotope labels always gets the second block `UHFFFAOYSA`. Since Phase 4c the
resolver compares the 3D detail itself whenever two records share a first
block.

**INSDC** (International Nucleotide Sequence Database Collaboration): GenBank
(USA), the European Nucleotide Archive (Europe) and DDBJ (Japan), three public
archives of DNA sequences that share one numbering. Each translated gene in them
gets a protein id such as `CAE02630.1`, the same in all three, written
`ncbiprotein:CAE02630.1` in this project.

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

**MIBiG GenBank file**: `mibig_gbk_4.0.tar.gz` (79.8 MB) on MIBiG's download
server: 2,636 GenBank records, one per entry. From Phase 4b the project reads its
CDS features for every name a gene goes by, which places gene records named only
by a gene name and the curators' removals no other list names. Pinned by its
SHA-256, like the protein file.

**MIBiG gene record**: the part of a MIBiG entry that lists the cluster's genes:
for each one, the id of the protein it makes, its name, a short product
description, and often its job and the experiment that showed it. In MIBiG 4.0,
452 of the 2,437 active entries have them. The MIBiG adapter reads them from
Phase 3, and from Phase 3b matches each one to its protein in MIBiG's protein
file.

**MIBiG protein file**: `mibig_prot_seqs_4.0.fasta`, a FASTA file on MIBiG's
download server listing every protein of every cluster in the release: 46,987
proteins, 40,009 of them in active entries. It gives every cluster its `Protein`
nodes and `ENCODES` arrows from Phase 3b, but no jobs, so no `CATALYZES`.

**MIBiG quality grade**: MIBiG's own rating of each entry: `high`, `medium`,
`low` or `questionable`. MicrobeGraph carries it through as the `confidence` of
every arrow from that entry (0.95, 0.85, 0.70, 0.50).

**Name search (PubChem)**: asking PubChem which records a name is filed under
(`POST .../compound/name/cids/JSON`). It answers with the numbers, or "No CID
found". From Phase 4b the PubChem adapter looks up the MIBiG names their own
numbers don't list, and the names of compounds with no number but a formula.
A long list (more than 300 names), or any list once the names file is on your
computer, is searched in PubChem's names file; a short one goes to the web,
one name a second. A number only the
search found joins a compound only when the formula agrees.

**Names file (PubChem)**: `CID-Synonym-filtered.gz`, PubChem's download of
every name it files under every compound, one line per name: the compound's
number, a tab, the name. It was 931 MB on 2026-10-12. The PubChem fetch
downloads it once into the evidence locker and searches it for MIBiG's names
on your computer, which asks PubChem nothing and takes a few minutes. On the
673 names both had answered, it agreed with PubChem's web search every time.

**NCBI**: the US National Center for Biotechnology Information. It runs Taxonomy
(the classification of life) and Datasets (genome records), among much else.
NCBI places no restrictions on using its data, although some people who submit
data to it claim rights in what they submitted.

**NCBI gene number** (GeneID): NCBI Gene's number for a gene, such as
`100272490`. A gene with no other name is called `LOC` plus its number
(`LOC100272490`), and a GenBank record writes it as `/db_xref="GeneID:100272490"`,
which is how Phase 4b matched four maize genes MIBiG's curators removed.

**Negative result**: a test that looked for something and did not find it. MIBiG
records some bioactivities as `"observed": false`. MicrobeGraph counts them but
never turns them into a `HAS_ACTIVITY` arrow, which would say the opposite.

**NPAtlas** (Natural Products Atlas): a curated database of molecules made by
microbes, with its own numbers (surfactin is `NPA018495`). MIBiG records NPAtlas
numbers for many compounds; in Phase 4, two MIBiG names with the same NPAtlas
number and the same formula become one compound.

**Pending (MIBiG entry)**: an entry submitted to MIBiG but not yet reviewed and
released, like a manuscript that has been sent in but not yet published. Its
status isn't `active`, so MicrobeGraph leaves it out. MIBiG's protein file holds
proteins for 199 pending entries (6,978 proteins), which are counted and skipped.

**Protein existence**: UniProt's note of how directly a protein is known to
exist, from "evidence at protein level" (someone detected the protein itself)
through "evidence at transcript level" and "inferred from homology" to
"predicted".

**Protein id**: the identifier a sequence archive gives a translated gene, such
as `CAE02630.1` (INSDC) or `WP_029025939.1` (RefSeq). The part after the dot is a
version number, which goes up if the sequence is corrected.

**PubChem**: the US National Institutes of Health's chemistry database. Given a
CID it returns a formula, weights, the structure and a synonym list; given a name
it can find the CID. Access is free and needs no account. Its synonym lists are
the raw material for entity resolution here.

**Qualifier (GenBank)**: one line of detail under a feature in a GenBank record,
starting with `/`: `/gene="srfAA"`, `/locus_tag=...`, `/protein_id="CAE02630.1"`.
A value in quotes can wrap onto the next line, which the reader in
`sources/mibig_genbank.py` has to allow for.

**RefSeq**: NCBI's Reference Sequence collection, a cleaned-up, non-redundant
copy of the public sequence archives. Its protein ids start with `WP_`, `NP_`,
`YP_` or `XP_`.

**Reviewed / unreviewed**: the two kinds of UniProt entry. A reviewed entry
(Swiss-Prot) was written by a curator from the literature; an unreviewed one
(TrEMBL) was made automatically from a sequence record. Most enzymes from gene
clusters are unreviewed.

**SMILES**: a way of writing a molecule's structure as one line of text, for
example `C=C(CC(=O)O)C(=O)O` for itaconic acid. `@` and `@@` at an atom say
which way a chiral centre goes, and `/` and `\` beside a double bond which side
its groups are on (**R and S**, **E and Z**). A SMILES without them is drawn
**flat**: it leaves those places open, so it agrees with any drawing that
fills them in (Phase 4c).

**Synonym**: another name for the same thing. One molecule can have dozens
(itaconic acid has about ninety in PubChem), which is why names alone can't be
trusted to match records.

**The curated bridge**: this project's own small, hand-assembled CSV linking
compounds to pathogens to crops, because no public database publishes those
links as a downloadable table. Every row carries a citation and every edge is
labelled `curated_literature`, and the whole layer can be filtered out. Every
row passes thirteen checks before it's loaded; how to add one is in
[`curation/README.md`](../curation/README.md).

**UniProt**: the world's main public catalogue of proteins, run by the European
Bioinformatics Institute, the Swiss Institute of Bioinformatics and the Protein
Information Resource, free under CC BY 4.0. Each entry has an **accession**, a
permanent identifier such as `Q70KJ7`, and an **entry name** such as
`Q70KJ7_BACAM`. It releases a new version about every eight weeks
(`2026_03`, for example). See [`05-proteomics-uniprot.md`](05-proteomics-uniprot.md).

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

**Median**: the middle value once everything is sorted, so half are smaller and
half larger. Unlike an average, a few giant values can't drag it up: the median
protein in MIBiG's protein file is 344 amino acids long, although the longest is
18,447.

**Normalise (text)**: put text into a consistent form before comparing:
lowercase, trimmed, punctuation stripped. It stops `Surfactin ` and `surfactin`
from being treated as different things. Phase 4 calls the result a *name key*,
and keeps the signs of mirror-image molecules as words, so (+)-menthol and
(-)-menthol never match.

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

**Human-in-the-loop**: a pipeline in which a person makes the decisions the rules
can't, at a defined point and in a recorded way, while the rules do the rest.
In this project the point is the review file, and the record is the ledger.

**Independent confirmation**: a second piece of evidence that doesn't depend on
the first. A PubChem number that MIBiG's curators typed in is joined to PubChem's
record only when the name or the formula agrees as well, because some of those
numbers belong to other molecules (Phase 4). Independence is the hard part: where
MIBiG copied a structure from the PubChem record its number points at, the
formulas agree whatever the number. That's why, from Phase 4b, the formula alone
no longer counts when PubChem's name search points at another molecule or
MIBiG's entries disagree about the formula.

**Ledger**: a written record of what a step did: what was merged, removed, or
changed, and why. The resolution ledger and the provenance log are both ledgers.
A bank statement is one in this sense; it records what happened to the money
rather than holding the money itself. The resolution ledger
(`data/processed/resolution_ledger.csv`, Phase 4) has one row per merge or
refusal, with the rule that decided it and its grounds in a sentence.

**Pipeline**: a series of stages where each one's output is the next one's
input, flowing one way. *Everyday example:* beans → grinder → espresso machine →
cup. Each stage has one job and can be tested alone.

**pytest**: the tool that runs this project's automated tests.

**Reproducibility**: the property that someone else, on a different machine, can
run your work and get the same result. That's why this project has
`requirements.txt`, the evidence locker and the provenance log.

**Review file**: `curation/resolution_decisions.csv` (Phase 4b), where a person
records a decision about two records (`join` or `keep_apart`) with a reason, a
citation and a date. The resolver applies it before the rules that join
compounds and proteins, and a pair kept apart can never end up in one node,
even through a chain of other joins. See
[`img/review_row.svg`](img/review_row.svg).

**Test (unit test)**: a small automated check proving one function does what you
claim. A cook tastes the sauce before serving instead of hoping; a test does the
same for code.

**Validation**: checking data against rules before accepting it. This project's
loader *refuses* invalid rows rather than warning about them, because warnings
get ignored.

---

*Missing a term? Please open an issue; I treat that as a documentation bug.*
