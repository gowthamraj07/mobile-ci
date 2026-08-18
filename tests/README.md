# Workflow logic tests

Behavioural tests for shell logic embedded in the reusable workflows.

## Why the logic is inline, and the tests reach into the YAML

A reusable workflow's `actions/checkout` clones the **calling app's** repo, not this
one. Anything in `.github/scripts/` here simply does not exist on the runner, so
non-trivial `run:` logic has to live inline in the workflow file.

Rather than keep a second copy to test against — which would drift — each test loads
the workflow with PyYAML, pulls out the named step's `run:` block, and executes it
under `bash -e` (the shell GitHub Actions uses) with the step's env vars. What runs
in CI is what the test asserts on.

## Running them

```sh
python3 tests/test_promotion_path.py
```

`ci.yml` runs every `tests/test_*.py` on PRs and on pushes to `main`, and the `v1`
tag only advances once they pass.

## The tests

| File | Covers |
|------|--------|
| `test_promotion_path.py` | `promote.yml` → *Validate promotion path*: the default ladder, per-app `allowed-promotions`, separator/whitespace tolerance, and failing closed on an empty policy. |
