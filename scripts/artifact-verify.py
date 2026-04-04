#!/usr/bin/env python3
"""
Deterministic three-level artifact verification script (ADR-087).

Checks each file for:
  EXISTS      — file is present on disk
  SUBSTANTIVE — file contains real logic, not stubs
  WIRED       — file is actually imported/used by other files

Usage:
    python3 scripts/artifact-verify.py --files path/to/handler.py path/to/model.py
    python3 scripts/artifact-verify.py --files path/to/handler.py --json
    python3 scripts/artifact-verify.py --files src/main.go --root /path/to/repo

Exit codes:
    0 = all files pass all checks
    1 = any non-substantive or unwired artifacts found
    2 = usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Stub patterns by language (regex, applied to file content)
# ---------------------------------------------------------------------------

_PYTHON_STUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\braise\s+NotImplementedError\b"), "raise NotImplementedError"),
    (re.compile(r"^\s*pass\s*$", re.MULTILINE), "pass-only body"),
    (re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE), "TODO/FIXME marker"),
    (re.compile(r"^\s*\.\.\.\s*$", re.MULTILINE), "ellipsis stub (...)"),
]

_GO_STUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'\bpanic\s*\(\s*"not implemented"', re.IGNORECASE), 'panic("not implemented")'),
    (re.compile(r'\bpanic\s*\(\s*"TODO"', re.IGNORECASE), 'panic("TODO")'),
    (re.compile(r"//\s*(TODO|FIXME|HACK)\b", re.IGNORECASE), "TODO/FIXME comment"),
    (re.compile(r"\breturn\s+nil\s*$", re.MULTILINE), "return nil (bare, no preceding logic)"),
]

_TS_JS_STUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r'\bthrow\s+new\s+Error\s*\(\s*["\']not implemented', re.IGNORECASE),
        "throw new Error('not implemented')",
    ),
    (re.compile(r"//\s*(TODO|FIXME|HACK)\b", re.IGNORECASE), "TODO/FIXME comment"),
    (re.compile(r"\breturn\s+null\s*;?\s*$", re.MULTILINE), "return null (bare)"),
    (re.compile(r"\breturn\s+undefined\s*;?\s*$", re.MULTILINE), "return undefined (bare)"),
]

_GENERAL_STUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"//\s*\.\.\.", re.IGNORECASE), "// ... placeholder"),
    (re.compile(r"//\s*rest of code", re.IGNORECASE), "// rest of code"),
    (re.compile(r"/\*\s*(placeholder|stub)\s*\*/", re.IGNORECASE), "/* placeholder */"),
    (re.compile(r"#\s*\.\.\.\s*$", re.MULTILINE), "# ... placeholder"),
]


def _get_stub_patterns(suffix: str) -> list[tuple[re.Pattern[str], str]]:
    if suffix == ".py":
        return _PYTHON_STUB_PATTERNS + _GENERAL_STUB_PATTERNS
    elif suffix == ".go":
        return _GO_STUB_PATTERNS + _GENERAL_STUB_PATTERNS
    elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return _TS_JS_STUB_PATTERNS + _GENERAL_STUB_PATTERNS
    else:
        return _GENERAL_STUB_PATTERNS


# ---------------------------------------------------------------------------
# WIRED check: grep codebase for imports of the given file
# ---------------------------------------------------------------------------


def _module_name_python(file_path: Path, root: Path) -> str:
    """Convert a Python file path to its importable module name."""
    try:
        rel = file_path.relative_to(root)
    except ValueError:
        rel = file_path
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_wired(file_path: Path, root: Path) -> tuple[bool, str]:
    """
    Check whether file_path is imported/referenced by any other file in root.
    Returns (is_wired, note).
    """
    suffix = file_path.suffix.lower()
    stem = file_path.stem
    name = file_path.name

    # Collect candidate import patterns to search for
    patterns: list[str] = []

    if suffix == ".py":
        module = _module_name_python(file_path, root)
        # from module import ... OR import module
        patterns.append(f"from {module} import")
        patterns.append(f"import {module}")
        # Also check partial (last segment)
        last = module.split(".")[-1]
        if last != module:
            patterns.append(f"from {last} import")
            patterns.append(f"import {last}")
    elif suffix == ".go":
        # Go: search for the directory name in import paths
        parent_name = file_path.parent.name
        patterns.append(f'"{parent_name}"')
        patterns.append(f'/{parent_name}"')
    elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        # TS/JS: search for import from './stem' or require('./stem')
        patterns.append(f'from "./{stem}"')
        patterns.append(f"from './{stem}'")
        patterns.append(f'require("./{stem}")')
        patterns.append(f"require('{stem}')")
        patterns.append(f'from "{stem}"')
        patterns.append(f"from '{stem}'")
    else:
        # Generic: search for the filename
        patterns.append(name)

    # Search all files in root (skip node_modules, .git, __pycache__, vendor)
    skip_dirs = {".git", "__pycache__", "node_modules", "vendor", ".venv", "venv"}
    found_in: list[str] = []

    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        if candidate.resolve() == file_path.resolve():
            continue
        if any(part in skip_dirs for part in candidate.parts):
            continue
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in patterns:
            if pat in content:
                found_in.append(str(candidate.relative_to(root)))
                break
        if found_in:
            break  # one reference is enough to confirm WIRED

    if found_in:
        return True, f"imported by {found_in[0]}"
    return False, f"no imports found in codebase (searched for: {patterns[:2]})"


# ---------------------------------------------------------------------------
# SUBSTANTIVE check: look for stub patterns in file content
# ---------------------------------------------------------------------------


def _is_substantive(file_path: Path) -> tuple[bool, list[str]]:
    """
    Returns (is_substantive, list_of_stub_patterns_found).
    A file is substantive if it contains real logic beyond stubs.
    We flag it as non-substantive only if the ENTIRE file looks like a stub
    (very short content with nothing but stub lines).
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return False, [f"could not read file: {e}"]

    suffix = file_path.suffix.lower()
    patterns = _get_stub_patterns(suffix)

    stub_hits: list[str] = []
    for pattern, label in patterns:
        if pattern.search(content):
            stub_hits.append(label)

    # Count non-blank, non-comment lines as a signal of real content
    non_trivial_lines = [
        line
        for line in content.splitlines()
        if line.strip()
        and not line.strip().startswith("#")
        and not line.strip().startswith("//")
        and not line.strip().startswith("*")
        and line.strip() not in ("pass", "...", "{", "}", "(", ")")
    ]

    # A file with >10 non-trivial lines is substantive even if it has some stubs
    if len(non_trivial_lines) > 10 and stub_hits:
        return True, []

    # A file with few non-trivial lines AND stub patterns is non-substantive
    if stub_hits and len(non_trivial_lines) <= 10:
        return False, stub_hits

    return True, []


# ---------------------------------------------------------------------------
# Main verification logic
# ---------------------------------------------------------------------------


def verify_file(file_path_str: str, root: Path) -> dict[str, object]:
    file_path = Path(file_path_str).resolve()
    result: dict[str, object] = {
        "exists": False,
        "substantive": False,
        "wired": False,
    }

    # Level 1: EXISTS
    if not file_path.exists():
        result["exists_note"] = "file not found"
        return result
    result["exists"] = True

    # Level 2: SUBSTANTIVE
    is_sub, stub_patterns = _is_substantive(file_path)
    result["substantive"] = is_sub
    if stub_patterns:
        result["stub_patterns"] = stub_patterns

    # Level 3: WIRED
    is_wired, wired_note = _is_wired(file_path, root)
    result["wired"] = is_wired
    if not is_wired:
        result["wired_note"] = wired_note

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Three-level artifact verification: EXISTS, SUBSTANTIVE, WIRED.")
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        metavar="PATH",
        help="One or more file paths to verify.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON (default: human-readable).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root for WIRED search (default: current directory).",
    )
    parser.add_argument(
        "--skip-wired",
        action="store_true",
        help="Skip the WIRED check (useful for new files not yet imported).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    results: dict[str, object] = {}
    all_passed = True

    for f in args.files:
        r = verify_file(f, root)
        if args.skip_wired:
            r.pop("wired", None)
            r.pop("wired_note", None)
        results[f] = r
        if not r.get("exists") or not r.get("substantive"):
            all_passed = False
        if not args.skip_wired and not r.get("wired"):
            all_passed = False

    if args.json_output:
        print(json.dumps(results, indent=2))
    else:
        for path, r in results.items():
            exists = r.get("exists", False)
            substantive = r.get("substantive", False)
            wired = r.get("wired", "skipped")
            stub_patterns = r.get("stub_patterns", [])
            wired_note = r.get("wired_note", "")
            exists_note = r.get("exists_note", "")

            ok = "OK" if (exists and substantive and (wired is True or wired == "skipped")) else "FAIL"
            print(f"[{ok}] {path}")
            if not exists:
                print(f"      EXISTS:      FAIL — {exists_note or 'not found'}")
            else:
                print(f"      EXISTS:      OK")
            if exists:
                s_status = "OK" if substantive else "FAIL"
                print(f"      SUBSTANTIVE: {s_status}" + (f" — {stub_patterns}" if stub_patterns else ""))
            if wired != "skipped":
                w_status = "OK" if wired else "FAIL"
                print(f"      WIRED:       {w_status}" + (f" — {wired_note}" if not wired else ""))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
