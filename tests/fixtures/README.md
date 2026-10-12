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
| `BGC0000433.json` | A real MIBiG 4.0 entry (surfactin), trimmed: its gene annotations and biosynthesis modules are removed because the adapter never reads them. Every field the adapter reads is unchanged. Its own `comment` field says so. |
| `BGC9999901.json` | Made up, describing nothing real. It covers what the surfactin entry doesn't: two compounds, a negative result, activity names in both of MIBiG's styles, a curator's comment, a PubChem number, a Greek letter in a name. |
| `BGC9999902.json` | Made up: a retired entry, which the adapter must skip. |
| `BGC9999903.json` | Made up: an entry whose only evidence is a prediction, so its arrows must be `database_assertion`. |

The made-up entries use numbers from 9999901 up, which MIBiG doesn't use, and
a DOI prefix (10.0000) that belongs to no publisher. Each one says so in its
own `comment` field.

## `pubchem/`, `ncbi_taxonomy/`, `kegg/` (Phase 2)

Captured on **2026-10-12** by [`capture_samples.py`](capture_samples.py),
which asks each source a few small questions and saves the answers exactly as
they arrived. The files below are those answers, renamed to the names the
adapters give them in a snapshot. Each fingerprint (SHA-256) is the one
`capture_samples.py` recorded when the answer arrived, so you can confirm
nothing was edited:

```bash
# macOS and Linux (Windows PowerShell: Get-FileHash <file> -Algorithm SHA256)
shasum -a 256 tests/fixtures/pubchem/* tests/fixtures/ncbi_taxonomy/* tests/fixtures/kegg/*
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

## Refreshing the samples

If a source changes its format, run the capture again (after Phase 1, with
`.venv` active):

```bash
python tests/fixtures/capture_samples.py
```

The new answers land in `data/samples/<date>/`, which never goes to GitHub.
Copy over the ones that changed, update the table above with the new date and
fingerprints, and run `pytest`. A failing test then shows exactly what the
source changed.
