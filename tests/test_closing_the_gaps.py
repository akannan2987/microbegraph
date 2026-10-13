"""
Tests for Phase 4b, closing the gaps: the PubChem rules with every number and
the name search, the review file, the activity synonyms, the GenBank file in
the MIBiG adapter, and the housekeeping fix for the circular import.

The resolver cases below are MADE UP, each shaped like a real case the
survey found (docs/06b-closing-the-gaps.md, Step 2), so every rule can be
tested on its own. The real cases (2-methylisoborneol, desosamine, baeI...)
are in the real slice that tests/test_resolve.py uses.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import build_archive, genbank_file_bytes, read_rows

from microbegraph.resolution.activities import read_synonyms
from microbegraph.resolution.groups import Groups
from microbegraph.resolution.reviewed import read_decisions
from microbegraph.resolve import report, resolve
from microbegraph.sources.base import EDGE_COLUMNS, NODE_COLUMNS, SourceError, write_table
from microbegraph.sources.mibig import GENBANK_FILE
from microbegraph.sources.mibig_genbank import find_in_genbank, read_cds

SOURCES = ("mibig", "pubchem", "ncbi_taxonomy", "kegg", "uniprot", "curation")
DATE = "2026-10-12"


# ------------------------------------------------------------------ a tiny made-up graph
def node(node_id: str, node_type: str, name: str, source: str, **props) -> dict:
    return {"node_id": node_id, "node_type": node_type, "name": name,
            "properties": json.dumps(props), "source": source, "retrieved_at": DATE}


def edge(start: str, end: str, edge_type: str, source: str = "mibig", record: str = "BGC0000001",
         level: str = "database_assertion") -> dict:
    return {"source_id": start, "target_id": end, "edge_type": edge_type,
            "evidence_level": level, "source": source, "source_record_id": record,
            "citation": "", "confidence": "0.95", "retrieved_at": DATE}


def compound(slug: str, name: str, **props) -> dict:
    return node(f"mg.compound:{slug}", "Compound", name, "mibig", **props)


def pubchem(cid: int, title: str, formula: str, inchikey: str = "", **props) -> dict:
    return node(f"pubchem.compound:{cid}", "Compound", title, "pubchem", pubchem_cid=cid,
                formula=formula, inchikey=inchikey, **props)


def made_up_staging(folder: Path) -> Path:
    """
    Eight made-up compound cases, an NPAtlas pair whose formula is disputed,
    and three activity words, with one cluster producing every compound.
    """
    mibig = [
        node("mibig:BGC0000001", "GeneCluster", "test BGC", "mibig"),
        # 1. clue 1: MIBiG's number lists the name
        compound("alpha", "alpha", pubchem_cid="1", formula="C1H2"),
        # 2. clue 2: the name is filed under another record of the same structure
        compound("beta", "beta", pubchem_cid="2", formula="C2H4"),
        # 3. the formula agrees, but the name search points at another molecule
        compound("gamma", "gamma", pubchem_cid="4", formula="C4H8"),
        # 4. clue 3: no number; the name search finds one and the formula agrees
        compound("delta", "delta", formula="C9H9"),
        # 5. two entries give two numbers (2-methylisoborneol's shape)
        compound("epsilon", "epsilon", pubchem_cid="7", formula="C15H16BrN3O4S",
                 pubchem_cid_by_entry="BGC0000001: 7|BGC0000002: 8|BGC0000003: 8",
                 formula_by_entry="BGC0000001: C15H16BrN3O4S|BGC0000002: C11H20O|"
                                  "BGC0000003: C11H20O"),
        # 6. one number, two MIBiG compounds (the minutissamides' shape)
        compound("zeta-a", "zeta A", pubchem_cid="9", formula="C5H5"),
        compound("zeta-b", "zeta B", pubchem_cid="9", formula="C5H5"),
        # 7. clue 4: the formula alone, and nothing points elsewhere
        compound("eta", "eta", pubchem_cid="10", formula="C6H6"),
        # 8. an NPAtlas pair whose first formula one entry got wrong (desosamine's shape)
        compound("theta", "theta", formula="C25H43NO7", database_ids="npatlas:NPA000001",
                 formula_by_entry="BGC0000001: C25H43NO7|BGC0000002: C8H17NO3"),
        compound("iota", "iota", formula="C25H43NO7", database_ids="npatlas:NPA000001"),
        # 8b. one number, two formulas from two entries (ferrichrome's shape)
        compound("mu", "mu", pubchem_cid="13", formula="C26H43N9O12",
                 formula_by_entry="BGC0000001: C26H43N9O12|BGC0000002: C27H42FeN9O12"),
        # 9. a pair a person keeps apart, and one a person joins
        compound("kappa", "kappa", pubchem_cid="11", formula="C7H7"),
        compound("lambda", "lambda", formula="C3H3"),
        # activities
        node("mg.activity:anticancer", "Activity", "anticancer", "mibig"),
        node("mg.activity:antitumor", "Activity", "antitumor", "mibig"),
        node("mg.activity:antineoplastic", "Activity", "antineoplastic", "mibig"),
    ]
    mibig_edges = [edge("mibig:BGC0000001", r["node_id"], "PRODUCES")
                   for r in mibig if r["node_id"].startswith("mg.compound:")]
    mibig_edges += [edge("mg.compound:alpha", f"mg.activity:{a}", "HAS_ACTIVITY")
                    for a in ("anticancer", "antitumor", "antineoplastic")]
    pubchem_rows = [
        pubchem(1, "Alpha", "C1H2", "AAAAAAAAAAAAAA-AAAAAAAAAA-N", mibig_compound_ids="mg.compound:alpha"),
        # (Phase 4c) record 2 gives one chiral centre, record 3 none: they agree in 3D
        pubchem(2, "(2S)-something", "C2H4", "BBBBBBBBBBBBBB-BBBBBBBBBB-N",
                mibig_compound_ids="mg.compound:beta", smiles="C[C@H](N)C(=O)O"),
        pubchem(3, "Beta", "C2H4", "BBBBBBBBBBBBBB-CCCCCCCCCC-N", found_by_name="mg.compound:beta",
                smiles="CC(N)C(=O)O"),
        pubchem(4, "a gamma look-alike", "C4H8", "DDDDDDDDDDDDDD-DDDDDDDDDD-N",
                mibig_compound_ids="mg.compound:gamma"),
        pubchem(5, "Gamma", "C10H20", "EEEEEEEEEEEEEE-EEEEEEEEEE-N",
                found_by_name="mg.compound:gamma"),
        pubchem(6, "Delta", "C9H9", "FFFFFFFFFFFFFF-FFFFFFFFFF-N", found_by_name="mg.compound:delta"),
        pubchem(7, "a bromine compound", "C15H16BrN3O4S", "GGGGGGGGGGGGGG-GGGGGGGGGG-N",
                mibig_compound_ids="mg.compound:epsilon"),
        pubchem(8, "Epsilon", "C11H20O", "HHHHHHHHHHHHHH-HHHHHHHHHH-N",
                mibig_compound_ids="mg.compound:epsilon"),
        pubchem(9, "Zeta B", "C5H5", "IIIIIIIIIIIIII-IIIIIIIIII-N",
                mibig_compound_ids="mg.compound:zeta-a|mg.compound:zeta-b"),
        pubchem(10, "a long systematic name", "C6H6", "JJJJJJJJJJJJJJ-JJJJJJJJJJ-N",
                mibig_compound_ids="mg.compound:eta"),
        pubchem(11, "Kappa", "C7H7", "KKKKKKKKKKKKKK-KKKKKKKKKK-N",
                mibig_compound_ids="mg.compound:kappa"),
        pubchem(12, "Lambda", "C3H3", "LLLLLLLLLLLLLL-LLLLLLLLLL-N"),
        pubchem(13, "[55Fe] Mu", "C27H42FeN9O12", "MMMMMMMMMMMMMM-MMMMMMMMMM-N",
                mibig_compound_ids="mg.compound:mu"),
    ]
    tables = {s: ([], []) for s in SOURCES}
    tables["mibig"] = (mibig, mibig_edges)
    tables["pubchem"] = (pubchem_rows, [])
    for source, (nodes, edges) in tables.items():
        write_table(folder / f"{source}_nodes.csv", NODE_COLUMNS, nodes)
        write_table(folder / f"{source}_edges.csv", EDGE_COLUMNS, edges)
        summary = {"source_version": "test", "retrieved_at": DATE}
        if source == "pubchem":
            summary["cids_not_in_pubchem"] = []
            summary["name_search_complete"] = True       # a Phase 4b fetch
        (folder / f"{source}_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


SYNONYMS = ("activity,same_as,reason,citation,added_on\n"
            "antitumor,anticancer,MIBiG says so.,doi:10.5281/zenodo.14169073,2026-10-12\n"
            "antineoplastic,anticancer,Same meaning.,mesh:D000970,2026-10-12\n"
            "antiwhatever,anticancer,A word the data doesn't use yet.,mesh:D000970,2026-10-12\n")
DECISIONS = ("identifier,other_identifier,decision,reason,citation,decided_on\n"
             "mg.compound:kappa,pubchem.compound:11,keep_apart,The paper says otherwise.,"
             "doi:10.1000/test.1,2026-10-12\n"
             "mg.compound:lambda,pubchem.compound:12,join,The paper names CID 12.,"
             "doi:10.1000/test.2,2026-10-12\n")


class Run:
    def __init__(self, tmp_path: Path, synonyms: str = SYNONYMS, decisions: str = DECISIONS):
        staging = made_up_staging(tmp_path / "staging")
        staging.mkdir(exist_ok=True)
        curation = tmp_path / "curation"
        curation.mkdir()
        (curation / "activity_synonyms.csv").write_text(synonyms, encoding="utf-8")
        (curation / "resolution_decisions.csv").write_text(decisions, encoding="utf-8")
        self.result = resolve(staging, tmp_path / "out", curation)
        self.nodes = {r["node_id"]: r for r in read_rows(self.result.nodes_path)}
        self.ledger = read_rows(self.result.ledger_path)
        self.edges = read_rows(self.result.edges_path)

    def row(self, identifier: str, compared_with: str) -> dict:
        [found] = [r for r in self.ledger if r["identifier"] == identifier
                   and r["compared_with"] == compared_with]
        return found

    def props(self, node_id: str) -> dict:
        return json.loads(self.nodes[node_id]["properties"])


@pytest.fixture
def run(tmp_path):
    (tmp_path / "staging").mkdir()
    return Run(tmp_path)


# ------------------------------------------------------------------- the PubChem rules
def test_a_number_that_lists_the_name_joins(run):
    row = run.row("mg.compound:alpha", "pubchem.compound:1")
    assert (row["rule"], row["decision"]) == ("pubchem_number_confirmed", "merged")
    assert row["grounds"].endswith("Confirmed by name.")


def test_the_name_under_another_record_of_the_same_structure_confirms_the_number(run):
    row = run.row("mg.compound:beta", "pubchem.compound:2")
    assert row["decision"] == "merged"
    assert "files it under CID 3, the same molecule drawn another way" in row["grounds"]
    assert "CID 3 describes no place in 3D, so nothing can disagree" in row["grounds"]
    assert row["grounds"].endswith("Confirmed by name, through the same structure.")
    other = run.row("mg.compound:beta", "pubchem.compound:3")
    assert (other["rule"], other["decision"]) == ("pubchem_name_search", "kept_apart")
    assert "CID 2 is better supported" in other["grounds"]


def test_a_name_filed_under_another_molecule_withdraws_the_formula_only_join(run):
    row = run.row("mg.compound:gamma", "pubchem.compound:4")
    assert row["decision"] == "kept_apart"
    assert "files it under CID 5, a different molecule" in row["grounds"]
    assert "pubchem.compound:4" not in run.nodes and "pubchem.compound:5" not in run.nodes
    assert run.props("mg.compound:gamma")["pubchem_cid_not_confirmed"] == "4"


def test_the_name_search_joins_a_compound_without_a_number_when_the_formula_agrees(run):
    row = run.row("mg.compound:delta", "pubchem.compound:6")
    assert (row["rule"], row["decision"]) == ("pubchem_name_search", "merged")
    assert row["node_id"] == "pubchem.compound:6"
    assert run.nodes["pubchem.compound:6"]["name"] == "delta"


def test_when_entries_give_two_numbers_the_named_one_joins(run):
    right = run.row("mg.compound:epsilon", "pubchem.compound:8")
    wrong = run.row("mg.compound:epsilon", "pubchem.compound:7")
    assert (right["rule"], right["decision"]) == ("pubchem_numbers_differ", "merged")
    assert "BGC0000002, BGC0000003 give CID 8" in right["grounds"]
    assert wrong["decision"] == "kept_apart"
    node = run.props("pubchem.compound:8")
    assert node["pubchem_cid"] == 8 and node["pubchem_cid_not_confirmed"] == "7"
    assert node["formula_by_entry"].startswith("BGC0000001: C15H16BrN3O4S")


def test_a_shared_number_still_needs_each_name(run):
    assert run.row("mg.compound:zeta-b", "pubchem.compound:9")["decision"] == "merged"
    row = run.row("mg.compound:zeta-a", "pubchem.compound:9")
    assert (row["rule"], row["decision"]) == ("pubchem_number_shared", "kept_apart")


def test_the_formula_alone_still_joins_when_nothing_points_elsewhere(run):
    row = run.row("mg.compound:eta", "pubchem.compound:10")
    assert row["decision"] == "merged"
    assert row["grounds"].endswith("Confirmed by the formula alone.")
    assert run.result.summary["still_open"]["pubchem_joins_on_the_formula_alone"] == 1


def test_a_formula_the_entries_disagree_about_confirms_nothing(run):
    row = run.row("mg.compound:mu", "pubchem.compound:13")
    assert row["decision"] == "kept_apart"
    assert "different formulas (C26H43N9O12, C27H42FeN9O12)" in row["grounds"]


def test_without_a_name_search_the_ledger_does_not_claim_one(tmp_path):
    (tmp_path / "staging").mkdir()
    staging = made_up_staging(tmp_path / "staging")
    summary = json.loads((staging / "pubchem_summary.json").read_text(encoding="utf-8"))
    del summary["name_search_complete"]                  # a Phase 2 fetch
    (staging / "pubchem_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    curation = tmp_path / "curation"
    curation.mkdir()
    result = resolve(staging, tmp_path / "out", curation)
    [row] = [r for r in read_rows(result.ledger_path) if r["identifier"] == "mg.compound:eta"]
    assert row["decision"] == "merged" and "name search" not in row["grounds"]


def test_a_name_the_search_never_reached_gets_no_claim_about_it(tmp_path):
    (tmp_path / "staging").mkdir()
    staging = made_up_staging(tmp_path / "staging")
    summary = json.loads((staging / "pubchem_summary.json").read_text(encoding="utf-8"))
    summary["name_search_complete"] = False              # PubChem stopped halfway
    summary["names_not_asked"] = ["mg.compound:eta"]
    (staging / "pubchem_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    curation = tmp_path / "curation"
    curation.mkdir()
    result = resolve(staging, tmp_path / "out", curation)
    [row] = [r for r in read_rows(result.ledger_path) if r["identifier"] == "mg.compound:eta"]
    assert row["decision"] == "merged" and "name search" not in row["grounds"]


def test_a_disputed_formula_never_confirms_an_npatlas_pair(run):
    [row] = [r for r in run.ledger if r["rule"] == "npatlas_and_formula"]
    assert row["decision"] == "kept_apart"
    assert "disagree about the formula of 'theta'" in row["grounds"]
    assert "mg.compound:theta" in run.nodes and "mg.compound:iota" in run.nodes


# -------------------------------------------------------------------- the review file
def test_a_decision_by_hand_wins_over_the_rules(run):
    row = run.row("mg.compound:kappa", "pubchem.compound:11")
    assert (row["rule"], row["decision"]) == ("reviewed_by_hand", "kept_apart")
    assert "Decided by hand on 2026-10-12" in row["grounds"]
    assert "doi:10.1000/test.1" in row["grounds"]
    # no rule row for that pair, though the name is listed and the formula agrees
    assert [r["rule"] for r in run.ledger if r["identifier"] == "mg.compound:kappa"] == [
        "reviewed_by_hand"]
    assert run.props("mg.compound:kappa")["pubchem_cid_not_confirmed"] == "11"


def test_a_join_by_hand_is_made_and_recorded(run):
    row = run.row("mg.compound:lambda", "pubchem.compound:12")
    assert (row["rule"], row["decision"]) == ("reviewed_by_hand", "merged")
    assert row["node_id"] == "pubchem.compound:12"


def test_a_pair_kept_apart_by_hand_can_never_meet_through_a_chain():
    groups = Groups()
    groups.forbid("mg.compound:a", "mg.compound:c")
    groups.join("mg.compound:a", "mg.compound:b")
    assert not groups.can_join("mg.compound:b", "mg.compound:c")
    with pytest.raises(ValueError, match="kept apart"):
        groups.join("mg.compound:c", "mg.compound:b")


@pytest.mark.parametrize("line, message", [
    ("mg.compound:a,pubchem.compound:1,merge,r,doi:1,2026-10-12", "join or keep_apart"),
    ("mg.compound:a,pubchem.compound:1,join,,doi:1,2026-10-12", "reason is empty"),
    ("mg.compound:a,16913,join,r,doi:1,2026-10-12", "isn't an identifier"),
    ("mg.compound:a,pubchem.compound:1,join,r,doi:1,12/10/2026", "YYYY-MM-DD"),
])
def test_a_bad_review_row_is_refused_with_its_line(tmp_path, line, message):
    path = tmp_path / "decisions.csv"
    path.write_text("identifier,other_identifier,decision,reason,citation,decided_on\n"
                    f"{line}\n", encoding="utf-8")
    with pytest.raises(SourceError, match=message):
        read_decisions(path)


def test_a_review_row_naming_a_record_nobody_has_stops_the_run(tmp_path):
    (tmp_path / "staging").mkdir()
    bad = DECISIONS + ("mg.compound:nosuch,pubchem.compound:1,join,r,doi:10.1/x,2026-10-12\n")
    with pytest.raises(SourceError, match="no source has mg.compound:nosuch"):
        Run(tmp_path, decisions=bad)


def test_keeping_apart_a_pair_a_row_above_joined_stops_the_run(tmp_path):
    (tmp_path / "staging").mkdir()
    # lambda joins CID 12 (in DECISIONS) and mu joins lambda, so mu and 12 are one group
    bad = DECISIONS + ("mg.compound:mu,mg.compound:lambda,join,r,doi:10.1/x,2026-10-12\n"
                       "mg.compound:mu,pubchem.compound:12,keep_apart,r,doi:10.1/x,2026-10-12\n")
    with pytest.raises(SourceError, match="already one group"):
        Run(tmp_path, decisions=bad)


def test_the_real_review_file_reads_cleanly():
    decisions = read_decisions()
    assert decisions, "curation/resolution_decisions.csv should hold the first decisions"
    assert all(d.citation and d.reason for d in decisions)


# ------------------------------------------------------------------ the activity synonyms
def test_activity_words_that_mean_the_same_become_one_node(run):
    assert "mg.activity:antitumor" not in run.nodes
    assert "mg.activity:antineoplastic" not in run.nodes
    node = run.props("mg.activity:anticancer")
    assert set(node["other_names"].split("|")) == {"antitumor", "antineoplastic"}
    arrows = [(e["source_id"], e["target_id"]) for e in run.edges
              if e["edge_type"] == "HAS_ACTIVITY"]
    # alpha joined PubChem's record 1, and its three arrows became one
    assert arrows == [("pubchem.compound:1", "mg.activity:anticancer")]
    row = run.row("mg.activity:antitumor", "mg.activity:anticancer")
    assert (row["rule"], row["decision"]) == ("activity_synonym", "merged")
    assert run.result.summary["curation"]["activity_synonyms_not_applied"] == ["antiwhatever"]


@pytest.mark.parametrize("rows, message", [
    ("anticancer,anticancer,r,c,2026-10-12\n", "mapped to itself"),
    ("antitumor,anticancer,r,c,2026-10-12\nantitumor,cytotoxic,r,c,2026-10-12\n",
     "already listed"),
    ("antitumor,anticancer,r,c,2026-10-12\nanticancer,cytotoxic,r,c,2026-10-12\n", "point both"),
])
def test_a_bad_synonym_row_is_refused(tmp_path, rows, message):
    path = tmp_path / "synonyms.csv"
    path.write_text("activity,same_as,reason,citation,added_on\n" + rows, encoding="utf-8")
    with pytest.raises(SourceError, match=message):
        read_synonyms(path)


def test_the_real_synonym_file_reads_cleanly():
    rows = read_synonyms()
    assert {r.same_as for r in rows} <= {"anticancer", "anti-gram-negative"}


# ------------------------------------------------------------- the GenBank file (MIBiG)
GENBANK_TSTY = b"""LOCUS       BGC9999901
FEATURES             Location/Qualifiers
     CDS             10501..11100
                     /gene="tstY"
                     /product="TstY"
                     /protein_id="XYZ99981.1"
     CDS             11201..11800
                     /gene="tstZ"
                     /product="TstY"
                     /protein_id="XYZ99982.1"
ORIGIN
//
"""


def test_the_genbank_file_places_a_gene_record_the_protein_file_cannot(make_adapter, tmp_path):
    archive = tmp_path / "raw" / "mibig" / "mibig_json_4.0.tar.gz"
    build_archive(archive)
    (archive.parent / GENBANK_FILE).write_bytes(genbank_file_bytes({"BGC9999901.gbk": GENBANK_TSTY}))
    result = make_adapter().tidy()
    summary = json.loads((tmp_path / "staging" / "mibig_summary.json").read_text("utf-8"))
    assert result.counts["genes_found_by_genbank"] == 1
    assert summary["genes_not_in_protein_file"] == []
    nodes = {r["node_id"]: json.loads(r["properties"])
             for r in read_rows(result.nodes_path) if r["node_type"] == "Protein"}
    assert nodes["ncbiprotein:XYZ99981.1"]["gene_record_id"] == "tstY"
    # and the curators' removal of "tstZ", which no other list names
    assert result.counts["removals_found_by_genbank"] == 1
    assert [(r["to_delete"], r["protein"], r["matched_by"]) for r in summary["removed_by_curators"]
            if r["matched_by"] == "genbank"] == [("tstZ", "XYZ99982.1", "genbank")]
    assert "ncbiprotein:XYZ99982.1" not in nodes


def test_without_the_genbank_file_the_tidy_says_what_to_run(make_adapter, tmp_path):
    archive = tmp_path / "raw" / "mibig" / "mibig_json_4.0.tar.gz"
    build_archive(archive)
    (archive.parent / GENBANK_FILE).unlink()
    with pytest.raises(SourceError, match="only the GenBank file is downloaded"):
        make_adapter().tidy()


def test_every_gene_name_uniprot_lists_is_read():
    from microbegraph.resolution.proteins import gene_names
    # Q1RS74 (baeI) as the UniProt adapter stores it: names joined with "|"
    assert gene_names("baeI|PV946_13250") == {"baei", "pv946_13250"}
    assert gene_names("srfAA") == {"srfaa"}
    assert gene_names("") == set()


def test_an_ncbi_gene_name_matches_its_gene_number():
    cds = read_cds('''FEATURES             Location/Qualifiers
     CDS             1..300
                     /protein_id="NP_001140431.1"
                     /db_xref="GeneID:100272490"
ORIGIN
''', "BGC0002390")
    assert find_in_genbank("LOC100272490", cds) == ["NP_001140431.1"]
    assert find_in_genbank("loc100272490", cds) == ["NP_001140431.1"]
    assert find_in_genbank("LOC1", cds) == []


def test_a_wrapped_value_is_never_read_as_a_name_and_synonyms_are_split():
    # A quoted value can wrap onto the next line. Here a note's second line
    # happens to start with "/gene=", which must stay part of the note.
    cds = read_cds('''FEATURES             Location/Qualifiers
     CDS             1..300
                     /gene="abcA"
                     /gene_synonym="abc1; orfA"
                     /note="the name used in the first paper was
                     /gene=xyz, later changed"
                     /protein_id="XYZ00001.1"
ORIGIN
''', "BGC9999901")
    assert find_in_genbank("abc1", cds) == ["XYZ00001.1"]
    assert find_in_genbank("orfA", cds) == ["XYZ00001.1"]
    assert find_in_genbank("xyz", cds) == []


def test_the_surfactin_sample_is_read_like_the_real_file():
    sample = Path(__file__).parent / "fixtures" / "mibig" / "genbank" / "BGC0000433.gbk"
    cds = read_cds(sample.read_text(encoding="utf-8"), "BGC0000433")
    assert len(cds) == 23                                  # the cluster's 23 proteins
    assert find_in_genbank("srfAA", cds) == ["CAE02630.1"]


def test_mibig_keeps_every_value_when_entries_disagree(make_adapter, tmp_path):
    from microbegraph.sources.mibig import _GraphBuilder
    builder = _GraphBuilder(DATE)
    base = {"status": "active", "taxonomy": {"name": "x", "ncbiTaxId": 1}, "loci": []}
    builder.add_entry({**base, "accession": "BGC0000001",
                       "compounds": [{"name": "Epsilon", "formula": "C1",
                                      "databaseIds": ["pubchem:7"]}]})
    builder.add_entry({**base, "accession": "BGC0000002",
                       "compounds": [{"name": "Epsilon", "formula": "C2",
                                      "databaseIds": ["pubchem:8"]}]})
    [row] = [r for r in builder.node_rows() if r["node_id"] == "mg.compound:epsilon"]
    props = json.loads(row["properties"])
    assert props["formula"] == "C1"                        # the first value stays
    assert props["formula_by_entry"] == "BGC0000001: C1|BGC0000002: C2"
    assert props["pubchem_cid_by_entry"] == "BGC0000001: 7|BGC0000002: 8"
    assert builder.counts["property_conflicts"] == 2


# ------------------------------------------------------------- the Phase 4b follow-ups
def test_mibig_lists_every_number_one_entry_gives():
    """Ferrichrome's shape: one entry, two PubChem numbers for one compound."""
    from microbegraph.sources.mibig import _GraphBuilder
    builder = _GraphBuilder(DATE)
    builder.add_entry({"status": "active", "taxonomy": {"name": "x", "ncbiTaxId": 1},
                       "loci": [], "accession": "BGC0000900",
                       "compounds": [{"name": "Ferri", "formula": "C27H42FeN9O12",
                                      "databaseIds": ["pubchem:90658043", "pubchem:644246"]}]})
    [row] = [r for r in builder.node_rows() if r["node_id"] == "mg.compound:ferri"]
    props = json.loads(row["properties"])
    assert props["pubchem_cid"] == "644246"                # the first, as before
    assert props["pubchem_cid_by_entry"] == "BGC0000900: 644246|BGC0000900: 90658043"
    assert builder.counts["compounds_with_several_pubchem_cids"] == 1
    assert builder.counts["property_conflicts"] == 0       # nothing was overwritten


def follow_up_staging(folder: Path) -> Path:
    """
    The four follow-ups, made up:
      ferri   one entry gives two numbers; one is an iron-55 record, and PubChem
              files the name under the ordinary record of the same structure
      omega   joins its own number by name; the name search also hit a
              look-alike, which is left out
      psi     no number; the name search finds one record, with a different
              formula, so nothing joins and that record is left out
      two KEGG maps: one holds omega's record, the other only the look-alike
    """
    folder.mkdir(parents=True, exist_ok=True)
    mibig = [
        node("mibig:BGC0000001", "GeneCluster", "test BGC", "mibig"),
        compound("ferri", "ferri", pubchem_cid="20", formula="C27H42FeN9O12",
                 pubchem_cid_by_entry="BGC0000001: 20|BGC0000001: 22"),
        compound("omega", "omega", pubchem_cid="31", formula="C8H8"),
        compound("psi", "psi", formula="C2H2"),
    ]
    mibig_edges = [edge("mibig:BGC0000001", r["node_id"], "PRODUCES")
                   for r in mibig if r["node_id"].startswith("mg.compound:")]
    pubchem_rows = [
        pubchem(20, "[55Fe] Ferri", "C27H42FeN9O12", "FFFFFFFFFFFFFF-AAAAAAAAAA-N",
                smiles="CC(=O)N[O-].[55Fe+3]", mibig_compound_ids="mg.compound:ferri"),
        pubchem(21, "Ferri", "C27H42FeN9O12", "FFFFFFFFFFFFFF-BBBBBBBBBB-N",
                smiles="CC(=O)N[O-].[Fe+3]", found_by_name="mg.compound:ferri"),
        pubchem(22, "an unrelated record", "C5H5", "QQQQQQQQQQQQQQ-QQQQQQQQQQ-N",
                mibig_compound_ids="mg.compound:ferri"),
        pubchem(30, "an omega look-alike", "C9H9", "RRRRRRRRRRRRRR-RRRRRRRRRR-N",
                found_by_name="mg.compound:omega"),
        pubchem(31, "Omega", "C8H8", "SSSSSSSSSSSSSS-SSSSSSSSSS-N",
                mibig_compound_ids="mg.compound:omega"),
        pubchem(32, "Psi", "C3H3", "TTTTTTTTTTTTTT-TTTTTTTTTT-N", found_by_name="mg.compound:psi"),
    ]
    kegg = [node("kegg.pathway:map00001", "Pathway", "A map with omega", "kegg"),
            node("kegg.pathway:map00002", "Pathway", "A map with the look-alike", "kegg")]
    kegg_edges = [edge("pubchem.compound:31", "kegg.pathway:map00001", "PARTICIPATES_IN",
                       source="kegg", record="C00031"),
                  edge("pubchem.compound:30", "kegg.pathway:map00002", "PARTICIPATES_IN",
                       source="kegg", record="C00030")]
    tables = {s: ([], []) for s in SOURCES}
    tables["mibig"] = (mibig, mibig_edges)
    tables["pubchem"] = (pubchem_rows, [])
    tables["kegg"] = (kegg, kegg_edges)
    for source, (nodes, edges) in tables.items():
        write_table(folder / f"{source}_nodes.csv", NODE_COLUMNS, nodes)
        write_table(folder / f"{source}_edges.csv", EDGE_COLUMNS, edges)
        summary = {"source_version": "test", "retrieved_at": DATE}
        if source == "pubchem":
            summary["cids_not_in_pubchem"] = []
            summary["name_search_complete"] = True
        (folder / f"{source}_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


@pytest.fixture
def follow_up(tmp_path):
    staging = follow_up_staging(tmp_path / "staging")
    result = resolve(staging, tmp_path / "out", tmp_path / "no-curation")
    return result, {r["node_id"]: r for r in read_rows(result.nodes_path)}, \
        read_rows(result.ledger_path)


def _row(ledger: list[dict], identifier: str, compared_with: str = "") -> dict:
    [found] = [r for r in ledger if r["identifier"] == identifier
               and r["compared_with"] == compared_with]
    return found


def test_an_isotope_labelled_record_is_not_the_compound(follow_up):
    _, nodes, ledger = follow_up
    tracer = _row(ledger, "mg.compound:ferri", "pubchem.compound:20")
    assert (tracer["rule"], tracer["decision"]) == ("pubchem_numbers_differ", "kept_apart")
    assert "built with the isotope 55Fe" in tracer["grounds"]
    assert "CID 21 is better supported" in tracer["grounds"]
    ordinary = _row(ledger, "mg.compound:ferri", "pubchem.compound:21")
    assert (ordinary["rule"], ordinary["decision"]) == ("pubchem_name_search", "merged")
    assert nodes["pubchem.compound:21"]["name"] == "ferri"
    assert "pubchem.compound:20" not in nodes


def test_two_numbers_from_one_entry_are_described_as_such(follow_up):
    _, _, ledger = follow_up
    row = _row(ledger, "mg.compound:ferri", "pubchem.compound:22")
    assert row["grounds"].startswith(
        "MIBiG gives this compound more than one number: CID 22 (BGC0000001) and "
        "20 (BGC0000001). ")
    assert "disagree" not in row["grounds"]


def test_a_record_only_the_name_search_found_says_whose_search_it_was(follow_up):
    _, _, ledger = follow_up
    joined_elsewhere = _row(ledger, "pubchem.compound:30")
    assert (joined_elsewhere["rule"], joined_elsewhere["decision"]) == ("not_used", "left_out")
    assert joined_elsewhere["grounds"] == (
        "PubChem's name search found this record for 'omega' (mg.compound:omega), which "
        "joined pubchem.compound:31 instead, so the entry describes nothing in the graph.")
    not_joined = _row(ledger, "pubchem.compound:32")
    assert "for 'psi' (mg.compound:psi), which no rule joined to it" in not_joined["grounds"]
    assert "(; see" not in joined_elsewhere["grounds"] + not_joined["grounds"]


def test_a_map_no_arrow_reaches_is_left_out_with_a_ledger_row(follow_up):
    result, nodes, ledger = follow_up
    assert "kegg.pathway:map00001" in nodes                # omega's record keeps it
    assert "kegg.pathway:map00002" not in nodes
    row = _row(ledger, "kegg.pathway:map00002")
    assert (row["rule"], row["decision"], row["node_type"]) == ("not_used", "left_out", "Pathway")
    assert row["grounds"] == (
        "The only compound record KEGG places on this map is pubchem.compound:30, and it "
        "joined no MIBiG compound (see its not_used row), so no arrow reaches the map and it "
        "describes nothing in the graph.")
    counts = result.summary["counts"]
    assert counts["maps_left_without_arrows"] == 1
    assert counts["identifiers_left_out"] == 5             # records 20, 22, 30, 32 and the map
    assert "1 of them maps no arrow reaches" in report(result.summary)


# ------------------------------------------------------------------------- housekeeping
def test_staging_can_be_imported_on_its_own():
    """The circular import Phase 4 listed: a fresh Python must load staging first."""
    src = Path(__file__).resolve().parents[1] / "src"
    done = subprocess.run([sys.executable, "-c", "import microbegraph.staging"],
                          capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(src)}, check=False)
    assert done.returncode == 0, done.stderr


def test_the_resolver_no_longer_needs_the_source_adapters():
    src = Path(__file__).resolve().parents[1] / "src"
    code = ("import sys, microbegraph.resolve; "
            "print(sorted(m for m in sys.modules if m.startswith('microbegraph.sources.')))")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(src)}, check=False)
    assert done.returncode == 0, done.stderr
    assert "pubchem" not in done.stdout and "uniprot" not in done.stdout
