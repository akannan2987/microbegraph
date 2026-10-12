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
    about one molecule onto another.

    So a number has to be confirmed by a second, independent piece of
    evidence before two records become one node:

    rule pubchem_number_confirmed
        MIBiG's name is one of PubChem's names for that number (its title or a
        synonym), OR the two formulas agree. Either one is enough.

        The formula is the weaker clue. It is only independent of the number
        if MIBiG worked it out on its own; where MIBiG copied the structure
        from the PubChem record the number points at, the formulas agree
        whether the number is right or not (MIBiG's "2-methylisoborneol"
        carries a bromine compound's formula, C15H16BrN3O4S). On the real data
        325 joins rest on the formula alone. Their ledger rows say "PubChem
        doesn't list the name", and Phase 4b checks each one against
        PubChem's full list of names.

    rule pubchem_number_shared
        When several MIBiG compounds give the same number, a matching formula
        proves nothing: minutissamides B, C and D all have the formula
        C55H91N13O16 but are different molecules (isomers, the same atoms
        arranged differently). So each needs its own NAME confirmed.

    rule pubchem_number_unknown
        PubChem has no compound with the number MIBiG gives. Nothing to join.

    rule npatlas_and_formula
        Two MIBiG compounds that share a number from NPAtlas (the Natural
        Products Atlas, a database of microbial natural products) AND have the
        same formula are one compound recorded twice under two names
        (lovastatin and monacolin K, for example). A shared NPAtlas number
        without the same formula on both sides stays apart; on the real data
        every such pair has one record with no formula at all.

    Whatever stays apart is written to the ledger as kept_apart, with the
    reason. The MIBiG compound keeps a note saying so, and its unconfirmed
    number moves from pubchem_cid to pubchem_cid_not_confirmed, so nobody
    filtering on pubchem_cid mistakes it for a confirmed one.
"""

from __future__ import annotations

from collections import defaultdict

from microbegraph.resolution.groups import Groups, rank_key
from microbegraph.resolution.ledger import Ledger
from microbegraph.resolution.names import compare_formulas, name_key, split_list
from microbegraph.resolution.pool import Pool

FORMULA_WORDS = {
    "agrees": "the formulas agree ({a})",
    "agrees_but_charge": "the formulas agree once the charge is ignored ({a} and {b})",
    "differs": "the formulas differ (MIBiG {a}, PubChem {b})",
    "missing": "there's no formula to compare",
}


def _mibig_names(pool: Pool, node_id: str) -> set[str]:
    """The name keys a MIBiG compound goes by: its name, synonyms and other names."""
    props = pool.props(node_id, "mibig")
    names = [pool.name(node_id, "mibig")]
    names += split_list(props.get("synonyms")) + split_list(props.get("other_names"))
    return {key for key in map(name_key, names) if key}


def _pubchem_names(pool: Pool, node_id: str) -> set[str]:
    """The name keys PubChem gives a compound: its title and its listed synonyms."""
    names = [pool.name(node_id, "pubchem")] + split_list(pool.props(node_id, "pubchem")
                                                         .get("synonyms"))
    return {key for key in map(name_key, names) if key}


def join_pubchem(pool: Pool, groups: Groups, ledger: Ledger, notes: dict[str, list[str]],
                 renames: dict[str, dict[str, str]]) -> None:
    """Apply the three PubChem rules (see the module notes)."""
    for pubchem_id in pool.ids("pubchem.compound"):
        props = pool.props(pubchem_id, "pubchem")
        title = pool.name(pubchem_id, "pubchem")
        claims = [m for m in split_list(props.get("mibig_compound_ids")) if m in pool.rows]
        shared = len(claims) > 1
        their_names = _pubchem_names(pool, pubchem_id)
        for mibig_id in claims:
            mibig_name = pool.name(mibig_id, "mibig")
            name_ok = bool(_mibig_names(pool, mibig_id) & their_names)
            ours = pool.props(mibig_id, "mibig").get("formula")
            formula = compare_formulas(ours, props.get("formula"))
            formula_text = FORMULA_WORDS[formula].format(a=ours, b=props.get("formula"))
            formula_ok = formula in ("agrees", "agrees_but_charge")
            cid = str(props.get("pubchem_cid", pubchem_id.split(":", 1)[1]))

            if shared:
                rule = "pubchem_number_shared"
                others = ", ".join(f"'{pool.name(m, 'mibig')}'" for m in claims if m != mibig_id)
                confirmed = name_ok
                why = (f"MIBiG gives CID {cid} to '{mibig_name}' and also to {others}. "
                       f"PubChem's title is '{title}'. ")
                why += ("PubChem lists the name '{n}', so this one is confirmed; {f}."
                        if name_ok else
                        "PubChem doesn't list the name '{n}', and with several names on one "
                        "number a formula can't tell isomers apart; {f}.").format(
                            n=mibig_name, f=formula_text)
            else:
                rule = "pubchem_number_confirmed"
                confirmed = name_ok or formula_ok
                checks = []
                checks.append(f"PubChem lists the name '{mibig_name}'" if name_ok
                              else f"PubChem doesn't list the name '{mibig_name}' "
                                   f"(its title is '{title}')")
                checks.append(formula_text)
                why = (f"MIBiG gives CID {cid}; " + "; ".join(checks) + ". "
                       + ("Confirmed." if confirmed else "Nothing besides the number confirms "
                          "it, so the two stay apart."))
                if confirmed and formula == "differs":
                    why += " PubChem's formula is kept, MIBiG's stays as mibig_formula."

            if confirmed:
                groups.join(mibig_id, pubchem_id)
                ledger.add(rule, "merged", mibig_id, "Compound", why, compared_with=pubchem_id,
                           sources="mibig|pubchem")
            else:
                ledger.add(rule, "kept_apart", mibig_id, "Compound", why,
                           compared_with=pubchem_id, sources="mibig|pubchem")
                notes[mibig_id].append(f"{mibig_name}: PubChem CID {cid} not joined, not "
                                       f"confirmed by name or formula (see the ledger)")
                renames[mibig_id]["pubchem_cid"] = "pubchem_cid_not_confirmed"

    unknown = set(map(str, pool.summaries["pubchem"].get("cids_not_in_pubchem", [])))
    for mibig_id in pool.ids("mg.compound"):
        cid = str(pool.props(mibig_id, "mibig").get("pubchem_cid", ""))
        if cid and cid in unknown:
            ledger.add("pubchem_number_unknown", "kept_apart", mibig_id, "Compound",
                       f"MIBiG gives CID {cid} for '{pool.name(mibig_id, 'mibig')}', but "
                       f"PubChem has no compound with that number.",
                       compared_with=f"pubchem.compound:{cid}", sources="mibig|pubchem")
            notes[mibig_id].append(f"{pool.name(mibig_id, 'mibig')}: PubChem has no "
                                   f"compound {cid}")
            renames[mibig_id]["pubchem_cid"] = "pubchem_cid_not_confirmed"


def join_same_npatlas(pool: Pool, groups: Groups, ledger: Ledger) -> None:
    """Join MIBiG compounds that share an NPAtlas number and a formula (see above)."""
    by_number: dict[str, list[str]] = defaultdict(list)
    for mibig_id in pool.ids("mg.compound"):
        for ref in split_list(pool.props(mibig_id, "mibig").get("database_ids")):
            if ref.startswith("npatlas:"):
                by_number[ref].append(mibig_id)

    for number, members in sorted(by_number.items()):
        if len(members) < 2:
            continue
        first, *rest = sorted(members, key=rank_key)
        first_formula = pool.props(first, "mibig").get("formula")
        for other in rest:
            other_formula = pool.props(other, "mibig").get("formula")
            names = f"'{pool.name(first, 'mibig')}' and '{pool.name(other, 'mibig')}'"
            state = compare_formulas(first_formula, other_formula)
            if state != "agrees":
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
