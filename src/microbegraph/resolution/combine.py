"""
MicrobeGraph, turning groups of records into nodes, and re-pointing arrows.

ONE NODE PER GROUP
    After the rules have run, every identifier belongs to a group, and each
    group becomes one row of nodes.csv. Its identifier is the group's naming
    identifier (groups.py). Its other columns are combined like this:

    node_type   the same for every record, except that an Organism and a
                Pathogen together make a Pathogen (rule organism_and_pathogen)
    name        the name a reader is most likely to recognise:
                  organisms   NCBI's current scientific name (names change when
                              species are reclassified, and NCBI tracks that)
                  compounds   MIBiG's name ("tubulysin G", where PubChem's title
                  proteins    is often a long systematic name); the gene name
                              for proteins ("srfAA", not "Surfactin synthetase A")
                every other name the records use is kept in other_names
    properties  every property every record has (except that a PubChem number
                the rules didn't confirm is kept as pubchem_cid_not_confirmed,
                see compounds.py). When two SOURCES disagree
                about one property, the value from the source that knows best
                stays (PubChem for a formula, NCBI for a rank) and the other is
                kept as "<source>_<property>", e.g. mibig_formula. When two
                records from the SAME source differ (two protein numbers that
                became one protein), both values are kept, joined with |.
    source      every source that contributed, e.g. "mibig|pubchem"
    retrieved_at  the most recent date among them

    The rule is the one a careful editor follows when two drafts of a
    document are merged: nothing is thrown away, and wherever the drafts
    disagree, both versions stay visible.

RE-POINTING ARROWS
    Every arrow's two ends are replaced by their group's identifier. Two
    arrows can then become the same arrow (a cluster that PRODUCES both
    "erythromycin" and "erythromycin A" now produces one compound twice).
    Those are combined into one arrow that keeps the strongest evidence level,
    the highest confidence and every record number and citation. An arrow that
    loses an end (it pointed at an entry that was left out) is dropped and
    counted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from microbegraph.ontology import evidence_rank, is_a
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.names import name_key, split_list
from microbegraph.resolution.pool import SOURCE_ORDER, Pool
from microbegraph.staging import edge_row, node_row, properties_of

# Which source knows best, per node type, when two sources disagree.
PREFERRED_SOURCES: dict[str, tuple[str, ...]] = {
    "Organism": ("ncbi_taxonomy", "curation", "mibig"),
    "Pathogen": ("ncbi_taxonomy", "curation", "mibig"),
    "Compound": ("pubchem", "mibig"),
    "Protein": ("uniprot", "mibig"),
}

# Properties that are lists (pipe-separated): combined from every record.
LIST_PROPERTIES = frozenset({
    "synonyms", "other_names", "database_ids", "locations", "locus_tags", "found_in",
    "merged_from", "mibig_compound_ids", "mibig_protein_ids", "aliases", "resolution_notes",
})


class ResolutionError(Exception):
    """Records that can't be combined into one node (two incompatible types, say)."""


def _source_rank(node_type: str, source: str) -> int:
    order = PREFERRED_SOURCES.get(node_type, SOURCE_ORDER)
    return order.index(source) if source in order else len(order) + SOURCE_ORDER.index(source)


def _choose_type(node_id: str, types: set[str]) -> str:
    if len(types) == 1:
        return next(iter(types))
    # A kind of a type wins over the type itself: Organism + Pathogen -> Pathogen.
    specific = [t for t in types if all(is_a(t, other) for other in types)]
    if len(specific) == 1:
        return specific[0]
    raise ResolutionError(f"{node_id} would combine records of types {sorted(types)}, "
                          f"which can't be one node")


def _choose_name(node_type: str, rows: list[tuple[str, dict[str, str]]],
                 final_id: str) -> str:
    """The name for a combined node (see ONE NODE PER GROUP, above)."""
    if node_type in ("Compound", "Protein"):
        mibig = sorted((i, r) for i, r in rows if r["source"] == "mibig")
        if mibig:
            if node_type == "Compound":
                titles = {name_key(r["name"]) for _, r in rows if r["source"] == "pubchem"}
                for _, row in mibig:
                    if name_key(row["name"]) in titles:
                        return row["name"]
            return mibig[0][1]["name"]
    ranked = sorted(rows, key=lambda item: (_source_rank(node_type, item[1]["source"]),
                                            item[0] != final_id, item[0]))
    return ranked[0][1]["name"]


def _combine_properties(node_type: str, rows: list[tuple[str, dict[str, str]]],
                        name: str, aliases: list[str], notes: list[str],
                        renames: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Every record's properties in one dict (see ONE NODE PER GROUP, above)."""
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for identifier, row in rows:
        props = properties_of(row)
        for old, new in renames.get(identifier, {}).items():   # an unconfirmed number, say
            if row["source"] == "mibig" and old in props:
                props[new] = props.pop(old)
        by_source[row["source"]].append(props)
    sources = sorted(by_source, key=lambda s: _source_rank(node_type, s))

    combined: dict[str, Any] = {}
    lists: dict[str, list[str]] = defaultdict(list)
    for source in sources:
        values: dict[str, list[Any]] = defaultdict(list)
        for props in by_source[source]:
            for key, value in props.items():
                if key in LIST_PROPERTIES:
                    for part in split_list(value):
                        if part not in lists[key]:
                            lists[key].append(part)
                elif value not in values[key] and str(value) not in map(str, values[key]):
                    values[key].append(value)
        for key, found in values.items():
            value = found[0] if len(found) == 1 else "|".join(map(str, found))
            if key not in combined:
                combined[key] = value
            elif str(combined[key]) != str(value):
                combined[f"{source}_{key}"] = value     # the other source's view, kept

    other_names = [row["name"] for _, row in rows if row["name"] and row["name"] != name]
    for other in other_names:
        if other not in lists["other_names"]:
            lists["other_names"].append(other)
    lists["aliases"] = list(aliases)
    lists["resolution_notes"] += [n for n in notes if n not in lists["resolution_notes"]]
    for key, items in lists.items():
        if items:
            combined[key] = "|".join(items)
    return combined


def combine_nodes(pool: Pool, final_id: Callable[[str], str], ledger: Ledger,
                  notes: dict[str, list[str]], renames: dict[str, dict[str, str]],
                  ) -> tuple[list[dict[str, Any]], set[str]]:
    """
    Build one node row per group. Returns (rows, identifiers left out).

    final_id(identifier) gives the group's naming identifier. A group whose
    records all come from PubChem or UniProt is left out: those sources only
    describe compounds and proteins MIBiG named, so an entry nothing joined
    belongs to nothing in the graph.
    """
    buckets: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for node_id, rows in pool.rows.items():
        for row in rows:
            buckets[final_id(node_id)].append((node_id, row))

    out: list[dict[str, Any]] = []
    left_out: set[str] = set()
    for node_id in sorted(buckets):
        rows = buckets[node_id]
        sources = [s for s in SOURCE_ORDER if any(r["source"] == s for _, r in rows)]
        identifiers = sorted({i for i, _ in rows})
        types = {r["node_type"] for _, r in rows}

        if set(sources) <= {"pubchem", "uniprot"}:
            for identifier in identifiers:
                left_out.add(identifier)
                ledger.add("not_used", "left_out", identifier, next(iter(types)),
                           _why_not_used(pool, identifier), sources="|".join(sources))
            continue

        node_type = _choose_type(node_id, types)
        for identifier in identifiers:
            here = pool.sources(identifier)
            if len(here) > 1:
                ledger.add("same_identifier", "combined", identifier, node_type,
                           f"{len(here)} sources describe {identifier}: "
                           f"{', '.join(here)}.", sources="|".join(here))
        if len(types) > 1:
            roles = "; ".join(
                f"{s} has it as {t}" for s, t in sorted({(r['source'], r['node_type'])
                                                          for _, r in rows}))
            ledger.add("organism_and_pathogen", "combined", node_id, node_type,
                       f"{roles}. A Pathogen is a kind of Organism, so one {node_type} node "
                       f"keeps both roles.", sources="|".join(sources))

        name = _choose_name(node_type, rows, node_id)
        aliases = [i for i in identifiers if i != node_id]
        node_notes = [n for i in identifiers for n in notes.get(i, [])]
        props = _combine_properties(node_type, rows, name, aliases, node_notes, renames)
        retrieved_at = max(r["retrieved_at"] for _, r in rows)
        out.append(node_row(node_id, node_type, name, props, "|".join(sources), retrieved_at))
    return out, left_out


def combine_edges(pool: Pool, final_id: Callable[[str], str],
                  left_out: set[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Re-point every arrow to the combined nodes, and combine arrows that became
    the same arrow (see RE-POINTING ARROWS, above). Returns (rows, counts).

    Only arrows at an entry that was LEFT OUT are dropped. An arrow pointing
    at an identifier no source has is kept as it is, so the twelve rules
    catch it (rule 6) instead of it vanishing quietly.
    """
    counts = {"edges_read": len(pool.edges), "edges_dropped_at_left_out_nodes": 0,
              "edges_that_became_loops": 0, "edges_combined": 0}
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for edge in pool.edges:
        start, end = final_id(edge["source_id"]), final_id(edge["target_id"])
        if start in left_out or end in left_out:
            counts["edges_dropped_at_left_out_nodes"] += 1
            continue
        if start == end:
            counts["edges_that_became_loops"] += 1
            continue
        key = (start, end, edge["edge_type"], edge["source"])
        if key not in merged:
            merged[key] = {**edge, "source_id": start, "target_id": end}
            continue
        counts["edges_combined"] += 1
        merged[key] = _stronger_together(merged[key], edge)

    rows = [edge_row(e["source_id"], e["target_id"], e["edge_type"], e["evidence_level"],
                     e["source"], e["source_record_id"], e["retrieved_at"],
                     e["citation"], e["confidence"]) for e in merged.values()]
    return rows, counts


def _stronger_together(kept: dict[str, Any], other: dict[str, str]) -> dict[str, Any]:
    """Two records of one arrow, combined: the strongest evidence, every reference."""
    def joined(column: str) -> str:
        return "|".join(dict.fromkeys(split_list(kept[column]) + split_list(other[column])))

    result = dict(kept)
    if evidence_rank(other["evidence_level"]) < evidence_rank(kept["evidence_level"]):
        result["evidence_level"] = other["evidence_level"]
    result["source_record_id"] = joined("source_record_id")
    result["citation"] = joined("citation")
    confidences = [c for c in (kept["confidence"], other["confidence"]) if str(c).strip()]
    if confidences:
        result["confidence"] = max(confidences, key=float)
    result["retrieved_at"] = max(kept["retrieved_at"], other["retrieved_at"])
    return result


def _why_not_used(pool: Pool, identifier: str) -> str:
    """The ledger's sentence for an entry no MIBiG record ended up joined to."""
    if identifier.startswith("pubchem.compound:"):
        asked = split_list(pool.props(identifier, "pubchem").get("mibig_compound_ids"))
        return (f"No MIBiG compound that gave this number was confirmed as this molecule "
                f"({', '.join(asked)}; see their pubchem_number rows), so the entry "
                f"describes nothing in the graph.")
    asked = split_list(pool.props(identifier, "uniprot").get("mibig_protein_ids"))
    return (f"None of the protein numbers that led to this entry joined it "
            f"({', '.join(asked)}; see their uniprot_cross_reference rows), so the entry "
            f"describes nothing in the graph.")
