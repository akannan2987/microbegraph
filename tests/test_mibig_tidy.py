"""
Tests for the MIBiG tidy step: does one archive become the right rows?

Each test spells out one promise the code makes, then checks it.
Run them with:   pytest        (from the repository root, .venv active)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from conftest import build_archive

from microbegraph import provenance
from microbegraph.sources.base import SourceError
from microbegraph.sources.mibig import FILENAME
from microbegraph.validate import check_tables


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def tidy_tables(adapter):
    result = adapter.tidy()
    nodes = {r["node_id"]: r for r in read_rows(result.nodes_path)}
    edges = {(r["source_id"], r["edge_type"], r["target_id"]): r
             for r in read_rows(result.edges_path)}
    return result, nodes, edges


def test_the_surfactin_chain_arrives_as_documented(make_adapter, archive_in_locker):
    """The worked example in docs/02 and docs/03, row for row."""
    _, nodes, edges = tidy_tables(make_adapter())

    organism = nodes["ncbitaxon:326423"]
    assert organism["node_type"] == "Organism"
    assert organism["name"] == "Bacillus velezensis FZB42"

    cluster = nodes["mibig:BGC0000433"]
    props = json.loads(cluster["properties"])
    assert cluster["name"] == "surfactin BGC"
    assert props["bgc_class"] == "NRPS"
    assert props["quality"] == "questionable"

    compound = json.loads(nodes["mg.compound:surfactin"]["properties"])
    assert compound["formula"] == "C52H91N7O13"
    assert compound["database_ids"] == "chemspider:391754|npatlas:NPA018495"

    harbors = edges[("ncbitaxon:326423", "HARBORS", "mibig:BGC0000433")]
    assert harbors["evidence_level"] == "curated_experimental"
    assert harbors["confidence"] == "0.50"          # MIBiG grades this entry "questionable"
    assert harbors["citation"] == "pubmed:14762003"

    produces = edges[("mibig:BGC0000433", "PRODUCES", "mg.compound:surfactin")]
    assert produces["evidence_level"] == "curated_experimental"


def test_a_predicted_cluster_is_not_called_an_experiment(make_adapter, archive_in_locker):
    """BGC9999903's only evidence is homology: both of its arrows are database assertions."""
    result, _, edges = tidy_tables(make_adapter())
    harbors = edges[("ncbitaxon:999999903", "HARBORS", "mibig:BGC9999903")]
    produces = edges[("mibig:BGC9999903", "PRODUCES", "mg.compound:predictamycin")]
    assert harbors["evidence_level"] == produces["evidence_level"] == "database_assertion"
    assert produces["confidence"] == "0.70"                       # MIBiG grade "low"
    assert result.counts["entries_with_experimental_evidence"] == 2
    assert result.counts["entries_predicted_or_unstated"] == 1


def test_archive_order_does_not_change_the_output(make_adapter, tmp_path):
    """Records stored in a different order inside the archive: identical tables."""
    build_archive(tmp_path / "raw" / "mibig" / FILENAME)
    first = make_adapter().tidy()
    before = first.nodes_path.read_bytes(), first.edges_path.read_bytes()
    build_archive(tmp_path / "raw" / "mibig" / FILENAME, reverse=True)
    second = make_adapter().tidy()
    assert (second.nodes_path.read_bytes(), second.edges_path.read_bytes()) == before


@pytest.mark.parametrize("compression", ["", "bz2", "xz"])
def test_the_file_name_does_not_decide_how_it_is_read(make_adapter, tmp_path, compression):
    """MIBiG 4.0's .tar.gz is not gzip-compressed. Whatever is inside, same tables."""
    locker_file = tmp_path / "raw" / "mibig" / FILENAME
    build_archive(locker_file)                                  # gzip, what the name promises
    first = make_adapter().tidy()
    before = first.nodes_path.read_bytes(), first.edges_path.read_bytes()
    build_archive(locker_file, compression=compression)         # same name, different inside
    second = make_adapter().tidy()
    assert second.counts["files_read"] == 4
    assert (second.nodes_path.read_bytes(), second.edges_path.read_bytes()) == before


def test_uncited_activity_is_a_database_assertion(make_adapter, archive_in_locker):
    """'surfactant' has no reference in MIBiG, so it is not called an experiment."""
    _, _, edges = tidy_tables(make_adapter())
    edge = edges[("mg.compound:surfactin", "HAS_ACTIVITY", "mg.activity:surfactant")]
    assert edge["evidence_level"] == "database_assertion"
    assert edge["citation"] == ""


def test_repeated_arrow_merges_and_keeps_the_stronger_evidence(make_adapter, archive_in_locker):
    """Two entries say surfactin is antibacterial; one cites a paper. One arrow, best of both."""
    _, _, edges = tidy_tables(make_adapter())
    edge = edges[("mg.compound:surfactin", "HAS_ACTIVITY", "mg.activity:antibacterial")]
    assert edge["source_record_id"] == "BGC0000433|BGC9999901"
    assert edge["evidence_level"] == "curated_experimental"
    assert edge["confidence"] == "0.85"
    assert edge["citation"] == "doi:10.0000/fixture.2"


def test_both_styles_of_activity_name_give_the_same_node(make_adapter, archive_in_locker):
    """
    MIBiG 4.0 writes an activity as {"activity": "antibacterial"} in some entries
    (the real surfactin record) and as plain text ("Antibacterial") in others.
    Both must land on mg.activity:antibacterial, never on a node named after
    the object itself.
    """
    _, nodes, _ = tidy_tables(make_adapter())
    activities = {node_id: row["name"] for node_id, row in nodes.items()
                  if row["node_type"] == "Activity"}
    assert activities == {
        "mg.activity:antibacterial": "antibacterial",
        "mg.activity:antifungal": "antifungal",
        "mg.activity:surfactant": "surfactant",
    }


def test_a_curators_comment_is_kept_on_the_compound(make_adapter, archive_in_locker):
    """The comment describes this compound's activity, so it stays with the compound."""
    _, nodes, _ = tidy_tables(make_adapter())
    testamide = json.loads(nodes["mg.compound:delta-testamide"]["properties"])
    assert testamide["activity_notes"] == "antifungal: Slows a test fungus in a plate assay"
    assert "activity_notes" not in json.loads(nodes["mg.compound:surfactin"]["properties"])


def test_one_compound_node_however_many_clusters_make_it(make_adapter, archive_in_locker):
    _, nodes, edges = tidy_tables(make_adapter())
    assert sum(1 for n in nodes if n.startswith("mg.compound:surfactin")) == 1
    producers = {s for (s, t, o) in edges if t == "PRODUCES" and o == "mg.compound:surfactin"}
    assert producers == {"mibig:BGC0000433", "mibig:BGC9999901"}


def test_retired_entries_are_skipped_and_counted(make_adapter, archive_in_locker):
    result, nodes, _ = tidy_tables(make_adapter())
    assert "mibig:BGC9999902" not in nodes
    assert result.counts["entries_skipped_status"] == 1
    assert result.counts["entries_active"] == 3


def test_a_negative_result_never_becomes_an_arrow(make_adapter, archive_in_locker):
    """'cytotoxic: observed false' means tested and NOT found. No HAS_ACTIVITY edge."""
    result, nodes, _ = tidy_tables(make_adapter())
    assert "mg.activity:cytotoxic" not in nodes
    assert result.counts["bioactivities_not_observed"] == 1


def test_greek_letters_classes_and_pubchem_ids(make_adapter, archive_in_locker):
    _, nodes, edges = tidy_tables(make_adapter())
    props = json.loads(nodes["mg.compound:delta-testamide"]["properties"])
    assert props["pubchem_cid"] == "999999901"
    assert props["synonyms"] == "delta-testamide|testamide D"
    assert ("mg.compound:delta-testamide", "BELONGS_TO", "mg.class:peptide-alkaloid") in edges
    assert json.loads(nodes["mibig:BGC9999901"]["properties"])["bgc_class"] == "NRPS|PKS"


def test_every_row_obeys_the_twelve_rules(make_adapter, archive_in_locker):
    result = make_adapter().tidy()
    assert check_tables(read_rows(result.nodes_path), read_rows(result.edges_path)) == []


def test_the_same_input_always_gives_the_same_output(make_adapter, archive_in_locker):
    """Reproducibility: two runs, byte-identical files."""
    first = make_adapter().tidy()
    before = first.nodes_path.read_bytes(), first.edges_path.read_bytes()
    second = make_adapter().tidy()
    assert (second.nodes_path.read_bytes(), second.edges_path.read_bytes()) == before


def test_retrieved_at_comes_from_the_download_not_from_today(make_adapter, archive_in_locker, tmp_path):
    adapter = make_adapter()
    row = {column: "" for column in provenance.COLUMNS}
    row.update(retrieved_at="2026-01-02T03:04:05Z", source="mibig", outcome="downloaded",
               local_path=FILENAME)   # outside the repo, paths are recorded by name only
    provenance.append(row, log_path=adapter.provenance_log)
    _, nodes, edges = tidy_tables(adapter)
    assert {n["retrieved_at"] for n in nodes.values()} == {"2026-01-02"}
    assert {e["retrieved_at"] for e in edges.values()} == {"2026-01-02"}


def test_broken_and_foreign_files_are_counted_not_fatal(make_adapter, tmp_path):
    build_archive(tmp_path / "raw" / "mibig" / FILENAME, extra={
        "mibig_json_4.0/broken.json": b"{ this is not json",
        "mibig_json_4.0/old_layout.json": json.dumps({"cluster": {}}).encode(),
    })
    result, nodes, _ = tidy_tables(make_adapter())
    assert result.counts["files_unreadable"] == 1
    assert result.counts["files_not_mibig4"] == 1
    assert "mibig:BGC0000433" in nodes


def test_tidy_without_a_download_explains_what_to_do(make_adapter):
    with pytest.raises(SourceError, match="python -m microbegraph.fetch --source mibig"):
        make_adapter().tidy()


def test_summary_file_is_written(make_adapter, archive_in_locker):
    result = make_adapter().tidy()
    summary = json.loads((result.nodes_path.parent / "mibig_summary.json").read_text())
    assert summary["source_version"] == "4.0"
    assert summary["counts"]["entries_active"] == 3
