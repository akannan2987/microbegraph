"""
MicrobeGraph, comparing names and formulas fairly.

WHY THIS FILE EXISTS
    "Erythromycin A", "erythromycin A" and "erythromycin-A" are the same name
    written three ways. Comparing the raw text would call them different, so
    every name is first turned into a KEY: lower case, accents and Greek
    letters spelled out, everything but letters and digits removed.

        "Erythromycin A"        -> "erythromycina"
        "α-galactosylceramide"  -> "alphagalactosylceramide"
        "(+)-semivioxanthin"    -> "plussemivioxanthin"

    Postal services do the same with addresses: "Main St." and "MAIN STREET"
    are normalised to one form before anyone checks whether two letters go to
    the same house.

WHAT THE KEY KEEPS ON PURPOSE
    The signs of mirror-image molecules: "(+)" becomes "plus" and "(-)"
    becomes "minus", so (+)-menthol and (-)-menthol never match by name
    (they smell different, and they are different molecules). Letters such
    as the D- and L- in D-alanine and L-alanine survive too, because only
    punctuation and spaces are removed.

FORMULAS
    A molecular formula lists the atoms: surfactin is C52H91N7O13 (52 carbon,
    91 hydrogen, 7 nitrogen, 13 oxygen). Two records of one molecule should
    give the same formula. A charge at the end ("C10H16NO4-") is the same
    molecule having gained or lost a proton, so a second comparison ignores it.
"""

from __future__ import annotations

import re
import unicodedata

# Greek letters are common in chemistry and biology names. Spelled out, they
# compare equal to names that already use the words ("alpha-amanitin").
GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho",
    "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}

# The optical-rotation signs, kept as words so mirror images stay apart.
SIGNS = (("(+/-)", "plusminus"), ("(±)", "plusminus"), ("(+)", "plus"), ("(-)", "minus"))


def name_key(text: object) -> str:
    """A name reduced to lower-case letters and digits, for comparing (see above)."""
    value = str(text or "")
    for sign, word in SIGNS:
        value = value.replace(sign, f" {word} ")
    value = "".join(GREEK.get(ch, GREEK.get(ch.lower(), ch)) for ch in value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", value.lower())


def split_list(text: object) -> list[str]:
    """A pipe-separated property ("a|b|c") as a list, with blanks removed."""
    return [part.strip() for part in str(text or "").split("|") if part.strip()]


def formula_key(formula: object) -> str:
    """A formula without spaces, e.g. "C52 H91 N7 O13" -> "C52H91N7O13"."""
    return re.sub(r"\s", "", str(formula or ""))


def formula_without_charge(formula: object) -> str:
    """A formula with any charge at the end removed: "C10H16NO4-" -> "C10H16NO4"."""
    # The charge is a sign with an optional number after it ("-", "+", "-2").
    # Digits BEFORE the sign belong to the last atom (the 4 in "NO4-"), so
    # they stay.
    return re.sub(r"[+-]\d*$", "", formula_key(formula))


def compare_formulas(ours: object, theirs: object) -> str:
    """
    How two formulas compare, as one of four words:

        "missing"          one of them is empty, so there's nothing to compare
        "agrees"           exactly the same atoms
        "agrees_but_charge"  the same atoms once a charge at the end is ignored
        "differs"          different atoms: not the same molecule as written
    """
    a, b = formula_key(ours), formula_key(theirs)
    if not a or not b:
        return "missing"
    if a == b:
        return "agrees"
    if formula_without_charge(a) == formula_without_charge(b):
        return "agrees_but_charge"
    return "differs"
