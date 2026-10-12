"""
Tests for the gene records the MIBiG adapter reads from Phase 3: does each
gene become the right Protein node, ENCODES arrow and CATALYZES arrows?

The surfactin record's gene records are real (copied unchanged from MIBiG
4.0); the made-up records BGC9999901 and BGC9999903 cover the cases surfactin
doesn't (tests/fixtures/README.md).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from microbegraph.sources.mibig import _GraphBuilder, protein_id_type

SURFACTIN_PROTEINS = ["CAE02630.1", "CAE02631.1", "CAE02632.1", "CAE02633.1", "CAE02634.1",
                      "CAE02636.1", "CAE02637.1", "CAE02638.1", "CAE02639.1"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def tidy_tables(adapter):
    result = adapter.tidy()
    nodes = {r["node_id"]: r for r in read_rows(result.nodes_path)}
    edges = {(r["source_id"], r["edge_type"], r["target_id"]): r
             for r in read_rows(result.edges_path)}
    return result, nodes, edges


def test_every_surfactin_gene_becomes_a_protein_the_cluster_encodes(make_adapter,
                                                                    archive_in_locker):
    _, nodes, edges = tidy_tables(make_adapter())

    encoded = sorted(t for (s, kind, t) in edges if s == "mibig:BGC0000433" and kind == "ENCODES")
    # From Phase 3b the protein file adds the cluster's other 14 proteins, so
    # the nine gene records are among 23 (tests/test_mibig_protein_file.py).
    assert set(f"ncbiprotein:{p}" for p in SURFACTIN_PROTEINS) <= set(encoded)
    srfaa = nodes["ncbiprotein:CAE02630.1"]
    assert srfaa["node_type"] == "Protein"
    assert srfaa["name"] == "srfAA"
    props = json.loads(srfaa["properties"])
    assert {k: props[k] for k in ("protein_id", "id_type", "gene_name", "product", "functions",
                                  "function_evidence")} == {
        "protein_id": "CAE02630.1", "id_type": "insdc", "gene_name": "srfAA",
        "product": "surfactin synthetase A", "functions": "Scaffold biosynthesis",
        "function_evidence": "Knock-out"}

    encodes = edges[("mibig:BGC0000433", "ENCODES", "ncbiprotein:CAE02630.1")]
    assert encodes["evidence_level"] == "database_assertion"
    assert encodes["confidence"] == "0.50"
    assert encodes["citation"] == "pubmed:14762003"


def test_only_genes_that_build_the_molecule_catalyze_it(make_adapter, archive_in_locker):
    """srfAA, srfAB and srfAC build surfactin's backbone; the other six don't."""
    _, _, edges = tidy_tables(make_adapter())

    makers = sorted(s for (s, kind, t) in edges
                    if kind == "CATALYZES" and s.startswith("ncbiprotein:CAE")
                    and t == "mg.compound:surfactin")
    assert makers == ["ncbiprotein:CAE02630.1", "ncbiprotein:CAE02631.1",
                      "ncbiprotein:CAE02633.1"]
    # sfp switches the synthetases on (and a knock-out showed it), but it
    # doesn't carry out a step in making the molecule.
    assert ("ncbiprotein:CAE02638.1", "CATALYZES", "mg.compound:surfactin") not in edges


def test_an_experiment_behind_the_job_makes_the_arrow_experimental(make_adapter,
                                                                    archive_in_locker):
    _, _, edges = tidy_tables(make_adapter())

    knocked_out = edges[("ncbiprotein:CAE02630.1", "CATALYZES", "mg.compound:surfactin")]
    stated_only = edges[("ncbiprotein:CAE02631.1", "CATALYZES", "mg.compound:surfactin")]
    assert knocked_out["evidence_level"] == "curated_experimental"
    assert stated_only["evidence_level"] == "database_assertion"


def test_a_cited_assay_is_kept_and_the_arrow_reaches_every_compound(make_adapter,
                                                                     archive_in_locker):
    """BGC9999901 lists two compounds and doesn't say which one tstB works on."""
    result, _, edges = tidy_tables(make_adapter())

    for compound in ("mg.compound:surfactin", "mg.compound:delta-testamide"):
        edge = edges[("mg.protein:bgc9999901-testi-00020", "CATALYZES", compound)]
        assert edge["evidence_level"] == "curated_experimental"
        assert "doi:10.0000/fixture.6" in edge["citation"].split("|")
    assert result.counts["catalyzes_in_multi_compound_entries"] == 8   # 4 genes x 2 compounds


def test_identifier_styles_decide_the_node_id(make_adapter, archive_in_locker):
    _, nodes, _ = tidy_tables(make_adapter())

    refseq = json.loads(nodes["ncbiprotein:WP_999999901.1"]["properties"])
    assert refseq["id_type"] == "refseq"
    # The same locus tag in two entries is two proteins, one per entry.
    assert "mg.protein:bgc9999901-testi-00020" in nodes
    assert "mg.protein:bgc9999903-testi-00020" in nodes
    assert nodes["mg.protein:bgc9999901-testi-00020"]["name"] == "tstB"
    assert nodes["mg.protein:bgc9999903-testi-00020"]["name"] == "prdA"


def test_a_gene_without_a_name_is_called_by_its_product(make_adapter, archive_in_locker):
    _, nodes, _ = tidy_tables(make_adapter())
    assert nodes["mg.protein:bgc9999901-testi-00030"]["name"] == "aminotransferase"


def test_a_gene_with_two_jobs_keeps_both(make_adapter, archive_in_locker):
    _, nodes, edges = tidy_tables(make_adapter())

    props = json.loads(nodes["mg.protein:bgc9999901-testi-00040"]["properties"])
    assert props["functions"] == "Regulation|Tailoring"
    edge = edges[("mg.protein:bgc9999901-testi-00040", "CATALYZES", "mg.compound:surfactin")]
    assert edge["evidence_level"] == "database_assertion"


def test_gene_counts_add_up(make_adapter, archive_in_locker):
    result, _, _ = tidy_tables(make_adapter())
    counts = result.counts

    # BGC9999901 gained three gene records in Phase 3b (TESTI_00060, tstQ, tstY),
    # none with a job, for the protein file's matching rules.
    assert counts["entries_with_gene_records"] == 3
    assert counts["genes_read"] == 19
    assert counts["genes_without_id"] == 1
    assert (counts["genes_insdc_id"], counts["genes_refseq_id"], counts["genes_other_id"]) == (
        9, 1, 8)
    # Every gene with an id lands in exactly one of these three.
    assert (counts["genes_in_biosynthesis"], counts["genes_other_roles"],
            counts["genes_role_not_stated"]) == (8, 4, 6)
    assert counts["genes_read"] - counts["genes_without_id"] == 8 + 4 + 6


@pytest.mark.parametrize(("identifier", "kind"), [
    ("CAE02630.1", "insdc"),
    ("MBA5221208.1", "insdc"),         # the newer style, with seven digits
    ("WP_029025939.1", "refseq"),
    ("NP_199072.1", "refseq"),
    ("TSTA_117750", "other"),          # a locus tag
    ("abyU", "other"),                 # a gene name
    ("CAE02630", "other"),             # no version number, so not a full protein id
])
def test_protein_id_type(identifier, kind):
    assert protein_id_type(identifier) == kind


def _entry(accession: str, genes: list[dict], quality: str = "high") -> dict:
    """A minimal active MIBiG entry, built in the test itself."""
    return {"accession": accession, "status": "active", "quality": quality,
            "taxonomy": {"name": "Testibacter", "ncbiTaxId": 999999904},
            "compounds": [{"name": "testin"}], "loci": [], "genes": {"annotations": genes}}


def test_a_prediction_is_not_an_experiment():
    builder = _GraphBuilder("2026-10-12")
    builder.add_entry(_entry("BGC9999904", [{
        "id": "TESTI_00010", "functions": [{"function": {"name": "Tailoring"},
                                            "evidence": [{"method": "Sequence-based prediction"}]}],
    }]))
    [edge] = [e for e in builder.edge_rows() if e["edge_type"] == "CATALYZES"]
    assert edge["evidence_level"] == "database_assertion"


def test_one_protein_number_in_two_entries_is_one_node():
    builder = _GraphBuilder("2026-10-12")
    gene = {"id": "ABC12345.1", "name": "abcA",
            "functions": [{"function": {"name": "Tailoring"}, "evidence": []}]}
    builder.add_entry(_entry("BGC9999904", [gene]))
    builder.add_entry(_entry("BGC9999905", [gene], quality="low"))

    assert [n["node_id"] for n in builder.node_rows()
            if n["node_type"] == "Protein"] == ["ncbiprotein:ABC12345.1"]
    encodes = [e for e in builder.edge_rows() if e["edge_type"] == "ENCODES"]
    assert sorted(e["source_id"] for e in encodes) == ["mibig:BGC9999904", "mibig:BGC9999905"]
    [catalyzes] = [e for e in builder.edge_rows() if e["edge_type"] == "CATALYZES"]
    assert catalyzes["source_record_id"] == "BGC9999904|BGC9999905"
    assert catalyzes["confidence"] == "0.95"                     # the higher grade wins
