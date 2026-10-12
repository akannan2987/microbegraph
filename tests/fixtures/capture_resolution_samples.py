"""
MicrobeGraph, cut a small, real slice out of the staging tables (Phase 4;
more clusters and the curation files from Phase 4b).

WHY THIS EXISTS
    The resolver's tests need staging tables shaped exactly like the real
    ones, with the real awkward cases in them: a PubChem number that points
    at the wrong molecule, two compounds sharing one number, a protein number
    with several UniProt entries, an organism that is also a pathogen. The
    full tables are 40 MB and never go to GitHub, so this script cuts out the
    rows around a list of chosen gene clusters and writes them to
    tests/fixtures/resolve/, about 300 KB in all.

    The cut is self-contained: every arrow in the slice points at a node in
    the slice, so each table passes the twelve rules on its own, like the
    originals do.

THE CHOSEN CLUSTERS, AND WHAT EACH ONE IS THERE FOR
    BGC0000433  surfactin, the worked example in every guide
    BGC0001089  bacillaene: gene records named only by a gene name (baeB...)
    BGC0001090  bacillomycin D: a PubChem number that points at another molecule
    BGC0000054, BGC0000055  erythromycin and erythromycin A: one number, both
                names confirmed
    BGC0001952, BGC0001953  minutissamides B and C: one number, names not
                confirmed (isomers)
    BGC0000088, BGC0000098  lovastatin and monacolin K: one NPAtlas number,
                one formula
    BGC0000094, BGC0000899  methymycin and MIBiG's "desosamine" record
    BGC0002187  monocillins VI and VII: numbers PubChem doesn't have
    BGC0001600  Fusarium graminearum, a producer that is also a pathogen
    BGC0000631  a Botrytis cinerea strain, below a pathogen in the family tree
    BGC0000519  an organism number NCBI has merged into another
    BGC0002180  a protein number with two equally good UniProt entries
    BGC0000670  protein numbers decided by length, and two numbers, one entry
    BGC0001865  a protein number decided by review status
    BGC0002005  a protein number decided by organism
    BGC0000546  the same sequence listed twice in one cluster
    BGC0001238, BGC0001239  one UniProt entry encoded by two clusters

    From Phase 4b:
    BGC0000657, BGC0000658  2-methylisoborneol: one entry gives a bromine
                compound's number, formula and structure, another 16913
    BGC0000898  desosamine with methymycin's number, formula and NPAtlas number
    BGC0002390  maize: four genes the curators removed and gene records named
                LOC..., all placed through the GenBank file
    BGC0000038, BGC0000849  one protein (CAB60184.1) named SCO6265 by one entry
                and scbR by the other
    BGC0001979, BGC0000028, BGC0000090, BGC0000224, BGC0000581, BGC0000185
                the activity words folded by curation/activity_synonyms.csv

    The slice also gets its own curation/ folder: the activity synonyms as
    they are, and the rows of curation/resolution_decisions.csv whose two
    records are both in the slice.

USAGE (from the project folder, with .venv active, after Phases 1 to 3b)
    python tests/fixtures/capture_resolution_samples.py --survey
        prints what the real tables say about duplicates, without writing
        anything: the look at the data that shaped every rule in Phase 4
        (docs/06-entity-resolution-graph-build.md, Step 2)
    python tests/fixtures/capture_resolution_samples.py
        writes the slice to tests/fixtures/resolve/

    Both read data/processed/staging/ and need no network.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microbegraph.paths import CURATION_DIR, STAGING_DIR, relative_to_repo
from microbegraph.resolution.names import compare_formulas
from microbegraph.sources.base import EDGE_COLUMNS, NODE_COLUMNS, write_table

OUT = Path(__file__).resolve().parent / "resolve"
SOURCES = ("mibig", "pubchem", "ncbi_taxonomy", "kegg", "uniprot", "curation")

CLUSTERS = (
    "BGC0000433", "BGC0001089", "BGC0001090", "BGC0000054", "BGC0000055", "BGC0001952",
    "BGC0001953", "BGC0000088", "BGC0000098", "BGC0000094", "BGC0000899", "BGC0002187",
    "BGC0001600", "BGC0000631", "BGC0000519", "BGC0002180", "BGC0000670", "BGC0001865",
    "BGC0002005", "BGC0000546", "BGC0001238", "BGC0001239",
    # Phase 4b
    "BGC0000657", "BGC0000658", "BGC0000898", "BGC0002390", "BGC0000038", "BGC0000849",
    "BGC0001979", "BGC0000028", "BGC0000090", "BGC0000224", "BGC0000581", "BGC0000185",
)


def rows(source: str, kind: str) -> list[dict[str, str]]:
    path = STAGING_DIR / f"{source}_{kind}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def keep_listed(row: dict[str, str], key: str, kept: set[str]) -> dict[str, str]:
    """A copy of a node row whose pipe-separated property `key` lists only kept ids."""
    props = json.loads(row["properties"] or "{}")
    props[key] = "|".join(i for i in str(props.get(key, "")).split("|") if i in kept)
    return {**row, "properties": json.dumps(props, sort_keys=True, ensure_ascii=False)}


def shorten_function(row: dict[str, str]) -> dict[str, str]:
    """
    UniProt's function text cut to its first sentence. The resolver never
    reads it, and the full paragraphs would make up most of the fixture.
    """
    props = json.loads(row["properties"] or "{}")
    if props.get("function"):
        props["function"] = str(props["function"]).split(". ")[0][:160].rstrip(".") + "."
    return {**row, "properties": json.dumps(props, sort_keys=True, ensure_ascii=False)}


def survey() -> None:
    """Count the duplicates and disagreements the resolver has to deal with."""
    nodes = {s: rows(s, "nodes") for s in SOURCES}
    props = {s: {r["node_id"]: json.loads(r["properties"] or "{}") for r in nodes[s]}
             for s in SOURCES}
    names = {s: {r["node_id"]: r["name"] for r in nodes[s]} for s in SOURCES}

    def show(label: str, value: object) -> None:
        print(f"  {label:<58} {value:>8}" if isinstance(value, str) else
              f"  {label:<58} {value:>8,}")

    print("Identifiers")
    sources_of: dict[str, set[str]] = defaultdict(set)
    for source in SOURCES:
        for row in nodes[source]:
            sources_of[row["node_id"]].add(source)
    show("identifiers in the six tables", len(sources_of))
    show("  ...that more than one source describes", sum(len(v) > 1 for v in sources_of.values()))

    print("Organisms")
    taxonomy = json.loads((STAGING_DIR / "ncbi_taxonomy_summary.json").read_text("utf-8"))
    mibig_organisms = [r["node_id"] for r in nodes["mibig"] if r["node_type"] == "Organism"]
    show("MIBiG organisms", len(mibig_organisms))
    show("  ...whose number NCBI has merged into another", len(taxonomy["merged_taxids"]))
    show("  ...that NCBI names differently today",
         sum(1 for i in mibig_organisms if i in names["ncbi_taxonomy"]
             and names["ncbi_taxonomy"][i] != names["mibig"][i]))
    show("organisms that are also crop pathogens", len(taxonomy["pathogens_also_organisms"]))

    print("Compounds")
    with_cid = {i: str(p["pubchem_cid"]) for i, p in props["mibig"].items()
                if i.startswith("mg.compound:") and p.get("pubchem_cid")}
    show("MIBiG compounds", sum(i.startswith("mg.compound:") for i in props["mibig"]))
    show("  ...that give a PubChem number", len(with_cid))
    pubchem_by_cid = {str(p["pubchem_cid"]): i for i, p in props["pubchem"].items()}
    states: Counter[str] = Counter()
    for mibig_id, cid in with_cid.items():
        if cid not in pubchem_by_cid:
            states["number PubChem doesn't have"] += 1
            continue
        theirs = props["pubchem"][pubchem_by_cid[cid]].get("formula")
        states[compare_formulas(props["mibig"][mibig_id].get("formula"), theirs)] += 1
    for word, label in (("agrees", "the formulas agree"),
                        ("agrees_but_charge", "they agree once the charge is ignored"),
                        ("differs", "the formulas differ"),
                        ("missing", "MIBiG gives no formula to compare"),
                        ("number PubChem doesn't have", "PubChem doesn't have the number")):
        show(f"    {label}", states[word])
    shared = Counter(with_cid.values())
    show("  PubChem numbers given to more than one MIBiG compound",
         sum(n > 1 for n in shared.values()))
    npatlas: Counter[str] = Counter(ref for i, p in props["mibig"].items()
                                    if i.startswith("mg.compound:")
                                    for ref in str(p.get("database_ids", "")).split("|")
                                    if ref.startswith("npatlas:"))
    show("  NPAtlas numbers given to more than one MIBiG compound",
         sum(n > 1 for n in npatlas.values()))

    print("Proteins")
    entries_of: dict[str, list[str]] = defaultdict(list)
    for entry, p in props["uniprot"].items():
        for number in str(p.get("mibig_protein_ids", "")).split("|"):
            if number:
                entries_of[number].append(entry)
    show("protein numbers UniProt found", len(entries_of))
    show("  ...with exactly one entry", sum(len(v) == 1 for v in entries_of.values()))
    show("  ...with several entries", sum(len(v) > 1 for v in entries_of.values()))
    show("UniProt entries reached from several numbers",
         sum(len(str(p.get("mibig_protein_ids", "")).split("|")) > 1
             for p in props["uniprot"].values()))
    md5s: Counter[str] = Counter(p["sequence_md5"] for p in props["mibig"].values()
                                 if p.get("sequence_md5"))
    show("sequences shared by more than one MIBiG protein record",
         sum(n > 1 for n in md5s.values()))
    show("gene records MIBiG's protein file doesn't name",
         sum(1 for i, p in props["mibig"].items()
             if i.startswith("mg.protein:") and p.get("found_in") == "gene_records"))


def main() -> int:
    if not (STAGING_DIR / "mibig_nodes.csv").exists():
        print(f"{relative_to_repo(STAGING_DIR)} has no MIBiG tables yet. Run Phases 1 to 3b "
              f"first: python -m microbegraph.fetch --all")
        return 1
    if "--survey" in sys.argv[1:]:
        survey()
        return 0
    clusters = {f"mibig:{c}" for c in CLUSTERS}

    # --- MIBiG: the clusters and everything they point at, and their organisms
    mibig_edges = rows("mibig", "edges")
    ids = set(clusters)
    for edge in mibig_edges:              # organisms, compounds and proteins of the clusters
        if edge["source_id"] in clusters or edge["target_id"] in clusters:
            ids |= {edge["source_id"], edge["target_id"]}
    for edge in mibig_edges:              # the compounds' activities and classes
        if edge["edge_type"] in ("HAS_ACTIVITY", "BELONGS_TO") and edge["source_id"] in ids:
            ids.add(edge["target_id"])
    mibig_edges_out = [e for e in mibig_edges if e["source_id"] in ids and e["target_id"] in ids]
    mibig_nodes_out = [n for n in rows("mibig", "nodes") if n["node_id"] in ids]

    # --- PubChem and KEGG: the PubChem records MIBiG's kept compounds point at
    def linked(row: dict[str, str]) -> bool:
        props = json.loads(row["properties"])
        return bool((set(props.get("mibig_compound_ids", "").split("|"))
                     | set(props.get("found_by_name", "").split("|"))) & ids)

    pubchem = [keep_listed(keep_listed(n, "mibig_compound_ids", ids), "found_by_name", ids)
               for n in rows("pubchem", "nodes") if linked(n)]
    pubchem_ids = {n["node_id"] for n in pubchem}
    kegg_edges = [e for e in rows("kegg", "edges") if e["source_id"] in pubchem_ids]
    kegg_nodes = [n for n in rows("kegg", "nodes")
                  if n["node_id"] in {e["target_id"] for e in kegg_edges}]

    # --- UniProt: the entries found through the kept protein numbers
    uniprot = [n for n in rows("uniprot", "nodes")
               if set(json.loads(n["properties"]).get("mibig_protein_ids", "").split("|")) & ids]
    uniprot = [shorten_function(keep_listed(n, "mibig_protein_ids", ids)) for n in uniprot]

    # --- the curated bridge: rows about kept compounds, their pathogens and crops
    bridge_edges = [e for e in rows("curation", "edges") if e["source_id"] in ids]
    pathogens = {e["target_id"] for e in bridge_edges}
    bridge_edges += [e for e in rows("curation", "edges")
                     if e["edge_type"] == "INFECTS" and e["source_id"] in pathogens]
    bridge_ids = pathogens | {e["target_id"] for e in bridge_edges}
    bridge_nodes = [n for n in rows("curation", "nodes") if n["node_id"] in bridge_ids]

    # --- NCBI Taxonomy: the organisms and pathogens kept, and their family trees
    taxonomy_summary = json.loads((STAGING_DIR / "ncbi_taxonomy_summary.json")
                                  .read_text(encoding="utf-8"))
    merged = taxonomy_summary.get("merged_taxids", {})
    organisms = {i for i in ids if i.startswith("ncbitaxon:")} | pathogens
    organisms |= {f"ncbitaxon:{merged[i.split(':')[1]]}" for i in organisms
                  if i.split(":")[1] in merged}
    tax_edges_all = rows("ncbi_taxonomy", "edges")
    parent = {e["source_id"]: e["target_id"] for e in tax_edges_all}
    climbing = set(organisms)
    for start in list(organisms):
        node = start
        while node in parent:
            node = parent[node]
            climbing.add(node)
    tax_nodes = [n for n in rows("ncbi_taxonomy", "nodes") if n["node_id"] in climbing]
    tax_edges = [e for e in tax_edges_all if e["source_id"] in climbing]

    # --- write the slice, and summaries carrying only what the resolver reads
    tables = {
        "mibig": (mibig_nodes_out, mibig_edges_out),
        "pubchem": (pubchem, []),
        "ncbi_taxonomy": (tax_nodes, tax_edges),
        "kegg": (kegg_nodes, kegg_edges),
        "uniprot": (uniprot, []),
        "curation": (bridge_nodes, bridge_edges),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for source, (nodes, edges) in tables.items():
        write_table(OUT / f"{source}_nodes.csv", NODE_COLUMNS,
                    sorted(nodes, key=lambda r: (r["node_type"], r["node_id"])))
        write_table(OUT / f"{source}_edges.csv", EDGE_COLUMNS,
                    sorted(edges, key=lambda r: (r["edge_type"], r["source_id"], r["target_id"])))
        full = json.loads((STAGING_DIR / f"{source}_summary.json").read_text(encoding="utf-8"))
        summary: dict[str, Any] = {k: full[k] for k in
                                   ("source", "source_version", "retrieved_at", "snapshot")
                                   if k in full}
        summary["counts"] = {"nodes": len(nodes), "edges": len(edges)}
        if source == "ncbi_taxonomy":
            summary["merged_taxids"] = {o: n for o, n in merged.items()
                                        if f"ncbitaxon:{o}" in ids}
        if source == "pubchem":
            cids = {str(json.loads(n["properties"]).get("pubchem_cid", ""))
                    for n in mibig_nodes_out if n["node_type"] == "Compound"}
            summary["cids_not_in_pubchem"] = [c for c in full.get("cids_not_in_pubchem", [])
                                              if str(c) in cids]
        if source == "mibig":
            summary["to_delete_not_found"] = [r for r in full.get("to_delete_not_found", [])
                                              if f"mibig:{r.get('entry', '')}" in clusters]
        (OUT / f"{source}_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  {source:<14} {len(nodes):>4} nodes {len(edges):>4} edges")

    # --- Phase 4b: the curation files, cut to the slice
    in_slice = {n["node_id"] for nodes, _ in tables.values() for n in nodes}
    (OUT / "curation").mkdir(exist_ok=True)
    synonyms = (CURATION_DIR / "activity_synonyms.csv").read_text(encoding="utf-8")
    (OUT / "curation" / "activity_synonyms.csv").write_text(synonyms, encoding="utf-8")
    with (CURATION_DIR / "resolution_decisions.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        decisions = [r for r in reader
                     if {r["identifier"], r["other_identifier"]} <= in_slice]
        write_table(OUT / "curation" / "resolution_decisions.csv", reader.fieldnames or [],
                    decisions)
    print(f"  curation/      {len(decisions)} decisions by hand, the activity synonyms")
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {relative_to_repo(OUT)}/ ({total / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
