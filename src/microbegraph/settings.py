"""
MicrobeGraph, private settings and how secrets stay secret.

WHAT LIVES HERE
    The few settings that belong to YOU rather than to the project, such as
    an API key. They are read from a file called .env in the project folder.

    .env is listed in .gitignore, so Git never sees it, and the safety gate
    (check-public-safe.sh) refuses to push if it ever slips through. The
    repository only holds .env.example, a copy with every value left empty,
    so a newcomer can see which settings exist without seeing anyone's.

WHAT AN API KEY IS, AND WHY IT'S A SECRET
    A key is a long code a service gives you so it can recognise your
    requests. NCBI's is free and optional: with it, NCBI lets you ask ten
    questions a second instead of three. It is tied to your NCBI account, so
    anyone holding it can make requests that count as yours.

    A key behaves like a house key: harmless on your keyring, a problem on
    a public noticeboard. Once a key has been published on GitHub it has to
    be treated as public forever, because copies of a repository spread.

THE RULES THIS PROJECT FOLLOWS
    1. Keys are read from .env (or from the environment) and nowhere else.
       Never type one into a .py file, a notebook or a document.
    2. A key is never printed, never logged and never put in a web address.
       It travels inside the request body, where error messages and
       provenance rows never show it. The program only ever says whether a
       key is "set" or "not set".
    3. Everything works without a key. Missing keys mean slower fetching,
       never a broken project.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from microbegraph.paths import ENV_FILE


def load_settings(env_file: Path = ENV_FILE) -> bool:
    """
    Read .env into the environment, if the file exists. Returns True if it did.

    Settings already present in the environment win over the file, so a
    scheduled job (Phase 12) can supply its own values without editing .env.
    """
    return load_dotenv(env_file, override=False)


def setting(name: str) -> str:
    """One setting, with surrounding spaces and quotes removed, or "" if unset."""
    return os.environ.get(name, "").strip().strip("'\"")


def describe(value: str) -> str:
    """How a secret is shown on screen: never the value, only whether there is one."""
    return "set" if value else "not set"


def ncbi_api_key() -> str:
    """The optional NCBI key (NCBI_API_KEY in .env)."""
    return setting("NCBI_API_KEY")


def ncbi_email() -> str:
    """The optional contact address NCBI asks tools to send (NCBI_EMAIL in .env)."""
    return setting("NCBI_EMAIL")
