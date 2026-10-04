# Bootstrap manifest contract (`manifestVersion` 1)

Public URL: `https://trust.scottstcgbinder.com/manifest.json`

Source file: `dist/manifest.json`

Cloudflare Workers static assets publish `dist/` as the Trust site. The manifest URL has no catalog release id in it. A new catalog release updates this document. It does not change the URL.

This document is discovery metadata. It is not application state, and it is not a feature-flag channel. The complete file is public. It must not contain secrets.

## Versioning

`manifestVersion` versions this JSON contract.

`catalog.schemaVersion` versions the SQLite catalog schema inside a release. Those numbers are independent. A new catalog release can keep `manifestVersion` at 1.

Clients that understand `manifestVersion` 1 must ignore object keys they do not recognize. Optional properties can be added without a version bump.

Bump `manifestVersion` only for an incompatible structural or semantic change. Examples: renaming a required field, changing the meaning of an existing field, or changing a value's type.

`null` is meaningful only where this contract says so. Unknown values are omitted. They are never empty strings.

## Client selection

There is one production catalog release. It is the `catalog` object.

A client selects it when all of the following are true:

1. `manifestVersion` is `1`.
2. `environment` is `production`.
3. `service.status` is absent or `active`. A future `maintenance` or `degraded` value is reserved and is not a catalog download instruction.
4. The client application version is greater than or equal to `catalog.compatibility.minimumApplicationVersion`.
5. `catalog.compatibility.maximumApplicationVersion` is `null`, or the client version is less than or equal to that value.

Compare application versions as `MAJOR.MINOR.PATCH` semantic versions. The current application marketing version is `1.0.0`. `maximumApplicationVersion: null` means there is no upper bound.

`catalog` remains the release a version-1 reader should use. A later manifest may add an optional top-level `catalogReleases` array of the same release objects, each with its own compatibility range, without bumping `manifestVersion`. Readers that do not know that array keep using `catalog`. Readers that do know it select every entry whose range contains the application version. When more than one entry matches, they use the highest `release` identifier.

A changed catalog is a new release id (`r000002`, `r000003`). `r000001` is an immutable namespace.

## Cache

`cache.recommendedCheckIntervalSeconds` is advisory. `86400` means about once per day. `cache.staleIfOffline` means a previously validated copy remains usable when the network is unavailable. Startup must not depend on fetching this file.

The serving policy is separate from that advisory. `dist/_headers` sets:

```text
Cache-Control: public, max-age=0, must-revalidate
```

That matches the Workers static-asset default and keeps this mutable document revalidated on every request. Browsers and the CDN may store it, but they must revalidate with `ETag` / `Last-Modified` before reuse. Do not mark `manifest.json` immutable or give it a long `max-age`. Versioned catalog zip files live on the catalog host and may be cached longer because their URLs do not change.

## Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `manifestVersion` | integer | required | Contract version. `1` for this document. |
| `generatedAt` | string | required | When this manifest file was generated, ISO-8601 UTC. This is not the catalog build time. Example: `2026-10-04T14:30:52Z`. |
| `environment` | string | required | `production` for this endpoint. |
| `application.name` | string | required | Product name. Example: `Scott's TCG Binder`. |
| `application.website` | string | required | Marketing site, HTTPS. Example: `https://www.scottstcgbinder.com`. |
| `links.privacy` | string | required | Privacy policy, HTTPS. Example: `https://trust.scottstcgbinder.com/privacy/`. |
| `links.support` | string | required | Support page, HTTPS. Example: `https://trust.scottstcgbinder.com/support/`. |
| `links.terms` | string | required | Terms page, HTTPS. Example: `https://trust.scottstcgbinder.com/terms/`. |
| `service.status` | string | optional | `active` while the service is available for normal discovery. Unknown statuses must not be treated as permission to download. |
| `catalog.schemaVersion` | integer | required | Catalog SQLite schema version. Current production value is `1`. |
| `catalog.release` | string | required | Immutable release id `r` plus six digits. Example: `r000001`. |
| `catalog.createdAt` | string | required | Catalog build time from release metadata (`builtAt` / `database_metadata.built_at`), ISO-8601 UTC. Example: `2026-10-04T01:20:45.519Z`. |
| `catalog.publishedAt` | string | required | When the zip object was published to the production catalog host, taken from that object's `Last-Modified` time, ISO-8601 UTC. Example: `2026-10-04T14:18:09Z`. |
| `catalog.downloadUrl` | string | required | HTTPS URL of the zip a client downloads. |
| `catalog.releaseUrl` | string | required | HTTPS URL of the immutable release namespace, without a file name. |
| `catalog.sizeBytes` | integer | required in production | Exact byte length of the object at `downloadUrl`. Must be greater than 0. |
| `catalog.sha256` | string | required in production | Lowercase hex SHA-256 of the bytes at `downloadUrl`. This is the zip, not the SQLite file inside it. |
| `catalog.contentType` | string | optional | Media type of the download. Example: `application/zip`. |
| `catalog.compression` | string | optional | Archive format. Example: `zip`. |
| `catalog.compatibility.minimumApplicationVersion` | string | required | Oldest application version that may use this release. Example: `1.0.0`. |
| `catalog.compatibility.maximumApplicationVersion` | string or null | required | Newest application version that may use this release. `null` means no upper bound. |
| `cache.recommendedCheckIntervalSeconds` | integer | optional | Advisory minimum interval between manifest fetches, in seconds. Must be at least `3600` when present. Production value: `86400`. |
| `cache.staleIfOffline` | boolean | optional | When `true`, a validated cached manifest may be used offline. |

Legal and marketing URLs stay on `application` and `links`. They are not properties of a catalog release.

## Provenance for `r000001`

| Value | Source |
| --- | --- |
| `schemaVersion` `1` | Production `manifest.json` in the release namespace, SQLite `database_metadata.catalog_schema_version`, and `schema_migrations` version 1. |
| `createdAt` | `builtAt` in that release manifest and `database_metadata.built_at`. Both are `2026-10-04T01:20:45.519Z`. |
| `publishedAt` | `Last-Modified: Sun, 04 Oct 2026 14:18:09 GMT` on the production zip. |
| `downloadUrl` | `catalog-v1-r000001.zip`, the archive named by the release manifest's `artifact` field and served under the release namespace with `Content-Type: application/zip`. |
| `sizeBytes` / `sha256` | Measured from the production zip. The release `SHA256SUMS` entry for that zip matches. |

## Validation

From the Trust repository root:

```bash
python3 scripts/validate_manifest.py
python3 scripts/validate_manifest.py --verify-artifact
python3 -m unittest tests/test_manifest.py
```

`--verify-artifact` downloads `catalog.downloadUrl` and checks `sizeBytes` and `sha256` against those bytes.

## Deployment

`dist/manifest.json` is the deployment artifact. Publishing the existing Worker (`wrangler.jsonc` assets directory `./dist`) is what makes `https://trust.scottstcgbinder.com/manifest.json` live. This repository has unrelated unpublished `dist/` edits, so a deploy from this working tree would publish those pages as well. Deploy only when that is intended.
