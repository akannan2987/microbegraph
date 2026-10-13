"""
MicrobeGraph, resolving compounds.

THE SITUATION
    MIBiG names 3,842 compounds and gives a PubChem number (a CID) for about a
    third of them. Phase 2 fetched PubChem's own record for each of those
    numbers, so the graph has two records for the same molecule: MIBiG's
    mg.compound:erythromycin-a and PubChem's pubchem.compound:12560. Each
    PubChem record remembers which MIBiG compounds gave its number
    (mibig_compound_ids), so finding the pairs is easy.

WHY A SHARED NUMBER ISN'T ENOUGH
    The numbers were typed in by people, and the survey of the real data
    (docs/06-entity-resolution-graph-build.md, Step 2) found that some point
    at a different molecule. MIBiG gives "bacillomycin D" the number of
    PubChem's "Bacillomycin Fc", a relative with a different formula, and it
    gives "minutissamide B" and "minutissamide C" the number of
    "Minutissamide D". Joining on the number alone would quietly move facts
    about one molecule onto another. So a number needs a second, independent
    clue before two records become one node.

THE CLUES, FROM STRONGEST TO WEAKEST (Phase 4, extended in Phase 4b)
    For each MIBiG compound the candidates are every PubChem number its
    entries give (from Phase 4b, all of them, not only the first; see
    pubchem_cid_by_entry in mibig.py) and every number PubChem's name search
    returned for its name (Phase 4b, see pubchem.py). Each candidate is
    judged on these clues, and the strongest decides:

    1. name     MIBiG gives the number, and PubChem lists MIBiG's name under
                it: as the title, in the first 20 synonyms, or (Phase 4b)
                anywhere in its full list of names; or PubChem's name search
                returns this very number. Two independent sources agree.

    2. same structure  (Phase 4b) MIBiG gives the number, PubChem files the
                name under a DIFFERENT number, and the two records share the
                first block of their InChIKey. An InChIKey is a fingerprint
                of a structure in three blocks; the first block encodes the
                atoms and how they connect, and leaves out the 3D arrangement.
                PubChem often keeps one record per way of drawing a molecule
                (with its 3D arrangement, without it...), and only one of
                them carries the name. A salt isn't one of these: its metal
                is part of the first block. Two library copies of one book,
                one with a library stamp on the cover and one without, are
                still the same book.

                One exception (a Phase 4b follow-up): the first block leaves
                out isotopes too, so a record built with an unusual isotope,
                such as PubChem's "[55Fe] Ferrichrome" with radioactive
                iron-55, shares it with the ordinary molecule. That record is a
                tracer made in a laboratory, not the compound a microbe makes,
                so clue 2 doesn't confirm a number whose record carries an
                isotope label (a mass number in its SMILES, as in [55Fe+3])
                when the record PubChem files the name under has none. The
                name's own record is then the candidate that wins.

                From Phase 4c the 3D detail is checked as well (stereo.py).
                Two records that share the first block can still be
                stereoisomers: the same atoms and bonds arranged differently
                in space, which makes them different compounds. Clue 2 counts
                only when the two records describe every place they both
                describe (chiral centres, and double bonds that can be E or Z)
                the same way. When they disagree, MIBiG's own structure (the
                SMILES in its entry) decides: the record whose 3D detail it
                matches is the compound, whether that's MIBiG's number or the
                record PubChem files the name under. When MIBiG's structure
                can't tell (there is none, it gives no 3D detail, it has
                another skeleton, it matches neither or both, or MIBiG's
                entries disagree), neither record is joined, and the ledger
                says a person should decide. A decision in the review file
                still comes first: echinomycin has one, because MIBiG's
                structure there matches the record its number points at and
                the literature gives the other record's 3D detail
                (docs/06c-checking-3d-detail.md, Step 5).

    3. name search  (Phase 4b) MIBiG gives no number that passes 1 or 2, but
                PubChem's name search finds the name under exactly one
                number whose formula agrees with MIBiG's.

    4. formula alone  MIBiG gives the number and the formulas agree, but
                PubChem lists the name nowhere. This was enough in Phase 4,
                and 325 joins rested on it. From Phase 4b it no longer is in
                two cases: when the name search points at a different molecule
                (a different first InChIKey block), and when MIBiG's own
                entries give the compound different formulas (formula_by_entry),
                since one of them agreeing proves little. MIBiG's
                "2-methylisoborneol" carries a bromine compound's number,
                formula and structure in one entry, so its formula agrees for
                the wrong reason; MIBiG's two formulas for ferrichrome (with and
                without its iron) would let it join PubChem's record of a
                radioactive form of iron in ferrichrome.

    A number several MIBiG compounds give (rule pubchem_number_shared) is
    only joined on clue 1: minutissamides B, C and D share a formula but are
    different molecules, so neither a formula nor a shared structure key
    can tell them apart.

    Two candidates on the same level that are different records stay apart
    from the compound, and the ledger lists both: choosing would be a guess.

THE RULES IN THE LEDGER
    pubchem_number_confirmed  one number from MIBiG; clue 1, 2 or 4
    pubchem_number_shared     a number several MIBiG compounds give; clue 1 only
    pubchem_numbers_differ    (Phase 4b) MIBiG gives more than one number, in
                              different entries or in one
    pubchem_name_search       (Phase 4b) a number only the name search found
    pubchem_number_unknown    a number PubChem doesn't have
    npatlas_and_formula       two MIBiG compounds with one NPAtlas number and one formula

    Every candidate that isn't joined gets a kept_apart row with the reason.
    The MIBiG compound keeps a note saying so, and an unconfirmed number from
    MIBiG moves from pubchem_cid to pubchem_cid_not_confirmed, so nobody
    filtering on pubchem_cid mistakes it for a confirmed one.

    A pair a person has settled in curation/resolution_decisions.csv
    (reviewed.py) is left alone by every rule here.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from microbegraph.resolution import stereo
from microbegraph.resolution.groups import Groups, rank_key
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.names import compare_formulas, name_key, split_list
from microbegraph.resolution.pool import Pool
from microbegraph.resolution.reviewed import Reviewed

FORMULA_WORDS = {
    "agrees": "the formulas agree ({a})",
    "agrees_but_charge": "the formulas agree once the charge is ignored ({a} and {b})",
    "differs": "the formulas differ (MIBiG {a}, PubChem {b})",
    "missing": "there's no formula to compare",
}
GOOD_FORMULA = ("agrees", "agrees_but_charge")

# How strong each clue is (lower is stronger), and the words the ledger uses.
NAME, SAME_STRUCTURE, NAME_SEARCH, FORMULA_ONLY, NONE = range(5)


def _mibig_names(pool: Pool, node_id: str) -> set[str]:
    """The name keys a MIBiG compound goes by: its name, synonyms and other names."""
    props = pool.props(node_id, "mibig")
    names = [pool.name(node_id, "mibig")]
    names += split_list(props.get("synonyms")) + split_list(props.get("other_names"))
    return {key for key in map(name_key, names) if key}


def _pubchem_names(pool: Pool, node_id: str) -> set[str]:
    """
    The name keys PubChem gives a compound: its title, its first 20 synonyms
    and (Phase 4b) the names further down its full list that match a MIBiG name.
    """
    props = pool.props(node_id, "pubchem")
    names = ([pool.name(node_id, "pubchem")] + split_list(props.get("synonyms"))
             + split_list(props.get("names_matching_mibig")))
    return {key for key in map(name_key, names) if key}


def _skeleton(pool: Pool, pubchem_id: str) -> str:
    """The first block of a PubChem record's InChIKey ("" if it has none)."""
    return str(pool.props(pubchem_id, "pubchem").get("inchikey") or "").split("-")[0]


# An atom written with a mass number in a SMILES string: [55Fe+3], [13CH3], [2H].
ISOTOPE_ATOM = re.compile(r"\[\d+[A-Z][a-z]?")


def _isotope_label(pool: Pool, pubchem_id: str) -> str:
    """The first isotope-labelled atom in a PubChem record's SMILES ("" if none)."""
    found = ISOTOPE_ATOM.search(_smiles(pool, pubchem_id))
    return found.group(0)[1:] if found else ""


def _smiles(pool: Pool, pubchem_id: str) -> str:
    """A PubChem record's SMILES, with its 3D marks ("" if it has none)."""
    return str(pool.props(pubchem_id, "pubchem").get("smiles") or "")


def _places(centres: int, bonds: int) -> str:
    """'2 chiral centres', '1 double bond', '1 chiral centre and 3 double bonds'."""
    parts = []
    if centres:
        parts.append(f"{centres} chiral centre{'s' if centres != 1 else ''}")
    if bonds:
        parts.append(f"{bonds} double bond{'s' if bonds != 1 else ''}")
    return " and ".join(parts)


def _more(n: int) -> str:
    return f"{n} more place{'s' if n != 1 else ''}"


def _agreement(check: stereo.Comparison, c: Candidate, twin: Candidate) -> str:
    """How two records' 3D detail agrees, in words (Phase 4c)."""
    if check.same == 0:
        if not check.only_first and not check.only_second:
            return "neither describes any place in 3D"
        if not check.only_first:
            return f"CID {c.cid} describes no place in 3D, so nothing can disagree"
        if not check.only_second:
            return f"CID {twin.cid} describes no place in 3D, so nothing can disagree"
        return (f"they describe different places in 3D ({check.only_first} and "
                f"{check.only_second}), so nothing can disagree")
    shared = check.same
    text = (f"their 3D detail agrees at the {shared} place{'s' if shared != 1 else ''} "
            f"both describe")
    if check.only_first and check.only_second:
        return (f"{text}, and each describes places the other leaves open "
                f"(CID {c.cid} {check.only_first}, CID {twin.cid} {check.only_second})")
    if check.only_first:
        return f"{text}, and CID {c.cid} describes {_more(check.only_first)}"
    if check.only_second:
        return f"{text}, and CID {twin.cid} describes {_more(check.only_second)}"
    return text


# Words for a pair the 3D check leaves for a person. _decide removes them when
# another candidate was joined after all (kosinostatin's second number), so
# the ledger never asks a person to decide something already decided.
PERSON = ", so a person should decide between them"

NOT_COMPARED = {
    "unreadable": "one of the two records has no SMILES, or RDKit can't read it",
    "other skeleton": "their atoms can't be matched one to one",
    "too symmetric": "the molecule has too many symmetric ways to match its atoms",
}


def _gap(check: stereo.Comparison) -> str:
    """'differs in 3D at 2 chiral centres', or why the 3D detail couldn't be compared."""
    if check.status == "differ":
        return f"differs in 3D at {_places(check.differing_centres, check.differing_bonds)}"
    return f"can't be compared in 3D ({NOT_COMPARED[check.status]})"


def _mibig_side(pool: Pool, mibig_id: str, given_id: str, twin_id: str) -> tuple[str, str]:
    """
    Which of two records that disagree in 3D MIBiG's own structure matches
    (Phase 4c): ("given", ""), ("twin", ""), or ("", the reason it can't tell).
    Every structure MIBiG's entries give for the compound is asked; they must
    all point the same way.
    """
    props = pool.props(mibig_id, "mibig")
    structures = [item.partition(": ")[2] for item in split_list(props.get("smiles_by_entry"))]
    if not structures and props.get("smiles"):
        structures = [str(props["smiles"])]
    if not structures:
        return "", "MIBiG gives no structure of its own"
    skeleton = _skeleton(pool, given_id)
    sides: set[str] = set()
    found: set[str] = set()
    for smiles in structures:
        key = stereo.skeleton_key(smiles)
        if not key:
            found.add("unreadable")
        elif key != skeleton:
            found.add("other skeleton")
        elif not stereo.described(smiles):
            found.add("flat")
        else:
            given = stereo.compare(smiles, _smiles(pool, given_id))
            twin = stereo.compare(smiles, _smiles(pool, twin_id))
            if {given.status, twin.status} - {"agree", "differ"}:
                found.add("not compared")
                continue
            sides.add({(True, False): "given", (False, True): "twin",
                       (True, True): "both", (False, False): "neither"}[
                given.agrees, twin.agrees])
    decisive = sides - {"both"}
    if decisive in ({"given"}, {"twin"}):
        return decisive.pop(), ""
    if len(decisive) > 1:
        return "", "MIBiG's entries give structures that disagree with each other"
    if decisive == {"neither"}:
        return "", "MIBiG's own structure differs from both"
    if sides == {"both"}:
        return "", ("MIBiG's own structure agrees with both (it leaves open the places "
                    "where they differ)")
    for kind, reason in (("other skeleton", "MIBiG's own structure has another skeleton"),
                         ("flat", "MIBiG's own structure gives no 3D detail"),
                         ("unreadable", "RDKit can't read MIBiG's own structure"),
                         ("not compared", "MIBiG's own structure can't be compared in 3D")):
        if kind in found:
            return "", reason
    return "", "MIBiG's own structure can't tell them apart"


@dataclass
class Candidate:
    """One PubChem record a MIBiG compound might be, and what the evidence says."""

    pubchem_id: str
    given: bool                       # MIBiG gives this number
    found: bool                       # the name search returned it
    shared: bool                      # several MIBiG compounds give it
    named: bool                       # PubChem lists the name, or the search found it here
    formula: str                      # "agrees", "differs"...
    formula_text: str
    formulas: list[str] = field(default_factory=list)  # MIBiG's formulas for this number
    entries: list[str] = field(default_factory=list)   # the entries that give it
    others: list[str] = field(default_factory=list)    # other MIBiG compounds giving it
    level: int = NONE
    why: str = ""
    how: str = ""                     # the ledger's closing words, when not the usual ones
    three_d: str = ""                 # Phase 4c: agree, kept, moved, undecided, not compared
    twin_id: str = ""                 # Phase 4c: the name's record that clue 2 compared it with

    @property
    def cid(self) -> str:
        return self.pubchem_id.split(":", 1)[1]


def _formulas_for(pool: Pool, mibig_id: str, entries: list[str]) -> list[str]:
    """
    The formulas MIBiG gives this compound, from the entries named (all of
    them when none are named). From Phase 4b a compound can carry several
    (formula_by_entry); otherwise it's the one formula.
    """
    props = pool.props(mibig_id, "mibig")
    by_entry = [item.partition(": ") for item in split_list(props.get("formula_by_entry"))]
    if by_entry:
        chosen = [f for entry, _, f in by_entry if not entries or entry in entries]
        return list(dict.fromkeys(chosen)) or [str(props.get("formula") or "")]
    return [str(props.get("formula") or "")]


def _given_entries(pool: Pool, mibig_id: str) -> dict[str, list[str]]:
    """CID -> the entries that give it, from pubchem_cid_by_entry (empty if they all agree)."""
    found: dict[str, list[str]] = defaultdict(list)
    for item in split_list(pool.props(mibig_id, "mibig").get("pubchem_cid_by_entry")):
        entry, _, cid = item.partition(": ")
        found[cid.strip()].append(entry.strip())
    return dict(found)


def _candidates(pool: Pool, mibig_id: str, given: list[str], found: list[str],
                claims: dict[str, list[str]]) -> list[Candidate]:
    """Every PubChem record this compound might be, each judged on the clues."""
    ours = _mibig_names(pool, mibig_id)
    entries = _given_entries(pool, mibig_id)
    result = []
    for pubchem_id in sorted(set(given) | set(found), key=rank_key):
        cid = pubchem_id.split(":", 1)[1]
        props = pool.props(pubchem_id, "pubchem")
        theirs = props.get("formula")
        formulas = _formulas_for(pool, mibig_id, entries.get(cid, []) if pubchem_id in given else [])
        states = [compare_formulas(f, theirs) for f in formulas]
        state = next((s for s in states if s in GOOD_FORMULA), states[0] if states else "missing")
        shown = next((f for f, s in zip(formulas, states, strict=True) if s == state), formulas[0] if formulas else "")
        is_found = pubchem_id in found
        result.append(Candidate(
            pubchem_id=pubchem_id, given=pubchem_id in given, found=is_found,
            shared=len(claims.get(pubchem_id, [])) > 1,
            named=bool(ours & _pubchem_names(pool, pubchem_id)) or is_found,
            formula=state, formula_text=FORMULA_WORDS[state].format(a=shown, b=theirs),
            formulas=[f for f in formulas if f], entries=entries.get(cid, []),
            others=[pool.name(m, "mibig") for m in claims.get(pubchem_id, []) if m != mibig_id]))
    return result


def _judge(pool: Pool, mibig_id: str, candidates: list[Candidate],
           name_search_ran: bool = True) -> None:
    """Set each candidate's level (the strongest clue it has) and the words for the ledger."""
    name = pool.name(mibig_id, "mibig")
    found_elsewhere = [c for c in candidates if c.found and c.named]
    several_given = sum(1 for c in candidates if c.given) > 1
    verdicts: dict[str, list[tuple[str, str]]] = defaultdict(list)   # Phase 4c, see below
    for c in candidates:
        title = pool.name(c.pubchem_id, "pubchem")
        if c.given and c.named:
            c.level = NAME
            how = (f"PubChem's name search returns this number for '{name}'" if c.found
                   else f"PubChem lists the name '{name}'")
            c.why = f"{how}; {c.formula_text}"
            continue
        if c.given and not c.shared:
            twin = next((f for f in found_elsewhere if f.pubchem_id != c.pubchem_id
                         and _skeleton(pool, f.pubchem_id)
                         and _skeleton(pool, f.pubchem_id) == _skeleton(pool, c.pubchem_id)), None)
            label = _isotope_label(pool, c.pubchem_id) if twin is not None else ""
            if twin is not None and label and not _isotope_label(pool, twin.pubchem_id):
                # Phase 4b follow-up: an isotope-labelled tracer, not the compound itself
                c.why = (f"PubChem doesn't list the name '{name}' under CID {c.cid} (its title "
                         f"is '{title}'), and this record is built with the isotope {label}. "
                         f"PubChem files the name under CID {twin.cid}, the same structure "
                         f"without the isotope, so that record is the compound; "
                         f"{c.formula_text}")
                continue
            if twin is not None:
                _judge_same_structure(pool, mibig_id, c, twin, title, verdicts)
                continue
            elsewhere = [f for f in found_elsewhere if f.pubchem_id != c.pubchem_id]
            disputed = len(set(c.formulas)) > 1
            if c.formula in GOOD_FORMULA and disputed and not elsewhere:
                c.why = (f"PubChem doesn't list the name '{name}' (its title is '{title}'); "
                         f"MIBiG's entries give it different formulas "
                         f"({', '.join(dict.fromkeys(c.formulas))}), so one of them agreeing "
                         f"with PubChem's ({pool.props(c.pubchem_id, 'pubchem').get('formula')}) "
                         f"can't confirm the number")
                continue
            if c.formula in GOOD_FORMULA and not elsewhere and not several_given:
                c.level = FORMULA_ONLY
                searched = (", and its name search finds the name under no other number"
                            if name_search_ran else "")
                c.why = (f"PubChem doesn't list the name '{name}' (its title is '{title}')"
                         f"{searched}; {c.formula_text}")
                continue
            if c.formula in GOOD_FORMULA and elsewhere:
                others = ", ".join(f"CID {f.cid}" for f in elsewhere)
                c.why = (f"PubChem doesn't list the name '{name}' (its title is '{title}') "
                         f"and files it under {others}, a different molecule (another "
                         f"structure key), so the formula alone isn't trusted; {c.formula_text}")
                continue
            c.why = (f"PubChem doesn't list the name '{name}' (its title is '{title}'); "
                     f"{c.formula_text}")
            continue
        if c.given:          # shared, and the name isn't listed
            c.why = (f"PubChem doesn't list the name '{name}', and with several MIBiG "
                     f"compounds on one number a formula can't tell isomers apart; "
                     f"{c.formula_text}")
            continue
        if c.formula in GOOD_FORMULA:
            c.level = NAME_SEARCH
            c.why = (f"PubChem's name search finds '{name}' under CID {c.cid} ('{title}'); "
                     f"{c.formula_text}")
        else:
            c.why = (f"PubChem's name search finds '{name}' under CID {c.cid} ('{title}'), "
                     f"but {c.formula_text}")
    # Phase 4c: a record the name search found, judged against a number MIBiG
    # gives that differs from it in 3D. Done after the loop, because the loop
    # may reach the found record before the number. Two cases are left alone:
    # a record MIBiG gives too (its own clues judge it, clue 1 first), and a
    # record another number MIBiG gives agrees with in 3D (that number is
    # the same molecule, and clue 2 joins it as usual).
    agreeing = {c.twin_id for c in candidates if c.three_d == "agree"}
    for c in candidates:
        if c.pubchem_id not in verdicts or c.given or c.pubchem_id in agreeing:
            continue
        title = pool.name(c.pubchem_id, "pubchem")
        kinds = [kind for kind, _ in verdicts[c.pubchem_id]]
        kind, text = next(v for v in verdicts[c.pubchem_id]
                          if v[0] == ("undecided" if "undecided" in kinds else
                                      "moved" if "moved" in kinds else "kept"))
        lead = f"PubChem's name search finds '{name}' under CID {c.cid} ('{title}')"
        if kind == "moved":
            c.level = SAME_STRUCTURE
            c.how = "Confirmed by name and by MIBiG's own 3D structure."
            c.why = f"{lead}, and MIBiG's own structure matches its 3D detail; {text}; {c.formula_text}"
        elif kind == "undecided":
            c.level = NONE
            c.why = f"{lead}, but {text}{PERSON}"
        else:
            c.why = f"{lead}, but {text}; {c.formula_text}"


def _judge_same_structure(pool: Pool, mibig_id: str, c: Candidate, twin: Candidate, title: str,
                          verdicts: dict[str, list[tuple[str, str]]]) -> None:
    """
    Clue 2 with the 3D check (Phase 4c). c is a number MIBiG gives; twin is
    the record PubChem files the name under, with the same skeleton. Sets c's
    level and words, and leaves a verdict for twin (applied after the loop).
    """
    name = pool.name(mibig_id, "mibig")
    skeleton = _skeleton(pool, c.pubchem_id)
    c.twin_id = twin.pubchem_id
    check = stereo.compare(_smiles(pool, c.pubchem_id), _smiles(pool, twin.pubchem_id))
    opening = (f"PubChem doesn't list the name '{name}' under CID {c.cid} (its title is "
               f"'{title}')")
    if check.agrees:
        c.level = SAME_STRUCTURE
        c.three_d = "agree"
        c.why = (f"{opening}, but files it under CID {twin.cid}, the same molecule drawn "
                 f"another way: both InChIKeys start {skeleton}, and "
                 f"{_agreement(check, c, twin)}; {c.formula_text}")
        return
    gap = _gap(check)
    record = (f"CID {twin.cid}, a record with the same skeleton (both InChIKeys start "
              f"{skeleton}) that {gap}")
    side, reason = (_mibig_side(pool, mibig_id, c.pubchem_id, twin.pubchem_id)
                    if check.status == "differ" else ("", ""))
    number = f"CID {c.cid}, the number MIBiG gives, has the same skeleton and {gap}"
    if side == "given":
        c.level = SAME_STRUCTURE
        c.three_d = "kept"
        c.how = "Confirmed through the same skeleton and MIBiG's own 3D structure."
        c.why = (f"{opening}, but files it under {record}; MIBiG's own structure matches "
                 f"CID {c.cid}, so the number MIBiG gives stands; {c.formula_text}")
        verdicts[twin.pubchem_id].append(
            ("kept", f"{number}, and MIBiG's own structure matches CID {c.cid}"))
    elif side == "twin":
        c.three_d = "moved"
        c.why = (f"{opening}, and files it under {record}; MIBiG's own structure matches "
                 f"CID {twin.cid}, so this record is another stereoisomer; {c.formula_text}")
        verdicts[twin.pubchem_id].append(("moved", number))
    else:
        c.three_d = "undecided" if check.status == "differ" else "not compared"
        because = f", and {reason}" if reason else ""
        c.why = f"{opening}, and files it under {record}{because}{PERSON}; {c.formula_text}"
        verdicts[twin.pubchem_id].append(("undecided", f"{number}{because}"))


def _rule_for(c: Candidate, several_given: bool) -> str:
    if not c.given:
        return "pubchem_name_search"
    if c.shared:
        return "pubchem_number_shared"
    return "pubchem_numbers_differ" if several_given else "pubchem_number_confirmed"


def join_pubchem(pool: Pool, groups: Groups, ledger: Ledger, notes: dict[str, list[str]],
                 renames: dict[str, dict[str, str]],
                 reviewed: Reviewed | None = None) -> dict[str, object]:
    """
    Apply the PubChem rules to every MIBiG compound (see the module notes).
    Returns what the 3D check of clue 2 found (Phase 4c), for the summary.
    """
    reviewed = reviewed or Reviewed([])
    outcomes: Counter[str] = Counter()
    for_a_person: list[str] = []
    claims: dict[str, list[str]] = {}               # pubchem id -> MIBiG compounds giving it
    found_by: dict[str, list[str]] = defaultdict(list)
    for pubchem_id in pool.ids("pubchem.compound"):
        props = pool.props(pubchem_id, "pubchem")
        claims[pubchem_id] = [m for m in split_list(props.get("mibig_compound_ids"))
                              if m in pool.rows]
        for mibig_id in split_list(props.get("found_by_name")):
            if mibig_id in pool.rows:
                found_by[mibig_id].append(pubchem_id)
    # Was the name search part of the PubChem fetch these tables came from (Phase 4b),
    # and was this compound's name asked? A search PubChem stopped halfway lists the
    # compounds it never reached, and the ledger mustn't claim anything about them.
    summary = pool.summaries["pubchem"]
    name_search_ran = "name_search_complete" in summary
    not_asked = set(summary.get("names_not_asked") or [])
    given_to: dict[str, list[str]] = defaultdict(list)
    for pubchem_id, mibig_ids in claims.items():
        for mibig_id in mibig_ids:
            given_to[mibig_id].append(pubchem_id)

    for mibig_id in sorted(set(given_to) | set(found_by)):
        settled = [p for p in given_to[mibig_id] + found_by[mibig_id]
                   if reviewed.settled(mibig_id, p)]
        if any(reviewed.settled(mibig_id, p).decision == "join" for p in settled):
            continue                                # a person joined it to one of them
        given = [p for p in given_to[mibig_id] if p not in settled]
        found = [p for p in found_by[mibig_id] if p not in settled]
        candidates = _candidates(pool, mibig_id, given, found, claims)
        if not candidates:
            _unconfirmed(pool, mibig_id, settled, notes, renames)
            continue
        _judge(pool, mibig_id, candidates, name_search_ran and mibig_id not in not_asked)
        chosen = _decide(pool, groups, ledger, notes, renames, mibig_id, candidates)
        checked = [c.three_d for c in candidates if c.three_d]
        outcomes.update(checked)
        if chosen is None and {"undecided", "not compared"} & set(checked):
            for_a_person.append(mibig_id)     # the 3D check left it without a record

    unknown = set(map(str, pool.summaries["pubchem"].get("cids_not_in_pubchem", [])))
    for mibig_id in pool.ids("mg.compound"):
        props = pool.props(mibig_id, "mibig")
        mine = {str(props.get("pubchem_cid", ""))} | set(_given_entries(pool, mibig_id))
        for cid in sorted(c for c in mine if c and c in unknown):
            ledger.add("pubchem_number_unknown", "kept_apart", mibig_id, "Compound",
                       f"MIBiG gives CID {cid} for '{pool.name(mibig_id, 'mibig')}', but "
                       f"PubChem has no compound with that number.",
                       compared_with=f"pubchem.compound:{cid}", sources="mibig|pubchem")
            notes[mibig_id].append(f"{pool.name(mibig_id, 'mibig')}: PubChem has no "
                                   f"compound {cid}")
            if str(props.get("pubchem_cid", "")) == cid:
                renames[mibig_id]["pubchem_cid"] = "pubchem_cid_not_confirmed"
    return {
        "pairs_checked": sum(outcomes.values()),
        "agree": outcomes["agree"],
        "differ": outcomes["kept"] + outcomes["moved"] + outcomes["undecided"],
        "not_compared": outcomes["not compared"],
        "mibig_structure_keeps_the_number": outcomes["kept"],
        "mibig_structure_moves_to_the_name": outcomes["moved"],
        "mibig_structure_cannot_decide": outcomes["undecided"],
        "compounds_left_for_a_person": len(for_a_person),
        "for_a_person": sorted(for_a_person),
    }


def _decide(pool: Pool, groups: Groups, ledger: Ledger, notes: dict[str, list[str]],
            renames: dict[str, dict[str, str]], mibig_id: str,
            candidates: list[Candidate]) -> Candidate | None:
    """
    Join the one candidate with the strongest clue, if exactly one has it;
    record the rest. Returns the candidate joined (None if none was).
    """
    several_given = sum(1 for c in candidates if c.given) > 1
    best = min(c.level for c in candidates)
    top = [c for c in candidates if c.level == best] if best != NONE else []
    chosen = top[0] if len(top) == 1 else None
    if chosen is not None and not groups.can_join(mibig_id, chosen.pubchem_id):
        chosen.why += (". It is already one with another PubChem compound, or a person kept "
                       "them apart, so it stays apart")
        chosen = None
    name = pool.name(mibig_id, "mibig")
    for c in candidates:
        rule = _rule_for(c, several_given)
        lead = _lead(c, name, candidates)
        if c is chosen:
            groups.join(mibig_id, c.pubchem_id)
            how = c.how or {NAME: "Confirmed by name.", SAME_STRUCTURE: "Confirmed by name, "
                            "through the same structure.", NAME_SEARCH: "Confirmed by name and "
                            "formula.", FORMULA_ONLY: "Confirmed by the formula alone."}[c.level]
            extra = (" PubChem's formula is kept, MIBiG's stays as mibig_formula."
                     if c.formula == "differs" else "")
            ledger.add(rule, "merged", mibig_id, "Compound", f"{lead}{c.why}. {how}{extra}",
                       compared_with=c.pubchem_id, sources="mibig|pubchem")
            continue
        if not c.given and c.level == NONE and chosen is not None:
            continue          # a stray name-search hit for a compound already joined: no row needed
        if len(top) > 1 and c in top:
            others = ", ".join(f"CID {o.cid}" for o in top if o is not c)
            reason = (f" {others} {'is' if len(top) == 2 else 'are'} just as well supported, so "
                      f"choosing one would be a guess.")
        else:
            reason = " Nothing else confirms it, so the two stay apart." if chosen is None else (
                f" CID {chosen.cid} is better supported, so this one stays apart.")
        why = c.why.replace(PERSON, "") if chosen is not None else c.why
        ledger.add(rule, "kept_apart", mibig_id, "Compound", f"{lead}{why}.{reason}",
                   compared_with=c.pubchem_id, sources="mibig|pubchem")
        if c.given:
            notes[mibig_id].append(f"{name}: PubChem CID {c.cid} not joined, not confirmed "
                                   f"(see the ledger)")
    joined = chosen.cid if chosen is not None else ""
    if str(pool.props(mibig_id, "mibig").get("pubchem_cid", "")) not in ("", joined):
        renames[mibig_id]["pubchem_cid"] = "pubchem_cid_not_confirmed"
    return chosen


def _lead(c: Candidate, name: str, candidates: list[Candidate]) -> str:
    """The start of the ledger sentence: which number, and where it came from."""
    if not c.given:
        return ""
    if c.shared:
        others = ", ".join(f"'{o}'" for o in c.others)
        return f"MIBiG gives CID {c.cid} to '{name}' and also to {others}. "
    given = [o for o in candidates if o.given]
    if len(given) > 1:
        others = ", ".join(f"{o.cid} ({', '.join(o.entries) or 'its first entry'})"
                           for o in given if o is not c)
        if set(c.entries) & {e for o in given if o is not c for e in o.entries}:
            # Phase 4b follow-up: an entry lists two numbers, so "disagree" won't do
            return (f"MIBiG gives this compound more than one number: CID {c.cid} "
                    f"({', '.join(c.entries)}) and {others}. ")
        return (f"MIBiG's entries disagree: {', '.join(c.entries) or 'one entry'} "
                f"give{'s' if len(c.entries) == 1 else ''} CID {c.cid}, others give {others}. ")
    return f"MIBiG gives CID {c.cid}; "


def _unconfirmed(pool: Pool, mibig_id: str, settled: list[str], notes: dict[str, list[str]],
                 renames: dict[str, dict[str, str]]) -> None:
    """Every candidate was settled by hand as different: MIBiG's number stays unconfirmed."""
    cid = str(pool.props(mibig_id, "mibig").get("pubchem_cid", ""))
    if cid and f"pubchem.compound:{cid}" in settled:
        renames[mibig_id]["pubchem_cid"] = "pubchem_cid_not_confirmed"
        notes[mibig_id].append(f"{pool.name(mibig_id, 'mibig')}: PubChem CID {cid} kept apart "
                               f"by hand (see the ledger)")


def join_same_npatlas(pool: Pool, groups: Groups, ledger: Ledger,
                      reviewed: Reviewed | None = None) -> None:
    """Join MIBiG compounds that share an NPAtlas number and a formula (see above)."""
    reviewed = reviewed or Reviewed([])
    by_number: dict[str, list[str]] = defaultdict(list)
    for mibig_id in pool.ids("mg.compound"):
        for ref in split_list(pool.props(mibig_id, "mibig").get("database_ids")):
            if ref.startswith("npatlas:"):
                by_number[ref].append(mibig_id)

    for number, members in sorted(by_number.items()):
        if len(members) < 2:
            continue
        first, *rest = sorted(members, key=rank_key)
        first_props = pool.props(first, "mibig")
        first_formula = first_props.get("formula")
        for other in rest:
            if reviewed.settled(first, other):
                continue
            other_props = pool.props(other, "mibig")
            other_formula = other_props.get("formula")
            names = f"'{pool.name(first, 'mibig')}' and '{pool.name(other, 'mibig')}'"
            disputed = [pool.name(m, "mibig") for m, p in ((first, first_props),
                                                          (other, other_props))
                        if p.get("formula_by_entry")]
            state = compare_formulas(first_formula, other_formula)
            if disputed:
                # Phase 4b: desosamine's first entry carries methymycin's formula and
                # NPAtlas number, so a formula the entries disagree about can't confirm.
                ledger.add("npatlas_and_formula", "kept_apart", other, "Compound",
                           f"{names} share {number}, but MIBiG's entries disagree about the "
                           f"formula of {' and '.join(repr(d) for d in disputed)} "
                           f"(formula_by_entry), so the formula can't confirm the number.",
                           compared_with=first, sources="mibig")
            elif state != "agrees":
                why = {
                    "missing": "one of them has no formula, so nothing confirms the number",
                    "agrees_but_charge": f"their formulas differ in charge ({first_formula} and "
                                         f"{other_formula})",
                    "differs": f"their formulas differ ({first_formula} and {other_formula})",
                }[state]
                ledger.add("npatlas_and_formula", "kept_apart", other, "Compound",
                           f"{names} share {number}, but {why}: two different molecules "
                           f"can be filed under one NPAtlas entry by mistake.",
                           compared_with=first, sources="mibig")
            elif groups.same(first, other):
                continue
            elif groups.kept_apart_by_hand(first, other):
                ledger.add("npatlas_and_formula", "kept_apart", other, "Compound",
                           f"{names} share {number} and the formula {first_formula}, but "
                           f"joining them would bring together records a person decided "
                           f"are different (see their reviewed_by_hand rows).",
                           compared_with=first, sources="mibig")
            elif not groups.can_join(first, other):
                ledger.add("npatlas_and_formula", "kept_apart", other, "Compound",
                           f"{names} share {number} and the formula {first_formula}, but "
                           f"they are already joined to two different PubChem compounds, "
                           f"and PubChem says those are different molecules.",
                           compared_with=first, sources="mibig")
            else:
                groups.join(first, other)
                ledger.add("npatlas_and_formula", "merged", other, "Compound",
                           f"{names} share {number} and the formula {first_formula}: one "
                           f"compound recorded under two names.",
                           compared_with=first, sources="mibig")
