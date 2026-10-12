"""
Tests for MIBiG's protein file (Phase 3b): is every protein of every active
cluster read, matched to its gene record, and turned into the right node and
ENCODES arrow, with the curators' removals left out and listed?

The sample file (tests/fixtures/mibig/mibig_prot_seqs_sample.fasta) holds
surfactin's 23 proteins copied unchanged from the real file, then made-up
proteins for the made-up entries, each one there for a case the tests below
name (tests/fixtures/README.md lists them).
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from conftest import PROTEIN_SAMPLE, build_archive

from microbegraph.sources.base import SourceError
from microbegraph.sources.mibig import FILENAME, PROTEIN_FILE
from microbegraph.sources.mibig_proteins import (
    count_records,
    find_gene,
    find_removed,
    parse_header,
    read_protein_file,
)
from microbegraph.sources.uniprot import BATCH_SIZE, UniprotSource

SRFAA_HEADER = "BGC0000433.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A|CAE02630.1"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def tidy_tables(adapter):
    result = adapter.tidy()
    nodes = {r["node_id"]: r for r in read_rows(result.nodes_path)}
    edges = {(r["source_id"], r["edge_type"], r["target_id"]): r
             for r in read_rows(result.edges_path)}
    summary = json.loads((result.nodes_path.parent / "mibig_summary.json").read_text("utf-8"))
    return result, nodes, edges, summary


def props(node: dict[str, str]) -> dict:
    return json.loads(node["properties"])


def encoded_by(edges: dict, cluster: str) -> list[str]:
    return sorted(t for (s, kind, t) in edges if s == cluster and kind == "ENCODES")


# --- reading the file -------------------------------------------------------------
def test_a_header_has_seven_parts():
    assert parse_header(SRFAA_HEADER) == (
        "BGC0000433.5", "c1", "8558-19312", "+", "CAE02630.1", "surfactin_synthetase_A",
        "CAE02630.1")


@pytest.mark.parametrize("header", [
    "BGC0000433.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A",      # six parts
    "BGC0000433.5|c1|1-9|+|CAE02630.1|a|b|CAE02630.1",                    # eight parts
    "NOTANENTRY.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A|CAE02630.1",
    "BGC0000433.5|c1|8558-19312|+|CAE02630.1|surfactin_synthetase_A|",    # no protein id
])
def test_a_header_in_another_shape_is_not_guessed_at(header):
    assert parse_header(header) is None


def test_the_sample_is_read_entry_by_entry(tmp_path):
    proteins = read_protein_file(PROTEIN_SAMPLE)
    assert {accession: len(records) for accession, records in proteins.items()} == {
        "BGC0000433": 23, "BGC9999901": 17, "BGC9999902": 1, "BGC9999903": 2}
    srfaa = next(r for r in proteins["BGC0000433"] if r.protein_id == "CAE02630.1")
    assert (srfaa.entry_version, srfaa.location, srfaa.strand, srfaa.label) == (
        "5", "8558-19312", "+", "CAE02630.1")
    assert srfaa.product == "surfactin synthetase A"         # "_" back to spaces
    assert srfaa.length == 3584
    assert count_records(PROTEIN_SAMPLE) == 43


def test_the_fingerprint_is_the_md5_of_the_letters():
    text = PROTEIN_SAMPLE.read_text(encoding="utf-8").splitlines()
    sequence = text[text.index(">" + SRFAA_HEADER) + 1]
    [srfaa] = [r for r in read_protein_file(PROTEIN_SAMPLE)["BGC0000433"]
               if r.protein_id == "CAE02630.1"]
    assert srfaa.md5 == hashlib.md5(sequence.encode()).hexdigest()


def test_a_file_with_an_unreadable_header_is_refused(tmp_path):
    broken = tmp_path / PROTEIN_FILE
    broken.write_bytes(PROTEIN_SAMPLE.read_bytes() + b">BGC0000433.5|c1|only|four\nMKV\n")
    with pytest.raises(SourceError, match="1 header"):
        read_protein_file(broken)


# --- the matching rules -----------------------------------------------------------
def test_a_gene_is_found_by_number_label_or_a_single_product():
    records = read_protein_file(PROTEIN_SAMPLE)["BGC9999901"]

    def number(name: str) -> tuple[str, str]:
        index, how = find_gene(name, records)
        return (records[index].protein_id if index is not None else "", how)

    assert number("WP_999999901.1") == ("WP_999999901.1", "id")
    assert number("TESTI_00060") == ("XYZ99960.1", "id")          # by its locus tag
    assert number("tstQ") == ("XYZ99980.1", "product")            # TstQ, ignoring capitals
    assert number("tstY") == ("", "")                             # two proteins are TstY
    assert number("LOC999001") == ("", "")                        # never a word inside a product


def test_a_removal_can_be_found_three_ways():
    records = read_protein_file(PROTEIN_SAMPLE)["BGC9999901"]

    def numbers(name: str) -> tuple[list[str], str]:
        found, how = find_removed(name, records)
        return [records[i].protein_id for i in found], how

    assert numbers("XYZ99990.1") == (["XYZ99990.1"], "id")
    assert numbers("tstD") == (["XYZ99991.1"], "product")
    assert numbers("LOC999001") == (["XYZ99992.1", "XYZ99993.1"], "word in product")
    assert numbers("LOC99900") == ([], "")                        # part of a word isn't a word
    assert numbers("tstZ") == ([], "")


# --- the tidy ------------------------------------------------------------------------
def test_surfactins_cluster_encodes_every_protein_in_the_file(make_adapter, archive_in_locker):
    _, nodes, edges, _ = tidy_tables(make_adapter())

    encoded = encoded_by(edges, "mibig:BGC0000433")
    assert encoded == [f"ncbiprotein:CAE026{n:02d}.1" for n in range(19, 42)]   # all 23
    srfaa = props(nodes["ncbiprotein:CAE02630.1"])
    assert srfaa["found_in"] == "gene_records|protein_file"
    assert srfaa["gene_name"] == "srfAA"                      # the gene record's details stay
    assert srfaa["locations"] == "BGC0000433:8558-19312:+"    # and the file's are added
    assert srfaa["sequence_length"] == 3584

    ycic = nodes["ncbiprotein:CAE02619.1"]
    assert ycic["name"] == "YciC protein"
    assert props(ycic) == {
        "protein_id": "CAE02619.1", "id_type": "insdc", "product": "YciC protein",
        "locations": "BGC0000433:64-1341:+", "sequence_length": 425,
        "sequence_md5": "8d735b44bddcae1d870998ad270ca816", "found_in": "protein_file"}
    encodes = edges[("mibig:BGC0000433", "ENCODES", "ncbiprotein:CAE02619.1")]
    assert encodes["evidence_level"] == "database_assertion"
    assert encodes["confidence"] == "0.50"
    assert encodes["citation"] == "pubmed:14762003"


def test_catalyzes_still_comes_only_from_gene_records(make_adapter, archive_in_locker):
    """The file says which proteins a cluster has, never what job they do."""
    _, _, edges, _ = tidy_tables(make_adapter())
    makers = sorted(s for (s, kind, t) in edges
                    if kind == "CATALYZES" and t == "mg.compound:surfactin"
                    and s.startswith("ncbiprotein:CAE"))
    assert makers == ["ncbiprotein:CAE02630.1", "ncbiprotein:CAE02631.1",
                      "ncbiprotein:CAE02633.1"]


def test_a_locus_tag_gains_the_protein_number_the_file_gives(make_adapter, archive_in_locker):
    _, nodes, edges, _ = tidy_tables(make_adapter())

    assert "mg.protein:bgc9999901-testi-00060" not in nodes
    tstu = nodes["ncbiprotein:XYZ99960.1"]
    assert tstu["name"] == "tstU"
    assert {k: props(tstu)[k] for k in ("protein_id", "id_type", "gene_record_id", "locus_tags")} == {
        "protein_id": "XYZ99960.1", "id_type": "insdc", "gene_record_id": "TESTI_00060",
        "locus_tags": "TESTI_00060"}
    assert ("mibig:BGC9999901", "ENCODES", "ncbiprotein:XYZ99960.1") in edges


def test_a_gene_name_matching_one_product_is_that_protein(make_adapter, archive_in_locker):
    _, nodes, _, _ = tidy_tables(make_adapter())
    tstq = nodes["ncbiprotein:XYZ99980.1"]
    assert tstq["name"] == "tstQ"
    assert props(tstq)["gene_record_id"] == "tstQ"
    assert props(tstq)["product"] == "TstQ"                   # the gene record had none


def test_an_ambiguous_gene_stays_its_own_protein_and_is_listed(make_adapter, archive_in_locker):
    result, nodes, _, summary = tidy_tables(make_adapter())
    assert props(nodes["mg.protein:bgc9999901-tsty"])["found_in"] == "gene_records"
    assert "ncbiprotein:XYZ99981.1" in nodes and "ncbiprotein:XYZ99982.1" in nodes
    assert summary["genes_not_in_protein_file"] == ["BGC9999901: tstY"]
    assert result.counts["genes_not_in_protein_file"] == 1


def test_a_locus_tag_without_a_number_still_means_one_genome(make_adapter, archive_in_locker):
    _, nodes, _, _ = tidy_tables(make_adapter())
    assert props(nodes["mg.protein:bgc9999901-testi-00020"])["found_in"] == \
        "gene_records|protein_file"
    assert props(nodes["mg.protein:bgc9999903-testi-00020"])["found_in"] == \
        "gene_records|protein_file"


def test_the_curators_removals_are_left_out_and_listed(make_adapter, archive_in_locker):
    result, nodes, _, summary = tidy_tables(make_adapter())

    for number in ("XYZ99990.1", "XYZ99991.1", "XYZ99992.1", "XYZ99993.1"):
        assert f"ncbiprotein:{number}" not in nodes
    assert [(r["to_delete"], r["protein"], r["matched_by"])
            for r in summary["removed_by_curators"]] == [
        ("XYZ99990.1", "XYZ99990.1", "id"), ("tstD", "XYZ99991.1", "product"),
        ("LOC999001", "XYZ99992.1", "word in product"),
        ("LOC999001", "XYZ99993.1", "word in product")]
    assert summary["removed_by_curators"][0]["reason"] == "Test removal by protein number"
    assert [r["to_delete"] for r in summary["to_delete_not_found"]] == ["tstZ"]
    assert result.counts["proteins_removed_by_curators"] == 4
    assert result.counts["to_delete_not_found"] == 1


def test_a_gene_the_curators_added_arrives_from_the_file(make_adapter, archive_in_locker):
    result, nodes, edges, _ = tidy_tables(make_adapter())
    added = nodes["mg.protein:bgc9999901-ctg1-orf7"]
    assert added["name"] == "ctg1_orf7"                       # no product in the file
    assert ("mibig:BGC9999901", "ENCODES", "mg.protein:bgc9999901-ctg1-orf7") in edges
    assert result.counts["proteins_added_by_curators"] == 1


def test_the_same_protein_twice_in_one_cluster_is_one_node(make_adapter, archive_in_locker):
    result, nodes, edges, _ = tidy_tables(make_adapter())
    peptide = props(nodes["ncbiprotein:WP_999999970.1"])
    assert peptide["locations"] == "BGC9999901:14301-14390:-|BGC9999901:14501-14590:-"
    assert peptide["locus_tags"] == "TESTI_00070|TESTI_00071"
    assert len([k for k in edges if k[2] == "ncbiprotein:WP_999999970.1"]) == 1
    assert result.counts["protein_file_repeats_in_entry"] == 1


def test_a_protein_in_two_clusters_is_one_node_with_two_arrows(make_adapter, archive_in_locker):
    _, nodes, edges, _ = tidy_tables(make_adapter())
    shared = props(nodes["ncbiprotein:XYZ99970.1"])
    assert shared["locations"] == "BGC9999901:8501-9700:-|BGC9999903:1001-2200:-"
    assert sorted(s for (s, kind, t) in edges
                  if kind == "ENCODES" and t == "ncbiprotein:XYZ99970.1") == [
        "mibig:BGC9999901", "mibig:BGC9999903"]


def test_proteins_of_entries_that_are_not_active_are_left_out(make_adapter, archive_in_locker):
    result, nodes, _, _ = tidy_tables(make_adapter())
    assert "ncbiprotein:XYZ99902.1" not in nodes             # BGC9999902 is retired
    assert result.counts["protein_file_records_not_active"] == 1


def test_the_protein_file_counts_add_up(make_adapter, archive_in_locker):
    result, nodes, edges, _ = tidy_tables(make_adapter())
    c = result.counts

    assert c["protein_file_records"] == 43
    assert c["protein_file_records"] == (c["protein_file_records_not_active"]
                                         + c["protein_file_insdc_id"] + c["protein_file_refseq_id"]
                                         + c["protein_file_other_id"])
    assert (c["protein_file_insdc_id"], c["protein_file_refseq_id"],
            c["protein_file_other_id"]) == (33, 3, 6)
    assert c["genes_found_by_id"] + c["genes_found_by_product"] + c["genes_not_in_protein_file"] \
        == c["genes_read"] - c["genes_without_id"]
    assert (c["genes_found_by_id"], c["genes_found_by_product"]) == (16, 1)
    assert c["genes_given_a_protein_number"] == 2             # TESTI_00060 and tstQ
    assert c["protein_file_version_differs"] == 0
    assert c["entries_with_proteins"] == 3

    # Each ENCODES arrow is one (cluster, protein) pair: the file's proteins of
    # active entries, less removals and repeats, plus gene records not in the file.
    n_encodes = sum(1 for k in edges if k[1] == "ENCODES")
    from_file = (c["protein_file_records"] - c["protein_file_records_not_active"]
                 - c["proteins_removed_by_curators"] - c["protein_file_repeats_in_entry"])
    assert n_encodes == from_file + c["genes_not_in_protein_file"] == 38
    assert sum(1 for n in nodes.values() if n["node_type"] == "Protein") == 37


def test_the_tidy_needs_the_protein_file(make_adapter, tmp_path):
    build_archive(tmp_path / "raw" / "mibig" / FILENAME, proteins=False)
    adapter = make_adapter()
    with pytest.raises(SourceError, match="--source mibig"):
        adapter.tidy()
    assert not (adapter.staging_dir / "mibig_nodes.csv").exists()


# --- what UniProt is asked about ---------------------------------------------------------
def test_uniprot_now_asks_about_every_numbered_protein(make_adapter, make_source,
                                                       archive_in_locker):
    make_adapter().tidy()
    ids = make_source(UniprotSource)._ids_from_mibig()
    assert "CAE02619.1" in ids["insdc"]           # surfactin's cluster, from the file only
    assert "XYZ99960.1" in ids["insdc"]           # a locus tag that gained a number
    assert "WP_999999970.1" in ids["refseq"]
    assert not any(i.startswith(("TESTI", "ctg1", "tst")) for i in ids["insdc"] + ids["refseq"])
    # 33 INSDC records in the file: 23 surfactin + 9 in BGC9999901 + 1 shared by
    # BGC9999903 (counted once) + 1 in the retired BGC9999902 (left out), and 4 of
    # BGC9999901's are removals. 23 + (9 - 4) = 28.
    assert (len(ids["insdc"]), len(ids["refseq"])) == (28, 2)


def test_the_batch_size_stays_inside_uniprots_limit():
    """UniProt accepts up to 100,000 ids in one ID mapping job."""
    assert 1_000 <= BATCH_SIZE <= 100_000
