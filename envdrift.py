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
  envdrift --help
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


def report(files: List[Path], strict: bool) -> int:
    parsed = [(p, *parse_env(p)) for p in files]
    all_keys: set[str] = set()
    for _, ks, _ in parsed:
        all_keys.update(ks.keys())

    drift = False
    print(f"envdrift: comparing {len(files)} file(s), {len(all_keys)} unique key(s)\n")

    # Missing keys per file
    for path, ks, dupes in parsed:
        missing = sorted(all_keys - ks.keys())
        if missing:
            drift = True
            print(f"  [missing in {path}]")
            for k in missing:
                print(f"    - {k}")
        if dupes:
            drift = True
            print(f"  [duplicates in {path}]")
            for k in sorted(set(dupes)):
                print(f"    - {k}")

    # Placeholder / empty values (strict mode)
    if strict:
        for path, ks, _ in parsed:
            bad = [k for k, v in ks.items() if v.lower() in PLACEHOLDER_VALUES]
            if bad:
                drift = True
                print(f"  [placeholder values in {path}]")
                for k in sorted(bad):
                    print(f"    - {k} = {ks[k]!r}")

    if not drift:
        print("  ok — no drift detected :>")
        return 0
    print("\nenvdrift: drift detected")
    return 1


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
    p.add_argument("--version", action="version", version="envdrift 0.1.0")
    args = p.parse_args(argv)

    if len(args.files) < 2:
        print("envdrift: need at least 2 files to compare", file=sys.stderr)
        return 2

    return report([Path(f) for f in args.files], args.strict)


if __name__ == "__main__":
    sys.exit(main())
