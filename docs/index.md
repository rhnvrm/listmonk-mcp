# Listmonk MCP

Use your MCP client to manage a self-hosted Listmonk instance through its REST API. The server runs locally over stdio and authenticates as a dedicated Listmonk API user.

## Get started

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.11 or newer.
2. Create a Listmonk API user, assign permissions and permitted lists, and generate an API token.
3. Configure your client using [[claude desktop|Claude Desktop]], [[vscode|VS Code]], [[cline|Cline]], or [[windsurf cursor|Windsurf and Cursor]].

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

The password variable contains the generated API token, not the dashboard password. See [[configuration|configuration]] for timeouts, logging, and explicit environment files.

## A campaign workflow

Ask the client to find a mailing list by name, create a draft, preview its content, and send a test to an existing subscriber. Only call the send/schedule tools when ready to deliver to the campaign audience. Test recipients must exist in Listmonk and be accessible to the API user.

The [[tools|tool reference]] describes available operations. [[compatibility|Compatibility]] covers v7 beta changes; [[docker setup|Docker setup]] provides a disposable local Listmonk installation.
