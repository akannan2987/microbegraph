"""
Tests for private settings (.env) and the fetch command's list of sources.

The key used here is made up.
"""

from __future__ import annotations

import pytest

from microbegraph import fetch
from microbegraph.settings import describe, load_settings, ncbi_api_key, setting

FAKE_KEY = "0123456789abcdef0123456789abcdef0123"


@pytest.fixture
def no_ncbi_settings(monkeypatch):
    """
    Start with neither NCBI setting in the environment, and put things back
    afterwards. Setting a value first makes pytest remember the original
    state, so whatever load_settings() writes is undone after the test.
    """
    for name in ("NCBI_API_KEY", "NCBI_EMAIL"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


def test_settings_are_read_from_a_dotenv_file(tmp_path, no_ncbi_settings):
    env = tmp_path / ".env"
    env.write_text(f'# my settings\nNCBI_API_KEY="{FAKE_KEY}"\nNCBI_EMAIL=\n', encoding="utf-8")

    assert load_settings(env) is True
    assert ncbi_api_key() == FAKE_KEY            # the quotes are not part of the key


def test_a_missing_dotenv_file_is_fine(tmp_path, no_ncbi_settings):
    assert load_settings(tmp_path / "no-such-file") is False
    assert ncbi_api_key() == ""


def test_the_environment_wins_over_the_file(tmp_path, no_ncbi_settings, monkeypatch):
    monkeypatch.setenv("NCBI_API_KEY", "from-the-environment")
    env = tmp_path / ".env"
    env.write_text(f"NCBI_API_KEY={FAKE_KEY}\n", encoding="utf-8")

    load_settings(env)

    assert ncbi_api_key() == "from-the-environment"


def test_stray_spaces_and_quotes_are_removed(monkeypatch):
    monkeypatch.setenv("SOME_SETTING", "  'value'  ")
    assert setting("SOME_SETTING") == "value"
    assert setting("A_SETTING_NOBODY_SET") == ""


def test_a_secret_is_only_ever_described():
    assert describe(FAKE_KEY) == "set"
    assert describe("") == "not set"


def test_list_shows_every_source_in_running_order(capsys):
    assert fetch.main(["--list"]) == 0
    out = capsys.readouterr().out
    names = [line.split()[0] for line in out.splitlines() if line.startswith("  ") and
             not line.strip().startswith("licence")]
    assert names == ["mibig", "pubchem", "ncbi_taxonomy", "kegg", "curation"]
