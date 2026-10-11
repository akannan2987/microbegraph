"""
MicrobeGraph, the twelve rules, as code.

WHY THIS FILE EXISTS
    docs/02-ontology-and-data-model.md, section 9, lists twelve rules every
    row must obey: identifiers that look right, arrows that point at real
    dots, evidence that is one of the four levels, citations where they are
    required. A rule that exists only in a document is easy to break without
    anyone noticing, so this file turns each one into a check the computer runs.

WHO CALLS IT
    * Phase 1: every adapter's tidy() checks its own output before writing
      it, so a parsing bug is caught at the source, with the source's name
      on it, instead of three phases later.
    * Phase 4: the graph build runs exactly the same checks on the merged
      tables of all sources, and refuses to build if any fail.

    Both callers use the one function below.

WHY "REFUSE", NOT "WARN"
    Warnings tend to get scrolled past. A refusal gets fixed the same day,
    while you still remember what you were doing.

    Think of a web form that won't submit with an invalid email address: it's
    annoying the first time, and the addresses it collects are never wrong
    afterwards.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from microbegraph.ontology import (
    EDGE_TYPES,
    EVIDENCE_LEVELS,
    NODE_TYPES,
    REQUIRES_CITATION,
    is_valid_curie,
)


def check_tables(
    nodes: Iterable[dict[str, object]],
    edges: Iterable[dict[str, object]],
    external_node_types: dict[str, str] | None = None,
) -> list[str]:
    """
    Check node and edge rows against the twelve rules.

    Returns a list of problems as readable sentences; an EMPTY list means
    every rule passed. Each problem names its rule number, so you can look it
    up in docs/02-ontology-and-data-model.md, section 9.

    external_node_types lets a per-source check accept arrows that point at
    nodes another source will supply (node_id -> node_type). Phase 1 never
    needs it; the curated bridge in Phase 2 will.
    """
    nodes = list(nodes)
    edges = list(edges)
    problems: list[str] = []

    # ---------------------------------------------------------------- nodes
    counts = Counter(str(n.get("node_id", "")) for n in nodes)
    for node_id, n in counts.items():
        if n > 1:
            problems.append(f"rule 1: node_id {node_id!r} appears {n} times (must be unique)")

    node_type_of: dict[str, str] = dict(external_node_types or {})
    for node in nodes:
        node_id = str(node.get("node_id", ""))
        node_type = str(node.get("node_type", ""))
        if not is_valid_curie(node_id):
            problems.append(f"rule 2: node_id {node_id!r} is not prefix:localid with a known prefix")
        if node_type not in NODE_TYPES:
            problems.append(f"rule 3: node {node_id!r} has unknown node_type {node_type!r}")
        if not str(node.get("name", "")).strip():
            problems.append(f"rule 4: node {node_id!r} has an empty name")
        for column in ("source", "retrieved_at"):
            if not str(node.get(column, "")).strip():
                problems.append(f"rule 5: node {node_id!r} has no {column}")
        node_type_of[node_id] = node_type

    # ---------------------------------------------------------------- edges
    seen: Counter[tuple[str, str, str, str]] = Counter()
    for edge in edges:
        source_id = str(edge.get("source_id", ""))
        target_id = str(edge.get("target_id", ""))
        edge_type = str(edge.get("edge_type", ""))
        label = f"{source_id} --{edge_type}--> {target_id}"

        for end in (source_id, target_id):
            if end not in node_type_of:
                problems.append(f"rule 6: edge {label} points at {end!r}, which is not a node")

        if edge_type not in EDGE_TYPES:
            problems.append(f"rule 7: edge {label} has unknown edge_type")
        else:
            want_from, want_to = EDGE_TYPES[edge_type]
            got_from = node_type_of.get(source_id)
            got_to = node_type_of.get(target_id)
            if got_from and got_to and (got_from, got_to) != (want_from, want_to):
                problems.append(
                    f"rule 8: edge {label} connects {got_from} -> {got_to}; "
                    f"{edge_type} must connect {want_from} -> {want_to}"
                )

        level = str(edge.get("evidence_level", ""))
        if level not in EVIDENCE_LEVELS:
            problems.append(f"rule 9: edge {label} has unknown evidence_level {level!r}")
        if level in REQUIRES_CITATION and not str(edge.get("citation", "")).strip():
            problems.append(f"rule 10: edge {label} is {level} but has no citation")

        confidence = edge.get("confidence", "")
        if str(confidence).strip():
            try:
                value = float(confidence)  # type: ignore[arg-type]
            except ValueError:
                problems.append(f"rule 11: edge {label} has a confidence that is not a number")
            else:
                if not 0.0 <= value <= 1.0:
                    problems.append(f"rule 11: edge {label} has confidence {value}, outside 0-1")

        seen[(source_id, target_id, edge_type, str(edge.get("source", "")))] += 1

    for key, n in seen.items():
        if n > 1:
            problems.append(f"rule 12: edge {key[0]} --{key[2]}--> {key[1]} from {key[3]} "
                            f"appears {n} times")

    return problems
