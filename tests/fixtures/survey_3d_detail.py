"""
MicrobeGraph, a look at the 3D detail of same-structure pairs (Phase 4c, Step 2).

USAGE (from the repository root, with .venv active)

    python tests/fixtures/survey_3d_detail.py

    Offline. It reads three files your computer already has:
        data/processed/resolution_ledger.csv        which pairs clue 2 looked at
        data/processed/staging/pubchem_nodes.csv    each PubChem record's SMILES
        data/processed/staging/mibig_nodes.csv      MIBiG's own structures
    and prints what docs/06c-checking-3d-detail.md, Step 2, reports. It finds
    the pairs by the phrase every clue 2 sentence contains ("both InChIKeys
    start"), whatever was decided, so it works before and after the Phase 4c
    resolver has run. The one difference: after it, echinomycin is decided
    in the review file (curation/resolution_decisions.csv), clue 2 no longer
    looks at it, and the survey finds 183 pairs instead of 184.

WHAT IT DOES
    1. Finds every ledger row that compares a number MIBiG gives with the
       record PubChem files the name under, the two sharing a skeleton.
    2. Sorts the pairs by their second InChIKey block (the 3D part): the same,
       one of them flat (UHFFFAOYSA, no 3D detail), or both 3D and different.
    3. Compares the two records' 3D detail in two ways and checks that they
       agree. Both start from RDKit's reading of the SMILES; after that they
       use different code:
         a. stereo.py: match the atoms, then compare how each place is
            arranged through the match
         b. InChI: RDKit writes each record as an InChI string, whose /t, /m
            and /b layers list every described place by atom number
    4. For each pair that differs, asks MIBiG's own structure which record
       it matches (with the InChI method, so this is a check on the resolver
       too, which uses stereo.py).

    Nothing is written anywhere.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from rdkit import Chem, RDLogger  # noqa: E402

from microbegraph.resolution import stereo  # noqa: E402

RDLogger.DisableLog("rdApp.*")
LEDGER = ROOT / "data" / "processed" / "resolution_ledger.csv"
STAGING = ROOT / "data" / "processed" / "staging"
FLAT = "UHFFFAOYSA"          # the second block of a structure drawn without 3D detail
TWIN = re.compile(r"files it under CID (\d+), (?:the same molecule|a record with the same skeleton)")


def read_nodes(name: str) -> dict[str, dict]:
    """node_id -> its properties, from one staging table."""
    with (STAGING / name).open(newline="", encoding="utf-8") as handle:
        return {row["node_id"]: json.loads(row["properties"]) for row in csv.DictReader(handle)}


def inchi_places(smiles: str) -> tuple[str, dict[str, str]] | None:
    """
    The first InChIKey block and every described place, from RDKit's InChI:
    "t12" -> "+" for a chiral centre, "b10-9" -> "-" for a double bond.
    The /m layer says the /t signs are written for the mirror image, so
    they are flipped back. "?" (described as unknown) counts as open.
    """
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return None
    layers: dict[str, str] = {}
    for part in Chem.MolToInchi(mol).split("/")[1:]:
        layers.setdefault(part[0], part[1:])
    flip = layers.get("m") == "1"
    places = {}
    for kind in ("t", "b"):
        for item in filter(None, layers.get(kind, "").split(",")):
            sign = item[-1]
            if kind == "t" and flip and sign in "+-":
                sign = "-" if sign == "+" else "+"
            if sign != "?":
                places[kind + item[:-1]] = sign
    return Chem.MolToInchiKey(mol).split("-")[0], places


def inchi_verdict(first: tuple | None, second: tuple | None) -> str:
    if first is None or second is None:
        return "unreadable"
    if first[0] != second[0]:
        return "other skeleton"
    shared = first[1].keys() & second[1].keys()
    return "differ" if any(first[1][k] != second[1][k] for k in shared) else "agree"


def mibig_side(structures: list[str], given: str, twin: str) -> str:
    """Which record MIBiG's own structures match: given, twin, or why they can't tell."""
    if not structures:
        return "MIBiG gives no structure"
    g, t = inchi_places(given), inchi_places(twin)
    sides, found = set(), set()
    for smiles in structures:
        mine = inchi_places(smiles)
        if mine is None:
            found.add("unreadable")
        elif g is None or mine[0] != g[0]:
            found.add("another skeleton")
        elif not mine[1]:
            found.add("no 3D detail")
        else:
            sides.add((inchi_verdict(mine, g), inchi_verdict(mine, t)))
    decisive = {s for s in sides if s != ("agree", "agree")}
    if decisive == {("agree", "differ")}:
        return "matches MIBiG's number"
    if decisive == {("differ", "agree")}:
        return "matches the name's record"
    if len(decisive) > 1:
        return "can't decide: MIBiG's entries disagree"
    if decisive == {("differ", "differ")}:
        return "can't decide: differs from both"
    if sides == {("agree", "agree")}:
        return "can't decide: agrees with both"
    return "can't decide: " + sorted(found)[0]


def main() -> int:
    if not LEDGER.is_file():
        print(f"{LEDGER.relative_to(ROOT)} isn't there yet. Run python -m microbegraph.resolve first.")
        return 1
    pubchem = read_nodes("pubchem_nodes.csv")
    mibig = read_nodes("mibig_nodes.csv")
    with LEDGER.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if "both InChIKeys start" in r["grounds"]]

    kinds, methods, sides, examples = Counter(), Counter(), Counter(), {}
    for row in rows:
        given, twin = row["compared_with"], f"pubchem.compound:{TWIN.search(row['grounds']).group(1)}"
        g, t = pubchem[given], pubchem[twin]
        block_g = (g.get("inchikey", "").split("-") + [""])[1]
        block_t = (t.get("inchikey", "").split("-") + [""])[1]
        kind = ("the same second block" if block_g == block_t else
                "MIBiG's number drawn flat" if block_g == FLAT else
                "the name's record drawn flat" if block_t == FLAT else
                "both 3D, and different")
        kinds[kind] += 1
        first = stereo.compare(g.get("smiles", ""), t.get("smiles", "")).status
        second = inchi_verdict(inchi_places(g.get("smiles", "")), inchi_places(t.get("smiles", "")))
        methods[(first, second)] += 1
        if first == "differ":
            props = mibig[row["identifier"]]
            structures = [item.partition(": ")[2] for item in
                          filter(None, (props.get("smiles_by_entry") or "").split("|"))]
            structures = structures or ([props["smiles"]] if props.get("smiles") else [])
            side = mibig_side(structures, g.get("smiles", ""), t.get("smiles", ""))
            sides[side] += 1
            examples.setdefault(side, row["identifier"].split(":", 1)[1])

    print("Part 1: pairs of records with one skeleton, in the ledger")
    print(f"    {'pairs':<36} {len(rows)}")
    for kind, n in kinds.most_common():
        print(f"    {kind:<36} {n}")
    print("Part 2: their 3D detail, compared place by place in two ways")
    for (first, second), n in sorted(methods.items()):
        same = "the methods agree" if first == second else "THE METHODS DISAGREE"
        print(f"    stereo.py {first:<8} InChI {second:<8} {n:>4}   {same}")
    print("Part 3: for the pairs that differ, what MIBiG's own structure matches")
    for side, n in sorted(sides.items(), key=lambda item: (-item[1], item[0])):
        print(f"    {side:<44} {n:>3}   (e.g. {examples[side]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
