# Listmonk MCP Server

An MCP (Model Context Protocol) server for Listmonk, providing programmatic access to newsletter management through AI assistants and IDEs.

## Features

- Complete Listmonk API integration with async operations
- Subscriber management (CRUD with query/pagination support)
- List management with tags, pagination, and name search
- Campaign creation, management, and sending
- Template management for campaigns and transactional messages
- Transactional email sending with template data
- Type-safe operations with Pydantic models

## Quick Start

1. **Install the server:**
   ```bash
   git clone https://github.com/rhnvrm/listmonk-mcp.git
   cd listmonk-mcp
   ```

2. **Create API credentials in Listmonk:**
   - Go to Listmonk Admin → Users
   - Create a new API user and token

3. **Choose your setup:**
   - [Claude Desktop](./claude-desktop.md) - Claude Desktop app configuration
   - [VS Code](./vscode.md) - VS Code MCP settings  
   - [Cline](./cline.md) - Cline extension configuration
   - [Windsurf & Cursor](./windsurf-cursor.md) - Windsurf and Cursor IDE setup

## Configuration

All setups use the same basic configuration format:

```json
{
  "command": "uv",
  "args": ["run", "python", "-m", "listmonk_mcp.server"],
  "cwd": "/path/to/listmonk-mcp",
  "env": {
    "LISTMONK_MCP_URL": "http://localhost:9000",
    "LISTMONK_MCP_USERNAME": "your-api-username", 
    "LISTMONK_MCP_PASSWORD": "your-api-token"
  }
}
```

## API Coverage

The MCP server exposes 30 tools covering all major Listmonk operations:

- **Subscribers**: Get, create, update, delete with advanced filtering
- **Lists**: Full CRUD operations with tag support, pagination, and name search
- **Campaigns**: Create, manage, and send campaigns
- **Templates**: Access campaign and transactional templates
- **Transactional Messages**: Send individual emails with template data
