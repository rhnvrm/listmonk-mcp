"""Listmonk MCP Server using FastMCP framework."""

import logging
from contextlib import asynccontextmanager
from typing import Any

import typer
from mcp.server import FastMCP

from .client import ListmonkAPIError, ListmonkClient, create_client
from .config import Config, load_config, validate_config
from .exceptions import safe_execute_async

# Global state
_client: ListmonkClient | None = None
_config: Config | None = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Any) -> Any:
    """Server lifespan context manager."""
    global _client, _config

    try:
        # Load and validate configuration
        _config = load_config()
        validate_config()

        logger.info(f"Connecting to Listmonk at {_config.url}")

        # Create and connect client
        _client = await create_client(_config)

        logger.info("Listmonk MCP Server started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
    finally:
        # Cleanup
        if _client:
            await _client.close()
            logger.info("Listmonk client disconnected")


# Create a basic MCP server just for decorator registration (no lifespan)
mcp = FastMCP("Listmonk MCP Server")


def create_production_server() -> FastMCP:
    """Create the production MCP server with lifespan management."""
    # Create a new server with the same tools but with lifespan
    production_server = FastMCP("Listmonk MCP Server", lifespan=lifespan)

    # Copy all registered tools from the decorator server to production server
    # Access the tool manager to copy tools properly
    if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools'):
        for tool_name, tool_func in mcp._tool_manager._tools.items():
            production_server._tool_manager._tools[tool_name] = tool_func

    return production_server


def get_client() -> ListmonkClient:
    """Get the global Listmonk client."""
    if _client is None:
        raise RuntimeError("Listmonk client not initialized")
    return _client


def get_config() -> Config:
    """Get the global configuration."""
    if _config is None:
        raise RuntimeError("Configuration not loaded")
    return _config


# Health Check Tool
@mcp.tool()
async def check_listmonk_health() -> str:
    """Check if Listmonk server is healthy and accessible."""
    async def _check_health_logic() -> str:
        client = get_client()
        health_data = await client.health_check()
        config = get_config()

        return f"Listmonk server is healthy at {config.url}. Health data: {health_data}"

    return await safe_execute_async(_check_health_logic)  # type: ignore[no-any-return]


# Subscriber Management Tools
@mcp.tool()
async def add_subscriber(
    email: str,
    name: str,
    lists: list[int],
    status: str = "enabled",
    attributes: dict[str, Any] | None = None,
    preconfirm: bool = False
) -> str:
    """
    Add a new subscriber to Listmonk.

    Args:
        email: Subscriber email address
        name: Subscriber name
        lists: List of mailing list IDs to subscribe to
        status: Subscriber status (enabled, disabled, blocklisted)
        attributes: Custom subscriber attributes
        preconfirm: Whether to preconfirm subscriptions
    """
    async def _add_subscriber_logic() -> str:
        client = get_client()
        result = await client.create_subscriber(
            email=email,
            name=name,
            status=status,
            lists=lists,
            attribs=attributes or {},
            preconfirm_subscriptions=preconfirm
        )

        subscriber_data = result.get("data", {})
        subscriber_id = subscriber_data.get("id", "unknown")
        return f"Successfully added subscriber: {email} (ID: {subscriber_id})"

    return await safe_execute_async(_add_subscriber_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_subscriber(
    subscriber_id: int,
    email: str | None = None,
    name: str | None = None,
    status: str | None = None,
    lists: list[int] | None = None,
    attributes: dict[str, Any] | None = None
) -> str:
    """
    Update an existing subscriber.

    Args:
        subscriber_id: ID of the subscriber to update
        email: New email address
        name: New name
        status: New status (enabled, disabled, blocklisted)
        lists: New list of mailing list IDs
        attributes: New custom attributes
    """
    async def _update_subscriber_logic() -> str:
        client = get_client()
        await client.update_subscriber(
            subscriber_id=subscriber_id,
            email=email,
            name=name,
            status=status,
            lists=lists,
            attribs=attributes
        )

        return f"Successfully updated subscriber {subscriber_id}"

    return await safe_execute_async(_update_subscriber_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def remove_subscriber(subscriber_id: int) -> str:
    """
    Remove a subscriber from Listmonk.

    Args:
        subscriber_id: ID of the subscriber to remove
    """
    async def _remove_subscriber_logic() -> str:
        client = get_client()
        await client.delete_subscriber(subscriber_id)

        return f"Successfully removed subscriber {subscriber_id}"

    return await safe_execute_async(_remove_subscriber_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def change_subscriber_status(subscriber_id: int, status: str) -> str:
    """
    Change subscriber status.

    Args:
        subscriber_id: ID of the subscriber
        status: New status (enabled, disabled, blocklisted)
    """
    async def _change_status_logic() -> str:
        client = get_client()
        await client.set_subscriber_status(subscriber_id, status)

        return f"Successfully changed subscriber {subscriber_id} status to {status}"

    return await safe_execute_async(_change_status_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def patch_subscriber(
    subscriber_id: int,
    action: str,
    target_list_ids: list[int] | None = None,
    status: str | None = None,
) -> str:
    """
    Patch a subscriber's lists or status (more surgical than update_subscriber).

    Args:
        subscriber_id: ID of the subscriber to patch.
        action: One of "add", "remove", "unsubscribe" (lists) or "blocklist" / "enable" (status).
        target_list_ids: List IDs (for list-related actions).
        status: New status (for status-related actions).
    """
    async def _patch_logic() -> str:
        client = get_client()
        await client.patch_subscriber(subscriber_id, action, target_list_ids, status)
        return f"Successfully patched subscriber {subscriber_id} (action={action})"

    return await safe_execute_async(_patch_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def subscriber_send_optin(subscriber_id: int) -> str:
    """
    Send a fresh opt-in confirmation email to a subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    """
    async def _optin_logic() -> str:
        client = get_client()
        await client.subscriber_send_optin(subscriber_id)
        return f"Successfully sent opt-in email to subscriber {subscriber_id}"

    return await safe_execute_async(_optin_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def blocklist_subscriber(subscriber_id: int) -> str:
    """
    Blocklist a single subscriber (cannot be re-subscribed without manual action).

    Args:
        subscriber_id: ID of the subscriber to blocklist.
    """
    async def _blocklist_logic() -> str:
        client = get_client()
        await client.blocklist_subscriber(subscriber_id)
        return f"Successfully blocklisted subscriber {subscriber_id}"

    return await safe_execute_async(_blocklist_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def blocklist_subscribers(subscriber_ids: list[int]) -> str:
    """
    Blocklist multiple subscribers in one call.

    Args:
        subscriber_ids: List of subscriber IDs to blocklist.
    """
    async def _blocklist_many_logic() -> str:
        client = get_client()
        await client.blocklist_subscribers(subscriber_ids)
        return f"Successfully blocklisted {len(subscriber_ids)} subscriber(s)"

    return await safe_execute_async(_blocklist_many_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def manage_subscriber_lists(
    subscriber_ids: list[int],
    target_list_ids: list[int],
    action: str,
    status: str | None = None,
) -> str:
    """
    Bulk add / remove / unsubscribe subscribers from lists.

    Args:
        subscriber_ids: Subscriber IDs to update.
        target_list_ids: Lists to operate on.
        action: One of "add", "remove", "unsubscribe".
        status: Optional subscription status (e.g. "confirmed", "unconfirmed").
    """
    async def _manage_lists_logic() -> str:
        client = get_client()
        await client.manage_subscriber_lists(subscriber_ids, target_list_ids, action, status)
        return (
            f"Successfully {action}ed {len(subscriber_ids)} subscriber(s) "
            f"on {len(target_list_ids)} list(s)"
        )

    return await safe_execute_async(_manage_lists_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_subscriber_activity(subscriber_id: int) -> str:
    """
    Get a subscriber's activity log (opt-ins, bounces, list changes).

    Args:
        subscriber_id: ID of the subscriber.
    """
    async def _activity_logic() -> str:
        client = get_client()
        result = await client.get_subscriber_activity(subscriber_id)
        events = result.get("data", [])
        if not events:
            return f"No activity recorded for subscriber {subscriber_id}"
        rows = [
            f"- {e.get('created_at', '?')} | {e.get('type', '?')} | {e.get('list_name') or e.get('subject') or ''}"
            for e in events
        ]
        return f"Activity for subscriber {subscriber_id} ({len(events)} events):\n" + "\n".join(rows)

    return await safe_execute_async(_activity_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_subscribers_by_query(query: str, list_ids: list[int] | None = None) -> str:
    """
    Delete subscribers matching an advanced SQL query expression.

    Args:
        query: Listmonk-style SQL query, e.g. "subscribers.status='disabled'".
        list_ids: Optional restriction to specific list IDs.
    """
    async def _del_query_logic() -> str:
        client = get_client()
        await client.delete_subscribers_by_query(query, list_ids)
        return f"Successfully ran query-delete (query={query!r})"

    return await safe_execute_async(_del_query_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def blocklist_subscribers_by_query(query: str, list_ids: list[int] | None = None) -> str:
    """
    Blocklist subscribers matching an advanced SQL query expression.

    Args:
        query: Listmonk-style SQL query.
        list_ids: Optional restriction to specific list IDs.
    """
    async def _bl_query_logic() -> str:
        client = get_client()
        await client.blocklist_subscribers_by_query(query, list_ids)
        return f"Successfully ran query-blocklist (query={query!r})"

    return await safe_execute_async(_bl_query_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def manage_subscriber_lists_by_query(
    query: str,
    target_list_ids: list[int],
    action: str,
    list_ids: list[int] | None = None,
    status: str | None = None,
) -> str:
    """
    Bulk add / remove / unsubscribe subscribers matching a query.

    Args:
        query: Listmonk-style SQL query.
        target_list_ids: Lists to operate on.
        action: One of "add", "remove", "unsubscribe".
        list_ids: Optional restriction to specific source list IDs.
        status: Optional subscription status.
    """
    async def _ml_query_logic() -> str:
        client = get_client()
        await client.manage_subscriber_lists_by_query(query, target_list_ids, action, list_ids, status)
        return f"Successfully ran query-{action} on {len(target_list_ids)} list(s)"

    return await safe_execute_async(_ml_query_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_subscriber_bounces(subscriber_id: int) -> str:
    """
    Get bounce records for a single subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    """
    async def _sb_logic() -> str:
        client = get_client()
        result = await client.get_subscriber_bounces(subscriber_id)
        bounces = result.get("data", [])
        if not bounces:
            return f"No bounces recorded for subscriber {subscriber_id}"
        rows = [
            f"- {b.get('created_at')} | {b.get('type')} | campaign {b.get('campaign_id', '-')} | {b.get('source', '?')}"
            for b in bounces
        ]
        return f"Bounces for subscriber {subscriber_id} ({len(bounces)}):\n" + "\n".join(rows)

    return await safe_execute_async(_sb_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_subscriber_bounces(subscriber_id: int) -> str:
    """
    Delete all bounce records for a single subscriber.

    Args:
        subscriber_id: ID of the subscriber.
    """
    async def _dsb_logic() -> str:
        client = get_client()
        await client.delete_subscriber_bounces(subscriber_id)
        return f"Successfully cleared bounce history for subscriber {subscriber_id}"

    return await safe_execute_async(_dsb_logic)  # type: ignore[no-any-return]


# Bounce Management Tools
@mcp.tool()
async def list_bounces(
    page: int = 1,
    per_page: int = 20,
    campaign_id: int | None = None,
    source: str | None = None,
) -> str:
    """
    List bounce records with pagination and filtering.

    Args:
        page: Page number.
        per_page: Page size.
        campaign_id: Optional campaign filter.
        source: Optional source filter (e.g. "smtp", "webhook").
    """
    async def _list_bounces_logic() -> str:
        client = get_client()
        result = await client.get_bounces(page=page, per_page=per_page, campaign_id=campaign_id, source=source)
        data = result.get("data", {})
        bounces = data.get("results", []) if isinstance(data, dict) else data
        total = data.get("total", 0) if isinstance(data, dict) else len(bounces)

        if not bounces:
            return "No bounces found."

        rows = []
        for b in bounces:
            rows.append(
                f"- ID: {b.get('id')} | {b.get('created_at')} | {b.get('type')} | "
                f"sub {b.get('subscriber_id')} | campaign {b.get('campaign_id', '-')} | {b.get('source', '?')}"
            )
        return f"Found {total} bounces (showing {len(bounces)}):\n" + "\n".join(rows)

    return await safe_execute_async(_list_bounces_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_bounce(bounce_id: int) -> str:
    """
    Get a single bounce record by ID.

    Args:
        bounce_id: ID of the bounce record.
    """
    async def _get_bounce_logic() -> str:
        client = get_client()
        result = await client.get_bounce(bounce_id)
        b = result.get("data", {})
        return (
            f"Bounce {b.get('id')}\n"
            f"Subscriber: {b.get('subscriber_id')} ({b.get('email', '?')})\n"
            f"Campaign: {b.get('campaign_id', '-')}\n"
            f"Type: {b.get('type')}\n"
            f"Source: {b.get('source')}\n"
            f"Created: {b.get('created_at')}\n\n"
            f"Meta:\n{b.get('meta', {})}"
        )

    return await safe_execute_async(_get_bounce_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_bounce(bounce_id: int) -> str:
    """
    Delete a single bounce record.

    Args:
        bounce_id: ID of the bounce record.
    """
    async def _del_bounce_logic() -> str:
        client = get_client()
        await client.delete_bounce(bounce_id)
        return f"Successfully deleted bounce {bounce_id}"

    return await safe_execute_async(_del_bounce_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_bounces(bounce_ids: list[int] | None = None) -> str:
    """
    Delete bounce records. Pass an empty/None list to delete ALL bounces.

    Args:
        bounce_ids: Specific IDs to delete, or None/empty to delete all.
    """
    async def _del_bounces_logic() -> str:
        client = get_client()
        await client.delete_bounces(bounce_ids)
        if bounce_ids:
            return f"Successfully deleted {len(bounce_ids)} bounce(s)"
        return "Successfully deleted ALL bounces"

    return await safe_execute_async(_del_bounces_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def blocklist_bounced_subscribers(bounce_ids: list[int] | None = None) -> str:
    """
    Blocklist subscribers who appear in specific bounces (or all bounces if empty).

    Args:
        bounce_ids: Specific bounce IDs, or None/empty to blocklist subscribers from all bounces.
    """
    async def _blbb_logic() -> str:
        client = get_client()
        await client.blocklist_bounced_subscribers(bounce_ids)
        scope = f"{len(bounce_ids)} specified bounces" if bounce_ids else "all bounces"
        return f"Successfully blocklisted subscribers from {scope}"

    return await safe_execute_async(_blbb_logic)  # type: ignore[no-any-return]


# Subscriber Import Tools
@mcp.tool()
async def import_subscribers(
    file_path: str,
    list_ids: list[int],
    mode: str = "subscribe",
    delim: str = ",",
    overwrite: bool = True,
    subscription_status: str = "confirmed",
) -> str:
    """
    Start a subscriber import from a CSV or .zip file.

    Args:
        file_path: Absolute path to a .csv or .zip file.
        list_ids: Lists to subscribe imported users to.
        mode: "subscribe" (default) or "blocklist".
        delim: CSV delimiter (default ",").
        overwrite: Whether to overwrite existing subscribers.
        subscription_status: "confirmed" or "unconfirmed".
    """
    async def _import_logic() -> str:
        client = get_client()
        result = await client.import_subscribers(
            file_path=file_path,
            mode=mode,
            list_ids=list_ids,
            delim=delim,
            overwrite=overwrite,
            subscription_status=subscription_status,
        )
        d = result.get("data", {})
        return f"Import started (status={d.get('status', '?')}, total={d.get('total', '?')})"

    return await safe_execute_async(_import_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_import_status() -> str:
    """Get the status of the current/last subscriber import."""
    async def _status_logic() -> str:
        client = get_client()
        result = await client.get_import_status()
        d = result.get("data", {})
        return (
            f"Status: {d.get('status', 'none')}\n"
            f"Total: {d.get('total', 0)}\n"
            f"Imported: {d.get('imported', 0)}"
        )

    return await safe_execute_async(_status_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_import_logs() -> str:
    """Get logs from the current/last subscriber import."""
    async def _logs_logic() -> str:
        client = get_client()
        result = await client.get_import_logs()
        return f"Import logs:\n{result.get('data', '(no logs)')}"

    return await safe_execute_async(_logs_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def stop_import() -> str:
    """Stop the currently running subscriber import."""
    async def _stop_logic() -> str:
        client = get_client()
        await client.stop_import()
        return "Successfully stopped the running import"

    return await safe_execute_async(_stop_logic)  # type: ignore[no-any-return]


# Subscriber Resources
@mcp.resource("listmonk://subscriber/{subscriber_id}")
async def get_subscriber_by_id(subscriber_id: str) -> str:
    """Get subscriber details by ID."""
    try:
        client = get_client()
        result = await client.get_subscriber(int(subscriber_id))

        subscriber = result.get("data", {})

        lists_items = "\n".join(f"- {lst.get('name')} (ID: {lst.get('id')})" for lst in subscriber.get('lists', []))
        attributes_items = "\n".join(f"- **{k}:** {v}" for k, v in subscriber.get('attribs', {}).items())

        return f"""# Subscriber Details

**ID:** {subscriber.get('id')}
**Email:** {subscriber.get('email')}
**Name:** {subscriber.get('name')}
**Status:** {subscriber.get('status')}
**Created:** {subscriber.get('created_at')}
**Updated:** {subscriber.get('updated_at')}

## Lists
{lists_items}

## Attributes
{attributes_items}
"""

    except ListmonkAPIError as e:
        return f"Error retrieving subscriber {subscriber_id}: {str(e)}"


@mcp.resource("listmonk://subscriber/email/{email}")
async def get_subscriber_by_email(email: str) -> str:
    """Get subscriber details by email address."""
    try:
        client = get_client()
        result = await client.get_subscriber_by_email(email)

        subscriber = result.get("data", {})

        lists_items = "\n".join(f"- {lst.get('name')} (ID: {lst.get('id')})" for lst in subscriber.get('lists', []))
        attributes_items = "\n".join(f"- **{k}:** {v}" for k, v in subscriber.get('attribs', {}).items())

        return f"""# Subscriber Details

**ID:** {subscriber.get('id')}
**Email:** {subscriber.get('email')}
**Name:** {subscriber.get('name')}
**Status:** {subscriber.get('status')}
**Created:** {subscriber.get('created_at')}
**Updated:** {subscriber.get('updated_at')}

## Lists
{lists_items}

## Attributes
{attributes_items}
"""

    except ListmonkAPIError as e:
        return f"Error retrieving subscriber {email}: {str(e)}"


@mcp.resource("listmonk://subscribers")
async def list_subscribers() -> str:
    """List all subscribers with basic information."""
    try:
        client = get_client()
        result = await client.get_subscribers(per_page=50)

        data = result.get("data", {})
        subscribers = data.get("results", [])
        total = data.get("total", 0)

        subscriber_list = []
        for sub in subscribers:
            lists_str = ", ".join(lst.get('name', '') for lst in sub.get('lists', []))
            subscriber_list.append(
                f"- **{sub.get('name')}** ({sub.get('email')}) - Status: {sub.get('status')} - Lists: {lists_str}"
            )

        subscriber_items = "\n".join(subscriber_list)

        return f"""# Subscribers List

**Total Subscribers:** {total}
**Showing:** {len(subscribers)} subscribers

{subscriber_items}

*Use the get_subscriber_by_id or get_subscriber_by_email resources for detailed information.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving subscribers: {str(e)}"


# List Management Tools
@mcp.tool()
async def get_mailing_lists() -> str:
    """
    Get all mailing lists.

    Returns a list of all mailing lists with their IDs, UUIDs, names, subscriber counts, and types.
    """
    async def _get_lists_logic() -> str:
        client = get_client()
        result = await client.get_lists()

        data = result.get("data", {})
        lists = data.get("results", []) if isinstance(data, dict) else data

        if not lists:
            return "No mailing lists found."

        list_items = []
        for lst in lists:
            list_items.append(
                f"- ID: {lst.get('id')} | {lst.get('name')} | "
                f"UUID: {lst.get('uuid')} | "
                f"Subscribers: {lst.get('subscriber_count', 0)} | "
                f"Type: {lst.get('type', 'unknown')}"
            )

        return f"Found {len(lists)} mailing lists:\n" + "\n".join(list_items)

    return await safe_execute_async(_get_lists_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def create_mailing_list(
    name: str,
    type: str = "public",
    optin: str = "single",
    tags: list[str] | None = None,
    description: str | None = None
) -> str:
    """
    Create a new mailing list.

    Args:
        name: List name
        type: List type (public, private)
        optin: Opt-in type (single, double)
        tags: List tags
        description: List description
    """
    async def _create_list_logic() -> str:
        client = get_client()
        result = await client.create_list(
            name=name,
            type=type,
            optin=optin,
            tags=tags or [],
            description=description
        )

        list_data = result.get("data", {})
        list_id = list_data.get("id", "unknown")
        return f"Successfully created mailing list '{name}' (ID: {list_id})"

    return await safe_execute_async(_create_list_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_mailing_list(
    list_id: int,
    name: str | None = None,
    type: str | None = None,
    optin: str | None = None,
    tags: list[str] | None = None,
    description: str | None = None
) -> str:
    """
    Update an existing mailing list.

    Args:
        list_id: ID of the list to update
        name: New list name
        type: New list type (public, private)
        optin: New opt-in type (single, double)
        tags: New list tags
        description: New list description
    """
    async def _update_list_logic() -> str:
        client = get_client()
        await client.update_list(
            list_id=list_id,
            name=name,
            type=type,
            optin=optin,
            tags=tags,
            description=description
        )

        return f"Successfully updated mailing list {list_id}"

    return await safe_execute_async(_update_list_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_mailing_list(list_id: int) -> str:
    """
    Delete a mailing list.

    Args:
        list_id: ID of the list to delete
    """
    async def _delete_list_logic() -> str:
        client = get_client()
        await client.delete_list(list_id)

        return f"Successfully deleted mailing list {list_id}"

    return await safe_execute_async(_delete_list_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_list_subscribers_tool(
    list_id: int,
    page: int = 1,
    per_page: int = 20
) -> str:
    """
    Get subscribers for a specific mailing list.

    Args:
        list_id: ID of the mailing list
        page: Page number for pagination
        per_page: Number of subscribers per page
    """
    async def _get_list_subscribers_logic() -> str:
        client = get_client()
        result = await client.get_list_subscribers(
            list_id=list_id,
            page=page,
            per_page=per_page
        )

        data = result.get("data", {})
        subscribers = data.get("results", []) if isinstance(data, dict) else data
        total = data.get("total", 0) if isinstance(data, dict) else len(subscribers)
        return f"Successfully retrieved {len(subscribers)} subscribers for list {list_id} (Total: {total}, Page: {page})"

    return await safe_execute_async(_get_list_subscribers_logic)  # type: ignore[no-any-return]


# Campaign Management Tools
@mcp.tool()
async def get_campaigns(
    status: str | None = None,
    page: int = 1,
    per_page: int = 20
) -> str:
    """
    Get all campaigns with optional status filter.

    Args:
        status: Filter by status (draft, running, paused, finished, cancelled)
        page: Page number for pagination
        per_page: Number of campaigns per page
    """
    async def _get_campaigns_logic() -> str:
        client = get_client()
        result = await client.get_campaigns(page=page, per_page=per_page, status=status)

        data = result.get("data", {})
        campaigns = data.get("results", []) if isinstance(data, dict) else data
        total = data.get("total", 0) if isinstance(data, dict) else len(campaigns)

        if not campaigns:
            return "No campaigns found."

        campaign_items = []
        for c in campaigns:
            lists_str = ", ".join(str(lst.get("id")) for lst in c.get("lists", []))
            campaign_items.append(
                f"- ID: {c.get('id')} | {c.get('name')} | "
                f"Status: {c.get('status', 'unknown')} | "
                f"Lists: [{lists_str}]"
            )

        return f"Found {total} campaigns (showing {len(campaigns)}):\n" + "\n".join(campaign_items)

    return await safe_execute_async(_get_campaigns_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_campaign(campaign_id: int) -> str:
    """
    Get a specific campaign by ID including its full body content.

    Args:
        campaign_id: ID of the campaign to retrieve
    """
    async def _get_campaign_logic() -> str:
        client = get_client()
        result = await client.get_campaign(campaign_id)

        campaign = result.get("data", {})
        body = campaign.get('body', 'No content')
        lists_str = ", ".join(str(lst.get("id")) for lst in campaign.get("lists", []))

        return f"""Campaign ID: {campaign.get('id')}
Name: {campaign.get('name')}
Subject: {campaign.get('subject')}
Status: {campaign.get('status')}
Template ID: {campaign.get('template_id')}
Lists: [{lists_str}]
Content Type: {campaign.get('content_type', 'richtext')}

Body:
{body}"""

    return await safe_execute_async(_get_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def create_campaign(
    name: str,
    subject: str,
    lists: list[int],
    type: str = "regular",
    content_type: str = "richtext",
    body: str | None = None,
    template_id: int | None = None,
    tags: list[str] | None = None
) -> str:
    """
    Create a new email campaign.

    Args:
        name: Campaign name
        subject: Email subject line
        lists: List of mailing list IDs to send to
        type: Campaign type (regular, optin)
        content_type: Content type (richtext, html, markdown, plain)
        body: Campaign content body
        template_id: Template ID to use (optional)
        tags: Campaign tags
    """
    async def _create_campaign_logic() -> str:
        client = get_client()
        result = await client.create_campaign(
            name=name,
            subject=subject,
            lists=lists,
            type=type,
            content_type=content_type,
            body=body,
            template_id=template_id,
            tags=tags or []
        )

        campaign_data = result.get("data", {})
        campaign_id = campaign_data.get("id", "unknown")
        return f"Successfully created campaign '{name}' (ID: {campaign_id})"

    return await safe_execute_async(_create_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_campaign(
    campaign_id: int,
    name: str | None = None,
    subject: str | None = None,
    lists: list[int] | None = None,
    body: str | None = None,
    tags: list[str] | None = None
) -> str:
    """
    Update an existing campaign.

    Args:
        campaign_id: ID of the campaign to update
        name: New campaign name
        subject: New email subject
        lists: New list of mailing list IDs
        body: New campaign content
        tags: New campaign tags
    """
    async def _update_campaign_logic() -> str:
        client = get_client()
        await client.update_campaign(
            campaign_id=campaign_id,
            name=name,
            subject=subject,
            lists=lists,
            body=body,
            tags=tags
        )

        return f"Successfully updated campaign {campaign_id}"

    return await safe_execute_async(_update_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def send_campaign(campaign_id: int) -> str:
    """
    Send a campaign immediately.

    Args:
        campaign_id: ID of the campaign to send
    """
    async def _send_campaign_logic() -> str:
        client = get_client()
        await client.send_campaign(campaign_id)

        return f"Successfully sent campaign {campaign_id}"

    return await safe_execute_async(_send_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def schedule_campaign(campaign_id: int, send_at: str) -> str:
    """
    Schedule a campaign for future delivery.

    Args:
        campaign_id: ID of the campaign to schedule
        send_at: ISO datetime string for when to send (e.g., '2024-12-25T10:00:00Z')
    """
    async def _schedule_campaign_logic() -> str:
        client = get_client()
        await client.schedule_campaign(campaign_id, send_at)

        return f"Successfully scheduled campaign {campaign_id} for {send_at}"

    return await safe_execute_async(_schedule_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def test_campaign(campaign_id: int, subscribers: list[str]) -> str:
    """
    Send a test of a campaign to specific email addresses without affecting list members.

    Args:
        campaign_id: ID of the campaign to test.
        subscribers: Recipient emails. IMPORTANT: each must already exist as a
            subscriber on this listmonk instance (the test handler looks them
            up by email and skips unknown addresses). Add them via
            add_subscriber first if needed.
    """
    async def _test_campaign_logic() -> str:
        client = get_client()
        await client.test_campaign(campaign_id, subscribers)
        recipients = ", ".join(subscribers)
        return f"Successfully queued test send of campaign {campaign_id} to: {recipients}"

    return await safe_execute_async(_test_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def change_campaign_status(campaign_id: int, status: str) -> str:
    """
    Change a campaign's status.

    Args:
        campaign_id: ID of the campaign.
        status: One of "draft", "scheduled", "running", "paused", "cancelled".
    """
    async def _change_status_logic() -> str:
        client = get_client()
        await client.change_campaign_status(campaign_id, status)
        return f"Successfully changed campaign {campaign_id} status to '{status}'"

    return await safe_execute_async(_change_status_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def archive_campaign(
    campaign_id: int,
    archive: bool = True,
    archive_template_id: int | None = None,
    archive_meta: dict[str, Any] | None = None,
    archive_slug: str | None = None,
) -> str:
    """
    Toggle whether a campaign appears on the public archive page.

    Args:
        campaign_id: ID of the campaign.
        archive: True to publish to archive, False to remove.
        archive_template_id: Template to use for the archive page (optional).
        archive_meta: Extra metadata for the archive entry (optional).
        archive_slug: URL slug for the archive page (optional).
    """
    async def _archive_logic() -> str:
        client = get_client()
        await client.archive_campaign(
            campaign_id,
            archive=archive,
            archive_template_id=archive_template_id,
            archive_meta=archive_meta,
            archive_slug=archive_slug,
        )
        verb = "archived" if archive else "unarchived"
        return f"Successfully {verb} campaign {campaign_id}"

    return await safe_execute_async(_archive_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_campaign(campaign_id: int) -> str:
    """
    Delete a campaign permanently.

    Args:
        campaign_id: ID of the campaign to delete.
    """
    async def _delete_campaign_logic() -> str:
        client = get_client()
        await client.delete_campaign(campaign_id)
        return f"Successfully deleted campaign {campaign_id}"

    return await safe_execute_async(_delete_campaign_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_campaigns(campaign_ids: list[int]) -> str:
    """
    Delete multiple campaigns in one call.

    Args:
        campaign_ids: List of campaign IDs to delete.
    """
    async def _delete_campaigns_logic() -> str:
        client = get_client()
        await client.delete_campaigns(campaign_ids)
        return f"Successfully deleted {len(campaign_ids)} campaign(s): {campaign_ids}"

    return await safe_execute_async(_delete_campaigns_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_running_campaign_stats() -> str:
    """Get live stats for currently running campaigns (sent, to_send, rate, ETA)."""
    async def _stats_logic() -> str:
        client = get_client()
        result = await client.get_running_campaign_stats()
        data = result.get("data", [])
        if not data:
            return "No campaigns are currently running."

        rows = []
        for s in data:
            rows.append(
                f"- Campaign {s.get('id')} ({s.get('name', 'unknown')}) — "
                f"sent: {s.get('sent', 0)}/{s.get('to_send', 0)} | "
                f"rate: {s.get('rate', 0)}/min | "
                f"net rate: {s.get('net_rate', 0)}/min | "
                f"started: {s.get('started_at', 'unknown')}"
            )
        return f"Running campaigns ({len(data)}):\n" + "\n".join(rows)

    return await safe_execute_async(_stats_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_campaign_analytics(
    analytics_type: str,
    campaign_ids: list[int],
    from_date: str | None = None,
    to_date: str | None = None,
) -> str:
    """
    Get campaign analytics (views, clicks, links, or bounces).

    Args:
        analytics_type: One of "views", "clicks", "links", "bounces".
        campaign_ids: Campaigns to fetch analytics for.
        from_date: Optional ISO date lower bound (e.g. "2026-01-01").
        to_date: Optional ISO date upper bound.
    """
    async def _analytics_logic() -> str:
        client = get_client()
        result = await client.get_campaign_analytics(
            analytics_type, campaign_ids, from_date=from_date, to_date=to_date
        )
        return f"Analytics ({analytics_type}) for campaigns {campaign_ids}: {result.get('data', [])}"

    return await safe_execute_async(_analytics_logic)  # type: ignore[no-any-return]


# Campaign Resources
@mcp.resource("listmonk://campaigns")
async def list_campaigns() -> str:
    """List all campaigns with basic information."""
    try:
        client = get_client()
        result = await client.get_campaigns(per_page=50)

        data = result.get("data", {})
        campaigns = data.get("results", [])
        total = data.get("total", 0)

        campaign_list = []
        for camp in campaigns:
            lists_str = ", ".join(lst.get('name', '') for lst in camp.get('lists', []))
            status = camp.get('status', 'unknown')
            sent = camp.get('sent', 0)
            to_send = camp.get('to_send', 0)

            campaign_list.append(
                f"- **{camp.get('name')}** - Status: {status} - Sent: {sent}/{to_send} - Lists: {lists_str}"
            )

        campaign_items = "\n".join(campaign_list)

        return f"""# Campaigns List

**Total Campaigns:** {total}
**Showing:** {len(campaigns)} campaigns

{campaign_items}

*Use the get_campaign_by_id resource for detailed information.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving campaigns: {str(e)}"


@mcp.resource("listmonk://campaign/{campaign_id}")
async def get_campaign_by_id(campaign_id: str) -> str:
    """Get campaign details by ID."""
    try:
        client = get_client()
        result = await client.get_campaign(int(campaign_id))

        campaign = result.get("data", {})

        # Format lists
        lists_info = []
        for lst in campaign.get('lists', []):
            lists_info.append(f"- {lst.get('name')} (ID: {lst.get('id')})")

        # Format tags
        tags = campaign.get('tags', [])
        tags_str = ", ".join(tags) if tags else "None"

        lists_items = "\n".join(lists_info) if lists_info else "No lists assigned"

        return f"""# Campaign Details

**ID:** {campaign.get('id')}
**Name:** {campaign.get('name')}
**Subject:** {campaign.get('subject')}
**Status:** {campaign.get('status')}
**Type:** {campaign.get('type', 'regular')}
**Content Type:** {campaign.get('content_type', 'richtext')}

## Statistics
**To Send:** {campaign.get('to_send', 0)}
**Sent:** {campaign.get('sent', 0)}
**Views:** {campaign.get('views', 0)}
**Clicks:** {campaign.get('clicks', 0)}

## Timing
**Created:** {campaign.get('created_at')}
**Updated:** {campaign.get('updated_at')}
**Started:** {campaign.get('started_at', 'Not started')}

## Lists
{lists_items}

## Tags
{tags_str}

## Template
**Template ID:** {campaign.get('template_id', 'None')}
"""

    except ListmonkAPIError as e:
        return f"Error retrieving campaign {campaign_id}: {str(e)}"


@mcp.resource("listmonk://campaign/{campaign_id}/preview")
async def get_campaign_preview(campaign_id: str) -> str:
    """Get campaign HTML preview."""
    try:
        client = get_client()
        result = await client.get_campaign_preview(int(campaign_id))

        preview_data = result.get("data", {})
        preview_html = preview_data.get("preview", "No preview available")

        return f"""# Campaign Preview

**Campaign ID:** {campaign_id}

## HTML Preview
```html
{preview_html}
```

*This is the rendered HTML content that will be sent to subscribers.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving campaign preview {campaign_id}: {str(e)}"


# List Resources
@mcp.resource("listmonk://lists")
async def list_mailing_lists() -> str:
    """List all mailing lists with basic information."""
    try:
        client = get_client()
        result = await client.get_lists()

        data = result.get("data", {})
        lists = data.get("results", []) if isinstance(data, dict) else data

        list_items = []
        for lst in lists:
            subscriber_count = lst.get('subscriber_count', 0)
            # status = lst.get('status', 'active')  # unused
            tags = lst.get('tags', [])
            tags_str = ", ".join(tags) if tags else "None"

            list_items.append(
                f"- **{lst.get('name')}** (ID: {lst.get('id')}) - Type: {lst.get('type')} - Subscribers: {subscriber_count} - Tags: {tags_str}"
            )

        list_items_text = "\n".join(list_items)

        return f"""# Mailing Lists

**Total Lists:** {len(lists)}

{list_items_text}

*Use the get_list_by_id resource for detailed information.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving mailing lists: {str(e)}"


@mcp.resource("listmonk://list/{list_id}")
async def get_list_by_id(list_id: str) -> str:
    """Get mailing list details by ID."""
    try:
        client = get_client()
        result = await client.get_list(int(list_id))

        list_data = result.get("data", {})

        # Format tags
        tags = list_data.get('tags', [])
        tags_str = ", ".join(tags) if tags else "None"

        return f"""# Mailing List Details

**ID:** {list_data.get('id')}
**Name:** {list_data.get('name')}
**Type:** {list_data.get('type', 'public')}
**Opt-in:** {list_data.get('optin', 'single')}
**Status:** {list_data.get('status', 'active')}

## Statistics
**Subscriber Count:** {list_data.get('subscriber_count', 0)}

## Details
**Created:** {list_data.get('created_at')}
**Updated:** {list_data.get('updated_at')}

## Tags
{tags_str}

## Description
{list_data.get('description', 'No description provided')}

*Use get_list_subscribers_tool to see subscribers for this list.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving list {list_id}: {str(e)}"


@mcp.resource("listmonk://list/{list_id}/subscribers")
async def get_list_subscribers_resource(list_id: str) -> str:
    """Get subscribers for a specific mailing list."""
    try:
        client = get_client()
        result = await client.get_list_subscribers(int(list_id), per_page=50)

        data = result.get("data", {})
        subscribers = data.get("results", [])
        total = data.get("total", 0)

        subscriber_list = []
        for sub in subscribers:
            status = sub.get('status', 'unknown')
            created = sub.get('created_at', 'Unknown')

            subscriber_list.append(
                f"- **{sub.get('name')}** ({sub.get('email')}) - Status: {status} - Joined: {created}"
            )

        subscriber_items = "\n".join(subscriber_list) if subscriber_list else "No subscribers in this list"

        return f"""# List Subscribers

**List ID:** {list_id}
**Total Subscribers:** {total}
**Showing:** {len(subscribers)} subscribers

{subscriber_items}

*Use the get_subscriber_by_id or get_subscriber_by_email resources for detailed subscriber information.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving subscribers for list {list_id}: {str(e)}"


# Template Management Tools
@mcp.tool()
async def get_templates() -> str:
    """
    Get all email templates.

    Returns a list of all templates with their IDs, names, types, and default status.
    """
    async def _get_templates_logic() -> str:
        client = get_client()
        result = await client.get_templates()

        data = result.get("data", {})
        templates = data.get("results", []) if isinstance(data, dict) else data

        if not templates:
            return "No templates found."

        template_items = []
        for t in templates:
            default_marker = " (DEFAULT)" if t.get('is_default', False) else ""
            template_items.append(
                f"- ID: {t.get('id')} | {t.get('name')} | "
                f"Type: {t.get('type', 'campaign')}{default_marker}"
            )

        return f"Found {len(templates)} templates:\n" + "\n".join(template_items)

    return await safe_execute_async(_get_templates_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_template(template_id: int) -> str:
    """
    Get a specific template by ID including its full body content.

    Args:
        template_id: ID of the template to retrieve
    """
    async def _get_template_logic() -> str:
        client = get_client()
        result = await client.get_template(template_id)

        template = result.get("data", {})
        body = template.get('body', 'No content')

        return f"""Template ID: {template.get('id')}
Name: {template.get('name')}
Type: {template.get('type', 'campaign')}
Default: {template.get('is_default', False)}

Body:
{body}"""

    return await safe_execute_async(_get_template_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def create_template(
    name: str,
    body: str,
    type: str = "campaign",
    is_default: bool = False
) -> str:
    """
    Create a new email template.

    Args:
        name: Template name
        body: Template HTML body content
        type: Template type (campaign, tx)
        is_default: Whether this is the default template
    """
    async def _create_template_logic() -> str:
        client = get_client()
        result = await client.create_template(
            name=name,
            body=body,
            type=type,
            is_default=is_default
        )

        template_data = result.get("data", {})
        template_id = template_data.get("id", "unknown")
        return f"Successfully created template '{name}' (ID: {template_id})"

    return await safe_execute_async(_create_template_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_template(
    template_id: int,
    name: str | None = None,
    body: str | None = None,
    is_default: bool | None = None
) -> str:
    """
    Update an existing email template.

    Args:
        template_id: ID of the template to update
        name: New template name
        body: New template HTML body content
        is_default: Whether this is the default template
    """
    async def _update_template_logic() -> str:
        client = get_client()
        await client.update_template(
            template_id=template_id,
            name=name,
            body=body,
            is_default=is_default
        )

        return f"Successfully updated template {template_id}"

    return await safe_execute_async(_update_template_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_template(template_id: int) -> str:
    """
    Delete an email template.

    Args:
        template_id: ID of the template to delete
    """
    async def _delete_template_logic() -> str:
        client = get_client()
        await client.delete_template(template_id)

        return f"Successfully deleted template {template_id}"

    return await safe_execute_async(_delete_template_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def set_default_template(template_id: int) -> str:
    """
    Mark a template as the default for its type.

    Args:
        template_id: ID of the template to set as default.
    """
    async def _set_default_logic() -> str:
        client = get_client()
        await client.set_default_template(template_id)
        return f"Successfully set template {template_id} as default"

    return await safe_execute_async(_set_default_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def preview_template_body(body: str, template_type: str = "campaign") -> str:
    """
    Render a preview of an unsaved template body.

    Args:
        body: Template HTML body.
        template_type: One of "campaign" (default), "campaign_visual", "tx".
    """
    async def _preview_body_logic() -> str:
        client = get_client()
        result = await client.preview_template_body(body, template_type)
        d = result.get("data", {})
        rendered = d.get("preview") if isinstance(d, dict) else d
        return f"# Template Preview\n\n{rendered}"

    return await safe_execute_async(_preview_body_logic)  # type: ignore[no-any-return]


# Settings & System Tools
@mcp.tool()
async def get_settings() -> str:
    """
    Get the full server settings document.

    Note: secret fields (passwords, tokens) are masked as bullets in the response.
    Do not PUT this back via update_settings — use update_setting for individual keys
    or scrub secret-looking keys first.
    """
    async def _get_settings_logic() -> str:
        client = get_client()
        result = await client.get_settings()
        return f"Settings:\n{result.get('data', {})}"

    return await safe_execute_async(_get_settings_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_settings(settings: dict[str, Any]) -> str:
    """
    Replace the full server settings document.

    WARNING: GET /api/settings masks secrets as bullets. PUTting that body back
    overwrites real values with literal bullets. Strip any password/token/secret
    keys from `settings` before calling this — or prefer `update_setting` for
    a single key.
    """
    async def _update_settings_logic() -> str:
        client = get_client()
        await client.update_settings(settings)
        return "Successfully updated settings"

    return await safe_execute_async(_update_settings_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def update_setting(key: str, value: Any) -> str:
    """
    Update a single settings key (avoids the password-masking footgun).

    Args:
        key: Dotted setting key (e.g. "appearance.public.custom_css").
        value: New value.
    """
    async def _update_one_logic() -> str:
        client = get_client()
        await client.update_setting(key, value)
        return f"Successfully updated setting '{key}'"

    return await safe_execute_async(_update_one_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def test_smtp_settings(settings: dict[str, Any]) -> str:
    """
    Send a test email through provided SMTP settings without persisting them.

    Args:
        settings: SMTP config with host/port/username/password/etc.
    """
    async def _test_smtp_logic() -> str:
        client = get_client()
        await client.test_smtp_settings(settings)
        return "SMTP test send dispatched successfully"

    return await safe_execute_async(_test_smtp_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def reload_app() -> str:
    """Trigger a hot-reload of the Listmonk app (re-reads settings)."""
    async def _reload_logic() -> str:
        client = get_client()
        await client.reload_app()
        return "Successfully triggered app reload"

    return await safe_execute_async(_reload_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_logs() -> str:
    """Get recent server logs."""
    async def _logs_logic() -> str:
        client = get_client()
        result = await client.get_logs()
        return f"Logs:\n{result.get('data', '')}"

    return await safe_execute_async(_logs_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_about_info() -> str:
    """Get version / build / runtime info about this Listmonk instance."""
    async def _about_logic() -> str:
        client = get_client()
        result = await client.get_about_info()
        return f"About:\n{result.get('data', {})}"

    return await safe_execute_async(_about_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_dashboard_counts() -> str:
    """Get dashboard counts (subscribers, lists, campaigns, etc)."""
    async def _counts_logic() -> str:
        client = get_client()
        result = await client.get_dashboard_counts()
        d = result.get("data", {})
        return f"Dashboard counts:\n{d}"

    return await safe_execute_async(_counts_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def get_dashboard_charts() -> str:
    """Get dashboard chart data (campaign views, link clicks over time)."""
    async def _charts_logic() -> str:
        client = get_client()
        result = await client.get_dashboard_charts()
        return f"Dashboard charts:\n{result.get('data', {})}"

    return await safe_execute_async(_charts_logic)  # type: ignore[no-any-return]


# Maintenance Tools
@mcp.tool()
async def gc_subscribers(gc_type: str) -> str:
    """
    Garbage collect subscribers.

    Args:
        gc_type: One of "blocklisted", "orphan", "unconfirmed".
    """
    async def _gc_subs_logic() -> str:
        client = get_client()
        await client.gc_subscribers(gc_type)
        return f"Successfully ran subscriber GC ({gc_type})"

    return await safe_execute_async(_gc_subs_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def gc_campaign_analytics(analytics_type: str) -> str:
    """
    Garbage collect campaign analytics.

    Args:
        analytics_type: One of "views", "clicks", "links", "bounces", "all".
    """
    async def _gc_analytics_logic() -> str:
        client = get_client()
        await client.gc_campaign_analytics(analytics_type)
        return f"Successfully ran analytics GC ({analytics_type})"

    return await safe_execute_async(_gc_analytics_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def gc_unconfirmed_subscriptions(before: str) -> str:
    """
    Delete unconfirmed double-opt-in subscriptions older than the given timestamp.

    Args:
        before: ISO timestamp; subscriptions created before this are removed.
    """
    async def _gc_unconfirmed_logic() -> str:
        client = get_client()
        await client.gc_unconfirmed_subscriptions(before)
        return f"Successfully GC'd unconfirmed subscriptions before {before}"

    return await safe_execute_async(_gc_unconfirmed_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def send_transactional_email(
    template_id: int,
    subscriber_email: str,
    data: dict[str, Any] | None = None,
    content_type: str = "html"
) -> str:
    """
    Send a transactional email using a template.

    Args:
        template_id: ID of the template to use
        subscriber_email: Recipient email address
        data: Template variables/data
        content_type: Content type (html, plain)
    """
    async def _send_transactional_logic() -> str:
        client = get_client()
        await client.send_transactional_email(
            template_id=template_id,
            subscriber_email=subscriber_email,
            data=data or {},
            content_type=content_type
        )

        return f"Successfully sent transactional email to {subscriber_email}"

    return await safe_execute_async(_send_transactional_logic)  # type: ignore[no-any-return]


# Template Resources
@mcp.resource("listmonk://templates")
async def list_templates() -> str:
    """List all email templates."""
    try:
        client = get_client()
        result = await client.get_templates()

        data = result.get("data", {})
        templates = data.get("results", []) if isinstance(data, dict) else data

        template_list = []
        for template in templates:
            template_type = template.get('type', 'campaign')
            is_default = template.get('is_default', False)
            default_marker = " (DEFAULT)" if is_default else ""

            template_list.append(
                f"- **{template.get('name')}** (ID: {template.get('id')}) - Type: {template_type}{default_marker}"
            )

        template_items = "\n".join(template_list)

        return f"""# Email Templates

**Total Templates:** {len(templates)}

{template_items}

*Use the get_template_by_id resource for detailed template information.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving templates: {str(e)}"


@mcp.resource("listmonk://template/{template_id}")
async def get_template_by_id(template_id: str) -> str:
    """Get template details by ID."""
    try:
        client = get_client()
        result = await client.get_template(int(template_id))

        template = result.get("data", {})

        # Format the body content preview (truncate if too long)
        body = template.get('body', '')
        body_preview = body[:500] + "..." if len(body) > 500 else body

        return f"""# Template Details

**ID:** {template.get('id')}
**Name:** {template.get('name')}
**Type:** {template.get('type', 'campaign')}
**Default:** {"Yes" if template.get('is_default') else "No"}

## Timing
**Created:** {template.get('created_at')}
**Updated:** {template.get('updated_at')}

## Template Body Preview
```html
{body_preview}
```

*Note: Body content may be truncated for display. Use the template in campaigns or transactional emails to see full content.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving template {template_id}: {str(e)}"


@mcp.resource("listmonk://template/{template_id}/preview")
async def get_template_preview(template_id: str) -> str:
    """Get full template body content."""
    try:
        client = get_client()
        result = await client.get_template(int(template_id))

        template = result.get("data", {})
        body = template.get('body', 'No content available')

        return f"""# Template Full Content

**Template ID:** {template_id}
**Template Name:** {template.get('name')}

## Full HTML Body
```html
{body}
```

*This is the complete template HTML that can be used for campaigns and transactional emails.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving template content {template_id}: {str(e)}"


# Media Management Tools
@mcp.tool()
async def get_media_list() -> str:
    """
    Get all media files from Listmonk.

    Returns a list of all uploaded media with their IDs, filenames, URLs, and metadata.
    """
    async def _get_media_logic() -> str:
        client = get_client()
        result = await client.get_media()

        # Debug: Check what we actually got
        if not isinstance(result, dict):
            return f"Error: Unexpected response type: {type(result)}. Response: {result}"

        data = result.get("data", [])

        # Handle both list and dict formats (Listmonk can return either)
        if isinstance(data, dict):
            # If it's a dict, it might be empty or have numbered keys
            if not data:
                return "No media files found."
            # Convert dict values to list
            media_list = list(data.values()) if data else []
        else:
            # It's already a list
            media_list = data

        # Flatten if the first element is itself a list (nested structure)
        if media_list and isinstance(media_list[0], list):
            media_list = media_list[0]

        if not media_list:
            return "No media files found."

        media_items = []
        for media in media_list:
            created = media.get('created_at', 'Unknown')[:10]  # Just the date part
            size_bytes = media.get('meta', {}).get('size', 0) if isinstance(media.get('meta'), dict) else 0
            size_kb = size_bytes / 1024 if size_bytes > 0 else 0
            media_items.append(
                f"- ID: {media.get('id')} | {media.get('filename')} | "
                f"Title: {media.get('title', media.get('filename', 'No title'))} | "
                f"Size: {size_kb:.1f} KB | "
                f"Created: {created}\n"
                f"  URL: {media.get('url', 'No URL')}"
            )

        return f"Found {len(media_list)} media files:\n" + "\n".join(media_items)

    return await safe_execute_async(_get_media_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def upload_media_file(
    file_path: str,
    title: str | None = None
) -> str:
    """
    Upload a media file to Listmonk.

    Args:
        file_path: Absolute path to the image file to upload
        title: Optional title/description for the media (defaults to filename)

    Returns:
        Success message with the uploaded file's URL
    """
    async def _upload_media_logic() -> str:
        client = get_client()
        result = await client.upload_media(file_path, title)

        media_data = result.get("data", {})
        media_id = media_data.get("id", "unknown")
        url = media_data.get("url", "No URL")
        filename = media_data.get("filename", "unknown")

        return f"Successfully uploaded '{filename}' (ID: {media_id})\nURL: {url}"

    return await safe_execute_async(_upload_media_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def rename_media(media_id: int, new_title: str) -> str:
    """
    Rename/update the title of a media file.

    Args:
        media_id: ID of the media file to rename
        new_title: New title/description for the media file

    Returns:
        Success message
    """
    async def _rename_media_logic() -> str:
        client = get_client()
        await client.update_media(media_id, new_title)

        return f"Successfully renamed media {media_id} to '{new_title}'"

    return await safe_execute_async(_rename_media_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def delete_media_file(media_id: int) -> str:
    """
    Delete a media file from Listmonk.

    Args:
        media_id: ID of the media file to delete

    Returns:
        Success message
    """
    async def _delete_media_logic() -> str:
        client = get_client()
        await client.delete_media(media_id)

        return f"Successfully deleted media {media_id}"

    return await safe_execute_async(_delete_media_logic)  # type: ignore[no-any-return]


# Media Resources
@mcp.resource("listmonk://media")
async def list_media_files() -> str:
    """List all media files with details."""
    try:
        client = get_client()
        result = await client.get_media()

        data = result.get("data", [])

        # Handle both list and dict formats
        if isinstance(data, dict):
            if not data:
                return "# Media Files\n\nNo media files found."
            media_list = list(data.values())
        else:
            media_list = data

        # Flatten if the first element is itself a list (nested structure)
        if media_list and isinstance(media_list[0], list):
            media_list = media_list[0]

        if not media_list:
            return "# Media Files\n\nNo media files found."

        media_items = []
        for media in media_list:
            size_bytes = media.get('meta', {}).get('size', 0) if isinstance(media.get('meta'), dict) else 0
            size_kb = size_bytes / 1024 if size_bytes > 0 else 0
            created = media.get('created_at', 'Unknown')
            media_items.append(
                f"- **{media.get('filename')}** (ID: {media.get('id')})\n"
                f"  - Title: {media.get('title', media.get('filename', 'No title'))}\n"
                f"  - Size: {size_kb:.1f} KB\n"
                f"  - Created: {created}\n"
                f"  - URL: {media.get('url', 'No URL')}"
            )

        media_items_text = "\n\n".join(media_items)

        return f"""# Media Files

**Total Files:** {len(media_list)}

{media_items_text}

*Use upload_media_file to add new files, rename_media to update titles, or delete_media_file to remove files.*
"""

    except ListmonkAPIError as e:
        return f"Error retrieving media files: {str(e)}"


# Campaign Body Editing Tools

@mcp.tool()
async def replace_in_campaign_body(
    campaign_id: int,
    search: str,
    replace: str
) -> str:
    """
    Search and replace text in a campaign body (simple string matching).

    This is much more token-efficient than updating the entire campaign body.

    Args:
        campaign_id: ID of the campaign to edit
        search: Text to search for (exact string match)
        replace: Text to replace it with

    Returns:
        Success message with number of replacements made

    Example:
        replace_in_campaign_body(
            campaign_id=11,
            search="</p>",
            replace="</p>\n<img src='https://...' style='...'>"
        )
    """
    async def _replace_logic() -> str:
        client = get_client()

        # Fetch current campaign
        result = await client.get_campaign(campaign_id)
        campaign = result.get("data", {})

        if not campaign:
            return f"Campaign {campaign_id} not found"

        current_body = campaign.get("body", "")

        # Perform replacement
        new_body = current_body.replace(search, replace)
        count = current_body.count(search)

        if count == 0:
            return f"Search text not found in campaign {campaign_id}"

        # Update campaign with new body
        await client.update_campaign(
            campaign_id=campaign_id,
            name=campaign.get("name"),
            subject=campaign.get("subject"),
            lists=[lst["id"] for lst in campaign.get("lists", [])],
            body=new_body
        )

        return f"Successfully replaced {count} occurrence(s) in campaign {campaign_id}"

    return await safe_execute_async(_replace_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def regex_replace_in_campaign_body(
    campaign_id: int,
    pattern: str,
    replace: str
) -> str:
    """
    Search and replace in campaign body using regex patterns.

    More powerful than simple replace - supports capturing groups and complex patterns.

    Args:
        campaign_id: ID of the campaign to edit
        pattern: Regex pattern to search for
        replace: Replacement string (can use \\1, \\2 for capture groups)

    Returns:
        Success message with number of replacements made

    Example:
        regex_replace_in_campaign_body(
            campaign_id=11,
            pattern=r"(Bondeni.*?</p>)",
            replace=r"\\1\n<img src='https://...'>"
        )
    """
    async def _regex_replace_logic() -> str:
        import re

        client = get_client()

        # Fetch current campaign
        result = await client.get_campaign(campaign_id)
        campaign = result.get("data", {})

        if not campaign:
            return f"Campaign {campaign_id} not found"

        current_body = campaign.get("body", "")

        # Perform regex replacement
        new_body, count = re.subn(pattern, replace, current_body)

        if count == 0:
            return f"Pattern not found in campaign {campaign_id}"

        # Update campaign with new body
        await client.update_campaign(
            campaign_id=campaign_id,
            name=campaign.get("name"),
            subject=campaign.get("subject"),
            lists=[lst["id"] for lst in campaign.get("lists", [])],
            body=new_body
        )

        return f"Successfully replaced {count} match(es) in campaign {campaign_id}"

    return await safe_execute_async(_regex_replace_logic)  # type: ignore[no-any-return]


@mcp.tool()
async def batch_replace_in_campaign_body(
    campaign_id: int,
    replacements: list[dict[str, str]]
) -> str:
    """
    Perform multiple search-and-replace operations in one go.

    Even more efficient - fetches campaign once, does all replacements, updates once.

    Args:
        campaign_id: ID of the campaign to edit
        replacements: List of dicts with 'search' and 'replace' keys

    Returns:
        Success message with total replacements made

    Example:
        batch_replace_in_campaign_body(
            campaign_id=11,
            replacements=[
                {"search": "Text A", "replace": "Text B"},
                {"search": "Text C", "replace": "Text D"}
            ]
        )
    """
    async def _batch_replace_logic() -> str:
        client = get_client()

        # Fetch current campaign
        result = await client.get_campaign(campaign_id)
        campaign = result.get("data", {})

        if not campaign:
            return f"Campaign {campaign_id} not found"

        current_body = campaign.get("body", "")
        new_body = current_body
        total_count = 0

        # Perform all replacements
        for replacement in replacements:
            search = replacement.get("search", "")
            replace = replacement.get("replace", "")

            if not search:
                continue

            count = new_body.count(search)
            new_body = new_body.replace(search, replace)
            total_count += count

        if total_count == 0:
            return f"No search texts found in campaign {campaign_id}"

        # Update campaign with new body
        await client.update_campaign(
            campaign_id=campaign_id,
            name=campaign.get("name"),
            subject=campaign.get("subject"),
            lists=[lst["id"] for lst in campaign.get("lists", [])],
            body=new_body
        )

        return f"Successfully completed {len(replacements)} replacement operation(s) with {total_count} total change(s) in campaign {campaign_id}"

    return await safe_execute_async(_batch_replace_logic)  # type: ignore[no-any-return]


# CLI application
cli_app = typer.Typer(
    name="listmonk-mcp",
    help="Listmonk MCP Server - Connect Claude Code to Listmonk via Model Context Protocol",
    add_completion=False
)


@cli_app.command()
def run(
    config_file: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file (.env format)"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging"
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit"
    )
) -> None:
    """
    Start the Listmonk MCP server.

    The server requires configuration via environment variables:
    - LISTMONK_MCP_URL: Listmonk server URL (e.g., http://localhost:9000)
    - LISTMONK_MCP_USERNAME: Listmonk API username
    - LISTMONK_MCP_PASSWORD: Listmonk API password/token

    Optional environment variables:
    - LISTMONK_MCP_TIMEOUT: Request timeout in seconds (default: 30)
    - LISTMONK_MCP_MAX_RETRIES: Maximum retry attempts (default: 3)
    - LISTMONK_MCP_DEBUG: Enable debug mode (default: false)
    - LISTMONK_MCP_LOG_LEVEL: Logging level (default: INFO)
    """
    if version:
        # Import here to avoid circular imports
        try:
            from importlib.metadata import version as get_version
            pkg_version = get_version("listmonk-mcp")
        except ImportError:
            pkg_version = "0.0.1"  # fallback
        typer.echo(f"listmonk-mcp {pkg_version}")
        raise typer.Exit()

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info("Starting Listmonk MCP Server...")
        # Create the production MCP server with lifespan management
        server = create_production_server()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        raise typer.Exit(0) from None
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise typer.Exit(1) from e


def main() -> None:
    """Main entry point for the CLI script."""
    cli_app()


if __name__ == "__main__":
    main()
