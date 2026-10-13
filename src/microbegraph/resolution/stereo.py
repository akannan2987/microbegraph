"""
MicrobeGraph, comparing the 3D detail of two drawings of one molecule (Phase 4c).

WHY THIS EXISTS
    Clue 2 in compounds.py joins two PubChem records when the first block of
    their InChIKeys matches. That block describes the atoms and how they
    connect, and nothing about how they sit in space. Two molecules can share
    it and still be different compounds: stereoisomers, with the same atoms
    and bonds but a different 3D arrangement. The survey of the real data
    (docs/06c-checking-3d-detail.md, Step 2) found 66 of the 184 pairs clue 2
    had looked at in Phase 4b where the two records describe the 3D
    arrangement differently.
    This module finds out, place by place, whether two drawings agree.

WHAT "3D DETAIL" MEANS HERE
    It sits at two kinds of place, and a SMILES string marks both:
      * a chiral centre, usually a carbon with four different groups
        attached, written [C@H] or [C@@H]; chemists name its arrangement
        R or S
      * a double bond whose two ends can sit on the same side or on
        opposite sides, written with / and \\; chemists name it Z or E
    A drawing can leave any of these places open (no @, no slash). An open
    place agrees with anything: it only says "not described here".

HOW TWO DRAWINGS ARE COMPARED
    1. Read both SMILES with RDKit. RDKit keeps, for every described chiral
       centre, which way round its neighbours go (clockwise or anticlockwise,
       in the order it lists them), and for every described double bond,
       whether two named neighbours sit on the same side or on opposite
       sides.
    2. Match the atoms of one drawing to the atoms of the other. The match
       uses which heavy atoms connect to which, and how many hydrogens each
       carbon carries, so it doesn't mind a hydrogen moved between two
       nitrogens (a tautomer), a charge drawn another way (P+ O- instead of
       P=O), or a deuterium label.
    3. A molecule with symmetry can be matched in more than one way (turn a
       pair of scissors over and it still fits its outline). RDKit's
       canonical numbering gives one match at once; when a described place
       sits on a symmetric spot, every way is tried, and the one with the
       fewest disagreements is kept, so symmetry never invents a difference.
       Of the 5,797 structures in the data in October 2026 (2,522 PubChem
       records and 3,275 MIBiG structures), 129 needed that, and the most
       any needed was 1,536 tries.
    4. At every place both drawings describe, the arrangements are compared
       through the match: are the matched neighbours of a centre listed the
       same way round, or the other way round? Are the matched neighbours of
       a double bond on the same side? This compares the 3D arrangement
       itself. Comparing the names R/S and E/Z would be simpler but wrong in
       rare cases: the naming rules rank an atom's neighbours, and moving a
       hydrogen (a tautomer) can change the ranking, and with it the name,
       while nothing moved in space.

    The result counts the places that agree, the places that differ, and the
    places only one drawing describes. "agree" means no place differs.

WHY RDKIT
    It's the standard free library for chemistry in Python (BSD licence),
    used in research and industry. Reading SMILES and keeping track of how
    each centre is arranged is subtle, and a home-made version would be
    wrong in ways nobody would notice. The version is pinned in
    requirements.txt (docs/06c-checking-3d-detail.md, section 3, says why
    it's 2025.9.3).
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem, RDLogger

# RDKit prints a warning for every odd SMILES it meets. This module reports
# problems in its own words instead (status "unreadable").
RDLogger.DisableLog("rdApp.*")

# A safety limit on the number of ways to match two drawings, tried only
# when a described place sits on a symmetric spot. A molecule that reaches it
# is reported as "too symmetric" rather than guessed.
MAX_FITS = 10_000

CENTRE_TAGS = (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
SAME_SIDE = (Chem.BondStereo.STEREOZ, Chem.BondStereo.STEREOCIS)
BOND_STEREO = SAME_SIDE + (Chem.BondStereo.STEREOE, Chem.BondStereo.STEREOTRANS)


@dataclass(frozen=True)
class Comparison:
    """How the 3D detail of two drawings compares, place by place."""

    status: str                  # "agree", "differ", "unreadable", "other skeleton", "too symmetric"
    same_centres: int = 0        # chiral centres both describe, the same way
    same_bonds: int = 0          # double bonds both describe, the same way
    differing_centres: int = 0   # chiral centres described differently
    differing_bonds: int = 0     # double bonds described differently
    only_first: int = 0          # places only the first drawing describes
    only_second: int = 0         # places only the second drawing describes

    @property
    def agrees(self) -> bool:
        return self.status == "agree"

    @property
    def same(self) -> int:
        return self.same_centres + self.same_bonds

    @property
    def differing(self) -> int:
        return self.differing_centres + self.differing_bonds


def described(smiles: str) -> int | None:
    """How many places a drawing describes in 3D (None if RDKit can't read it)."""
    mol = _molecule(smiles)
    if mol is None:
        return None
    centres, bonds = _places(mol)
    return len(centres) + len(bonds)


def skeleton_key(smiles: str) -> str:
    """
    The first block of the InChIKey RDKit computes for a SMILES ("" if it
    can't read it). PubChem's records carry their own InChIKey; MIBiG's
    structures don't, so this is how a MIBiG structure is checked for the
    same skeleton as a PubChem record.
    """
    mol = _molecule(smiles)
    if mol is None:
        return ""
    return Chem.MolToInchiKey(mol).split("-")[0]


def compare(first: str, second: str) -> Comparison:
    """Compare the 3D detail of two SMILES strings for the same skeleton."""
    a, b = _molecule(first), _molecule(second)
    if a is None or b is None:
        return Comparison("unreadable")
    graph_a, atoms_a = _skeleton(a)
    graph_b, atoms_b = _skeleton(b)
    centres_a, bonds_a = _places(a)
    centres_b, bonds_b = _places(b)
    spots_a = set(centres_a) | {i for pair in bonds_a for i in pair}
    spots_b = set(centres_b) | {i for pair in bonds_b for i in pair}
    fits = _fits(graph_a, graph_b, atoms_a, atoms_b, spots_a, spots_b)
    if fits is None:
        return Comparison("other skeleton")
    if len(fits) >= MAX_FITS:
        return Comparison("too symmetric")
    best = None
    for fit in fits:
        # fit[i] is the atom of the first skeleton matched to atom i of the second;
        # translate both into atom numbers of the original drawings.
        to_a = {atoms_b[i]: atoms_a[j] for i, j in enumerate(fit)}
        same = [0, 0]
        differ = [0, 0]
        for atom in centres_b:
            if to_a[atom] in centres_a:
                verdict = _same_centre(a, b, to_a[atom], atom, to_a)
                if verdict is not None:
                    (same if verdict else differ)[0] += 1
        for end1, end2 in bonds_b:
            pair = _bond_key(to_a[end1], to_a[end2])
            if pair in bonds_a:
                verdict = _same_bond(a, b, pair, (end1, end2), to_a)
                if verdict is not None:
                    (same if verdict else differ)[1] += 1
        score = (sum(differ), -sum(same))
        if best is None or score < best[0]:
            best = (score, same, differ)
    _, same, differ = best
    shared = sum(same) + sum(differ)
    return Comparison(
        status="differ" if sum(differ) else "agree",
        same_centres=same[0], same_bonds=same[1],
        differing_centres=differ[0], differing_bonds=differ[1],
        only_first=len(centres_a) + len(bonds_a) - shared,
        only_second=len(centres_b) + len(bonds_b) - shared,
    )


def _same_centre(a: Chem.Mol, b: Chem.Mol, atom_a: int, atom_b: int,
                 to_a: dict[int, int]) -> bool | None:
    """
    Is a chiral centre arranged the same way in both drawings? None when it
    can't be told (a hydrogen with an isotope label sits on the centre).

    RDKit records a centre as clockwise or anticlockwise for the order in
    which it lists the centre's neighbours (a hydrogen not written as an
    atom has a fixed place in that order). Swapping two neighbours in the
    list turns clockwise into anticlockwise, so: put the second drawing's
    neighbours, matched, into the first drawing's order, count the swaps
    needed, and an even count with the same word (or an odd count with
    opposite words) means the same arrangement.
    """
    first = a.GetAtomWithIdx(atom_a)
    second = b.GetAtomWithIdx(atom_b)
    order_a = [n.GetIdx() for n in first.GetNeighbors()]
    order_b = [n.GetIdx() for n in second.GetNeighbors()]
    if any(a.GetAtomWithIdx(i).GetAtomicNum() == 1 for i in order_a) or \
            any(b.GetAtomWithIdx(i).GetAtomicNum() == 1 for i in order_b):
        return None
    matched = [to_a[i] for i in order_b]
    if sorted(matched) != sorted(order_a):
        return None
    swaps = _swaps([order_a.index(i) for i in matched])
    same_word = first.GetChiralTag() == second.GetChiralTag()
    return same_word == (swaps % 2 == 0)


def _same_bond(a: Chem.Mol, b: Chem.Mol, pair_a: tuple[int, int], pair_b: tuple[int, int],
               to_a: dict[int, int]) -> bool | None:
    """
    Is a double bond arranged the same way in both drawings? None when it
    can't be told.

    RDKit records, for each described double bond, one neighbour at each end
    and whether those two sit on the same side. For each end, check whether
    the second drawing's neighbour is matched to the first drawing's; each
    end where it isn't (the other neighbour at that end was chosen) turns
    "same side" into "opposite sides".
    """
    bond_a = a.GetBondBetweenAtoms(*pair_a)
    bond_b = b.GetBondBetweenAtoms(*pair_b)
    refs_a, refs_b = list(bond_a.GetStereoAtoms()), list(bond_b.GetStereoAtoms())
    if len(refs_a) != 2 or len(refs_b) != 2:
        return None
    ends_a = (bond_a.GetBeginAtomIdx(), bond_a.GetEndAtomIdx())
    ends_b = (bond_b.GetBeginAtomIdx(), bond_b.GetEndAtomIdx())
    turns = 0
    for end_b, ref_b in zip(ends_b, refs_b, strict=True):
        if ref_b not in to_a:                 # a neighbour that isn't a heavy atom
            return None
        ref_a = refs_a[ends_a.index(to_a[end_b])]
        if to_a[ref_b] != ref_a:
            turns += 1
    same_side_a = bond_a.GetStereo() in SAME_SIDE
    same_side_b = bond_b.GetStereo() in SAME_SIDE
    return same_side_b == (same_side_a if turns % 2 == 0 else not same_side_a)


def _swaps(positions: list[int]) -> int:
    """How many swaps of two neighbours put a list of positions in order."""
    return sum(1 for i in range(len(positions)) for j in range(i + 1, len(positions))
               if positions[i] > positions[j])


def _fits(graph_a: Chem.Mol, graph_b: Chem.Mol, atoms_a: list[int], atoms_b: list[int],
          spots_a: set[int], spots_b: set[int]) -> list | None:
    """
    The ways to match the second skeleton onto the first that matter for the
    comparison (None when the skeletons don't match). spots_a and spots_b are
    the atoms of the described places in each drawing.

    RDKit's canonical numbering gives one match straight away: both skeletons
    are numbered by the same rules, so atom number k of one is atom number k of
    the other. That match is the only one that matters unless a described
    place sits on a symmetric spot, an atom that has a twin somewhere else in
    the molecule. Only then are all the ways tried, up to MAX_FITS.
    """
    if (graph_a.GetNumAtoms() != graph_b.GetNumAtoms()
            or graph_a.GetNumBonds() != graph_b.GetNumBonds()):
        return None
    rank_a = list(Chem.CanonicalRankAtoms(graph_a, breakTies=True, includeChirality=False))
    rank_b = list(Chem.CanonicalRankAtoms(graph_b, breakTies=True, includeChirality=False))
    by_rank = {rank: i for i, rank in enumerate(rank_a)}
    fit = tuple(by_rank[rank] for rank in rank_b)
    same_elements = all(graph_a.GetAtomWithIdx(fit[i]).GetAtomicNum() == atom.GetAtomicNum()
                        and graph_a.GetAtomWithIdx(fit[i]).GetIsotope() == atom.GetIsotope()
                        for i, atom in enumerate(graph_b.GetAtoms()))
    same_bonds = all(graph_a.GetBondBetweenAtoms(fit[bond.GetBeginAtomIdx()],
                                                 fit[bond.GetEndAtomIdx()])
                     for bond in graph_b.GetBonds())
    if not (same_elements and same_bonds):
        # Numbered alike but not built alike. Usually another skeleton; the
        # full search below makes sure (it also catches the rare case where
        # the numbering rules can't tell two identical skeletons apart).
        fits = graph_a.GetSubstructMatches(graph_b, uniquify=False, useChirality=False,
                                           maxMatches=MAX_FITS)
        return list(fits) or None
    # Symmetry classes: atoms with the same class could swap places.
    classes = list(Chem.CanonicalRankAtoms(graph_a, breakTies=False, includeChirality=False))
    seen: dict[int, int] = {}
    for c in classes:
        seen[c] = seen.get(c, 0) + 1
    where_a = {old: new for new, old in enumerate(atoms_a)}
    where_b = {old: new for new, old in enumerate(atoms_b)}
    places = {where_a[i] for i in spots_a if i in where_a}
    places |= {fit[where_b[i]] for i in spots_b if i in where_b}
    if all(seen[classes[i]] == 1 for i in places):
        return [fit]
    return list(graph_a.GetSubstructMatches(graph_b, uniquify=False, useChirality=False,
                                            maxMatches=MAX_FITS))


# ------------------------------------------------------------------------ helpers
def _molecule(smiles: str) -> Chem.Mol | None:
    """Read a SMILES (None if it's missing or RDKit can't read it)."""
    if not smiles:
        return None
    return Chem.MolFromSmiles(smiles)


def _places(mol: Chem.Mol) -> tuple[dict[int, Chem.ChiralType],
                                    dict[tuple[int, int], Chem.BondStereo]]:
    """
    Every described chiral centre (atom -> clockwise or anticlockwise) and
    double bond (its two atoms -> same side or opposite). RDKit has already
    dropped a mark on an atom or bond that can't carry one.
    """
    centres = {atom.GetIdx(): atom.GetChiralTag() for atom in mol.GetAtoms()
               if atom.GetChiralTag() in CENTRE_TAGS}
    bonds = {_bond_key(bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()): bond.GetStereo()
             for bond in mol.GetBonds() if bond.GetStereo() in BOND_STEREO}
    return centres, bonds


def _bond_key(i: int, j: int) -> tuple[int, int]:
    return (i, j) if i < j else (j, i)


def _skeleton(mol: Chem.Mol) -> tuple[Chem.Mol, list[int]]:
    """
    The heavy atoms and which connect to which: every bond single, no
    charges, no isotope labels, and hydrogens only as a count on each carbon.
    Returns the skeleton and, for each of its atoms, the atom number in the
    original drawing.

    The count on carbons matters: without it, a carbon with a C=O and a
    carbon with a C-OH look alike, and a chiral centre could be matched with
    a ketone. The tautomers clue 2 meets move a hydrogen between nitrogen or
    oxygen atoms, so the carbons keep their counts and those tautomers still
    match. (A hydrogen that moves onto a carbon, as between a ketone and an
    enol, changes the first InChIKey block too, so clue 2 never pairs such
    records.) The count is kept in the atom's isotope field, which the
    matching compares.
    """
    keep = [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetAtomicNum() != 1]
    where = {old: new for new, old in enumerate(keep)}
    graph = Chem.RWMol()
    for old in keep:
        source = mol.GetAtomWithIdx(old)
        atom = Chem.Atom(source.GetAtomicNum())
        if source.GetAtomicNum() == 6:
            atom.SetIsotope(1 + source.GetTotalNumHs(includeNeighbors=True))
        atom.SetNoImplicit(True)
        graph.AddAtom(atom)
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        if i in where and j in where:
            graph.AddBond(where[i], where[j], Chem.BondType.SINGLE)
    skeleton = graph.GetMol()
    skeleton.UpdatePropertyCache(strict=False)
    Chem.FastFindRings(skeleton)
    return skeleton, keep
