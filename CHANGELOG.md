# Changelog

## v0.2.0 — 2026-11-16

### Added

- Campaign test emails, lifecycle controls, archives, deletion, running statistics, and analytics; resolves #9. Thanks to @jlxq0 for the API coverage contribution (#8).
- Subscriber activity, subscription and bounce management, CSV/ZIP imports, settings, dashboard, and maintenance tools (#8).
- Paginated mailing-list retrieval and name search, plus campaign target resolution. Thanks to @KVSocial (#10).
- Transactional template subject preservation and overrides. Thanks to @ohm-meter (#11). Subjects are also supported when creating transactional templates.
- Live compatibility tests against Listmonk v6.0.0 and v7.0.0-beta.2, including a local SMTP sink and MCP stdio discovery/calls/resources.
- CI on Python 3.11–3.14, regression tests, strict source type checks, package checks, and contributor/release instructions.

### Fixed

- Startup on fresh installations: import FastMCP from its supported module and bound the MCP SDK to `>=1.30.0,<2`; resolves #12.
- Resources and resource templates are now available on the production server, alongside tools, without copying private registration dictionaries.
- Explicit `--config` files are loaded and missing files produce an error. Failed startup closes its HTTP client.
- Subscriber updates preserve unspecified fields and list memberships, with a full-update fallback for v6. List/campaign updates preserve required fields and campaign sender/content/attachments.
- Scheduling saves the timestamp before changing campaign status.
- Media retrieval handles paginated responses, v7 media tags are exposed, and the unsupported legacy media-title rename reports an explicit error.
- Preview responses support HTML; template-body previews use the upstream form fields.
- Bounce blocklisting uses query IDs. Bulk bounce operations require IDs or explicit `all=true`.
- Analytics supports required date ranges, intervals, and v7 unique counts. Maintenance uses the required cutoff parameter and supported operation types.
- Mutations are never automatically retried after transport failures, preventing accidental duplicate writes/sends. API failures are reported as MCP tool errors; unexpected tracebacks stay in server logs.
- Single-setting updates preserve raw JSON values, including arrays and null. Multipart uploads reuse the authenticated HTTP client.

### Documentation and maintenance

- Migrated documentation from MkDocs to oddship/moat, with search and agent-readable exports. GitHub Pages URL remains unchanged.
- Rewrote README and configuration/compatibility guides, corrected `uv tool install`, updated client setup, and generated a tool/resource reference from registered schemas.
- Updated dependency lockfile, formatter, package metadata, models, local development setup, and tag-driven Trusted Publishing workflow.

## v0.1.0

- Media management, discovery tools, campaign editing, API fixes, and client cleanup.
