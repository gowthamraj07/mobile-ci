#!/usr/bin/env python3
"""Tests for promote.yml's "Validate promotion path" gate.

The gate lives INLINE in the reusable workflow and has to stay there: a reusable
workflow's `actions/checkout` clones the CALLING app's repo, not this one, so a
script file next to it would not exist on the runner. The test therefore lifts the
step's `run:` script straight out of the YAML and executes it — no second copy of
the logic to drift out of sync.

    python3 tests/test_promotion_path.py
"""

import pathlib
import subprocess
import sys

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/promote.yml"
STEP_NAME = "Validate promotion path"

LADDER = "internal->alpha, alpha->beta, beta->production"


def validator_script() -> str:
    # `on:` is parsed by PyYAML as the boolean True (YAML 1.1), so reach for the
    # jobs tree, which is unambiguous.
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = doc["jobs"]["promote"]["steps"]
    for step in steps:
        if step.get("name") == STEP_NAME:
            return step["run"]
    raise AssertionError(f"No step named {STEP_NAME!r} in {WORKFLOW}")


def run(script: str, frm: str, to: str, allowed: str) -> subprocess.CompletedProcess:
    # `bash -e` is what GitHub Actions uses for a `run:` block.
    return subprocess.run(
        ["bash", "-e", "-c", script],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "FROM": frm, "TO": to, "ALLOWED": allowed},
        capture_output=True,
        text=True,
    )


CASES = [
    # (name, from, to, allowed, should_pass)
    ("ladder: internal->alpha allowed", "internal", "alpha", LADDER, True),
    ("ladder: alpha->beta allowed", "alpha", "beta", LADDER, True),
    ("ladder: beta->production allowed", "beta", "production", LADDER, True),
    # The regression this change is about: the default must still refuse the jump,
    # and an app that declares it must be able to make it.
    ("ladder: internal->production refused", "internal", "production", LADDER, False),
    ("declared: internal->production allowed", "internal", "production", "internal->production", True),
    # A declared policy is exhaustive — it does not also inherit the ladder.
    ("declared: unlisted hop refused", "alpha", "beta", "internal->production", False),
    # Formatting tolerance: commas, newlines, tabs, spaces around the arrow.
    ("format: newline separated", "alpha", "beta", "internal->alpha\nalpha->beta\n", True),
    ("format: spaces around arrow", "internal", "production", "internal -> production", True),
    ("format: tabs and double spaces", "beta", "production", "internal->alpha,\tbeta ->  production", True),
    ("format: trailing comma", "internal", "alpha", "internal->alpha,", True),
    # Degenerate policies must fail closed, never open.
    ("empty policy refused", "internal", "alpha", "", False),
    ("whitespace-only policy refused", "internal", "alpha", "   \n  ", False),
    # No partial or substring matching.
    ("no prefix match", "internal", "alph", LADDER, False),
    ("no reverse hop", "alpha", "internal", LADDER, False),
    ("no self hop", "internal", "internal", LADDER, False),
]


def main() -> int:
    script = validator_script()
    failures = []

    for name, frm, to, allowed, should_pass in CASES:
        result = run(script, frm, to, allowed)
        passed = result.returncode == 0
        if passed != should_pass:
            failures.append(
                f"{name}: expected {'accept' if should_pass else 'reject'}, "
                f"got exit {result.returncode}\n"
                f"    stdout: {result.stdout.strip()}\n"
                f"    stderr: {result.stderr.strip()}"
            )
            print(f"FAIL  {name}")
            continue

        # A rejection must say so in a way the Actions UI surfaces.
        if not should_pass and "::error::" not in result.stdout:
            failures.append(f"{name}: rejected without an ::error:: annotation")
            print(f"FAIL  {name}")
            continue

        print(f"ok    {name}")

    print()
    if failures:
        print(f"{len(failures)} of {len(CASES)} cases failed:\n")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(CASES)} promotion-path cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
