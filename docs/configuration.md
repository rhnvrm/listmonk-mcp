# Configuration

The process reads `LISTMONK_MCP_` environment variables and, by default, a `.env` file in its working directory. Environment variables override values in that file.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LISTMONK_MCP_URL` | Required | Listmonk URL, including any reverse-proxy path prefix |
| `LISTMONK_MCP_USERNAME` | Required | Dedicated API username |
| `LISTMONK_MCP_PASSWORD` | Required | Generated API token |
| `LISTMONK_MCP_TIMEOUT` | `30` | HTTP timeout in seconds |
| `LISTMONK_MCP_MAX_RETRIES` | `3` | Additional GET/HEAD attempts after transport errors |
| `LISTMONK_MCP_LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, or CRITICAL |
| `LISTMONK_MCP_DEBUG` | `false` | Enable debug logs on stderr |

```sh
listmonk-mcp --config /absolute/path/to/listmonk.env
listmonk-mcp --debug
listmonk-mcp --help
listmonk-mcp --version
```

An explicit missing configuration file is an error. `--help` and `--version` work without credentials or a running Listmonk server. Protocol messages use stdout; logs use stderr.

## Permissions and networking

Listmonk checks every API request using `Authorization: token username:api_token`. Give each integration the roles and list access it needs. Sending campaigns, managing settings, querying subscribers with SQL, and maintenance require their corresponding permissions. In v7, targeting existing subscribers with transactional email also requires subscriber read permission.

The Listmonk URL must be reachable from the machine running this MCP process. This server does not provide a remote HTTP endpoint or OAuth login flow.

## Troubleshooting

- Startup import errors on older installations: upgrade to v0.2.0; it uses the correct FastMCP import and excludes incompatible SDK 2.x.
- Authentication errors: verify that you created an API user, supplied its generated token, and granted the required roles/list permissions.
- Connection refused: check the URL and whether Listmonk is running. Inside containers, localhost refers to that container.
- Client cannot find `uvx`: use its absolute executable path in client configuration.
- A write times out: inspect Listmonk before repeating it. Writes are never automatically retried, since the original operation may already have succeeded.
