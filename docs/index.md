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

## Installation

### Using uvx (Recommended)

Install and run directly from PyPI:

```bash
# Run directly (installs if needed)
uvx listmonk-mcp --help

# Or install globally
uvx install listmonk-mcp
listmonk-mcp --help
```

### Using pip

```bash
pip install listmonk-mcp
```

## Quick Start

1. **Install the server using uvx:**
   ```bash
   uvx install listmonk-mcp
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
- **Lists**: Full CRUD operations with tag support, pagination (100 by default), and name search
- **Campaigns**: Create, manage, and send campaigns
- **Templates**: Access campaign and transactional templates
- **Transactional Messages**: Send individual emails with template data

### Campaign Targeting

Call `search_mailing_lists` to resolve a list name to an ID before calling
`create_campaign`. The campaign tool verifies each ID before creating the
campaign, and sending remains a separate explicit operation.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely connect to external data sources and tools. This server implements MCP to provide AI assistants with direct access to Listmonk's newsletter management capabilities.

## Requirements

- Python 3.11+
- Running Listmonk instance
- API credentials from Listmonk admin panel

---

📚 **Documentation built with MkDocs Material**
