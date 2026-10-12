"""
Tests for the resolver (Phase 4): every rule, the ledger, and the refusals.

The input is a real slice of the six sources' staging tables, cut around
chosen clusters by tests/fixtures/capture_resolution_samples.py, so every
case below is one the real data contains. The few made-up rows are added in
the test that needs them, and say so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import add_rows, read_rows

from microbegraph.resolution.combine import ResolutionError
from microbegraph.resolution.groups import Groups
from microbegraph.resolution.ledger import RULES, Ledger
from microbegraph.resolution.names import compare_formulas, name_key
from microbegraph.resolve import resolve
from microbegraph.sources.base import SourceError
from microbegraph.validate import check_tables


class Resolved:
    """One resolver run on a staging folder, with handy lookups."""

    def __init__(self, staging: Path, out: Path) -> None:
        self.result = resolve(staging, out)
        self.nodes = {r["node_id"]: r for r in read_rows(self.result.nodes_path)}
        self.edges = read_rows(self.result.edges_path)
        self.ledger = read_rows(self.result.ledger_path)
        self.summary = self.result.summary

    def props(self, node_id: str) -> dict:
        return json.loads(self.nodes[node_id]["properties"])

    def rows(self, identifier: str, rule: str | None = None) -> list[dict[str, str]]:
        return [r for r in self.ledger if r["identifier"] == identifier
                and (rule is None or r["rule"] == rule)]

    def arrows(self, edge_type: str, start: str | None = None,
               end: str | None = None) -> list[dict[str, str]]:
        return [e for e in self.edges if e["edge_type"] == edge_type
                and (start is None or e["source_id"] == start)
                and (end is None or e["target_id"] == end)]


@pytest.fixture
def run(staging_copy, tmp_path):
    return Resolved(staging_copy, tmp_path / "processed")


# --------------------------------------------------------------------- the whole run
def test_the_merged_tables_pass_the_twelve_rules(run):
    assert check_tables(list(run.nodes.values()), run.edges) == []
    assert run.result.ledger_path.exists() and run.result.summary_path.exists()


def test_the_summary_counts_add_up(run):
    counts = run.summary["counts"]
    assert counts["nodes_written"] == len(run.nodes) == sum(run.summary["nodes_by_type"].values())
    assert counts["edges_written"] == len(run.edges)
    assert counts["edges_read"] == (counts["edges_written"] + counts["edges_combined"]
                                    + counts["edges_dropped_at_left_out_nodes"]
                                    + counts["edges_that_became_loops"])
    assert set(run.summary["rules"]) <= set(RULES)


def test_every_identifier_that_disappeared_is_in_the_ledger(run, staging_copy):
    every_id = {r["node_id"] for p in staging_copy.glob("*_nodes.csv") for r in read_rows(p)}
    gone = every_id - set(run.nodes)
    explained = {r["identifier"] for r in run.ledger
                 if r["decision"] in ("merged", "moved", "left_out")}
    assert gone and gone <= explained
    for row in run.ledger:                    # and it says where each one went
        if row["decision"] == "left_out":
            assert row["node_id"] == ""
        else:
            assert row["node_id"] in run.nodes


def test_a_join_the_ledger_does_not_record_is_refused(staging_copy, tmp_path, monkeypatch):
    # Made up: a careless rule that joins records and forgets to say so.
    original = Ledger.add

    def forgetful(self, rule, *args, **kwargs):
        if rule != "identical_sequence":
            original(self, rule, *args, **kwargs)

    monkeypatch.setattr(Ledger, "add", forgetful)
    with pytest.raises(ResolutionError, match="without a ledger row"):
        resolve(staging_copy, tmp_path / "processed")
    assert not (tmp_path / "processed" / "nodes.csv").exists()


def test_the_same_input_gives_the_same_files(staging_copy, tmp_path):
    first = Resolved(staging_copy, tmp_path / "a")
    second = Resolved(staging_copy, tmp_path / "b")
    for name in ("nodes.csv", "edges.csv", "resolution_ledger.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert first.summary["counts"] == second.summary["counts"]


# --------------------------------------------------------------------- organisms
def test_one_identifier_from_two_sources_is_one_node(run):
    fzb42 = run.nodes["ncbitaxon:326423"]
    assert fzb42["name"] == "Bacillus velezensis FZB42"
    assert fzb42["source"] == "mibig|ncbi_taxonomy"
    assert run.props("ncbitaxon:326423")["rank"] == "strain"            # from NCBI
    assert run.rows("ncbitaxon:326423", "same_identifier")[0]["decision"] == "combined"


def test_a_merged_ncbi_number_moves_to_the_current_one(run):
    assert "ncbitaxon:182080" not in run.nodes
    node = run.nodes["ncbitaxon:46161"]
    assert node["name"] == "Actinomadura kijaniata"                     # NCBI's name wins
    props = run.props("ncbitaxon:46161")
    assert "Actinomadura namibiensis" in props["other_names"].split("|")  # MIBiG's is kept
    assert props["aliases"] == "ncbitaxon:182080"
    assert run.arrows("HARBORS", "ncbitaxon:46161", "mibig:BGC0000519")
    [moved] = run.rows("ncbitaxon:182080")
    assert (moved["decision"], moved["node_id"]) == ("moved", "ncbitaxon:46161")


def test_an_organism_that_is_also_a_pathogen_is_one_pathogen_node(run):
    fusarium = run.nodes["ncbitaxon:5518"]
    assert fusarium["node_type"] == "Pathogen"
    assert fusarium["source"] == "mibig|ncbi_taxonomy|curation"
    assert run.arrows("HARBORS", "ncbitaxon:5518", "mibig:BGC0001600")   # still a producer
    assert run.arrows("INFECTS", "ncbitaxon:5518", "mg.crop:wheat")       # and a pathogen
    assert run.arrows("MEMBER_OF", "ncbitaxon:5518")                      # in the family tree
    botrytis = run.nodes["ncbitaxon:40559"]
    assert botrytis["node_type"] == "Pathogen"
    assert run.arrows("MEMBER_OF", "ncbitaxon:332648", "ncbitaxon:40559")  # a strain below it
    assert run.rows("ncbitaxon:5518", "organism_and_pathogen")


# --------------------------------------------------------------------- compounds
def test_a_number_confirmed_by_name_or_formula_joins(run):
    [row] = run.rows("mg.compound:bacillaene", "pubchem_number_confirmed")
    assert (row["decision"], row["node_id"]) == ("merged", "pubchem.compound:25144999")
    assert "mg.compound:bacillaene" not in run.nodes
    node = run.nodes["pubchem.compound:25144999"]
    assert node["name"] == "bacillaene" and node["source"] == "mibig|pubchem"
    assert run.arrows("PRODUCES", "mibig:BGC0001089", "pubchem.compound:25144999")


def test_a_number_that_points_at_another_molecule_stays_apart(run):
    # MIBiG gives bacillomycin D the number of PubChem's "Bacillomycin Fc".
    [row] = run.rows("mg.compound:bacillomycin-d", "pubchem_number_confirmed")
    assert row["decision"] == "kept_apart"
    assert "Bacillomycin Fc" in row["grounds"] and "formulas differ" in row["grounds"]
    props = run.props("mg.compound:bacillomycin-d")
    assert props["pubchem_cid_not_confirmed"] == "3086563" and "pubchem_cid" not in props
    assert "not joined" in props["resolution_notes"]
    assert "pubchem.compound:3086563" not in run.nodes                  # left out
    assert run.rows("pubchem.compound:3086563", "not_used")[0]["decision"] == "left_out"
    # The cited bridge still says what it said, about the right molecule.
    assert run.arrows("INHIBITS", "mg.compound:bacillomycin-d", "ncbitaxon:5518")


def test_a_shared_number_joins_only_names_pubchem_confirms(run):
    for name in ("erythromycin", "erythromycin-a"):
        [row] = run.rows(f"mg.compound:{name}", "pubchem_number_shared")
        assert row["node_id"] == "pubchem.compound:12560"
    assert run.nodes["pubchem.compound:12560"]["name"] == "erythromycin"
    assert "erythromycin A" in run.props("pubchem.compound:12560")["other_names"]
    # Isomers: minutissamides B and C both carry minutissamide D's number.
    for name in ("minutissamide-b", "minutissamide-c"):
        [row] = run.rows(f"mg.compound:{name}", "pubchem_number_shared")
        assert row["decision"] == "kept_apart" and row["node_id"] == f"mg.compound:{name}"
    assert "pubchem.compound:53467423" not in run.nodes


def test_numbers_pubchem_does_not_have_are_listed(run):
    for name, cid in (("monocillin-vi", "406870989"), ("monocillin-vii", "406870990")):
        [row] = run.rows(f"mg.compound:{name}", "pubchem_number_unknown")
        assert row["decision"] == "kept_apart" and cid in row["grounds"]
        assert run.props(f"mg.compound:{name}")["pubchem_cid_not_confirmed"] == cid


def test_one_npatlas_number_and_one_formula_is_one_compound(run):
    [row] = run.rows("mg.compound:monacolin-k", "npatlas_and_formula")
    assert (row["decision"], row["node_id"]) == ("merged", "mg.compound:lovastatin")
    props = run.props("mg.compound:lovastatin")
    assert "monacolin K" in props["other_names"]
    assert "pubchem_cid" not in props          # monacolin K's refused number isn't promoted
    assert run.arrows("PRODUCES", "mibig:BGC0000098", "mg.compound:lovastatin")


def test_arrows_that_became_one_are_combined(run):
    [arrow] = run.arrows("HAS_ACTIVITY", "pubchem.compound:12560", "mg.activity:antibacterial")
    assert arrow["source_record_id"] == "BGC0000054|BGC0000055"
    assert run.summary["counts"]["edges_combined"] > 0


# --------------------------------------------------------------------- proteins
def test_a_protein_number_joins_its_uniprot_entry(run):
    assert "ncbiprotein:CAE02630.1" not in run.nodes
    srfaa = run.nodes["uniprot:Q70KJ7"]
    assert srfaa["name"] == "srfAA" and srfaa["source"] == "mibig|uniprot"
    props = run.props("uniprot:Q70KJ7")
    assert props["functions"] == "Scaffold biosynthesis"                 # MIBiG's facts
    assert props["protein_names"] == "Surfactin synthetase A"            # UniProt's facts
    assert run.arrows("CATALYZES", "uniprot:Q70KJ7", "mg.compound:surfactin")
    assert run.arrows("ENCODES", "mibig:BGC0000433", "uniprot:Q70KJ7")


@pytest.mark.parametrize("number, entry, word", [
    ("WP_012444311.1", "Q8KWW8", "organism"),     # 2 entries, one for the cluster's organism
    ("NP_851152.1", "F4K051", "amino acids"),     # 2 for the organism, one the right length
    ("XP_001798919.1", "Q0UI04", "reviewed"),     # 2 alike, one reviewed by a curator
])
def test_a_number_with_several_entries_is_decided_step_by_step(run, number, entry, word):
    [row] = run.rows(f"ncbiprotein:{number}", "uniprot_cross_reference")
    assert row["node_id"] == f"uniprot:{entry}" and word in row["grounds"]


def test_a_number_with_two_equally_good_entries_stays_on_its_own(run):
    [row] = run.rows("ncbiprotein:CBF82293.1", "uniprot_cross_reference")
    assert row["decision"] == "kept_apart" and row["compared_with"] == "uniprot:P0CU77|uniprot:P0CU78"
    assert "ncbiprotein:CBF82293.1" in run.nodes
    assert "UniProt candidates" in run.props("ncbiprotein:CBF82293.1")["resolution_notes"]
    assert "uniprot:P0CU77" not in run.nodes


def test_one_entry_found_through_two_clusters_is_one_node(run):
    assert len(run.arrows("ENCODES", end="uniprot:E0WB07")) == 2


def test_the_same_sequence_in_the_same_organism_is_one_protein(run):
    [row] = run.rows("mg.protein:bgc0000546-sshg-03592", "identical_sequence")
    assert row["node_id"] == "ncbiprotein:WP_037630570.1"
    assert "mg.protein:bgc0000546-sshg-03592" not in run.nodes


def test_a_twin_of_a_protein_already_in_uniprot_gets_its_own_row(staging_copy, tmp_path):
    # Made up: a second number for srfAA, same sequence, same cluster. Its
    # number sorts before CAE02630.1, which already joined UniProt entry Q70KJ7,
    # so the row must be about the made-up number (the one that disappears),
    # and CAE02630.1 must keep its single row.
    srfaa = next(r for r in read_rows(staging_copy / "mibig_nodes.csv")
                 if r["node_id"] == "ncbiprotein:CAE02630.1")
    add_rows(staging_copy / "mibig_nodes.csv", [{**srfaa, "node_id": "ncbiprotein:AAA00001.1"}])
    add_rows(staging_copy / "mibig_edges.csv", [{
        "source_id": "mibig:BGC0000433", "target_id": "ncbiprotein:AAA00001.1",
        "edge_type": "ENCODES", "evidence_level": "database_assertion", "source": "mibig",
        "source_record_id": "BGC0000433", "citation": "pubmed:14762003",
        "confidence": "0.50", "retrieved_at": "2026-10-10"}])
    made_up = Resolved(staging_copy, tmp_path / "processed")
    [row] = made_up.rows("ncbiprotein:AAA00001.1")
    assert (row["rule"], row["decision"]) == ("identical_sequence", "merged")
    assert row["node_id"] == row["compared_with"] == "uniprot:Q70KJ7"
    assert len(made_up.rows("ncbiprotein:CAE02630.1")) == 1


def test_a_gene_record_named_only_by_gene_name_joins_through_uniprot(run):
    [row] = run.rows("mg.protein:bgc0001089-baeb", "gene_name_in_uniprot")
    assert row["node_id"] == "uniprot:Q1RS81" and "'baeB'" in row["grounds"]
    # baeJ's gene record says a knock-out showed its job; that arrow now starts
    # at the numbered protein, UniProt entry Q1RS73.
    [row] = run.rows("mg.protein:bgc0001089-baej", "gene_name_in_uniprot")
    assert row["node_id"] == "uniprot:Q1RS73"
    [arrow] = run.arrows("CATALYZES", "uniprot:Q1RS73", "pubchem.compound:25144999")
    assert arrow["evidence_level"] == "curated_experimental"
    [left] = run.rows("mg.protein:bgc0001089-baei", "gene_name_in_uniprot")
    assert left["decision"] == "kept_apart"
    assert run.summary["for_phase_4b"]["gene_records_without_a_protein_number"] == [
        "mg.protein:bgc0001089-baei"]


# --------------------------------------------------------------------- refusals
def test_a_broken_merged_table_is_refused_and_nothing_is_written(staging_copy, tmp_path):
    # Made up: a bridge arrow to a compound no source has.
    add_rows(staging_copy / "curation_edges.csv", [{
        "source_id": "mg.compound:made-up", "target_id": "ncbitaxon:5518",
        "edge_type": "INHIBITS", "evidence_level": "curated_literature", "source": "curation",
        "source_record_id": "made-up", "citation": "doi:10.0000/made-up",
        "retrieved_at": "2026-10-12"}])
    with pytest.raises(ResolutionError, match="rule 6"):
        resolve(staging_copy, tmp_path / "processed")
    assert not (tmp_path / "processed" / "nodes.csv").exists()


def test_an_arrow_at_a_left_out_entry_is_dropped_and_counted(staging_copy, tmp_path):
    # Made up: a KEGG arrow from the PubChem entry the rules refuse (Bacillomycin Fc).
    add_rows(staging_copy / "kegg_edges.csv", [{
        "source_id": "pubchem.compound:3086563", "target_id": "kegg.pathway:map01100",
        "edge_type": "PARTICIPATES_IN", "evidence_level": "database_assertion",
        "source": "kegg", "source_record_id": "made-up", "retrieved_at": "2026-10-12"}])
    run = Resolved(staging_copy, tmp_path / "processed")
    assert run.summary["counts"]["edges_dropped_at_left_out_nodes"] == 1


def test_a_missing_table_says_which_command_makes_it(staging_copy, tmp_path):
    (staging_copy / "kegg_nodes.csv").unlink()
    with pytest.raises(SourceError, match="fetch --source kegg"):
        resolve(staging_copy, tmp_path / "processed")


# --------------------------------------------------------------------- the pieces
def test_groups_never_hold_two_authority_identifiers():
    groups = Groups()
    groups.join("mg.compound:a", "pubchem.compound:1")
    groups.join("mg.compound:b", "pubchem.compound:2")
    assert not groups.can_join("mg.compound:a", "mg.compound:b")
    with pytest.raises(ValueError):
        groups.join("mg.compound:a", "mg.compound:b")
    groups.settle()
    assert groups.canonical("mg.compound:a") == "pubchem.compound:1"
    assert groups.canonical("mg.compound:never-seen") == "mg.compound:never-seen"


@pytest.mark.parametrize("name, key", [
    ("Erythromycin A", "erythromycina"),
    ("erythromycin-A", "erythromycina"),
    ("α-galactosylceramide", "alphagalactosylceramide"),
    ("(+)-semivioxanthin", "plussemivioxanthin"),
])
def test_name_keys(name, key):
    assert name_key(name) == key


def test_mirror_images_never_match_by_name():
    assert name_key("(+)-menthol") != name_key("(-)-menthol")
    assert name_key("D-alanine") != name_key("L-alanine")


@pytest.mark.parametrize("a, b, word", [
    ("C37H67NO13", "C37H67NO13", "agrees"),
    ("C10H16NO4", "C10H16NO4-", "agrees_but_charge"),
    ("C49H76N10O15", "C52H84N12O14", "differs"),
    ("", "C5H6O4", "missing"),
])
def test_formula_comparison(a, b, word):
    assert compare_formulas(a, b) == word
