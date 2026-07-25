# Secret contract

Canonical list of the repository **secret names** the reusable workflows read. Set
these on each consumer app (Settings → Secrets and variables → Actions). All are
optional — a missing secret degrades gracefully (Android dry-run / iOS skipped /
listing or promote fails fast with a clear message). Pass them through with
`secrets: inherit` in the caller.

Store every value with `printf '%s'` (never `echo`, which appends a `\n` that breaks
URL/token secrets).

## Android — `release.yml`, `sync-listing.yml`, `promote.yml`

| Secret | Format | Used by |
|---|---|---|
| `RELEASE_KEYSTORE_B64` | base64 of the `.jks` keystore | release |
| `RELEASE_STORE_PASSWORD` | string | release |
| `RELEASE_KEY_ALIAS` | string | release |
| `RELEASE_KEY_PASSWORD` | string | release |
| `PLAY_SERVICE_ACCOUNT_JSON` | **raw** service-account JSON (not base64) | release, sync-listing, promote |

Missing keystore → Android builds a debug-signed dry-run (no Play upload).

## iOS — `release.yml`

| Secret | Format | Notes |
|---|---|---|
| `APP_STORE_CONNECT_API_KEY_ID` | 10-char id | |
| `APP_STORE_CONNECT_API_KEY_ISSUER_ID` | UUID | note the `KEY_` infix |
| `APP_STORE_CONNECT_API_KEY_P8` | base64 of the `.p8` | consumed as key content |
| `APPLE_TEAM_ID` | 10-char team id | the iOS job is **gated** on this |
| `MATCH_GIT_URL` | git URL of the match certs repo | scheme decides the auth secret ↓ |
| `MATCH_PASSWORD` | match encryption password | |
| `MATCH_GIT_BASIC_AUTHORIZATION` | base64 `user:token` | required for an **`https://`** match repo |
| `MATCH_GIT_SSH_KEY` | SSH private key | required for a **`git@`/`ssh://`** match repo (an ssh-agent is started) |

Missing any core iOS secret → the iOS job is skipped (Android still releases).

## Build-time config (optional) — `release.yml`

| Secret | Format | Purpose |
|---|---|---|
| `EXTRA_GRADLE_PROPERTIES` | multiline `key=value` | appended to `gradle.properties` on both platform jobs before the build (e.g. mTLS `dev.cert.password` / `prod.cert.password`) |

## `GITHUB_TOKEN`

Auto-provided; never set it manually. Callers must grant the permissions each
workflow needs (`contents: write` + `packages: read` for release; `packages: read` +
`pull-requests: read` for pr-check; `actions: write` [+ `packages: write`] for cleanup).

---

Per-app migrations from a bespoke pipeline map that app's old secret names onto the
names above — see each app's `documentation/ci-cd/MOBILE_CI_MIGRATION.md`.
