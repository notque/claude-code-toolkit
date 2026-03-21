#!/usr/bin/env python3
"""Perses Lint Gate Hook.

Blocks raw `percli apply` commands and redirects to the perses-lint skill
to ensure validation before deployment.

Event: PreToolUse (Bash)
"""

import json
import re
import sys


def main():
    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError, ValueError):
        # Safety gate fails closed: if we can't parse the event, block
        print("[perses-lint-gate] WARNING: could not parse hook event", file=sys.stderr)
        sys.exit(2)

    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "")

    # Detect percli apply without prior lint
    if re.search(r"percli\s+apply", command):
        # Check if lint was also in the command chain
        if not re.search(r"percli\s+lint", command):
            print(
                "[perses-lint-gate] BLOCKED: percli apply detected without percli lint.\n"
                "Run `percli lint -f <file>` first to validate resources.\n"
                "[fix-with-skill] perses-lint"
            )
            # Exit 2 to block the tool use
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
