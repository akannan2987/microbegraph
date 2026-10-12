"""
MicrobeGraph, ask the database a question (Phase 4).

USAGE (from the repository root, with .venv active)

    python -m microbegraph.query --list             the recipes in docs/QUERY_COOKBOOK.md
    python -m microbegraph.query --recipe 9         run one recipe, by its number
    python -m microbegraph.query "SELECT count(*) FROM nodes"     any SQL of your own

    On Windows, PowerShell and Command Prompt accept the same double quotes
    around your SQL; inside the SQL, text goes in single quotes, as in
    WHERE node_id = 'mibig:BGC0000433'.

WHY A COMMAND, WHEN PYTHON CAN RUN SQL DIRECTLY
    Both work. The cookbook shows the Python way too. This command saves
    typing while you learn, and it opens the database READ-ONLY: no query run
    through it can change or delete anything, so experimenting is safe. It's
    the difference between a museum's glass case and its workshop.

THE RECIPES LIVE IN THE COOKBOOK
    Each recipe in docs/QUERY_COOKBOOK.md starts with a heading like
    "### R9. Which microbes might help against which crop disease?" followed
    by its SQL in a ```sql block. --recipe reads them from there, so the
    document and the command can't drift apart, and tests/test_query.py runs
    every one of them on every change.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

from microbegraph.paths import DATABASE_FILE, REPO_ROOT, relative_to_repo

COOKBOOK = REPO_ROOT / "docs" / "QUERY_COOKBOOK.md"
HEADING = re.compile(r"^### R(\d+)\. (.+)$")
WIDEST_CELL = 60          # longer text is cut, with "..." at the end


def recipes(cookbook: Path = COOKBOOK) -> dict[int, tuple[str, str]]:
    """Every recipe in the cookbook: {number: (title, sql)}."""
    if not cookbook.exists():
        raise FileNotFoundError(f"{relative_to_repo(cookbook)} is missing; the recipes "
                                f"live there. Get it back with: git checkout -- "
                                f"{relative_to_repo(cookbook)}")
    found: dict[int, tuple[str, str]] = {}
    current: tuple[int, str] | None = None
    lines = cookbook.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        heading = HEADING.match(lines[i])
        if heading:
            # The title without Markdown's emphasis marks (*Bacillus* -> Bacillus).
            current = (int(heading.group(1)), re.sub(r"[*`]", "", heading.group(2)).strip())
        elif current and lines[i].strip() == "```sql":
            end = next(j for j in range(i + 1, len(lines)) if lines[j].strip() == "```")
            found[current[0]] = (current[1], "\n".join(lines[i + 1:end]))
            current, i = None, end
        i += 1
    return found


def run_sql(sql: str, db_path: Path | None = None) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Run one query on the database, read-only. Returns (column names, rows)."""
    path = Path(db_path or DATABASE_FILE)
    if not path.exists():
        raise FileNotFoundError(f"{relative_to_repo(path)} doesn't exist yet.\n"
                                f"  Run:  python -m microbegraph.resolve\n"
                                f"        python -m microbegraph.build_graph")
    con = duckdb.connect(str(path), read_only=True)
    try:
        result = con.sql(sql)
        if result is None:                      # a statement that returns nothing
            return [], []
        return list(result.columns), result.fetchall()
    finally:
        con.close()


def as_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    """Rows as a plain-text table with aligned columns (no special characters)."""
    def cell(value: Any) -> str:
        text = "" if value is None else str(value)
        return text if len(text) <= WIDEST_CELL else text[:WIDEST_CELL - 3] + "..."
    shown = [[cell(v) for v in row] for row in rows]
    widths = [max([len(c)] + [len(r[i]) for r in shown]) for i, c in enumerate(columns)]
    lines = ["  ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True)).rstrip(),
             "  ".join("-" * w for w in widths)]
    lines += ["  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)).rstrip() for row in shown]
    lines.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microbegraph.query",
        description="Run a cookbook recipe, or your own SQL, on the project database "
                    "(read-only).",
    )
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--list", action="store_true", help="list the cookbook's recipes")
    which.add_argument("--recipe", type=int, metavar="N", help="run recipe number N")
    which.add_argument("sql", nargs="?", help="your own SQL, in double quotes")
    args = parser.parse_args(argv)

    try:
        if args.list:
            for number, (title, _) in sorted(recipes().items()):
                print(f"  R{number:<3} {title}")
            return 0
        if args.recipe is not None:
            book = recipes()
            if args.recipe not in book:
                print(f"There's no recipe R{args.recipe}. See: python -m microbegraph.query --list")
                return 2
            title, sql = book[args.recipe]
            print(f"R{args.recipe}. {title}\n")
        else:
            sql = args.sql
        columns, rows = run_sql(sql)
    except (FileNotFoundError, duckdb.Error) as error:
        print(f"[query] {error}")
        return 1
    print(as_table(columns, rows) if columns else "(done; nothing to show)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
