"""
MicrobeGraph, setup verification.

WHY THIS EXISTS:
    Setup has many steps, and a half-finished environment tends to produce
    confusing errors three phases later. This script checks every piece at
    once and tells you exactly which step to revisit.

USAGE:
    python check-setup.py
"""

import shutil              # for finding command-line tools on the PATH
import subprocess          # for running other programs (git) and reading output
import sys                 # for information about the running Python
from pathlib import Path   # for file paths that work on every operating system

# Pathlib note: we use Path("docs") rather than "docs/" or "docs\\" because
# Windows uses backslashes and Unix uses forward slashes. Path handles the
# difference, which is one reason this project runs unchanged on all three
# operating systems.

checks: list[tuple[str, bool, str]] = []   # (label, passed?, hint if failed)


def check(label: str, passed: bool, hint: str = "") -> None:
    """Record one check result."""
    checks.append((label, passed, hint))


# --- 1. Python version -------------------------------------------------
version = sys.version_info
# Both bounds matter. The LOWER one: scikit-learn 1.9, which this project
# needs, no longer supports Python 3.10. The UPPER one: a brand-new Python
# release is newer than anything this project is tested on, and some
# scientific packages take months to publish ready-built versions for it
# (pip then tries to compile them and fails). See Troubleshooting T11.
check(
    f"Python {version.major}.{version.minor}.{version.micro}",
    (3, 11) <= version < (3, 14),
    "Need Python 3.11 or 3.12 (3.13 also works for Phases 1-6). "
    "See Step 1 / Troubleshooting T11.",
)

# 3.13 works for everything in requirements.txt, but the Phase 7 extras in
# requirements-ml.txt have no build for it yet. Flag it now rather than letting
# it surprise someone months later.
if version[:2] == (3, 13):
    print("\n  NOTE: Python 3.13 runs the core project fine, but the Phase 7")
    print("        extras (requirements-ml.txt) have no build for it yet.")
    print("        Prefer 3.11 or 3.12 if you have one available.")

# --- 2. Virtual environment active -------------------------------------
# When a venv is active, sys.prefix points inside it and differs from
# sys.base_prefix (the original Python installation).
in_venv = sys.prefix != sys.base_prefix
check(
    "Virtual environment active",
    in_venv,
    "Activate it: source .venv/bin/activate  "
    "(Windows:.\\.venv\\Scripts\\Activate.ps1). See Step 7.",
)

# --- 3. Required packages import ---------------------------------------
# Every package in requirements.txt is listed here. If you add one there,
# add it here too, or this check quietly stops meaning what it says.
#
# NOTE ON THE PAIRS BELOW: a package's INSTALL name and its IMPORT name are
# not always the same. You install "scikit-learn" but you write
# "import sklearn"; you install "python-dotenv" but you write "import dotenv".
# So each entry is (name you install, name you import).
#
# It's like a shop that sells "sparkling mineral water", which at home you
# just call "fizzy water": one thing with two names, depending on where you are.
PACKAGES = [
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("requests", "requests"),
    ("tenacity", "tenacity"),
    ("duckdb", "duckdb"),
    ("networkx", "networkx"),
    ("rdkit", "rdkit"),                 # Phase 4c: the 3D check of compounds
    ("matplotlib", "matplotlib"),
    ("plotly", "plotly"),
    ("pyvis", "pyvis"),
    ("scikit-learn", "sklearn"),        # installs as scikit-learn, imports as sklearn
    ("streamlit", "streamlit"),
    ("pytest", "pytest"),
    ("python-dotenv", "dotenv"),        # installs as python-dotenv, imports as dotenv
]

for install_name, import_name in PACKAGES:
    try:
        __import__(import_name)
        check(f"package: {install_name}", True)
    except ImportError:
        check(f"package: {install_name}", False,
              "Run: pip install -r requirements.txt  (with .venv active). See Step 8.")

# ruff is checked differently, for a reason that's useful to know.
#
# Most packages are LIBRARIES: code you import into your own program.
# ruff is a TOOL: a standalone program you run from the terminal. It installs
# a command rather than something importable, so "import ruff" fails even
# when it is installed perfectly well. Testing it that way would report a
# problem that does not exist, which is worse than not testing it at all.
#
# A kitchen comparison: you check the flour by looking in the cupboard, and
# you check the oven by turning it on. They are different kinds of thing, so
# they need different tests.
check(
    "tool: ruff",
    shutil.which("ruff") is not None,
    "Run: pip install -r requirements.txt  (with .venv active). See Step 8.",
)

# --- 3b. The project's own package -----------------------------------------
# From Phase 1 on, MicrobeGraph is itself an installed package, so that
#     python -m microbegraph.fetch
# works from any folder. "pip install -e ." installs it in EDITABLE mode:
# Python gets a pointer to src/microbegraph/ instead of a copy, so your edits
# are live immediately. We check two things: that it imports at all, and that
# it imports from THIS folder (not from a stale copy somewhere else).
try:
    import microbegraph
    here = Path("src/microbegraph").resolve()
    found = Path(microbegraph.__file__).resolve().parent
    check("package: microbegraph (editable install)", found == here,
          f"It imports from {found}, not from this folder. "
          "Run: pip install -e .  (with .venv active, from the project folder). See Step 8.")
except ImportError:
    check("package: microbegraph (editable install)", False,
          "Run: pip install -e .  (with .venv active, from the project folder). See Step 8.")

# --- 4. Git available and configured -----------------------------------
try:
    subprocess.run(["git", "--version"], capture_output=True, check=True)
    check("git installed", True)

    name = subprocess.run(["git", "config", "user.name"],
                          capture_output=True, text=True).stdout.strip()
    email = subprocess.run(["git", "config", "user.email"],
                           capture_output=True, text=True).stdout.strip()
    check("git identity configured", bool(name and email),
          'Run: git config --global user.name "Your Name" (and user.email). See Step 3.')
except (subprocess.CalledProcessError, FileNotFoundError):
    check("git installed", False, "Install Git. See Step 3.")

# --- 5. Branches exist --------------------------------------------------
# Only master and develop are REQUIRED locally. The push command
#     git push origin develop develop:beta develop:master
# updates remote beta straight from local develop, so a local beta branch is
# never needed. Keeping one anyway is purely a matter of taste.
try:
    local = subprocess.run(["git", "branch"], capture_output=True,
                           text=True).stdout
    for branch in ["master", "develop"]:
        check(f"local branch: {branch}", branch in local,
              f"Create it: git branch {branch}. See Step 10.")

    # The remote is what actually matters for beta.
    remote = subprocess.run(["git", "branch", "-r"], capture_output=True,
                            text=True).stdout
    for branch in ["master", "beta", "develop"]:
        check(f"remote branch: origin/{branch}", f"origin/{branch}" in remote,
              f"Push it: git push origin develop:{branch}. See Step 10.")
except FileNotFoundError:
    pass

# --- 6. Folder structure ------------------------------------------------
# data/raw and data/processed are NOT checked: data/ is never in Git, so a
# fresh clone does not have it, and the pipeline creates those folders itself
# the first time it writes to them (Phase 1 onwards).
# app/ is not checked either: it arrives with its first file in Phase 8.
for folder in ["docs", "src/microbegraph", "curation", "artifacts", "tests"]:
    check(f"folder: {folder}", Path(folder).is_dir(),
          f"Create it: mkdir -p {folder}. See Step 6.")

# --- 7. Safety files ----------------------------------------------------
check("file: .gitignore", Path(".gitignore").is_file(), "See Step 9.")
check("file: requirements.txt", Path("requirements.txt").is_file(), "See Step 8.")
check("file: pyproject.toml", Path("pyproject.toml").is_file(),
      "It arrives in Phase 1 (docs/03-ingestion-mibig.md). See Step 8.")
check("file: check-public-safe.sh", Path("check-public-safe.sh").is_file(), "See Step 9.")

# --- Report -------------------------------------------------------------
print("\nMicrobeGraph setup check")
print("=" * 52)

failed = 0
for label, passed, hint in checks:
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}]  {label}")
    if not passed:
        failed += 1
        print(f"          → {hint}")

print("=" * 52)
if failed == 0:
    print("All checks passed. Your workshop is ready.\n")
    sys.exit(0)
else:
    print(f"{failed} check(s) failed, see the hints above.\n")
    sys.exit(1)
