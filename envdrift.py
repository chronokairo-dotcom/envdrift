#!/usr/bin/env python3
"""envdrift — detect drift between .env files.

Zero dependencies. Compares 2+ dotenv-style files and reports:
  - keys missing in some files
  - keys with empty/placeholder values
  - duplicate keys within a single file

Exit codes:
  0  no drift
  1  drift detected
  2  usage / file error

Usage:
  envdrift .env.example .env
  envdrift .env.example .env .env.local --strict
  envdrift --json .env.example .env
  envdrift --ci   .env.example .env   # GitHub Actions annotations
  envdrift --help
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

__version__ = "0.2.0"

PLACEHOLDER_VALUES = {"", "changeme", "todo", "xxx", "your-key-here", "<your-key>"}


def parse_env(path: Path) -> Tuple[Dict[str, str], List[str]]:
    """Parse a dotenv file. Returns (keys->value, duplicate_keys)."""
    keys: Dict[str, str] = {}
    dupes: List[str] = []
    seen: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"envdrift: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if not k:
            continue
        if k in seen:
            dupes.append(k)
        seen.add(k)
        keys[k] = v
    return keys, dupes


def analyze(files: List[Path], strict: bool) -> dict:
    """Return a structured drift report."""
    parsed = [(p, *parse_env(p)) for p in files]
    all_keys: set[str] = set()
    for _, ks, _ in parsed:
        all_keys.update(ks.keys())

    per_file = []
    drift = False
    for path, ks, dupes in parsed:
        missing = sorted(all_keys - ks.keys())
        dup_unique = sorted(set(dupes))
        placeholders = []
        if strict:
            placeholders = sorted(
                k for k, v in ks.items() if v.lower() in PLACEHOLDER_VALUES
            )
        if missing or dup_unique or placeholders:
            drift = True
        per_file.append(
            {
                "file": str(path),
                "missing": missing,
                "duplicates": dup_unique,
                "placeholders": placeholders,
            }
        )

    return {
        "files": [str(p) for p in files],
        "unique_keys": sorted(all_keys),
        "drift": drift,
        "results": per_file,
    }


def render_human(report: dict) -> None:
    print(
        f"envdrift: comparing {len(report['files'])} file(s), "
        f"{len(report['unique_keys'])} unique key(s)\n"
    )
    for entry in report["results"]:
        path = entry["file"]
        if entry["missing"]:
            print(f"  [missing in {path}]")
            for k in entry["missing"]:
                print(f"    - {k}")
        if entry["duplicates"]:
            print(f"  [duplicates in {path}]")
            for k in entry["duplicates"]:
                print(f"    - {k}")
        if entry["placeholders"]:
            print(f"  [placeholder values in {path}]")
            for k in entry["placeholders"]:
                print(f"    - {k}")
    if report["drift"]:
        print("\nenvdrift: drift detected")
    else:
        print("  ok — no drift detected :>")


def render_ci(report: dict) -> None:
    """Emit GitHub Actions workflow command annotations.

    See: https://docs.github.com/actions/reference/workflow-commands-for-github-actions
    """
    for entry in report["results"]:
        path = entry["file"]
        for k in entry["missing"]:
            print(f"::error file={path}::envdrift: missing key {k}")
        for k in entry["duplicates"]:
            print(f"::warning file={path}::envdrift: duplicate key {k}")
        for k in entry["placeholders"]:
            print(f"::warning file={path}::envdrift: placeholder value for {k}")
    if not report["drift"]:
        print("::notice::envdrift: no drift detected")


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="envdrift",
        description="Detect drift between .env files (zero deps).",
    )
    p.add_argument("files", nargs="+", help="env files to compare (2+)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="also flag empty/placeholder values (changeme, todo, xxx, ...)",
    )
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="emit JSON report to stdout")
    fmt.add_argument(
        "--ci",
        action="store_true",
        help="emit GitHub Actions error/warning annotations",
    )
    p.add_argument("--version", action="version", version=f"envdrift {__version__}")
    args = p.parse_args(argv)

    if len(args.files) < 2:
        print("envdrift: need at least 2 files to compare", file=sys.stderr)
        return 2

    report = analyze([Path(f) for f in args.files], args.strict)

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    elif args.ci:
        render_ci(report)
    else:
        render_human(report)

    return 1 if report["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
