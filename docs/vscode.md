# VS Code

Create `.vscode/mcp.json` in your workspace (or use **MCP: Add Server** for user-level configuration). VS Code uses a top-level `servers` object rather than Claude Desktop's `mcpServers` format.

```json
{
  "inputs": [
    {"type": "promptString", "id": "listmonk-token", "description": "Listmonk API token", "password": true}
  ],
  "servers": {
    "listmonk": {
      "type": "stdio",
      "command": "uvx",
      "args": ["listmonk-mcp@0.2.0"],
      "env": {
        "LISTMONK_MCP_URL": "https://listmonk.example.com",
        "LISTMONK_MCP_USERNAME": "your-api-user",
        "LISTMONK_MCP_PASSWORD": "${input:listmonk-token}"
      }
    }
  }
}
```

Install uv first. Start the server from the configuration editor or the MCP commands in the Command Palette. See [[configuration|configuration]] for required permissions and connection troubleshooting.
