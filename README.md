# mobile-ci

Shared CI for my Compose Multiplatform apps. Reusable workflows:
- **`pr-check.yml`** — build gate for every PR/push: detekt, lint, unit +
  screenshot tests, assemble, and a two-tier iOS check.
- **`release.yml`** — a single run that ships **iOS and Android at the same version**.
- **`sync-listing.yml`** — push the **Google Play store listing** (icon, feature
  graphic, screenshots, listing text) on demand, decoupled from releases.
- **`promote.yml`** — promote an Android release up the Play track ladder.
- **`cleanup.yml`** — scheduled repo housekeeping (old runs / container images).

All the secret names these workflows read live in one place: **[`SECRETS.md`](./SECRETS.md)**.

- `version` job resolves/creates the shared `vX.Y.Z` tag (source of truth for both platforms).
- `android` job → Google Play via Gradle Play Publisher, and attaches the AAB to a GitHub Release.
- `ios` job → TestFlight via fastlane (`match → gym → pilot`).

`versionCode` is derived from the version (`major*10000 + minor*100 + patch`, e.g. `1.4.3 → 10403`)
so it's deterministic and monotonic and can never regress below what's live on Play.

## Use it from an app

Add `.github/workflows/release.yml` to the app repo:

```yaml
name: Release

on:
  push:
    tags: [ "v*" ]
  workflow_dispatch:
    inputs:
      track:
        description: Play track
        type: choice
        default: internal
        options: [ internal, alpha, beta, production ]
      versionName:
        description: versionName override (blank = auto-bump the patch)
        type: string
        required: false

jobs:
  release:
    permissions:
      contents: write            # push the tag + create the GitHub Release
    uses: gowthamraj07/mobile-ci/.github/workflows/release.yml@v1
    with:
      track: ${{ inputs.track || 'internal' }}
      versionName: ${{ inputs.versionName }}
    secrets: inherit             # pass the app's release secrets through
```

Pin `@v1` (a tag in this repo) so upstream changes never surprise an app; bump the ref to adopt them.

### How `v1` moves (self-check gate)

`v1` is a moving tag, so a broken workflow would break every consumer at once. To
prevent that, `ci.yml` runs **actionlint** on every PR and every workflow change on
`main`, and **only advances `v1` after lint passes** (the `advance-v1` job) — so `v1`
can never point at an invalid revision. Don't `git tag -f v1` by hand; merge to `main`
and let the gate move it. (Requires the repo's Actions token to have write permission:
Settings → Actions → General → Workflow permissions → *Read and write*.)

## Triggers

| Trigger | Version | Tag |
|---|---|---|
| Push `v1.4.3` | `1.4.3` both platforms | already exists |
| Dispatch, versionName `1.5.0` | `1.5.0` both | created by CI |
| Dispatch, versionName blank | latest tag + patch | created by CI |

The iOS job is **skipped, not failed,** until the Apple secrets exist — Android still releases.

## PR checks (`pr-check.yml`)

Build-verify every PR and every push to the long-lived branches, identically across
apps. Two jobs matter:

- **`build`** (ubuntu) — `detekt` → Android `lintDebug` → `testDebugUnitTest` +
  Roborazzi `verifyRoborazziDebug` → `assembleDebug` → compile the iOS simulator
  target's Kotlin **and its test sources** (klib/metadata). The iOS compile catches
  `iosMain`/`iosTest` breakage without a macOS runner.
- **`ios-check`** (macOS) — the full `xcodebuild` link. macOS minutes bill **10x**, so
  a cheap `changes` job (`dorny/paths-filter`) gates it: on PRs it runs only when an
  iOS-affecting path changed; a push to the default branch or a manual dispatch always
  runs it (the mainline never skips iOS).

Add `.github/workflows/pr-check.yml` to the app repo:

```yaml
name: PR check

on:
  pull_request:
  push:
    branches: [ "main" ]
  workflow_dispatch:

concurrency:
  group: pr-check-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  pr-check:
    permissions:
      contents: read
      packages: read          # resolve the shared version catalog (GitHub Packages)
      pull-requests: read       # dorny/paths-filter reads the PR file list
    uses: gowthamraj07/mobile-ci/.github/workflows/pr-check.yml@v1
    with:
      default-branch: main      # set to `master` if that's your mainline
    secrets: inherit             # passes GITHUB_TOKEN through for catalog auth
```

The `permissions` block is the ceiling for the reusable jobs — omit `packages: read`
and catalog resolution 401s; omit `pull-requests: read` and the path filter can't read
the PR. Keep `concurrency` in the caller so superseded runs cancel per ref.

### Inputs

| Input | Default | Purpose |
|---|---|---|
| `android-module` | `composeApp` | Module that builds/tests the app |
| `ios-directory` | `iosApp` | iOS dir the path filter watches |
| `ios-project` | `iosApp/iosApp.xcodeproj` | `.xcodeproj` the macOS job builds |
| `ios-scheme` | `iosApp` | Xcode scheme |
| `java-version` | `17` | Temurin JDK |
| `xcode-version` | `latest-stable` | Xcode on the macOS runner |
| `default-branch` | `main` | Owns the caches; pushes to it always run iOS |
| `run-detekt` | `true` | Run `./gradlew detekt` |
| `run-android-lint` | `true` | Run `:<module>:lintDebug` |
| `run-screenshot-tests` | `true` | Run Roborazzi `:<module>:verifyRoborazziDebug` |
| `ios-workspace` | `""` | Build this `.xcworkspace` instead of `ios-project` |
| `ios-uses-cocoapods` | `false` | `pod install` in `ios-directory` before the macOS build |
| `ios-prebuild-command` | `""` | Shell command run before the macOS build (e.g. create a gitignored file) |

Defaults target the fleet-standard **direct-framework** iOS integration (no CocoaPods,
builds the `.xcodeproj`). For a CocoaPods or SPM-workspace app, set `ios-workspace`
(and `ios-uses-cocoapods: true` for pods). Apps that lack detekt / Roborazzi / lint can
opt those steps out via the `run-*` flags.

## Sync the Play store listing (`sync-listing.yml`)

Push store *graphics and text* to Google Play, decoupled from binary releases —
run it on demand when the brand assets change. It uploads whatever the app has
committed under Gradle Play Publisher's convention
`<module>/src/main/play/listings/<locale>/…` via the `publishListing` task
(missing files are skipped). Because Play rate-limits listing edits and GPP
re-uploads all graphics each run, this is intentionally separate from `release.yml`.

Add `.github/workflows/sync-store-assets.yml` to the app repo:

```yaml
name: Sync store assets
on:
  workflow_dispatch:
jobs:
  sync:
    uses: gowthamraj07/mobile-ci/.github/workflows/sync-listing.yml@v1
    secrets: inherit             # needs PLAY_SERVICE_ACCOUNT_JSON
```

App layout (generate the images with `mobile-brand-kit`):

```
composeApp/src/main/play/listings/en-US/graphics/
├── icon/icon.png                       # 512×512, 32-bit (alpha OK)
├── feature-graphic/feature-graphic.png # 1024×500, opaque (no alpha)
└── phone-screenshots/1.png 2.png …
```

Inputs: `android-module` (default `composeApp`), `java-version` (default `17`).
Secret: `PLAY_SERVICE_ACCOUNT_JSON` (the same one `release.yml` uses).

> The **App Store** icon isn't uploaded here — it ships inside the iOS binary's
> asset catalog via `release.yml`. App Store *screenshots* would go through
> fastlane `deliver` (not yet wired).

## Promote a Play track (`promote.yml`)

Promote an already-published Android release up the track ladder
(`internal → alpha → beta → production`) via GPP `promoteReleaseArtifact` — no new
binary is built. Only the sanctioned one-step promotions are allowed.

```yaml
on:
  workflow_dispatch:
    inputs:
      from-track: { type: choice, options: [ internal, alpha, beta ] }
      to-track:   { type: choice, options: [ alpha, beta, production ] }
jobs:
  promote:
    uses: gowthamraj07/mobile-ci/.github/workflows/promote.yml@v1
    with:
      from-track: ${{ inputs.from-track }}
      to-track: ${{ inputs.to-track }}
    secrets: inherit   # PLAY_SERVICE_ACCOUNT_JSON
```

## Housekeeping (`cleanup.yml`)

Scheduled prune of old workflow runs (all repos) and, optionally, old GHCR container
image versions (`container-package`, for repos that ship a server image).

```yaml
on:
  schedule: [ { cron: "0 0 * * 0" } ]
  workflow_dispatch:
jobs:
  cleanup:
    permissions:
      actions: write
      packages: write            # only needed with container-package
    uses: gowthamraj07/mobile-ci/.github/workflows/cleanup.yml@v1
    with:
      container-package: my-server   # omit for app-only repos
```

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `android-module` | `composeApp` | Gradle module that builds the AAB |
| `ios-directory` | `iosApp` | Directory holding the iOS fastlane project |
| `java-version` | `17` | Temurin JDK |
| `ruby-version` | `3.3` | Ruby for fastlane |
| `track` | `internal` | Play track |
| `versionName` | `""` | Explicit version; blank auto-bumps the patch |
| `android-prebuild-gradle-task` | `""` | Optional Gradle task run before `bundleRelease`; blank = skipped |
| `ios-prebuild-gradle-task` | `""` | Optional Gradle task run before fastlane (e.g. `:composeApp:updateIosPlist`); blank = skipped |

## Secrets (all optional; pass via `secrets: inherit`)

**Android** — `RELEASE_KEYSTORE_B64`, `RELEASE_STORE_PASSWORD`, `RELEASE_KEY_ALIAS`,
`RELEASE_KEY_PASSWORD`, `PLAY_SERVICE_ACCOUNT_JSON`.
Missing → Android does a build-only dry-run (debug-signed, not published).

**iOS** — `MATCH_GIT_URL`, `MATCH_PASSWORD`, `APP_STORE_CONNECT_API_KEY_ID`,
`APP_STORE_CONNECT_API_KEY_ISSUER_ID`, `APP_STORE_CONNECT_API_KEY_P8`, `APPLE_TEAM_ID`,
plus **match repo auth by URL scheme**: `MATCH_GIT_BASIC_AUTHORIZATION` for an
`https://` certs repo, or `MATCH_GIT_SSH_KEY` (an SSH private key; an ssh-agent is
started for it) for a `git@`/`ssh://` certs repo.
Missing → the iOS job is skipped.

**Build-time config (optional)** — `EXTRA_GRADLE_PROPERTIES`: a multiline `key=value`
block appended to `gradle.properties` on **both** platform jobs before the build, for
apps that feed secrets into Gradle (e.g. mTLS client-cert passwords read via
`project.findProperty(...)` and baked into `BuildConfig` / `Info.plist`). Unset →
nothing is appended, so apps without it are unaffected. Pair it with the
`*-prebuild-gradle-task` inputs when a task must consume those properties (the iOS
plist embed runs before fastlane; the properties are applied first).

## App conventions this workflow assumes

- **Android** `build.gradle.kts` reads `-PappVersionCode` / `-PappVersionName` project
  properties into `versionCode` / `versionName`, and applies Gradle Play Publisher behind
  a `-PenablePlayPublisher` flag (GPP reads `play-service-account.json` at the repo root).
- **iOS** has a fastlane project under `ios-directory` with a `beta` lane that honours the
  `BUILD_NUMBER` and `MARKETING_VERSION` env vars.

## Versioning constraints

`minor < 100` and `patch < 100` (the versionCode encoding). Because the auto-bump path reads
the latest git tag, **keep tags in sync with what's live on the store** — if the store is ahead
of your tags, create the matching tag first (e.g. `git tag v1.4.2 && git push origin v1.4.2`)
or cut the next release with an explicit `versionName`.
