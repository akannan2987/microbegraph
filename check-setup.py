"""
MicrobeGraph — setup verification.

WHY THIS EXISTS:
    Setup has many steps and a half-finished environment produces confusing
    errors three phases later. This checks every piece at once and tells you
    exactly which step to revisit.

USAGE:
    python check-setup.py
"""

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
# Upper bound matters as much as the lower one: several scientific packages
# have no pre-built version for a brand-new Python release, so pip tries to
# compile them from source and fails with C compiler errors. The ecosystem
# takes 6-12 months to catch up. See Troubleshooting T11.
check(
    f"Python {version.major}.{version.minor}.{version.micro}",
    (3, 10) <= version < (3, 14),
    "Need Python 3.11 or 3.12. "
    "3.14+ has no builds yet for some packages. See Step 1 / Troubleshooting T11.",
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
    "(Windows: .\\.venv\\Scripts\\Activate.ps1). See Step 7.",
)

# --- 3. Required packages import ---------------------------------------
for package in ["pandas", "numpy", "requests", "duckdb", "networkx",
                "matplotlib", "plotly", "streamlit", "pytest"]:
    try:
        __import__(package)
        check(f"package: {package}", True)
    except ImportError:
        check(f"package: {package}", False,
              "Run: pip install -r requirements.txt  (with .venv active). See Step 8.")

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
try:
    branches = subprocess.run(["git", "branch"], capture_output=True,
                              text=True).stdout
    for branch in ["master", "beta", "develop"]:
        check(f"branch: {branch}", branch in branches,
              f"Create it: git branch {branch}. See Step 10.")
except FileNotFoundError:
    pass

# --- 6. Folder structure ------------------------------------------------
for folder in ["docs", "src/microbegraph", "curation", "artifacts",
               "app", "tests", "data/raw", "data/processed"]:
    check(f"folder: {folder}", Path(folder).is_dir(),
          f"Create it: mkdir -p {folder}. See Step 6.")

# --- 7. Safety files ----------------------------------------------------
check("file: .gitignore", Path(".gitignore").is_file(), "See Step 9.")
check("file: requirements.txt", Path("requirements.txt").is_file(), "See Step 8.")
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
    print(f"{failed} check(s) failed — see the hints above.\n")
    sys.exit(1)
