"""
Tests for the query command and for every recipe in docs/QUERY_COOKBOOK.md.

Each SQL recipe (R1, R2...) and each Python recipe (N1, N2...) runs here on a
database built from the real slice in tests/fixtures/resolve/. A recipe that
stops working, because a table or column changed, fails the tests the same day.
"""

from __future__ import annotations

import code
import contextlib
import io
import re
from pathlib import Path

import pytest

import microbegraph.build_graph as build_graph
from microbegraph.build_graph import build
from microbegraph.query import COOKBOOK, as_table, main, recipes, run_sql
from microbegraph.resolve import resolve


@pytest.fixture(scope="module")
def database(tmp_path_factory) -> Path:
    from conftest import RESOLVE_FIXTURES
    out = tmp_path_factory.mktemp("processed")
    resolve(RESOLVE_FIXTURES, out, RESOLVE_FIXTURES / "curation")
    db = out / "microbegraph.duckdb"
    build(out / "nodes.csv", out / "edges.csv", out / "resolution_ledger.csv",
          out / "resolve_summary.json", db)
    return db


BOOK = recipes()
PYTHON_RECIPES = re.findall(r"### (N\d+)\.[^\n]*\n.*?```python\n(.*?)```",
                            COOKBOOK.read_text(encoding="utf-8"), flags=re.S)


def test_the_cookbook_has_its_recipes_numbered_in_order():
    assert sorted(BOOK) == list(range(1, len(BOOK) + 1))
    assert len(BOOK) >= 18 and len(PYTHON_RECIPES) >= 5


@pytest.mark.parametrize("number", sorted(BOOK))
def test_every_sql_recipe_runs(database, number):
    columns, _ = run_sql(BOOK[number][1], database)
    assert columns


@pytest.mark.parametrize("name, code", PYTHON_RECIPES, ids=[n for n, _ in PYTHON_RECIPES])
def test_every_python_recipe_runs(database, monkeypatch, name, code):
    monkeypatch.setattr(build_graph, "DATABASE_FILE", database)
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        exec(code, {"__name__": "__cookbook__"})
    assert printed.getvalue().strip()


@pytest.mark.parametrize("name, code_text", PYTHON_RECIPES, ids=[n for n, _ in PYTHON_RECIPES])
def test_every_python_recipe_can_be_pasted_into_python(database, monkeypatch, name, code_text):
    # The cookbook says to type `python` and paste a recipe. The interactive
    # prompt reads line by line and needs a blank line to end an indented
    # block, so a recipe that runs as a file can still fail when pasted.
    monkeypatch.setattr(build_graph, "DATABASE_FILE", database)
    console = code.InteractiveConsole({"__name__": "__console__"})
    printed, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(errors):
        for line in code_text.splitlines():
            console.push(line)
        console.push("")
    assert "Error" not in errors.getvalue(), errors.getvalue()
    assert printed.getvalue().strip()


def test_recipe_answers_on_the_slice(database):
    def answer(number: int) -> list[tuple]:
        return run_sql(BOOK[number][1], database)[1]

    assert ("ncbiprotein:CAE02630.1", "uniprot:Q70KJ7", "uniprot_cross_reference") in answer(5)
    chains = answer(9)
    assert ("jujube", "Botrytis cinerea", "surfactin", "Bacillus velezensis FZB42",
            "curated_literature", "doi:10.1186/s13568-023-01543-w") in chains
    assert answer(10) == [("Bacillus velezensis FZB42", "mibig:BGC0000433")]
    assert [row[0] for row in answer(11)] == ["srfAA", "srfAB", "srfAC", "srfAD"]
    # Phase 4b's recipes: the slice holds the real review file and activity words.
    assert ("mg.compound:desosamine", "mg.compound:methymycin", "kept_apart") in answer(20)
    assert len(answer(20)) == 5
    assert ("2-methylisoborneol",
            "BGC0000657: 9237955|BGC0000658: 16913|BGC0000659: 16913") in answer(21)
    assert ("mg.activity:antitumor", "mg.activity:anticancer") in answer(22)


def test_the_command_runs_a_recipe_and_your_own_sql(database, monkeypatch, capsys):
    monkeypatch.setattr("microbegraph.query.DATABASE_FILE", database)
    assert main(["--recipe", "2"]) == 0
    assert "Protein" in capsys.readouterr().out
    assert main(["SELECT count(*) AS n FROM nodes WHERE node_type = 'Crop'"]) == 0
    assert capsys.readouterr().out.splitlines()[2].strip() != "0"
    assert main(["--recipe", "999"]) == 2
    assert main(["--list"]) == 0
    assert "R9" in capsys.readouterr().out


def test_the_command_can_not_change_the_database(database, monkeypatch, capsys):
    monkeypatch.setattr("microbegraph.query.DATABASE_FILE", database)
    assert main(["DELETE FROM nodes"]) == 1
    assert "read-only" in capsys.readouterr().out.lower()
    assert run_sql("SELECT count(*) FROM nodes", database)[1][0][0] > 0


def test_a_missing_database_says_what_to_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("microbegraph.query.DATABASE_FILE", tmp_path / "none.duckdb")
    assert main(["SELECT 1"]) == 1
    assert "microbegraph.build_graph" in capsys.readouterr().out


def test_tables_are_plain_text_and_long_cells_are_cut():
    text = as_table(["a", "b"], [("x" * 100, None)])
    assert text.isascii()
    lines = text.splitlines()
    assert lines[1].startswith("-") and lines[2].rstrip().endswith("...")
    assert lines[-1] == "(1 row)"
