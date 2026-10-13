"""
Tests for Phase 4c, the 3D check of same-structure joins.

The first half tests resolution/stereo.py on small molecules whose 3D
arrangement is easy to check by hand: alanine, threonine, butane-2,3-diol and
crotonic acid. The second half runs the resolver on MADE-UP compounds, each
shaped like a real case the survey found (docs/06c-checking-3d-detail.md,
Step 2): MIBiG's own structure keeping its number (A-201A's shape),
moving to the record PubChem names (macbecin II's), being unable to decide
(nocardicin A's), and one number of two settling a tie (kosinostatin's).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import read_rows
from rdkit import Chem

from microbegraph.resolution import stereo
from microbegraph.resolve import resolve, three_d_report
from microbegraph.sources.base import EDGE_COLUMNS, NODE_COLUMNS, write_table

# Threonine has two chiral centres, so it comes in four arrangements.
THR = "C[C@@H](O)[C@H](N)C(=O)O"            # (2S,3R), the one in proteins
ALLO_THR = "C[C@H](O)[C@H](N)C(=O)O"        # (2S,3S): one centre differs
D_THR = "C[C@H](O)[C@@H](N)C(=O)O"          # (2R,3S): the mirror image
FLAT_THR = "CC(O)C(N)C(=O)O"                # no 3D detail at all
L_ALA = "C[C@H](N)C(=O)O"
D_ALA = "C[C@@H](N)C(=O)O"


# ------------------------------------------------------------------ comparing two drawings
def test_the_same_drawing_agrees_everywhere():
    check = stereo.compare(THR, THR)
    assert (check.status, check.same_centres, check.only_first, check.only_second) == \
        ("agree", 2, 0, 0)


def test_a_drawing_with_no_3d_detail_agrees_with_anything():
    check = stereo.compare(L_ALA, "CC(N)C(=O)O")
    assert check.agrees
    assert (check.same, check.only_first, check.only_second) == (0, 1, 0)


def test_one_centre_drawn_the_other_way_is_a_difference():
    check = stereo.compare(L_ALA, D_ALA)
    assert (check.status, check.differing_centres, check.same) == ("differ", 1, 0)


def test_an_epimer_differs_at_one_centre_and_agrees_at_the_other():
    check = stereo.compare(THR, ALLO_THR)
    assert (check.status, check.same_centres, check.differing_centres) == ("differ", 1, 1)


def test_a_mirror_image_differs_at_every_centre():
    check = stereo.compare(THR, D_THR)
    assert (check.status, check.same, check.differing_centres) == ("differ", 0, 2)


def test_a_double_bond_drawn_e_and_z_is_a_difference():
    check = stereo.compare("C/C=C/C(=O)O", "C/C=C\\C(=O)O")
    assert (check.status, check.differing_bonds, check.differing_centres) == ("differ", 1, 0)


def test_writing_the_atoms_in_another_order_changes_nothing():
    # (R,R)-butane-2,3-diol, written from either end
    check = stereo.compare("C[C@@H](O)[C@@H](C)O", "O[C@H](C)[C@H](O)C")
    assert (check.status, check.same_centres) == ("agree", 2)


def test_symmetry_never_invents_a_difference():
    # Butane-2,3-diol has two centres that can swap places. Each drawing
    # describes one of them; matched the right way round, they agree.
    check = stereo.compare("C[C@@H](O)C(C)O", "CC(O)[C@@H](C)O")
    assert check.agrees


def test_two_diastereomers_of_a_symmetric_molecule_still_differ():
    # (R,R) against meso (R,S): no way of matching makes both centres agree
    check = stereo.compare("C[C@@H](O)[C@@H](C)O", "C[C@@H](O)[C@H](C)O")
    assert (check.status, check.same_centres, check.differing_centres) == ("differ", 1, 1)


def test_a_tautomer_is_matched_atom_for_atom():
    # Saxitoxin as PubChem draws it in two records: a hydrogen sits on a
    # different nitrogen, which is the same molecule
    first = "C1CN2C(=N[C@H]([C@H]3[C@]2(C1(O)O)N=C(N3)N)COC(=O)N)N"
    second = "C1CN2C(=N[C@H]([C@H]3[C@]2(C1(O)O)NC(=N3)N)COC(=O)N)N"
    check = stereo.compare(first, second)
    assert (check.status, check.same_centres) == ("agree", 3)


def test_a_tautomer_whose_names_change_still_agrees():
    # Moving the hydrogen changes how the naming rules rank the centre's
    # neighbours, and with it the name R or S, though nothing moved in space.
    # The comparison looks at the arrangement itself, so the two agree.
    check = stereo.compare("C[C@@H](N(C)C)NC(C)=NC", "C[C@@H](N(C)C)N=C(C)NC")
    assert (check.status, check.same_centres) == ("agree", 1)


def test_a_ketone_carbon_is_never_matched_with_a_chiral_centre():
    # Without hydrogen counts on carbons, the C=O carbon and the CH(OH) centre
    # of this ring look alike, and the mirror image could match its centre to
    # the ketone and seem to agree.
    first = "C1[C@@H](CC(=O)C2=C(C=C(C=C21)O)O)O"
    mirror = "C1[C@H](CC(=O)C2=C(C=C(C=C21)O)O)O"
    check = stereo.compare(first, mirror)
    assert (check.status, check.differing_centres) == ("differ", 1)


@pytest.mark.parametrize("smiles", [THR, ALLO_THR, "C/C=C/C(=O)O",
                                    "C[C@@H](O)[C@@H](C)O", "O=C(O)/C=C/[C@H](N)C"])
def test_the_order_atoms_are_written_in_never_matters(smiles):
    mol = Chem.MolFromSmiles(smiles)
    places = stereo.described(smiles)
    for other in Chem.MolToRandomSmilesVect(mol, 10, randomSeed=42):
        check = stereo.compare(smiles, other)
        assert (check.status, check.same, check.only_first, check.only_second) == \
            ("agree", places, 0, 0), other


def test_a_deuterium_label_does_not_stop_the_match():
    assert stereo.compare("[2H]CC[C@H](N)C(=O)O", "CC[C@H](N)C(=O)O").agrees


@pytest.mark.parametrize(("first", "second", "status"), [
    ("not a smiles", "CC", "unreadable"),
    ("", "CC", "unreadable"),
    ("CCO", "CCN", "other skeleton"),
    ("CCO", "CCCO", "other skeleton"),
])
def test_what_cannot_be_compared_says_why(first, second, status):
    assert stereo.compare(first, second).status == status


def test_a_molecule_with_too_many_symmetric_matches_is_not_guessed(monkeypatch):
    monkeypatch.setattr(stereo, "MAX_FITS", 2)
    check = stereo.compare("C[C@@H](O)[C@@H](C)O", "C[C@@H](O)[C@@H](C)O")
    assert check.status == "too symmetric"


def test_the_skeleton_key_is_the_first_inchikey_block():
    assert stereo.skeleton_key(L_ALA) == "QNAYBMKLOCPYGJ"
    assert stereo.skeleton_key("not a smiles") == ""


def test_described_counts_the_places_a_drawing_gives():
    assert stereo.described(THR) == 2
    assert stereo.described(FLAT_THR) == 0
    assert stereo.described("C/C=C/C(=O)O") == 1
    assert stereo.described("not a smiles") is None


# ------------------------------------------------------------------ the resolver, made up
DATE = "2026-10-13"
SOURCES = ("mibig", "pubchem", "ncbi_taxonomy", "kegg", "uniprot", "curation")


def node(node_id: str, node_type: str, name: str, source: str, **props) -> dict:
    return {"node_id": node_id, "node_type": node_type, "name": name,
            "properties": json.dumps(props), "source": source, "retrieved_at": DATE}


def compound(slug: str, name: str, **props) -> dict:
    return node(f"mg.compound:{slug}", "Compound", name, "mibig", formula="C4H9NO3", **props)


def pubchem(cid: int, title: str, smiles: str, **props) -> dict:
    key = Chem.MolToInchiKey(Chem.MolFromSmiles(smiles)) if smiles else "AYFVYJQAPQTCCC-X-N"
    return node(f"pubchem.compound:{cid}", "Compound", title, "pubchem", pubchem_cid=cid,
                formula="C4H9NO3", inchikey=key, smiles=smiles, **props)


def three_d_staging(folder: Path) -> Path:
    """
    Eight made-up compounds, each with the numbers MIBiG gives and a record
    PubChem's name search found, all threonine with different 3D detail:
      tau      MIBiG's structure matches its own number      (A-201A's shape)
      upsilon  MIBiG's structure matches the name's record   (macbecin II's shape)
      phi      MIBiG's structure gives no 3D detail          (nocardicin A's shape)
      chi      MIBiG gives no structure at all
      psi      one record has no SMILES, so nothing can be compared
      omega    two numbers: one agrees with the name's record, one differs and
               MIBiG's structure can't decide                (kosinostatin's shape)
      sigma    two numbers, one of them the record PubChem names (clue 1); the
               other differs from it, and MIBiG's structure is flat
      rho      two numbers: one agrees with the name's record, the other differs
               from it, and MIBiG's structure matches the name's record
    """
    folder.mkdir(parents=True, exist_ok=True)
    mibig = [
        node("mibig:BGC0000001", "GeneCluster", "test BGC", "mibig"),
        compound("tau", "tau", pubchem_cid="41", smiles=THR),
        compound("upsilon", "upsilon", pubchem_cid="51", smiles=ALLO_THR),
        compound("phi", "phi", pubchem_cid="61", smiles=FLAT_THR),
        compound("chi", "chi", pubchem_cid="71"),
        compound("psi", "psi", pubchem_cid="81", smiles=THR),
        compound("omega", "omega", pubchem_cid="91", smiles=FLAT_THR,
                 pubchem_cid_by_entry="BGC0000001: 91|BGC0000002: 92"),
        compound("sigma", "sigma", pubchem_cid="101", smiles=FLAT_THR,
                 pubchem_cid_by_entry="BGC0000001: 101|BGC0000002: 102"),
        compound("rho", "rho", pubchem_cid="111", smiles=ALLO_THR,
                 pubchem_cid_by_entry="BGC0000001: 111|BGC0000002: 112"),
    ]
    edges = [{"source_id": "mibig:BGC0000001", "target_id": r["node_id"],
              "edge_type": "PRODUCES", "evidence_level": "database_assertion",
              "source": "mibig", "source_record_id": "BGC0000001", "citation": "",
              "confidence": "0.95", "retrieved_at": DATE}
             for r in mibig if r["node_id"].startswith("mg.compound:")]
    pubchem_rows = [
        pubchem(41, "(2S,3R)-something", THR, mibig_compound_ids="mg.compound:tau"),
        pubchem(42, "Tau", ALLO_THR, found_by_name="mg.compound:tau"),
        pubchem(51, "(2S,3R)-something else", THR, mibig_compound_ids="mg.compound:upsilon"),
        pubchem(52, "Upsilon", ALLO_THR, found_by_name="mg.compound:upsilon"),
        pubchem(61, "(2S,3R)-a third", THR, mibig_compound_ids="mg.compound:phi"),
        pubchem(62, "Phi", D_THR, found_by_name="mg.compound:phi"),
        pubchem(71, "(2S,3R)-a fourth", THR, mibig_compound_ids="mg.compound:chi"),
        pubchem(72, "Chi", ALLO_THR, found_by_name="mg.compound:chi"),
        pubchem(81, "(2S,3R)-a fifth", THR, mibig_compound_ids="mg.compound:psi"),
        pubchem(82, "Psi", "", found_by_name="mg.compound:psi"),
        pubchem(91, "(2S,3R)-a sixth", THR, mibig_compound_ids="mg.compound:omega"),
        pubchem(92, "(2S,3S)-a seventh", ALLO_THR, mibig_compound_ids="mg.compound:omega"),
        pubchem(93, "Omega", FLAT_THR.replace("CC(O)", "C[C@@H](O)"),
                found_by_name="mg.compound:omega"),
        pubchem(101, "Sigma", THR, mibig_compound_ids="mg.compound:sigma",
                found_by_name="mg.compound:sigma"),
        pubchem(102, "(2S,3S)-an eighth", ALLO_THR, mibig_compound_ids="mg.compound:sigma"),
        pubchem(111, "(3S)-a ninth", "C[C@H](O)C(N)C(=O)O", mibig_compound_ids="mg.compound:rho"),
        pubchem(112, "(2S,3R)-a tenth", THR, mibig_compound_ids="mg.compound:rho"),
        pubchem(113, "Rho", ALLO_THR, found_by_name="mg.compound:rho"),
    ]
    tables = {s: ([], []) for s in SOURCES}
    tables["mibig"] = (mibig, edges)
    tables["pubchem"] = (pubchem_rows, [])
    for source, (nodes, source_edges) in tables.items():
        write_table(folder / f"{source}_nodes.csv", NODE_COLUMNS, nodes)
        write_table(folder / f"{source}_edges.csv", EDGE_COLUMNS, source_edges)
        summary = {"source_version": "test", "retrieved_at": DATE}
        if source == "pubchem":
            summary["cids_not_in_pubchem"] = []
            summary["name_search_complete"] = True
        (folder / f"{source}_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


@pytest.fixture
def three_d(tmp_path):
    result = resolve(three_d_staging(tmp_path / "staging"), tmp_path / "out",
                     tmp_path / "no-curation")
    nodes = {r["node_id"]: r for r in read_rows(result.nodes_path)}
    return result, nodes, read_rows(result.ledger_path)


def _row(ledger: list[dict], identifier: str, compared_with: str) -> dict:
    [found] = [r for r in ledger if r["identifier"] == identifier
               and r["compared_with"] == compared_with]
    return found


def test_mibig_structure_keeps_its_own_number(three_d):
    _, nodes, ledger = three_d
    row = _row(ledger, "mg.compound:tau", "pubchem.compound:41")
    assert (row["rule"], row["decision"]) == ("pubchem_number_confirmed", "merged")
    assert "that differs in 3D at 1 chiral centre" in row["grounds"]
    assert "MIBiG's own structure matches CID 41, so the number MIBiG gives stands" in row["grounds"]
    assert row["grounds"].endswith(
        "Confirmed through the same skeleton and MIBiG's own 3D structure.")
    named = _row(ledger, "mg.compound:tau", "pubchem.compound:42")
    assert named["decision"] == "kept_apart"
    assert "CID 41 is better supported" in named["grounds"]
    assert "pubchem.compound:42" not in nodes


def test_mibig_structure_moves_the_compound_to_the_named_record(three_d):
    _, nodes, ledger = three_d
    given = _row(ledger, "mg.compound:upsilon", "pubchem.compound:51")
    assert given["decision"] == "kept_apart"
    assert "so this record is another stereoisomer" in given["grounds"]
    assert "CID 52 is better supported" in given["grounds"]
    named = _row(ledger, "mg.compound:upsilon", "pubchem.compound:52")
    assert (named["rule"], named["decision"]) == ("pubchem_name_search", "merged")
    assert named["grounds"].endswith("Confirmed by name and by MIBiG's own 3D structure.")
    assert nodes["pubchem.compound:52"]["name"] == "upsilon"
    props = json.loads(nodes["pubchem.compound:52"]["properties"])
    assert props["pubchem_cid_not_confirmed"] == "51"     # MIBiG's number, not confirmed


@pytest.mark.parametrize(("slug", "given", "named", "reason"), [
    ("phi", 61, 62, "MIBiG's own structure gives no 3D detail"),
    ("chi", 71, 72, "MIBiG gives no structure of its own"),
])
def test_when_mibig_structure_cannot_decide_neither_record_joins(three_d, slug, given, named,
                                                                  reason):
    _, nodes, ledger = three_d
    for cid in (given, named):
        row = _row(ledger, f"mg.compound:{slug}", f"pubchem.compound:{cid}")
        assert row["decision"] == "kept_apart"
        assert reason in row["grounds"]
        assert "so a person should decide between them" in row["grounds"]
        assert f"pubchem.compound:{cid}" not in nodes
    props = json.loads(nodes[f"mg.compound:{slug}"]["properties"])
    assert props["pubchem_cid_not_confirmed"] == str(given)


def test_a_record_without_smiles_cannot_be_compared(three_d):
    _, nodes, ledger = three_d
    row = _row(ledger, "mg.compound:psi", "pubchem.compound:81")
    assert row["decision"] == "kept_apart"
    assert "can't be compared in 3D (one of the two records has no SMILES" in row["grounds"]
    assert "mg.compound:psi" in nodes and "pubchem.compound:81" not in nodes


def test_the_number_that_agrees_settles_a_tie(three_d):
    _, nodes, ledger = three_d
    agrees = _row(ledger, "mg.compound:omega", "pubchem.compound:91")
    assert (agrees["rule"], agrees["decision"]) == ("pubchem_numbers_differ", "merged")
    assert "their 3D detail agrees at the 1 place both describe" in agrees["grounds"]
    differs = _row(ledger, "mg.compound:omega", "pubchem.compound:92")
    assert differs["decision"] == "kept_apart"
    assert "that differs in 3D at 1 chiral centre" in differs["grounds"]
    # a person isn't asked to decide what the other number already settled
    assert "a person should decide" not in differs["grounds"]
    assert "CID 91 is better supported" in differs["grounds"]
    named = _row(ledger, "mg.compound:omega", "pubchem.compound:93")
    assert "a person should decide" not in named["grounds"]


def test_a_number_pubchem_names_is_never_overruled_by_another_numbers_check(three_d):
    _, nodes, ledger = three_d
    row = _row(ledger, "mg.compound:sigma", "pubchem.compound:101")
    assert row["decision"] == "merged"
    assert row["grounds"].endswith("Confirmed by name.")
    assert nodes["pubchem.compound:101"]["name"] == "sigma"


def test_a_number_that_agrees_wins_over_a_move_to_the_same_record(three_d):
    _, nodes, ledger = three_d
    agrees = _row(ledger, "mg.compound:rho", "pubchem.compound:111")
    assert (agrees["rule"], agrees["decision"]) == ("pubchem_numbers_differ", "merged")
    moved = _row(ledger, "mg.compound:rho", "pubchem.compound:112")
    assert moved["decision"] == "kept_apart"
    assert "so this record is another stereoisomer" in moved["grounds"]
    assert "pubchem.compound:113" not in nodes


def test_the_summary_counts_the_check_and_lists_who_waits(three_d):
    result, _, _ = three_d
    check = result.summary["same_structure_3d_check"]
    assert check == {"pairs_checked": 10, "agree": 2, "differ": 7, "not_compared": 1,
                     "mibig_structure_keeps_the_number": 1,
                     "mibig_structure_moves_to_the_name": 2,
                     "mibig_structure_cannot_decide": 4, "compounds_left_for_a_person": 3}
    # omega's other number joined, so omega isn't waiting for anyone
    assert result.summary["still_open"]["same_structure_3d_for_a_person"] == [
        "mg.compound:chi", "mg.compound:phi", "mg.compound:psi"]


def test_the_report_says_what_the_check_did(three_d):
    result, _, _ = three_d
    assert three_d_report(result.summary).splitlines() == [
        "[resolve] 3D check of same-structure joins: 10 pairs, 2 agree, 7 differ",
        "  MIBiG's own structure keeps the number 1, moves to the name's record 2, "
        "can't decide 4",
        "  1 couldn't be compared in 3D",
        "  3 compounds are left without a PubChem record, for a person to decide",
    ]
