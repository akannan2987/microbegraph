"""
MicrobeGraph, the ingestion command.

USAGE (from the repository root, with .venv active)

    python -m microbegraph.fetch --list                  which sources exist
    python -m microbegraph.fetch --probe                 ask every source what it has (free)
    python -m microbegraph.fetch --all                   fetch + tidy every source
    python -m microbegraph.fetch --source mibig          fetch + tidy one source
    python -m microbegraph.fetch --tidy-only --all       re-tidy from the locker, offline

WHY "python -m microbegraph.fetch" AND NOT "python fetch.py"
    "-m" means "run this MODULE from the installed package". It works from
    any folder and on any operating system, and it makes sure the code that
    runs is the package you installed with "pip install -e ." rather than
    some stray copy.

WHAT THE EXIT CODE MEANS (useful later, when Airflow runs this in Phase 12)
    0  everything worked
    1  something failed; the message says what and what to do
    2  the command was typed wrongly
"""

from __future__ import annotations

import argparse
import sys
import tarfile

import requests

from microbegraph.sources import SOURCES, get_source
from microbegraph.sources.base import SourceError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m microbegraph.fetch",
        description="Probe, fetch and tidy MicrobeGraph's public data sources.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="list the registered sources")
    mode.add_argument("--probe", action="store_true",
                      help="ask each source what it has, without downloading")
    mode.add_argument("--tidy-only", action="store_true",
                      help="rebuild staging tables from the locker, without the network")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--all", action="store_true", help="every registered source")
    which.add_argument("--source", action="append", choices=sorted(SOURCES),
                       help="one source by name (repeat for several)")
    parser.add_argument("--debug", action="store_true",
                        help="show the full Python error instead of the short message")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.list:
        for name, cls in SOURCES.items():
            print(f"  {name:<10} {cls.homepage}  (licence {cls.licence})")
        return 0

    # Probing everything is harmless, so --probe alone means "all sources".
    names = list(SOURCES) if (args.all or (args.probe and not args.source)) else args.source
    if not names:
        print("Say which sources: --all, or --source NAME. (--list shows the names.)")
        return 2

    failures = 0
    for name in names:
        source = get_source(name)
        try:
            if args.probe:
                if not _run_probe(source):
                    failures += 1
            else:
                if not args.tidy_only:
                    print(f"[{name}] fetch")
                    source.fetch()
                print(f"[{name}] tidy")
                result = source.tidy()
                print(f"  [{name}] wrote {result.nodes_path.name} and {result.edges_path.name}")
                # Pad every name to the longest one, so the numbers line up in a column.
                width = max((len(key) for key in result.counts), default=0)
                for key, value in result.counts.items():
                    print(f"    {key:<{width}} {value:>6}")
        except (SourceError, requests.RequestException, OSError,
                tarfile.TarError, EOFError) as error:   # EOFError: a cut-off archive
            failures += 1
            if args.debug:
                raise
            print(f"\n[{name}] FAILED: {error}\n  (add --debug to see the full error)")

    return 1 if failures else 0


def _run_probe(source: object) -> bool:
    """Print one source's probe report. Returns False if the source was unreachable."""
    print(f"[{source.name}] probe")  # type: ignore[attr-defined]
    report = source.probe()  # type: ignore[attr-defined]
    for fact in report.facts:
        print(f"  {fact}")
    for warning in report.warnings:
        print(f"  WARNING: {warning}")
    if not report.reachable:
        # Not treated as a crash, because the probe still told you something useful.
        print("  (source not reachable right now)")
    return report.reachable


if __name__ == "__main__":
    sys.exit(main())
