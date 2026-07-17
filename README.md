# mobile-ci

Shared CI for my Compose Multiplatform apps. Currently one reusable workflow:
**`release.yml`** — a single run that ships **iOS and Android at the same version**.

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

## Triggers

| Trigger | Version | Tag |
|---|---|---|
| Push `v1.4.3` | `1.4.3` both platforms | already exists |
| Dispatch, versionName `1.5.0` | `1.5.0` both | created by CI |
| Dispatch, versionName blank | latest tag + patch | created by CI |

The iOS job is **skipped, not failed,** until the Apple secrets exist — Android still releases.

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `android-module` | `composeApp` | Gradle module that builds the AAB |
| `ios-directory` | `iosApp` | Directory holding the iOS fastlane project |
| `java-version` | `17` | Temurin JDK |
| `ruby-version` | `3.3` | Ruby for fastlane |
| `track` | `internal` | Play track |
| `versionName` | `""` | Explicit version; blank auto-bumps the patch |

## Secrets (all optional; pass via `secrets: inherit`)

**Android** — `RELEASE_KEYSTORE_B64`, `RELEASE_STORE_PASSWORD`, `RELEASE_KEY_ALIAS`,
`RELEASE_KEY_PASSWORD`, `PLAY_SERVICE_ACCOUNT_JSON`.
Missing → Android does a build-only dry-run (debug-signed, not published).

**iOS** — `MATCH_GIT_URL`, `MATCH_PASSWORD`, `MATCH_GIT_BASIC_AUTHORIZATION` (HTTPS match repos),
`APP_STORE_CONNECT_API_KEY_ID`, `APP_STORE_CONNECT_API_KEY_ISSUER_ID`,
`APP_STORE_CONNECT_API_KEY_P8`, `APPLE_TEAM_ID`.
Missing → the iOS job is skipped.

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
