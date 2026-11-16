# Compatibility

## v0.2.0

Requires Python 3.11+. Uses MCP Python SDK `>=1.30.0,<2` and the stdio transport. No migration of the Listmonk database is required by this integration.

The API contracts are checked against **Listmonk v7.0.0-beta.2**. Integration tests also run against **v6.0.0**. The live suite covers list/subscriber/campaign/template operations, scheduling, previews, settings, analytics, imports, bounces, maintenance, and MCP tool/resource discovery. SMTP tests use an isolated local mail sink when configured; no production instance is used.

## v7-specific details

- `app.from_email` is an array. When using `update_setting`, send an array of sender addresses, not a single string. Settings are passed through in the server's native shape; no automatic conversion is applied.
- Campaign analytics requires `from_date` and `to_date`. The tools expose `interval` and v7's `unique` flag.
- Subscriber PATCH sends actual subscriber fields. Omitted memberships are preserved; explicitly passing `lists=[]` removes memberships. On v6, which lacks PATCH, the client fetches the original subscriber before a full PUT.
- Transactional template updates preserve the existing subject. A subject can also be supplied on creation or overridden on update.
- Preview endpoints return HTML. Template-body previews use form-encoded `body` and `template_type`.
- Scheduling first saves `send_at` on the campaign, then changes its status to `scheduled`.
- Garbage collection uses `before_date` and supports the upstream types: subscriber `blocklisted`/`orphan`, analytics `views`/`clicks`/`all`.
- v7 adds permission checks, including subscriber read access for transactional messages. The MCP does not bypass those checks.
- Bounce webhook schema changes are handled by Listmonk; this integration does not register webhook handlers.

## Upgrade notes

Upgrade with `uv tool upgrade listmonk-mcp` or update your client's pinned package to `listmonk-mcp@0.2.0`, then restart the client.

The new analytics and maintenance tools require explicit dates. Bulk bounce deletion/blocklisting requires IDs or an explicit `all=true`; an omitted or empty ID list never silently targets everyone. Existing tool names and `listmonk://` resource URIs are retained. The old `rename_media` tool now reports that Listmonk does not support mutable media titles; use `update_media_tags` for v7 tags.

This project exposes selected operational APIs, not every Listmonk endpoint. Older Listmonk releases may lack some operations. SDK 2.x migration and native HTTP/OAuth support are outside v0.2.0.
