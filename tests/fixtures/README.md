# Test fixtures: where every sample record came from

The tests never touch the internet. Instead they read small sample records
kept in this folder, and this page says where each one came from, so anyone
can check that the samples are real.

**Why it matters.** Phase 1 taught this project the same lesson twice: test
records written by hand from documentation drift away from what a server
really sends. The MIBiG archive turned out not to be gzip-compressed, and
activity names arrived in a second style no documentation mentioned, and both
times every test had passed. So from Phase 2 on, sample answers are cut from
real ones.

## `mibig/` (Phase 1)

| File | What it is |
|---|---|
| `BGC0000433.json` | A real MIBiG 4.0 entry (surfactin), trimmed: its biosynthesis modules are removed because the adapter never reads them. Every field the adapter reads is unchanged, including (from Phase 3) its nine gene records. Its own `comment` field says so. |
| `BGC9999901.json` | Made up, describing nothing real. It covers what the surfactin entry doesn't: two compounds, a negative result, activity names in both of MIBiG's styles, a curator's comment, a PubChem number, a Greek letter in a name; from Phase 3, gene records with a RefSeq id, locus tags, a gene with no name, a cited assay, a gene with two jobs, an activation gene and a record with no id; and, from Phase 3b, three more gene records (a locus tag the protein file gives a number, a gene name matching one product, a gene name matching two), a gene the curators added (`to_add`) and four removals (`to_delete`). |
| `BGC9999902.json` | Made up: a retired entry, which the adapter must skip. |
| `BGC9999903.json` | Made up: an entry whose only evidence is a prediction, so its arrows must be `database_assertion`. Its one gene record shares a locus tag with BGC9999901, to prove the two stay separate proteins. From Phase 3b it shares one protein number with BGC9999901 in the protein file sample, to prove that is one protein in two clusters. |
| `mibig_prot_seqs_sample.fasta` | Phase 3b: a sample of MIBiG's protein file. Surfactin's 23 real records first, then made-up ones (see below). |
| `genbank/` | Phase 4b: samples of MIBiG's GenBank file, one record per file (see below). |

The made-up entries use numbers from 9999901 up, which MIBiG doesn't use, and
a DOI prefix (10.0000) that belongs to no publisher. Each one says so in its
own `comment` field. The made-up protein ids (`WP_999999901.1`,
`WP_999999970.1`, the `XYZ999..` numbers, `TESTI_...`, `ctg1_orf7`) belong to no
real protein.

## `pubchem/`, `ncbi_taxonomy/`, `kegg/` (Phase 2)

Captured on **2026-10-12** by [`capture_samples.py`](capture_samples.py),
which asks each source a few small questions and saves the answers exactly as
they arrived. The files below are those answers, renamed to the names the
adapters give them in a snapshot. Each fingerprint (SHA-256) is the one
`capture_samples.py` recorded when the answer arrived, so you can confirm
nothing was edited:

```bash
# macOS and Linux (Windows PowerShell: Get-FileHash <file> -Algorithm SHA256)
shasum -a 256 tests/fixtures/pubchem/* tests/fixtures/ncbi_taxonomy/* tests/fixtures/kegg/* tests/fixtures/uniprot/*
```

| File | The question that was asked | SHA-256 (first 16 characters) |
|---|---|---|
| `pubchem/properties_001.json` | Properties of CIDs 811, 5281917, 16132390, 102196435, 406870990 | `e0b41e26eaceb673` |
| `pubchem/synonyms_001.json` | Other names of the same five CIDs | `ad3a300ab2c82b60` |
| `ncbi_taxonomy/einfo.json` | Facts about the taxonomy database | `84051dc072211bb7` |
| `ncbi_taxonomy/efetch_organisms.xml` | Records for taxids 326423, 33, 109376, 746360, 2961896 | `069f3d6099992aa6` |
| `ncbi_taxonomy/efetch_pathogens.xml` | Records for the six bridge pathogens | `28b5716c01ce5523` |
| `ncbi_taxonomy/efetch_retired.xml` | Records for 2056260 (merged), 3897929 (deleted) and 326423 | `02dba3a8926ef76f` |
| `kegg/info_kegg.txt` | `/info/kegg`, release dates | `fbb3a0a35348d9f7` |
| `kegg/list_pathway.txt` | `/list/pathway`, every map | `46c36040530f1de2` |
| `kegg/pathway_categories.txt` | `/get/br:br08901`, the map categories | `86f3c0037e72b96e` |
| `kegg/link_pathway_compound.txt` | **An excerpt** of `/link/pathway/compound` (see below) | `bc4738fcc607cf25` |

**The one excerpt.** The full compound-to-map list is 19,689 lines (492 KB),
far more than a test needs. The fixture keeps its first 40 lines exactly as
they arrived, followed by every line for C00490 (itaconic acid) and C07481
(caffeine), also exactly as they arrived. Nothing is reworded or reordered.
The fingerprint of the full answer was
`4d7ed0f8b3bdcf14c3857ae4bf5428b1543f63ba1ddebd663344f2e65dd5a547`.

**Byte for byte on every system.** `.gitattributes` tells Git never to change
the line endings of these files, so the fingerprints above hold on Windows
too.

**What the samples show.** CID 406870990 is a number PubChem doesn't know: it
comes back holding only its own number. CID 102196435 has properties but no
other names. Taxid 2056260 was merged into 435890 and comes back under the new
number, with the old one listed as "also known as". Taxid 3897929 was deleted
and comes back with nothing at all. The tests check that the adapters handle
each case.

## `uniprot/` (Phase 3)

Captured on **2026-10-12** by
[`capture_uniprot_samples.py`](capture_uniprot_samples.py), which first surveys
MIBiG's gene records offline and then asks UniProt about surfactin's nine protein
ids, twenty more spread evenly through MIBiG's INSDC ids, one made-up id
(`XYZ99999.99`) and five RefSeq ids. The files are those answers, renamed to the
names the adapter gives them in a snapshot (the status answers aren't kept in a
snapshot; the tests use them as the server's reply):

| File | The question that was asked | SHA-256 (first 16 characters) |
|---|---|---|
| `idmapping_fields.json` | `GET /configure/idmapping/fields`, the identifier types ID mapping accepts (the probe's question) | `4c3619c629aadd3b` |
| `insdc_001_job.json` | `POST /idmapping/run` with the 30 INSDC ids, from `EMBL-GenBank-DDBJ_CDS` to `UniProtKB` | `7429b3d6ae4b6939` |
| `insdc_001_status.json` | `GET /idmapping/status/8Pr33gbOw8`, redirects off: HTTP 303, finished | `796866f6f44dfffc` |
| `insdc_001_results.tsv` | `GET /idmapping/uniprotkb/results/stream/8Pr33gbOw8` as TSV, with the adapter's twelve fields | `3ef8900b75b506a5` |
| `refseq_001_job.json` | `POST /idmapping/run` with the five RefSeq ids, from `RefSeq_Protein` | `f9f3e237d31e32a6` |
| `refseq_001_status.json` | `GET /idmapping/status/sufWW4pG1o`, redirects off: HTTP 303, finished | `796866f6f44dfffc` |
| `refseq_001_results.tsv` | The RefSeq job's results, as TSV | `a41ddcf9a7c9c1c4` |
| `headers.json` | Not an answer: the status code and headers each file above arrived with, copied from the capture, so the fake server can answer `303` where UniProt did | |

(The two status answers are the same 24 bytes, `{"jobStatus":"FINISHED"}`,
so they share a fingerprint.)

**What the samples show.** UniProt was on release `2026_03` (published
02-September-2026). 18 of the 30 INSDC ids and 2 of the 5 RefSeq ids map; the
made-up id is among the 12 INSDC ids that don't, which come back with no row at
all. All nine surfactin genes map, each to an unreviewed entry: `CAE02630.1`
(srfAA) is `Q70KJ7`, "Surfactin synthetase A". Five of the twenty entries are
reviewed. The capture also showed that UniProt doesn't cross-reference MIBiG
(asking its list of databases for "mibig" returns nothing), which is why the
join goes through protein numbers.

**Two answers in the tests are made up:** a job that is still running
(`{"jobStatus": "RUNNING"}`) and one that failed (`{"jobStatus": "ERROR"}`).
Both real jobs had finished by the first check, so the capture never saw them.
The first follows the example in UniProt's documentation; the second has the
same shape with a different state. The tests that use them say so.

## `mibig/mibig_prot_seqs_sample.fasta` (Phase 3b)

The real file, `mibig_prot_seqs_4.0.fasta`, was downloaded on **2026-10-12** from
<https://dl.secondarymetabolites.org/mibig/> by
[`capture_mibig_protein_samples.py`](capture_mibig_protein_samples.py), which also
surveyed it against the MIBiG archive. Its SHA-256 is
`4b196343ed82d49f2b8f3babe89d512b92f0e026040fa50b15eeb97950717e8b` (31,833,799
bytes), the value pinned in `src/microbegraph/sources/mibig.py`.

The sample has 43 records:

| Records | Real or made up | Why it's there |
|---|---|---|
| 23 for `BGC0000433` (`CAE02619.1` to `CAE02641.1`) | **Real**, copied line for line from the file | Surfactin's whole cluster: 9 proteins with gene records and 14 without |
| `WP_999999901.1`, `TESTI_00020` to `TESTI_00050` in `BGC9999901` | Made up | The proteins of BGC9999901's Phase 3 gene records, by number and by locus tag |
| `TESTI_00060` > `XYZ99960.1` | Made up | A gene record named only by a locus tag gains a protein number |
| `XYZ99980.1` (`TstQ`); `XYZ99981.1` and `XYZ99982.1` (both `TstY`) | Made up | A gene name matching one product, and one matching two |
| `XYZ99990.1`; `XYZ99991.1` (`TstD`); `XYZ99992.1`, `XYZ99993.1` (`LOC999001` isoforms) | Made up | The curators' removals, by number, by product, by word in the product |
| `WP_999999970.1`, twice (`TESTI_00070`, `TESTI_00071`) | Made up | One protein at two positions in a cluster |
| `XYZ99970.1`, in `BGC9999901` and `BGC9999903` | Made up | One protein in two clusters |
| `ctg1_orf7` | Made up | A gene the curators added |
| `TESTI_00020` in `BGC9999903` | Made up | The same locus tag in another genome, with no number: a separate protein |
| `XYZ99902.1` in `BGC9999902` | Made up | A protein of an entry that isn't active, which the adapter leaves out |

The made-up sequences are strings of amino-acid letters made up for the tests;
they describe no real protein. The whole sample's SHA-256 is
`164bc6167da030215af65002935688b26b4989a64b50a06916529f10ab1d89f6`.

**Checking the real records.** With the real file in your locker (after
`python -m microbegraph.fetch --source mibig`), this compares surfactin's records
in the sample with the file:

```bash
python -c "real = open('data/raw/mibig/mibig_prot_seqs_4.0.fasta').read().split('\n'); i = [n for n, l in enumerate(real) if l.startswith('>BGC0000433.')]; sample = open('tests/fixtures/mibig/mibig_prot_seqs_sample.fasta').read().split('\n'); print(len(i), 'surfactin records, identical in the sample:', all(sample[2 * k: 2 * k + 2] == real[n: n + 2] for k, n in enumerate(i)))"
```

Expected: `23 surfactin records, identical in the sample: True`.

**What the real file showed** (the full survey is in
[`docs/05b-all-cluster-proteins.md`, Step 2](../../docs/05b-all-cluster-proteins.md#6-step-2-look-at-the-real-file-first)):
46,987 proteins in 2,636 entries (2,437 active, 199 pending), every header in one
seven-part shape, every gene added with `to_add` already present, and some genes
removed with `to_delete` still present.

## `mibig/genbank/` (Phase 4b)

The tests pack these three records into a `.tar.gz` of the same shape as MIBiG's
GenBank file, the way they do with the JSON samples.

| File | What it is | SHA-256 (first 16 characters) |
|---|---|---|
| `BGC0000433.gbk` | Surfactin's real record from `mibig_gbk_4.0.tar.gz`, cut down by `capture_gap_samples.py --fixture`: the header, the features the reader looks at and the CDS lines it uses. Lines are removed, never edited, so every line left is byte for byte the real one | `42a8fdddc14f0319` |
| `BGC9999901.gbk` | Made up, matching the made-up JSON entry and the protein file sample: CDS with and without gene names, locus tags and protein numbers, a gene named `LOC999001` with its NCBI gene number (`GeneID:999001`) on two isoforms, one protein number listed twice, and a CDS with no protein number | `c631f51a4bf94577` |
| `BGC9999903.gbk` | Made up: a second record sharing a locus tag (`TESTI_00020`) and a protein number with BGC9999901, so the tests can check that a name is looked up in its own entry | `c71a7664d45fe7f4` |

Two more cases, a `/gene_synonym` holding two names and a wrapped `/note` whose
second line starts with `/gene=` (which the reader must not take for a gene
name), are written inside the test that needs them,
`tests/test_closing_the_gaps.py`.

## `pubchem/name_search_*.json` (Phase 4b)

Two real answers from PubChem's name search
(`POST https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/cids/JSON`),
captured on **2026-10-12** by `capture_gap_samples.py`:

| File | The name that was asked | SHA-256 (first 16 characters) |
|---|---|---|
| `pubchem/name_search_found.json` | `1233A`: PubChem files it under CID 54144091 | `84f618383365e9e9` |
| `pubchem/name_search_not_found.json` | A name PubChem doesn't know: the real "No CID found" answer (HTTP 404) | `b4e8d861301a4d4b` |

## `resolve/` (Phase 4, extended in Phases 4b and 5)

A real slice of all six sources' staging tables, cut on **2026-10-12** by
[`capture_resolution_samples.py`](capture_resolution_samples.py), last from the
tables of the Phase 4b run (MIBiG read with its GenBank file). It holds the 18
files the resolver reads (`<source>_nodes.csv`, `<source>_edges.csv` and
`<source>_summary.json` for each source), plus, since Phase 4b, a `curation/`
folder with the two files the resolver reads from the project's own
`curation/`: the activity synonyms as they are, and the rows of the review file
whose two records are both in the slice (today all five). About 570 KB in all:
593 MIBiG nodes and 792 arrows, 304 UniProt entries, 112 NCBI Taxonomy nodes,
23 PubChem compounds, 5 KEGG pathways and the bridge's 5 nodes. Every arrow in
it points at a node in it. Three things differ from the originals, all on
purpose:

* the summaries keep only what the resolver reads (the source's version and
  date, and the lists of merged taxids, unknown PubChem numbers and curators'
  removals, cut to the slice);
* `mibig_compound_ids` on PubChem records and `mibig_protein_ids` on UniProt
  records list only identifiers in the slice;
* UniProt's `function` text is cut to its first sentence, because the resolver
  never reads it.

**Since Phase 5,** 243 of the slice's MIBiG proteins in `mibig_nodes.csv` also
carry `genbank_gene`, the gene name MIBiG's GenBank file gives them. It was
added to the same rows, value for value, from the MIBiG table re-tidied in
Phase 5, and written back with the project's own table writer; nothing else in
the slice changed. (Cutting the whole slice again from today's tables would
also bring in small changes from the Phase 4b follow-ups to the KEGG and
PubChem files, which the resolver tests were written against, so the slice was
extended rather than cut again.)

The slice is cut around these 34 clusters, each there for a case the resolver
must handle (the last 12 since Phase 4b):

| Cluster | What it is | The case it brings |
|---|---|---|
| `BGC0000433` | surfactin, *Bacillus velezensis* FZB42 | The worked example: srfAA joins UniProt entry Q70KJ7; surfactin against grey mould on jujube |
| `BGC0001089` | bacillaene, FZB42 | Gene records named only by a gene name (`baeB`, `baeJ`...); in Phase 4 joined through UniProt's gene names, since Phase 4b given their protein numbers by MIBiG's GenBank file |
| `BGC0001090` | bacillomycin D, FZB42 | A PubChem number that belongs to another molecule (Bacillomycin Fc): kept apart |
| `BGC0000054`, `BGC0000055` | erythromycin, erythromycin A | One PubChem number, both names confirmed: one node |
| `BGC0001952`, `BGC0001953` | minutissamides | One number given to minutissamides B and C, names not confirmed: kept apart |
| `BGC0000088`, `BGC0000098` | lovastatin, monacolin K | One NPAtlas number and one formula: one compound |
| `BGC0000094`, `BGC0000899` | methymycin, MIBiG's "desosamine" record | A record whose structure, numbers and formula are methymycin's |
| `BGC0002187` | monorden D and the monocillins | Two PubChem numbers PubChem doesn't have |
| `BGC0001600` | *Fusarium graminearum* | An organism that is also a crop pathogen |
| `BGC0000631` | *Botrytis cinerea* B05.10 | A strain below a pathogen in the family tree |
| `BGC0000519` | *Actinomadura namibiensis* | An organism number NCBI has merged into another (182080 into 46161) |
| `BGC0002180` | (+)-asperlin, *Aspergillus nidulans* FGSC A4 | A protein number with two equally good UniProt entries: kept apart |
| `BGC0000670` | thalianol, *Arabidopsis thaliana* | A protein number decided by sequence length; two numbers, one entry |
| `BGC0001865` | elsinochrome C, *Parastagonospora nodorum* SN15 | Protein numbers decided by review status |
| `BGC0002005` | RaxX, *Xanthomonas oryzae* pv. *oryzae* | A RefSeq "WP_" number with two UniProt entries, decided by the cluster's organism |
| `BGC0000546` | SAL-2242, *Streptomyces albidoflavus* | The same sequence listed twice in one cluster |
| `BGC0001238`, `BGC0001239` | two biotin clusters | One UniProt entry encoded by two clusters |
| `BGC0000657`, `BGC0000658` | 2-methylisoborneol | One entry gives a bromine compound's number, formula and structure, the other 16913: values kept by entry, and the wrong join kept apart by hand |
| `BGC0000898` | desosamine | An entry giving desosamine methymycin's number, formula and NPAtlas number: kept apart by hand from both |
| `BGC0002390` | zealexins, maize | Four genes the curators removed and gene records named `LOC...`, all placed through the GenBank file |
| `BGC0000038`, `BGC0000849` | two *Streptomyces coelicolor* entries | One protein (CAB60184.1) named SCO6265 by one entry and scbR by the other: a disagreement kept by entry |
| `BGC0001979`, `BGC0000028`, `BGC0000090`, `BGC0000224`, `BGC0000581`, `BGC0000185` | six clusters with the activity words that are folded | antitumor, its duplicate label and antineoplastic folded into anticancer; antibacterial (gram-negative) into anti-gram-negative |

Cases the real data doesn't contain (an arrow to nowhere, a KEGG arrow from a
PubChem record that gets left out, two sources stating one arrow) are added as
made-up rows inside the test that needs them, and the test says so.

The 20 files' SHA-256, taken together in path order, is
`039a1f709833ebf2442214f9270c654498b8c8b3c1e8b58243182cd935340b0f` (it was
`50e4eb19...c1ef8a47f` before Phase 5 added `genbank_gene`). To check it:

```bash
python -c "import hashlib, pathlib; h = hashlib.sha256(); [h.update(p.read_bytes()) for p in sorted(pathlib.Path('tests/fixtures/resolve').rglob('*')) if p.is_file()]; print(h.hexdigest())"
```

Cutting the slice again from the tables it was cut from gives the same bytes,
apart from the `genbank_gene` values Phase 5 added.

## The 3D check (Phase 4c)

No new files here. `tests/test_3d_check.py` writes its made-up records in the
test itself: threonine in three of its four 3D arrangements, plus a drawing
that describes only one of its two centres and a flat one (and alanine,
butane-2,3-diol and crotonic acid for the comparison alone), under names and
numbers no compound has (tau to omega, sigma and rho, CIDs 41 to 113). The one
real pair is saxitoxin's two PubChem records, 37165 and 56947150, two
tautomers, whose SMILES the test copies from PubChem's answers in Phase 4b's
run.

`survey_3d_detail.py`, beside the capture scripts, is the look at the real data
that came before the Phase 4c rules ([`docs/06c-checking-3d-detail.md`, Step 2](../../docs/06c-checking-3d-detail.md#6-step-2-look-at-the-real-data-first)).
It captures nothing: it reads the ledger and two staging tables on your
computer, compares every same-skeleton pair in two ways (both start from
RDKit's reading of the SMILES, then use different code) and prints what it
found. It imports `stereo.py`, so that file has to be in place first.

## The graph analytics (Phase 5)

`tests/test_graph_analytics.py` resolves and builds the slice above once and
runs the analytics on it (its three crops are jujube, maize and wheat). The
ranking rules and a few awkward cases need paths the slice doesn't have, so
those tests build small graphs inside the test, with made-up identifiers
(`o:a`, `c:1`, `k:crop`) that belong to nothing real. The GenBank gene names are
checked on surfactin's real record in `mibig/genbank/BGC0000433.gbk` (srfAA's
and yciC's `/gene`).

`survey_graph_shape.py`, beside the capture scripts, is the look at the graph
that came before the Phase 5 code ([`docs/07-graph-analytics.md`, Step 2](../../docs/07-graph-analytics.md#6-step-2-look-at-the-graph-first)).
It captures nothing: it reads the database read-only and MIBiG's GenBank file
on your computer, and prints the graph's shape, the shortest route from jujube,
the typed route's paths, betweenness two ways, communities with and without the
labels and in one randomly rewired copy (seed 1), and what the proteins are
called. It imports the new analytics
package, so Phase 5's files have to be in place first.

## Refreshing the samples

If a source changes its format, run the capture again (after Phase 1, with
`.venv` active):

```bash
python tests/fixtures/capture_samples.py                 # PubChem, NCBI Taxonomy, KEGG
python tests/fixtures/capture_uniprot_samples.py         # MIBiG's gene records and UniProt
python tests/fixtures/capture_mibig_protein_samples.py   # MIBiG's protein file
python tests/fixtures/capture_resolution_samples.py      # the resolver's slice (Phase 4)
python tests/fixtures/capture_gap_samples.py --fixture   # surfactin's GenBank record (Phase 4b)
```

The new answers land in `data/samples/<date>/`, which never goes to GitHub.
The last one is different: it writes straight into `tests/fixtures/resolve/`,
because it cuts its slice from your own staging tables rather than asking a
server. Run `git diff --stat tests/fixtures/resolve` afterwards to see what
changed.
Copy over the ones that changed, update the table above with the new date and
fingerprints, and run `pytest`. A failing test then shows exactly what the
source changed.
