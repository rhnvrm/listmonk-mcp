# Listmonk MCP

<img src="docs/_static/logo.png" alt="Listmonk MCP" width="160">

Connect MCP clients to your self-hosted [Listmonk](https://listmonk.app) instance. Manage subscribers and mailing lists, prepare and test campaigns, work with templates and media, and inspect analytics through Listmonk's REST API.

[Documentation](https://rhnvrm.github.io/listmonk-mcp/) · [PyPI](https://pypi.org/project/listmonk-mcp/) · [Changelog](CHANGELOG.md)

## Quick start

Requires Python 3.11+ and a running Listmonk instance. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then add this configuration to an MCP client that supports stdio servers:

```json
{
  "mcpServers": {
    "listmonk": {
      "command": "uvx",
      "args": ["listmonk-mcp@0.2.0"],
      "env": {
        "LISTMONK_MCP_URL": "https://listmonk.example.com",
        "LISTMONK_MCP_USERNAME": "your-api-user",
        "LISTMONK_MCP_PASSWORD": "your-api-token"
      }
    }
  }
}
```

Create an **API user** in Listmonk's user management screen, assign the permissions and lists it needs, and generate an API token. `LISTMONK_MCP_PASSWORD` is that token, not your dashboard password. Requests use `Authorization: token username:api_token`; Listmonk enforces the user's permissions.

For a persistent installation:

```sh
uv tool install listmonk-mcp==0.2.0
listmonk-mcp --help
listmonk-mcp --version
```

Or install with `pip install listmonk-mcp==0.2.0` in a virtual environment. The client starts the MCP process; there is no separate HTTP listener or hosted MCP endpoint.

## What it supports

- **Campaigns:** search/list, create drafts, edit content, preview, send tests to existing subscribers, schedule, send, pause/cancel, archive, delete, and analytics.
- **Subscribers and lists:** paginated list-name search, subscriber updates, subscription management, activity, opt-in emails, blocklisting, and CSV/ZIP imports.
- **Templates and media:** campaign and transactional templates with subject preservation, previews, defaults, uploads, v7 media tags, and deletion.
- **Operations:** bounces, dashboard data, settings, logs, and maintenance.
- **Resources:** browsable `listmonk://` lists, subscribers, campaigns, templates, previews, and media.

Start with “Find the Weekly News mailing list, create a draft campaign, and send a test to my existing subscriber address.” Creating a campaign does not send it; sending is a separate tool. Tools act with the configured API user's permissions, including write and send access when granted. Bulk bounce operations require an explicit `all=true` to target every bounce.

## Compatibility

v0.2.0 targets the Listmonk v7.0.0-beta.2 API and retains the existing v6 workflows. See the [compatibility notes](https://rhnvrm.github.io/listmonk-mcp/compatibility/) for checked behavior and version-specific settings. The MCP Python SDK is bounded to `>=1.30.0,<2`; SDK 2.x removed the FastMCP interface used here.

## Configuration

Environment variables or a local `.env` file configure the server. Use `listmonk-mcp --config /absolute/path/to/listmonk.env` for an explicit file. See [.env.example](.env.example) and the [configuration reference](https://rhnvrm.github.io/listmonk-mcp/configuration/).

## Development

```sh
git clone https://github.com/rhnvrm/listmonk-mcp.git
cd listmonk-mcp
uv sync --frozen --extra dev
make check
uv build
```

`make check` runs linting, formatting checks, strict source type checks, and tests. CI runs Python 3.11–3.14. Tests use HTTP mocks by default; an opt-in integration suite exercises a disposable Listmonk instance, including a real MCP stdio connection. See [CONTRIBUTING.md](CONTRIBUTING.md).

Documentation is built with [oddship/moat](https://github.com/oddship/moat):

```sh
go install github.com/oddship/moat@latest
moat build docs/ _site/
moat serve _site/
```

## License

[MIT](LICENSE). An independent integration, not an official Listmonk project.
