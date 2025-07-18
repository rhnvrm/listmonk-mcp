# Listmonk MCP Server

An MCP (Model Context Protocol) server implementation for Listmonk, providing programmatic access to newsletter and mailing list management functionality.

<image width=200px src="docs/logo.png" alt="Listmonk MCP Logo">

## Project Status

✅ **Implementation Complete** - The core MCP server is fully implemented and functional.

## Goal

Create an MCP server that enables LLMs and AI assistants to interact with Listmonk instances through the Model Context Protocol. This will allow for:

- Subscriber management (add, remove, update subscribers)
- Mailing list operations (create, manage lists)
- Campaign management (create, send newsletters)
- Analytics and reporting access
- Template and content management

## Architecture

This server will bridge the MCP protocol with Listmonk's REST API, providing a standardized interface for AI models to interact with Listmonk installations.

## Features

- **Complete Listmonk API Coverage**: All major Listmonk operations supported
- **18 MCP Tools**: Comprehensive subscriber, list, campaign, and template management
- **MCP Resources**: Easy access to subscriber, list, campaign, and template data
- **Async Operations**: Built with modern async/await patterns
- **Type Safety**: Full Pydantic model validation
- **Environment Configuration**: Easy setup with environment variables

## Installation

### Using uv (Recommended)

```bash
git clone https://github.com/rhnvrm/listmonk-mcp.git
cd listmonk-mcp
```

### Using pip

```bash
git clone https://github.com/rhnvrm/listmonk-mcp.git
cd listmonk-mcp
pip install -e .
```

## Quick Start

### 1. Set up Listmonk (Local Development)

For testing, you can run a local Listmonk instance using Docker:

```bash
# Option 1: Use the provided compose file
docker compose -f docs/listmonk-docker-compose.yml up -d

# Option 2: Download the latest compose file
curl -LO https://github.com/knadh/listmonk/raw/master/docker-compose.yml
docker compose up -d

# Access Listmonk at http://localhost:9000
# Default credentials: admin / listmonk
```

### 2. Create API User and Token

1. Access the Listmonk admin interface at http://localhost:9000/admin
2. Login with the default credentials: `admin` / `listmonk`
3. Navigate to **Admin → Users** (http://localhost:9000/admin/users)
4. Create a new API user:
   - Click "Add new"
   - Enter a username (e.g., `api-user`)
   - Assign appropriate role/permissions
   - Save the user
5. Generate an API token:
   - Click on the created user
   - Click "Generate API token"
   - Copy the generated token

### 3. Configure Environment Variables

The MCP server requires the following environment variables:

```bash
export LISTMONK_MCP_URL=http://localhost:9000
export LISTMONK_MCP_USERNAME=your-api-username
export LISTMONK_MCP_PASSWORD=your-generated-api-token
```

**Important**: The password field should contain the API token (not the user's login password). The server uses Listmonk's token authentication format: `Authorization: token username:api_token`.

**Troubleshooting Configuration**:
- **Verify variables**: `echo $LISTMONK_MCP_URL` should show your Listmonk URL
- **Test API access**: `curl -H "Authorization: token username:api_token" http://localhost:9000/api/health`
- **Common errors**: "invalid session" or 403 errors indicate incorrect credentials

### 4. Run the MCP Server

```bash
# Using uv (recommended)
uv run python -m listmonk_mcp.server

# Or using the entry point
listmonk-mcp
```

**Common Issues**:
- **Connection refused**: Listmonk server not running or wrong URL
- **Module not found**: Install dependencies with `uv install` or `pip install -e .`

