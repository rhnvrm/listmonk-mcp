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
- **70 MCP Tools**: Subscriber, list, campaign, template, media, bounce, import, settings, and maintenance management — full campaign lifecycle (test/send/pause/cancel/delete/archive/analytics), bounce handling, bulk operations, and admin endpoints
- **MCP Resources**: Easy access to subscriber, list, campaign, and template data
- **Async Operations**: Built with modern async/await patterns
- **Type Safety**: Full Pydantic model validation
- **Environment Configuration**: Easy setup with environment variables

## Installation

### Using uvx (Recommended)

Install and run directly from PyPI without managing dependencies:

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

### Development Installation

```bash
git clone https://github.com/rhnvrm/listmonk-mcp.git
cd listmonk-mcp
uv sync --extra dev
```

## Development

### Code Quality Checks

Run the same checks that are executed in the CI/CD pipeline:

```bash
# Install development dependencies
uv sync --extra dev

# Run linting (same as CI)
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check src/ --fix

# Run type checking (same as CI)
uv run mypy src/

# Run all checks together
uv run ruff check src/ && uv run mypy src/
```

### Building and Testing

```bash
# Build the package (same as CI)
uv build

# Test CLI locally (using entry point)
uv run listmonk-mcp --help
uv run listmonk-mcp --version

# Or install locally and test
uv pip install -e .
listmonk-mcp --help
```

### Version Management

To release a new version:

```bash
# 1. Update version in pyproject.toml (e.g., 0.0.1 -> 0.0.2)
# 2. Commit and tag
git add pyproject.toml
git commit -m "chore: bump version to 0.0.2"
git tag v0.0.2
git push origin master
git push origin v0.0.2

# GitHub Actions will automatically:
# - Run linting and type checking
# - Build and publish to PyPI  
# - Create GitHub release with auto-generated notes
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

