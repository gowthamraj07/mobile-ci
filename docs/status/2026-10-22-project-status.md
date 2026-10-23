# mobile-ci — project status report

**Project:** mobile-ci · **Group:** Fleet tooling · **Audit date:** 2026-10-22
**Audited revision:** `d66a935` — *fix(release): publish jobs inherit the transitive skip; add verify-published guard (#6)*, committed 2026-07-27
**Run type:** first run — **no previous report and no `docs/status/scores.csv` existed, so there is no delta to report.** This run establishes the baseline.

## Preflight caveats — read before acting on any number

1. **The audited revision is NOT the revision the fleet consumes.** Every app pins
   `gowthamraj07/mobile-ci/...@v1`. A read-only `git ls-remote` shows
   `refs/tags/v1` and `refs/heads/main` both at **`854b961`**, while this working copy is at
   **`d66a935`** (`.git/FETCH_HEAD` last written 2026-07-27 — roughly three months stale).
   Nothing was fetched for this audit, by instruction. **Every finding below was verified
   against local HEAD `d66a935` only.** Where a finding could be affected by the eight-plus
   commits between `d66a935` and `854b961`, it is marked **[HEAD-only — unverified at `v1`]**.
   Findings about the repo's *process* (how `v1` moves, what gates it) are marked
   **[structural]** and hold regardless of which commit `v1` names, because the mechanism
   itself is what is at issue.
2. **Two consumer-referenced features do not exist at `d66a935`.** `NEPtune-Mobile`'s
   `.github/workflows/promote.yml` (a) calls
   `gowthamraj07/mobile-ci/.github/workflows/submit-ios.yml@v1` — **no such file here** — and
   (b) passes an `allowed-promotions:` input to `promote.yml`, which **declares no such
   input** here (an undeclared input is a hard workflow error, not a warning). Either `v1`
   has advanced to include both, or the fleet's iOS promotion is broken. **This audit cannot
   tell those two apart without fetching.** The consumer's own file is dated later than
   `d66a935`, so the former is the likely explanation — but it is inference, not evidence.
3. **No knowledge graph.** `code-review-graph` indexes source code; this repo is 7 YAML
   files and 2 Markdown files, so all structural evidence here is `grep`/`find`/direct
   reading of the YAML. Nothing was executed: no `act`, no dispatch, no re-run.
4. **Working tree is clean** at `d66a935` (`git status --short` empty). No unshipped local work.
5. **No `openspec/`.** The module list below was derived by hand (see *Method*).

---

## The objective

No `openspec/config.yaml`, no `CLAUDE.md` and no `project_objective` memory exist for this
repo. The objective is therefore quoted verbatim from `README.md`, lines 1–11, which is the
repo's only statement of intent:

> # mobile-ci
>
> Shared CI for my Compose Multiplatform apps. Reusable workflows:
> - **`pr-check.yml`** — build gate for every PR/push: detekt, lint, unit +
>   screenshot tests, assemble, and a two-tier iOS check.
> - **`release.yml`** — a single run that ships **iOS and Android at the same version**.
> - **`sync-listing.yml`** — push the **Google Play store listing** (icon, feature
>   graphic, screenshots, listing text) on demand, decoupled from releases.
> - **`promote.yml`** — promote an Android release up the Play track ladder.
> - **`cleanup.yml`** — scheduled repo housekeeping (old runs / container images).
>
> All the secret names these workflows read live in one place: **[`SECRETS.md`](./SECRETS.md)**.

…reinforced by `pr-check.yml`'s own header, which states the operative goal in one line:

> One place to own the fleet's build gate so every app verifies identically and fixes land once.

Operationally: **every app in the fleet verifies and releases identically, through one place.**

### Alignment axes

Derived from the objective's own words, adapted to CI rather than to an application:

| Axis | Objective's words | What it covers |
|---|---|---|
| **V — Verify identically** | "build gate for every PR/push … every app verifies identically and fixes land once" | `pr-check`, per-app configurability |
| **S — Ship identically** | "a single run that ships iOS and Android at the same version" | `release` DAG, version derivation, Android publish, iOS/match, Play store ops |
| **F — Fleet safety** | the enablers nobody requests: "all the secret names … live in one place", "`v1` can never point at an invalid revision" | secret contract, the `v1` release train, housekeeping |

A future run must reuse these three axes or the deltas are meaningless.

---

## Headline

**Overall 75%** — V 85% · S 70% · F 70%

First run: **no delta** (no prior report, no prior `scores.csv`).

Read the split, not the blend. The thing this repo does most often (verify a PR) is in good
shape; the thing it does most consequentially (ship a release) is where the correctness debt
sits, and the machinery that protects the fleet from this repo itself (**F**) is the weakest
link relative to its blast radius.

### Why this repo is weighted by blast radius, not size

Nine tracked files, ~1,730 lines of YAML — and every mobile app the user owns calls it by a
moving `@v1` tag. A defect here is not a defect in one app; it is a defect in all of them
simultaneously, with no staged rollout between the merge and the breakage. The repo knows
this: `ci.yml`'s header says so outright ("a broken push to a reusable workflow would break
EVERY app at once — this already happened once"), and `release.yml` carries two separate
failure-mode postmortems in comments, each naming the real run id it was found in. The
scoring below reflects that — a Low-severity item in a single app would not be worth a line;
here it is multiplied by the fleet.

---

## Module table

Sorted by axis, then by score ascending — least complete first.

| Module | Axis | Score | Label | reqs | bugs | gaps | verification | surface | What's missing |
|---|---|---|---|---|---|---|---|---|---|
| Per-app configurability (inputs & toggles) | V | **80%** | 🟢 Shipped, with gaps | 7 | 1 | 1 | lint only; opt-in paths unexercised | 18 `workflow_call` inputs across 5 workflows | `release.yml` hardcodes `xcode-version: latest-stable` with no input, while `pr-check` exposes one — so the *signed* build is the one that cannot be pinned. CocoaPods / `ios-workspace` / `ios-prebuild-command` paths have no known consumer. |
| `pr-check` build gate | V | **85%** | 🟢 Shipped, with gaps | 8 | 2 | 1 | exercised daily by consumers + actionlint | `pr-check.yml`, called by `NEPtune-Mobile/.github/workflows/ci.yml` | macOS `ios-check` uploads nothing on failure (only the ubuntu job does). `ios-prebuild-command` is run as `bash -c "$CMD"`. |
| Version & versionCode derivation | S | **65%** | 🟡 Partial | 5 | 3 | 2 | none — inline bash, no test of the arithmetic | `version` job outputs consumed by every other job | No semver validation and no enforcement of the documented `minor<100`/`patch<100` constraint. |
| iOS signing & TestFlight (match → gym → pilot) | S | **65%** | 🟡 Partial | 8 | 3 | 2 | **never proven end-to-end anywhere in the fleet** | `build-ios` + `publish-ios` jobs | The readiness gate and the job's own preflight disagree about what "configured" means (see DEBT-2). No app has ever completed this path: NEPtune's own header records the certs repo as empty with no `MATCH_*` value set, so iOS skips. |
| `release` DAG — build-before-tag + fail-loud | S | **70%** | 🟡 Partial | 8 | 4 | 2 | real consumer runs (two postmortems cite run ids) + actionlint | 7-job DAG in `release.yml` | `verify-published` only catches the *neither-platform-ready* case, so one mis-forwarded secret still produces a green run (DEBT-3). The published AAB is a *rebuild*, not the artifact the gate verified. |
| Play store operations (`promote` + `sync-listing`) | S | **75%** | 🟢 Shipped, with gaps | 6 | 3 | 1 | promote's validator observably exercised; listing lint-only | `promote.yml`, `sync-listing.yml` | The promotion ladder is hardcoded and rejects the only hop the consuming app can perform; the `allowed-promotions` input its caller passes does not exist at this revision (DEBT-5). |
| Android signing & Play publish | S | **80%** | 🟢 Shipped, with gaps | 6 | 2 | 1 | proven: NEPtune shipped 1.2.0 → code 10200 | `compile-android` + `publish-android` | Readiness checks 2 of the 5 Android secrets, so a missing `RELEASE_STORE_PASSWORD` declares "ready" and then dies inside Gradle. `track` is interpolated inline into the publish command. |
| `v1` release train & self-check | F | **65%** | 🟡 Partial | 5 | 2 | 3 | actionlint on itself; no behavioural test | `ci.yml` (`lint` → `advance-v1`), `dependabot.yml`, SHA-pinned third-party actions | The only gate on the moving tag every app consumes is a **syntax** linter — and both fleet-breaking bugs this repo has already shipped were actionlint-clean. No immutable `v1.x` tags, so no consumer can pin away from a bad `v1` and there is no rollback path (DEBT-1). |
| Secret contract & cross-owner forwarding | F | **70%** | 🟡 Partial | 5 | 1 | 2 | manual; nothing asserts doc/code name parity | `SECRETS.md` + 4 runtime credential checks | Nothing can detect a **partial** forwarding or a typo'd secret name — the failure mode cross-owner callers actually hit. "Graceful degradation" is inconsistent: `release` dry-runs silently, `promote`/`sync-listing` hard-fail, iOS claims "skipped" but hard-fails in one case. |
| Repo housekeeping (`cleanup.yml`) | F | **80%** | 🟢 Shipped, with gaps | 3 | 2 | 0 | lint only | `cleanup.yml` | `ignore-versions` protects only branch-shaped tags, so a semver container tag still in service can be pruned once 10 newer versions exist. No `timeout-minutes`. |

**Labels:** 0 ✅ Complete · 5 🟢 Shipped-with-gaps · 5 🟡 Partial · 0 🟠 Started · 0 ⬜ Not-started · 0 ⛔ Deferred.

Nothing is deferred: this repo keeps no deliberate-exclusion list, and no module here is a
declared non-goal.

---

## Correctness debt

Ranked by severity. Every item below was read directly out of the YAML at `d66a935`.
Nothing was executed.

### High

**DEBT-1 — The only gate on a fleet-wide moving tag is a syntax linter.** `[structural]`
`ci.yml` runs `actionlint` and then `advance-v1` force-moves `v1` to the new commit
(`git tag -f v1 && git push -f origin v1`). Every app pins `@v1`, so the moment a workflow
change lands on `main`, every app in the fleet is on it — with no smoke test against a
fixture app, no staged rollout, and no immutable `v1.x.y` tag to pin back to. The repo's own
comments record **two** fleet-affecting bugs that already shipped this way (the `tag` job
skipped by an unconfigured iOS; the publish jobs inheriting that skip transitively) — and
**both were actionlint-clean**, because both were semantic, not syntactic. The claim in
`README.md` that "`v1` can never point at an invalid revision" is true only for *invalid*
in the parser's sense. *Module: `v1` release train (F).*
*Consequence: one bad merge breaks every app's CI at once, with no rollback path.*

**DEBT-2 — iOS readiness gate and iOS preflight disagree; the gap hard-fails the whole
release.** `[HEAD-only — unverified at v1]`
`release.yml` `version` → *Detect publishability* sets `ios=true` after checking **six**
secrets: `MATCH_GIT_URL`, `MATCH_PASSWORD`, the three `APP_STORE_CONNECT_API_KEY_*` and
`APPLE_TEAM_ID`. It never checks the **transport** credential. `build-ios`'s own
*Verify Apple credentials are present* step then checks a **seventh**, scheme-aware:
`MATCH_GIT_BASIC_AUTHORIZATION` for an `https://` certs repo, `MATCH_GIT_SSH_KEY` for
`git@`/`ssh://`. So with six of seven set, `ios_ready == 'true'`, a macOS runner starts, and
the job **exits 1** in its second step. *Module: iOS signing (S).*
*Consequence is worse than a wasted job:* `tag` requires
`build-ios.result == 'success' || 'skipped'`, and this is `failure` — so no tag is pushed,
`publish-android` and `publish-ios` are skipped, and `verify-published` fails the run. **A
missing iOS transport secret takes the Android release down with it.** The documented
contract ("the iOS job is *skipped, not failed*, until the Apple secrets exist — Android
still releases") is contradicted precisely in this case. Fix is one block: move the
scheme-aware check into *Detect publishability*.

**DEBT-3 — A GitHub Release can ship a debug-signed, unpublishable AAB, green.**
`[HEAD-only — unverified at v1]`
In `publish-android`, *Configure release signing* sets `signed=false` and emits only a
`::warning::` when `RELEASE_KEYSTORE_B64` is absent, then builds anyway. The Play upload is
correctly gated on `signed == 'true' && play available`. But *Create GitHub Release* is gated
on `github.ref_type == 'tag' || (signed && play)` — **the first disjunct alone is enough**.
On a `v*` tag push with no keystore, `gh release create` therefore attaches the
**debug-signed** AAB to a public GitHub Release. Meanwhile `android_ready` is `false`, so
`verify-published` does not require Android to have published and the run is **SUCCESS**.
*Module: release DAG (S) / Android publish (S).*
*Consequence: a release that looks shipped, carries an artifact that can never be installed
as an upgrade or uploaded to Play, and raises no failure.*

### Medium

**DEBT-4 — `verify-published` is fleet-blind to a single-platform silent non-publish.**
`[HEAD-only]` The guard fails a run only when **neither** platform is ready. A platform
judged "not ready" is never *required* to publish — which is correct for an app that
genuinely has no iOS, and indistinguishable from an app whose `RELEASE_KEYSTORE_B64` was
renamed, typo'd, or not forwarded. That app's releases stay green forever while nothing
reaches Play. *Module: release DAG (S).* Fix: an explicit per-platform
`android-required` / `ios-required` input, defaulting to "required if any secret for that
platform arrived".

**DEBT-5 — The promotion ladder is hardcoded against its only consumer's process.**
`[HEAD-only — unverified at v1]` `promote.yml` whitelists exactly
`internal->alpha`, `alpha->beta`, `beta->production`. NEPtune has one internal track with
four testers and needs `internal->production`; its caller passes
`allowed-promotions: internal->production`, an input **`promote.yml` does not declare at
this revision** — which fails the run as an undefined input rather than at the validator.
Either `v1` already carries that input (likely, given the consumer's commit is later) or
every NEPtune promotion is broken. **Unresolvable without fetching.** *Module: Play store
operations (S).*

**DEBT-6 — `versionName` is never validated; a bad one yields versionCode 0 and poisons the
next auto-bump.** `[HEAD-only]` The `version` job computes
`CODE=$(( MAJOR*10000 + MINOR*100 + PATCH ))`. Bash evaluates an unset/non-numeric name as
`0` without erroring, so a dispatch with `versionName: abc` produces **`CODE=0`** and tag
**`vabc`** — and once `vabc` exists, the auto-bump path (`git tag -l 'v*' --sort=-v:refname
| head -n1`) can read it back and derive a nonsense next version. *Module: version
derivation (S).*

**DEBT-7 — The documented `minor < 100` / `patch < 100` constraint is unenforced.**
`[HEAD-only]` `1.100.0` encodes to `1*10000 + 100*100 = 20000`, identical to `2.0.0`.
`README.md` documents the constraint; nothing checks it. *Module: version derivation (S).*

**DEBT-8 — Android readiness checks 2 of the 5 Android secrets.** `[HEAD-only]`
`android_ready` requires only `RELEASE_KEYSTORE_B64` + `PLAY_SERVICE_ACCOUNT_JSON`. A missing
`RELEASE_STORE_PASSWORD`, `RELEASE_KEY_ALIAS` or `RELEASE_KEY_PASSWORD` declares the platform
ready and then fails deep inside `bundleRelease` with a Gradle signing error instead of a
readable preflight message. The same asymmetry as DEBT-2, other platform.
*Module: Android publish (S).*

**DEBT-9 — Nothing detects a partial or misnamed secret forwarding.** `[structural]`
`SECRETS.md` is canonical and (verified by grep at this revision) matches the names the
workflows actually read. But the cross-owner hazard it warns about is all-or-nothing only in
its *worst* case; the common case is one name drifting. No workflow reports which secret
names arrived non-empty, so an app can be silently half-configured indefinitely.
*Module: secret contract (F).*

### Low (listed, not detailed)

`gh release create` is non-idempotent — a re-run of a tag-push release fails at the final
step, *after* publishing to Play. · `publish-android` **rebuilds** the AAB rather than
publishing the artifact `compile-android` verified, so the shipped binary is not the gated
one. · The iOS build number is `GITHUB_RUN_NUMBER`, which is not monotonic across a workflow
rename and is reused by a re-run → TestFlight duplicate-build rejection. · `track`,
`android-module` and both `*-prebuild-gradle-task` inputs are interpolated inline into `run:`
blocks, while `versionName` was deliberately hardened via `env:` for exactly that reason —
the hardening is inconsistent. · `pr-check`'s `ios-prebuild-command` executes
`bash -c "$CMD"`. · `release.yml` pins Xcode to `latest-stable`, so an Apple Xcode bump can
break every app's signed build simultaneously. · `cleanup.yml`'s `ignore-versions` protects
only branch-shaped tags. · `advance-v1` moves `v1` on any workflow-touching push to `main`,
including changes to `cleanup.yml` that no release path uses, with no record of what moved. ·
No `timeout-minutes` on `ci.yml` or `cleanup.yml` jobs.

### What the docs get right

Worth stating, because this audit is largely a list of what is wrong: `SECRETS.md` and
`README.md` are **accurate** where they could easily have drifted. Both warn about
`secrets: inherit` in the right terms, the secret-name table matches the YAML, the
`printf` vs `echo` note is correct and followed in all four credential-writing steps, and
the two postmortem comments in `release.yml` name real run ids. This is unusually honest
documentation for CI, and it is why several findings above could be confirmed at all.

---

## The three reported failure modes

| # | Reported (from `NEPtune-Mobile`) | Verdict against `d66a935` |
|---|---|---|
| a | `secrets: inherit` silently forwards nothing across repository owners, so cross-owner callers must name secrets explicitly | **Confirmed as a real hazard, and correctly handled here.** Not verifiable from YAML as a GitHub platform behaviour, but the repo treats it as true in both `README.md` and `SECRETS.md`, declares all 14 secrets `required: false`, and — critically — `verify-published` **does** catch the all-empty case: both platforms read not-ready, so the run fails with a pointer to `SECRETS.md` rather than reporting green. `promote`/`sync-listing` fail fast on the same condition. `pr-check` is immune (declares no secrets). **Residual gap:** only the *total* case is caught; a partial forwarding is not (DEBT-9). |
| b | The iOS readiness gate does not check the transport secret, so a job with six of seven secrets declares itself ready and then dies in preflight | **Confirmed, and the consequence is worse than reported.** `release.yml` *Detect publishability* checks six secrets and omits the transport credential; `build-ios`'s own preflight checks seven, scheme-aware. Six-of-seven ⇒ `ios_ready=true` ⇒ macOS runner starts ⇒ `exit 1`. Because `tag` tolerates a *skipped* iOS but not a *failed* one, the failure **blocks the tag and the Android publish too** — the whole release, not just iOS. See DEBT-2. |
| c | A missing Android signing secret can still produce a SUCCESS run with an unpublishable debug-signed artifact ("green ≠ published") | **Confirmed, in two distinct shapes.** (i) On a `v*` **tag push** with no keystore, *Create GitHub Release* fires on `github.ref_type == 'tag'` alone and publishes the **debug-signed** AAB as a GitHub Release asset; the run is SUCCESS (DEBT-3). (ii) On any trigger, a not-ready Android platform is never *required* to publish by `verify-published`, so a mis-forwarded or typo'd keystore secret yields an indefinitely green release that reaches Play never (DEBT-4). The `::warning::` is the only signal, and warnings do not fail runs. |

---

## Unspecified surface

Nothing in this repo lacks a module — 7 of 7 workflows and both docs are covered above. The
gap runs the *other* way, which for shared CI is the more dangerous direction:

- **`submit-ios.yml` — referenced by a consumer, absent here.**
  `NEPtune-Mobile/.github/workflows/promote.yml` calls
  `gowthamraj07/mobile-ci/.github/workflows/submit-ios.yml@v1` with `version` /
  `build-number` inputs and four App Store Connect secrets. No such file exists at
  `d66a935`. Scored nowhere, because it cannot be audited: it is either present at `v1`
  (unread) or the consumer's iOS promotion is broken.
- **`promote.yml`'s `allowed-promotions` input** — same situation (DEBT-5).

Both are the direct consequence of Caveat 1 and resolve the moment this clone is fetched.

## Deliberate exclusions

None declared. The repo keeps no `deferred-*` list, and no scoped-out item was found in
`README.md` or `SECRETS.md`. Two items are *noted* as not-yet-wired rather than excluded —
App Store screenshots via fastlane `deliver` ("not yet wired") and byte-reproducible
archives (left to the consumer by a comment) — and both are carried in *Later* below rather
than scored as absent modules.

---

## Development plan

Priority = `axis_weight × (100 − score) ÷ 100`, with **F raised from the rubric's enabler
weight of 1 to 3**: in shared CI the enablers *are* the blast radius, so F ranks alongside
S (see *Method*). Weights used: **S = 3 · F = 3 · V = 2.** Correctness debt jumps the queue
regardless of score, and a blocked prerequisite outranks its dependent — which is why the
fetch comes first.

### Now

| # | Item | Module · axis · score | Outcome |
|---|---|---|---|
| 1 | **Fetch and re-audit before changing anything.** This clone is at `d66a935`; `v1` and `main` are at `854b961`. The fleet is running a revision nobody has reviewed here, and two consumer-referenced features (`submit-ios.yml`, `allowed-promotions`) can't be resolved until then. | `v1` release train · F · 65% | The audited revision and the consumed revision are the same, and DEBT-2/3/5/6/7/8 are re-checked against what apps actually run. |
| 2 | **Move the scheme-aware transport check into *Detect publishability*.** | iOS signing · S · 65% | A six-of-seven iOS config is cleanly **skipped**, Android still releases, and no macOS runner is started to fail two steps in. Closes DEBT-2 (High). |
| 3 | **Gate *Create GitHub Release* on `signed == 'true' && play available`, dropping the bare `github.ref_type == 'tag'` disjunct.** | release DAG · S · 70% | No run can ever attach a debug-signed AAB to a GitHub Release. Closes DEBT-3 (High). |
| 4 | **Make `verify-published` per-platform strict** — require a platform to publish when any of its secrets arrived non-empty, via explicit `android-required` / `ios-required` inputs. | release DAG · S · 70% | A single missing or mis-forwarded secret fails loudly instead of shipping green. Closes DEBT-4, and most of the residual gap in failure mode (a). |
| 5 | **Validate `versionName` in the `version` job** — semver shape, and enforce `minor < 100` / `patch < 100` before computing `CODE`. | version derivation · S · 65% | No `versionCode 0`, no `vabc` tag, no poisoned auto-bump, no `1.100.0`/`2.0.0` collision. Closes DEBT-6 and DEBT-7. |

### Next (1–2 months)

- **Smoke-test the reusable workflows against a fixture app before `v1` moves, and cut
  immutable `v1.x.y` tags.** `v1` release train · F · 65%. The single highest-leverage change
  in the repo: it is the only item that would have caught either of the two bugs that already
  shipped, and immutable tags give consumers somewhere to roll back to. Closes DEBT-1.
- **Report arriving secret names.** A preflight step that prints which of the names in
  `SECRETS.md` arrived non-empty (names only, never values). Secret contract · F · 70%.
  Closes DEBT-9 and makes a cross-owner partial forwarding diagnosable in one glance.
- **Add an `xcode-version` input to `release.yml`** for parity with `pr-check`, and pin it in
  the fleet. Per-app configurability · V · 80% / iOS signing · S · 65%.
- **Replace `GITHUB_RUN_NUMBER` as the iOS build number** with a monotonic source.
  Version derivation · S · 65%.
- **Make `gh release create` idempotent, and publish the gate-verified AAB** instead of
  rebuilding it in `publish-android`. release DAG · S · 70%.

### Later

- **Prove the iOS path end-to-end once, on one real app.** No app in the fleet has ever
  completed `match → gym → pilot` through this workflow; half the headline objective
  ("ships iOS and Android at the same version") is unexercised. This is why iOS scores 65%
  with a Verification of 5/20, and no amount of code review substitutes for one green run.
- **Give the fleet contract a written spec.** Behaviour here was *judged*, not counted —
  there are no capability specs, so the `reqs` counts are contract clauses read out of
  `README.md` and the workflow headers. Either integrate OpenSpec or add a
  `WORKFLOW-CONTRACT.md` enumerating each workflow's promises; the second run then has a real
  denominator and becomes genuinely comparable.
- **Per-app policy inputs where the fleet default is wrong** — `allowed-promotions` is the
  worked example: the strict ladder is right for a team with closed/open testing tracks and
  impossible for an app with one internal track.
- **Normalise input interpolation.** Route `track`, `android-module` and the
  `*-prebuild-gradle-task` inputs through `env:` as `versionName` already is.
- **Container-prune safety** in `cleanup.yml`: protect semver tags that are in service.
- **Unit-test the version arithmetic** (bats/shellspec) — it is ~15 lines of bash that every
  release in the fleet depends on, and it currently has no test of any kind.
- **App Store screenshots via fastlane `deliver`**, noted in `README.md` as not yet wired.

---

## Method

Reproduce this run exactly as follows; deviations make the next report incomparable.

**Rubric** — four dimensions, 100 points, rounded to the nearest 5:

- **Behaviour (50)** — `50 × (contract clauses honoured ÷ total clauses)`. A clause the code
  implements but contradicts counts **half**, not zero.
- **Correctness (20)** — from 20: **−7** High, **−5** Medium, **−2** Low per active item
  touching the module; **−2** per known gap flagged as a defect. Floor 0.
- **Verification (20)** — adapted for CI, where there are no unit tests to count:
  **20** = a behavioural test runs in CI · **10** = exercised by real consumer runs plus
  actionlint · **5** = actionlint/manual only · **0** = nothing. Stated per module in the
  table.
- **Reachability (10)** — **10** = a consumer repo actually calls it · **5** = callable but
  no consumer exercises it · **0** = nothing surfaces it.

**Rollup** — weighted by `reqs`, never a plain mean:
`overall = Σ(score × reqs) ÷ Σ(reqs)` = **4490 ÷ 61 = 73.6 → 75%**.
Axis rollups: V `1240 ÷ 15 = 82.7 → 85%` · S `2335 ÷ 33 = 70.8 → 70%` ·
F `915 ÷ 13 = 70.4 → 70%`.

**How the rubric's vocabulary was mapped to CI.** This is not an application, so three
substitutions were made, and a future run must repeat them:

1. **Modules are not specs or source packages.** There is no `openspec/`, and the fallback
   (build modules / source dirs) is meaningless for 7 YAML files. The module list is the
   **reusable workflows plus their cross-cutting concerns** — the things a consuming app
   either calls or depends on: `pr-check`, the `release` DAG, version/versionCode derivation,
   Android signing + Play publish, iOS signing via `match`, Play store operations, the secret
   contract, per-app configurability, the `v1` release train, housekeeping. Ten modules for
   nine files is proportionate here *only* because each is independently consumable and
   independently breakable by the fleet.
2. **`reqs` are contract clauses, and Behaviour was judged, not counted.** With no specs,
   each module's `reqs` is the number of distinct promises the repo makes about it in
   `README.md`, `SECRETS.md` or the workflow's own header comment — counted once, listed in
   the module's "what's missing" column where unmet. The honest consequence: these counts are
   defensible but not mechanically reproducible, which is exactly what the *Later* item about
   writing the contract down would fix.
3. **"Tests" and "UI" have CI analogues.** Verification is *how a workflow's behaviour is
   proven* (see the scale above), not a test-file count; Reachability is *whether a real app
   calls it*, standing in for "reachable in the UI". `scripts/spec-evidence.sh` was not used:
   its stack detection finds no source or test roots in a YAML-only repo and would have
   emitted an empty evidence table.

**Weights** — `S = 3`, `F = 3`, `V = 2`. The rubric's example weights enablers at 1; that is
wrong for shared CI, where the enablers (the `v1` gate, the secret contract) are precisely
the blast-radius surface. Documented here so the next run doesn't silently re-weight.

**Evidence base** — direct reading of all 7 workflow YAMLs, `dependabot.yml`, `README.md`
and `SECRETS.md` at `d66a935`; `git ls-files`, `git log`, `git status`, and one read-only
`git ls-remote` to establish that `v1 = 854b961 ≠ HEAD`. Cross-checked against the consuming
repo's callers (`NEPtune-Mobile/.github/workflows/{release,promote,ci}.yml`), which carry
their own annotations about this repo's behaviour — those were used as *reported claims to
verify*, never as evidence in themselves. **No workflow was executed, dispatched or re-run;
no `act`; nothing was fetched; no graph was built.**

**Score history** — `docs/status/scores.csv`, one row per module per run
(`date,module,axis,score,reqs,bugs,gaps`). Created by this run with the 2026-10-22 baseline.
