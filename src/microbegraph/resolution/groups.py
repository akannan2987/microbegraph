"""
MicrobeGraph, keeping track of which records are the same thing.

THE IDEA: GROUPS THAT GROW BY JOINING
    Every identifier starts in a group of its own. When a rule decides that
    two identifiers are the same thing, their groups are joined. If A is
    joined to B, and later B to C, then A, B and C are one group, even though
    no rule compared A with C directly.

    Picture guests arriving at a party in small groups. Whenever two people
    turn out to know each other, their groups merge and stand together. At
    the end of the evening every cluster of people is one group, however it
    came about.

    Computer scientists call this structure "union-find" (or a disjoint-set
    forest). It answers two questions quickly: "are these two in the same
    group?" and "join these two groups".

WHICH IDENTIFIER NAMES THE GROUP
    When the groups are done, each one becomes one node, and the node needs
    one identifier. The identifier from the most specific public authority
    wins, as decided in docs/02-ontology-and-data-model.md, section 3:

        compounds   pubchem.compound  before  mg.compound
        proteins    uniprot           before  ncbiprotein  before  mg.protein

    Within the same kind, the identifier that sorts first wins, so the choice
    is the same on every run and every computer.

    While the joining is still going on, leader() gives the identifier that
    would name a group if it stopped now. A rule uses it to write its ledger
    row about the identifier that is about to disappear, not the one that
    stays.

THE GUARD AGAINST OVER-MERGING
    A group may hold at most ONE identifier from the top authority (one
    PubChem compound, or one UniProt entry). PubChem and UniProt have already
    decided those are different things, so a chain of joins that would put two
    of them in one group is refused, and the rule that asked for it records
    the refusal in the ledger.
"""

from __future__ import annotations

# The order of preference for the identifier that names a group (lower wins).
PREFIX_RANK: dict[str, int] = {
    "pubchem.compound": 0,
    "uniprot": 0,
    "mg.compound": 1,
    "ncbiprotein": 1,
    "mg.protein": 2,
}
OTHER_RANK = 5


def prefix_of(node_id: str) -> str:
    """The part of an identifier before the colon: "uniprot:Q70KJ7" -> "uniprot"."""
    return node_id.split(":", 1)[0]


def rank_key(node_id: str) -> tuple[int, str]:
    """How strongly an identifier should name its group: lower comes first."""
    return (PREFIX_RANK.get(prefix_of(node_id), OTHER_RANK), node_id)


def is_authority(node_id: str) -> bool:
    """True for a PubChem compound or a UniProt entry: the guard counts these."""
    return PREFIX_RANK.get(prefix_of(node_id), OTHER_RANK) == 0


class Groups:
    """Identifiers joined into groups of the same thing (union-find, see above)."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._authorities: dict[str, set[str]] = {}
        self._leaders: dict[str, str] = {}           # representative -> best member so far
        self._best: dict[str, str] | None = None     # filled in by settle()

    def find(self, node_id: str) -> str:
        """The current representative of a node's group (any member will do)."""
        parent = self._parent.setdefault(node_id, node_id)
        if parent == node_id:
            self._authorities.setdefault(node_id, {node_id} if is_authority(node_id) else set())
            self._leaders.setdefault(node_id, node_id)
            return node_id
        root = self.find(parent)
        self._parent[node_id] = root          # shortcut next time ("path compression")
        return root

    def same(self, a: str, b: str) -> bool:
        """Are a and b already in one group?"""
        return self.find(a) == self.find(b)

    def authorities(self, node_id: str) -> set[str]:
        """The PubChem or UniProt identifiers in a node's group (0 or 1 of them)."""
        return set(self._authorities[self.find(node_id)])

    def leader(self, node_id: str) -> str:
        """The identifier that would name a node's group if the joining stopped now."""
        return self._leaders[self.find(node_id)]

    def can_join(self, a: str, b: str) -> bool:
        """Would joining a and b keep at most one PubChem or UniProt id per group?"""
        return len(self.authorities(a) | self.authorities(b)) <= 1

    def join(self, a: str, b: str) -> None:
        """Put a and b in one group. Call can_join() first; this refuses otherwise."""
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return
        if not self.can_join(a, b):
            raise ValueError(f"{a} and {b} would put two authority identifiers in one group")
        self._parent[root_b] = root_a
        self._authorities[root_a] |= self._authorities.pop(root_b)
        self._leaders[root_a] = min(self._leaders[root_a], self._leaders.pop(root_b),
                                    key=rank_key)

    def settle(self) -> None:
        """Work out every group's naming identifier, once all the joining is done."""
        members: dict[str, list[str]] = {}
        for node_id in list(self._parent):
            members.setdefault(self.find(node_id), []).append(node_id)
        self._best = {root: min(ids, key=rank_key) for root, ids in members.items()}

    def canonical(self, node_id: str) -> str:
        """The identifier that names a node's group (see WHICH IDENTIFIER, above)."""
        if node_id not in self._parent:
            return node_id                       # never joined to anything: itself
        if self._best is None:
            raise RuntimeError("Groups.settle() must run before canonical()")
        return self._best[self.find(node_id)]
