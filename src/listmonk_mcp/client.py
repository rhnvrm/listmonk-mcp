"""Listmonk API client abstraction using httpx."""

import asyncio
import json
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from httpx import AsyncClient, Response

from .config import Config

_UNSET = object()


class ListmonkAPIError(Exception):
    """Base exception for Listmonk API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ListmonkClient:
    """Async HTTP client for Listmonk API operations."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.url.rstrip("/")
        self._client: AsyncClient | None = None

    async def __aenter__(self) -> "ListmonkClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Initialize the HTTP client with authentication."""
        # Use API token authentication format: "username:token"
        auth_token = f"{self.config.username}:{self.config.password}"

        self._client = AsyncClient(
            timeout=self.config.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "User-Agent": "Listmonk-MCP-Server/0.2.0",
                "Accept": "application/json",
                "Authorization": f"token {auth_token}",
            },
        )

        # Test connection with health check
        try:
            await self.health_check()
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> AsyncClient:
        """Get the HTTP client, raising error if not connected."""
        if self._client is None:
            raise RuntimeError(
                "Client not connected. Call connect() first or use as async context manager."
            )
        return self._client

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: Any = _UNSET,
        retry_count: int = 0,
        form_data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic and error handling."""
        client = self._get_client()
        url = self._build_url(endpoint)

        try:
            kwargs: dict[str, Any] = {}
            if json_data is not _UNSET:
                kwargs["content"] = json.dumps(json_data)
                kwargs["headers"] = {"Content-Type": "application/json"}
            if form_data is not None:
                kwargs["data"] = form_data
            response = await client.request(method, url, params=params, **kwargs)

            return await self._handle_response(response)

        except httpx.RequestError as e:
            if (
                method.upper() in {"GET", "HEAD"}
                and retry_count < self.config.max_retries
            ):
                await asyncio.sleep(2**retry_count)  # Exponential backoff
                return await self._request(
                    method, endpoint, params, json_data, retry_count + 1, form_data
                )

            raise ListmonkAPIError(f"Request failed: {str(e)}") from e

    async def _handle_response(self, response: Response) -> dict[str, Any]:
        """Handle HTTP response and extract data."""
        try:
            response_data = response.json()
        except Exception:
            response_data = {"data": response.text}

        if not isinstance(response_data, dict):
            response_data = {"data": response_data}
        if response.is_success:
            return response_data

        # Handle API errors
        error_message = response_data.get("message", f"HTTP {response.status_code}")
        raise ListmonkAPIError(
            message=error_message,
            status_code=response.status_code,
            response=response_data,
        )

    # Health and Authentication
    async def health_check(self) -> dict[str, Any]:
        """Check if Listmonk server is healthy and accessible."""
        return await self._request("GET", "/api/health")

    # Subscriber Operations
    async def get_subscribers(
        self,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order: str = "desc",
        query: str | None = None,
    ) -> dict[str, Any]:
        """Get subscribers with pagination and filtering."""
        params = {
            "page": page,
            "per_page": per_page,
            "order_by": order_by,
            "order": order,
        }
        if query:
            params["query"] = query

        return await self._request("GET", "/api/subscribers", params=params)

    async def get_subscriber(self, subscriber_id: int) -> dict[str, Any]:
        """Get subscriber by ID."""
        return await self._request("GET", f"/api/subscribers/{subscriber_id}")

    async def get_subscriber_by_email(self, email: str) -> dict[str, Any]:
        """Get subscriber by email address."""
        escaped_email = email.replace("'", "''")
        params = {"query": f"subscribers.email = '{escaped_email}'"}
        response = await self._request("GET", "/api/subscribers", params=params)

        if response.get("data", {}).get("results"):
            return {"data": response["data"]["results"][0]}
        else:
            raise ListmonkAPIError(
                f"Subscriber with email {email} not found", status_code=404
            )

    async def create_subscriber(
        self,
        email: str,
        name: str,
        status: str = "enabled",
        lists: list[int] | None = None,
        attribs: dict[str, Any] | None = None,
        preconfirm_subscriptions: bool = False,
    ) -> dict[str, Any]:
        """Create a new subscriber."""
        data = {
            "email": email,
            "name": name,
            "status": status,
            "lists": lists or [],
            "attribs": attribs or {},
            "preconfirm_subscriptions": preconfirm_subscriptions,
        }
        return await self._request("POST", "/api/subscribers", json_data=data)

    async def update_subscriber(
        self,
        subscriber_id: int,
        email: str | None = None,
        name: str | None = None,
        status: str | None = None,
        lists: list[int] | None = None,
        attribs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update only supplied fields, preserving other subscriber data."""
        return await self.patch_subscriber(
            subscriber_id,
            email=email,
            name=name,
            status=status,
            lists=lists,
            attribs=attribs,
        )

    async def delete_subscriber(self, subscriber_id: int) -> dict[str, Any]:
        """Delete a subscriber."""
        return await self._request("DELETE", f"/api/subscribers/{subscriber_id}")

    async def set_subscriber_status(
        self, subscriber_id: int, status: str
    ) -> dict[str, Any]:
        """Set subscriber status (enabled, disabled, blocklisted)."""
        return await self.patch_subscriber(subscriber_id, status=status)

    async def patch_subscriber(
        self,
        subscriber_id: int,
        email: str | None = None,
        name: str | None = None,
        status: str | None = None,
        lists: list[int] | None = None,
        attribs: dict[str, Any] | None = None,
        preconfirm_subscriptions: bool = False,
    ) -> dict[str, Any]:
        """PATCH fields directly; omitted lists preserve existing memberships."""
        data: dict[str, Any] = {
            key: value
            for key, value in {
                "email": email,
                "name": name,
                "status": status,
                "lists": lists,
                "attribs": attribs,
            }.items()
            if value is not None
        }
        if preconfirm_subscriptions:
            data["preconfirm_subscriptions"] = True
        try:
            return await self._request(
                "PATCH", f"/api/subscribers/{subscriber_id}", json_data=data
            )
        except ListmonkAPIError as e:
            if e.status_code not in {404, 405}:
                raise
            # v6 has no PATCH route. Fetch first so PUT preserves required fields
            # and memberships; a missing subscriber still fails on this GET.
            current = (await self.get_subscriber(subscriber_id))["data"]
            payload = {
                key: current[key]
                for key in ("email", "name", "status", "attribs")
                if key in current
            }
            payload["lists"] = [item["id"] for item in current.get("lists", [])]
            payload.update(data)
            return await self._request(
                "PUT", f"/api/subscribers/{subscriber_id}", json_data=payload
            )

    async def subscriber_send_optin(self, subscriber_id: int) -> dict[str, Any]:
        """Trigger an opt-in confirmation email to a subscriber."""
        return await self._request("POST", f"/api/subscribers/{subscriber_id}/optin")

    async def blocklist_subscriber(self, subscriber_id: int) -> dict[str, Any]:
        """Blocklist a single subscriber."""
        return await self._request("PUT", f"/api/subscribers/{subscriber_id}/blocklist")

    async def blocklist_subscribers(self, subscriber_ids: list[int]) -> dict[str, Any]:
        """Blocklist multiple subscribers in one call."""
        return await self._request(
            "PUT",
            "/api/subscribers/blocklist",
            json_data={"ids": subscriber_ids},
        )

    async def manage_subscriber_lists(
        self,
        subscriber_ids: list[int],
        target_list_ids: list[int],
        action: str,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Bulk add / remove / unsubscribe subscribers from lists.

        Args:
            subscriber_ids: Subscriber IDs to update.
            target_list_ids: Lists to operate on.
            action: One of "add", "remove", "unsubscribe".
            status: Optional subscription status (e.g. "confirmed", "unconfirmed").
        """
        data: dict[str, Any] = {
            "ids": subscriber_ids,
            "action": action,
            "target_list_ids": target_list_ids,
        }
        if status is not None:
            data["status"] = status
        return await self._request("PUT", "/api/subscribers/lists", json_data=data)

    async def get_subscriber_activity(self, subscriber_id: int) -> dict[str, Any]:
        """Get a subscriber's activity log (opt-ins, bounces, list changes)."""
        return await self._request("GET", f"/api/subscribers/{subscriber_id}/activity")

    async def delete_subscribers(self, subscriber_ids: list[int]) -> dict[str, Any]:
        """Delete multiple subscribers by ID."""
        params = {"id": [str(sid) for sid in subscriber_ids]}
        return await self._request("DELETE", "/api/subscribers", params=params)

    async def delete_subscribers_by_query(
        self,
        query: str,
        list_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Delete subscribers matching an advanced SQL query expression."""
        data: dict[str, Any] = {"query": query, "list_ids": list_ids or []}
        return await self._request(
            "POST", "/api/subscribers/query/delete", json_data=data
        )

    async def blocklist_subscribers_by_query(
        self,
        query: str,
        list_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Blocklist subscribers matching an advanced SQL query expression."""
        data: dict[str, Any] = {"query": query, "list_ids": list_ids or []}
        return await self._request(
            "PUT", "/api/subscribers/query/blocklist", json_data=data
        )

    async def manage_subscriber_lists_by_query(
        self,
        query: str,
        target_list_ids: list[int],
        action: str,
        list_ids: list[int] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Bulk add/remove/unsubscribe subscribers matching a query."""
        data: dict[str, Any] = {
            "query": query,
            "list_ids": list_ids or [],
            "target_list_ids": target_list_ids,
            "action": action,
        }
        if status is not None:
            data["status"] = status
        return await self._request(
            "PUT", "/api/subscribers/query/lists", json_data=data
        )

    async def get_subscriber_bounces(self, subscriber_id: int) -> dict[str, Any]:
        """Get bounce records for a single subscriber."""
        return await self._request("GET", f"/api/subscribers/{subscriber_id}/bounces")

    async def delete_subscriber_bounces(self, subscriber_id: int) -> dict[str, Any]:
        """Delete all bounce records for a single subscriber."""
        return await self._request(
            "DELETE", f"/api/subscribers/{subscriber_id}/bounces"
        )

    # Bounce Operations
    async def get_bounces(
        self,
        page: int = 1,
        per_page: int = 20,
        campaign_id: int | None = None,
        source: str | None = None,
        order_by: str = "created_at",
        order: str = "desc",
    ) -> dict[str, Any]:
        """Get bounce records with pagination and filtering."""
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "order_by": order_by,
            "order": order,
        }
        if campaign_id is not None:
            params["campaign_id"] = campaign_id
        if source is not None:
            params["source"] = source
        return await self._request("GET", "/api/bounces", params=params)

    async def get_bounce(self, bounce_id: int) -> dict[str, Any]:
        """Get a single bounce record by ID."""
        return await self._request("GET", f"/api/bounces/{bounce_id}")

    async def delete_bounce(self, bounce_id: int) -> dict[str, Any]:
        """Delete a single bounce record."""
        return await self._request("DELETE", f"/api/bounces/{bounce_id}")

    async def delete_bounces(
        self,
        bounce_ids: list[int] | None = None,
        *,
        all: bool = False,
    ) -> dict[str, Any]:
        """Delete selected bounces, or explicitly request all=True."""
        if bool(bounce_ids) == all:
            raise ValueError(
                "Provide bounce_ids or explicitly set all=True, exclusively"
            )
        params = {"id": bounce_ids} if bounce_ids else {"all": "true"}
        return await self._request("DELETE", "/api/bounces", params=params)

    async def blocklist_bounced_subscribers(
        self,
        bounce_ids: list[int] | None = None,
        *,
        all: bool = False,
    ) -> dict[str, Any]:
        """Blocklist subscribers for selected bounces, or explicitly all=True."""
        if bool(bounce_ids) == all:
            raise ValueError(
                "Provide bounce_ids or explicitly set all=True, exclusively"
            )
        params = {"id": bounce_ids} if bounce_ids else None
        return await self._request("PUT", "/api/bounces/blocklist", params=params)

    # Subscriber Import Operations
    async def get_import_status(self) -> dict[str, Any]:
        """Get the status of the current/last subscriber import."""
        return await self._request("GET", "/api/import/subscribers")

    async def get_import_logs(self) -> dict[str, Any]:
        """Get logs from the current/last subscriber import."""
        return await self._request("GET", "/api/import/subscribers/logs")

    async def import_subscribers(
        self,
        file_path: str,
        mode: str = "subscribe",
        list_ids: list[int] | None = None,
        delim: str = ",",
        overwrite: bool = True,
        subscription_status: str = "confirmed",
    ) -> dict[str, Any]:
        """Start a subscriber import from a CSV/zip file.

        Args:
            file_path: Local path to a .csv or .zip file.
            mode: "subscribe" or "blocklist".
            list_ids: Lists to subscribe imported users to.
            delim: CSV delimiter (default ",").
            overwrite: Whether to overwrite existing subscribers.
            subscription_status: "confirmed" or "unconfirmed".
        """
        import json as _json
        from pathlib import Path

        url = self._build_url("/api/import/subscribers")
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ListmonkAPIError(f"File not found: {file_path}")

        ext = file_path_obj.suffix.lower()
        content_type = "application/zip" if ext == ".zip" else "text/csv"

        with open(file_path, "rb") as f:
            file_content = f.read()

        params = {
            "mode": mode,
            "subscription_status": subscription_status,
            "delim": delim,
            "lists": list_ids or [],
            "overwrite": overwrite,
        }

        files = {"file": (file_path_obj.name, file_content, content_type)}
        data = {"params": _json.dumps(params)}

        try:
            response = await self._get_client().post(url, files=files, data=data)
            return await self._handle_response(response)
        except httpx.RequestError as e:
            raise ListmonkAPIError(f"Subscriber import failed: {e}") from e

    async def stop_import(self) -> dict[str, Any]:
        """Stop the currently running subscriber import."""
        return await self._request("DELETE", "/api/import/subscribers")

    # List Operations
    async def get_lists(
        self,
        page: int = 1,
        per_page: int = 100,
        query: str | None = None,
        status: str | None = None,
        minimal: bool = False,
        tags: list[str] | None = None,
        order_by: str | None = None,
        order: str | None = None,
    ) -> dict[str, Any]:
        """Get mailing lists with pagination and optional filters."""
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if query:
            params["query"] = query
        if status:
            params["status"] = status
        if minimal:
            params["minimal"] = "true"
        if tags:
            params["tag"] = tags
        if order_by:
            params["order_by"] = order_by
        if order:
            params["order"] = order

        return await self._request("GET", "/api/lists", params=params)

    async def get_list(self, list_id: int) -> dict[str, Any]:
        """Get mailing list by ID."""
        return await self._request("GET", f"/api/lists/{list_id}")

    async def create_list(
        self,
        name: str,
        type: str = "public",
        optin: str = "single",
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new mailing list."""
        data = {
            "name": name,
            "type": type,
            "optin": optin,
            "tags": tags or [],
            "messenger": "email",
        }
        if description:
            data["description"] = description

        return await self._request("POST", "/api/lists", json_data=data)

    async def update_list(
        self,
        list_id: int,
        name: str | None = None,
        type: str | None = None,
        optin: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing mailing list."""
        current = (await self.get_list(list_id)).get("data", {})
        data: dict[str, Any] = {
            key: current[key]
            for key in ("name", "type", "optin", "tags", "description", "status")
            if key in current
        }
        if name is not None:
            data["name"] = name
        if type is not None:
            data["type"] = type
        if optin is not None:
            data["optin"] = optin
        if tags is not None:
            data["tags"] = tags
        if description is not None:
            data["description"] = description

        return await self._request("PUT", f"/api/lists/{list_id}", json_data=data)

    async def delete_list(self, list_id: int) -> dict[str, Any]:
        """Delete a mailing list."""
        return await self._request("DELETE", f"/api/lists/{list_id}")

    async def get_list_subscribers(
        self, list_id: int, page: int = 1, per_page: int = 20
    ) -> dict[str, Any]:
        """Get subscribers for a specific list."""
        params = {"page": page, "per_page": per_page, "list_id": list_id}
        return await self._request("GET", "/api/subscribers", params=params)

    # Campaign Operations
    async def get_campaigns(
        self, page: int = 1, per_page: int = 20, status: str | None = None
    ) -> dict[str, Any]:
        """Get campaigns with pagination and filtering."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status

        return await self._request("GET", "/api/campaigns", params=params)

    async def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Get campaign by ID."""
        return await self._request("GET", f"/api/campaigns/{campaign_id}")

    async def create_campaign(
        self,
        name: str,
        subject: str,
        lists: list[int],
        type: str = "regular",
        content_type: str = "richtext",
        body: str | None = None,
        template_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new campaign."""
        data: dict[str, Any] = {
            "name": name,
            "subject": subject,
            "lists": lists,
            "type": type,
            "content_type": content_type,
            "tags": tags or [],
            "messenger": "email",
        }

        if body:
            data["body"] = body
        if template_id:
            data["template_id"] = template_id

        return await self._request("POST", "/api/campaigns", json_data=data)

    async def update_campaign(
        self,
        campaign_id: int,
        name: str | None = None,
        subject: str | None = None,
        lists: list[int] | None = None,
        body: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing campaign.

        If lists is not provided, fetches the current campaign's lists to preserve them.
        """
        current = (await self.get_campaign(campaign_id)).get("data", {})
        data = self._campaign_payload(current)
        for key, value in {
            "name": name,
            "subject": subject,
            "lists": lists,
            "body": body,
            "tags": tags,
        }.items():
            if value is not None:
                data[key] = value
        return await self._request(
            "PUT", f"/api/campaigns/{campaign_id}", json_data=data
        )

    @staticmethod
    def _campaign_payload(campaign: dict[str, Any]) -> dict[str, Any]:
        """Build writable campaign fields without copying server-managed state."""
        keys = (
            "name",
            "subject",
            "from_email",
            "body",
            "body_source",
            "altbody",
            "content_type",
            "messenger",
            "type",
            "tags",
            "template_id",
            "headers",
            "send_at",
            "archive",
            "archive_template_id",
            "archive_meta",
            "archive_slug",
        )
        data = {key: campaign[key] for key in keys if key in campaign}
        data["lists"] = [
            item["id"] if isinstance(item, dict) else item
            for item in campaign.get("lists", [])
        ]
        if "media" in campaign:
            data["media"] = [
                item["id"] if isinstance(item, dict) else item
                for item in campaign["media"] or []
            ]
        return data

    async def send_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Send a campaign immediately."""
        return await self._request(
            "PUT",
            f"/api/campaigns/{campaign_id}/status",
            json_data={"status": "running"},
        )

    async def schedule_campaign(self, campaign_id: int, send_at: str) -> dict[str, Any]:
        """Schedule a campaign for future delivery."""
        current = (await self.get_campaign(campaign_id)).get("data", {})
        data = self._campaign_payload(current)
        data["send_at"] = send_at
        await self._request("PUT", f"/api/campaigns/{campaign_id}", json_data=data)
        return await self.change_campaign_status(campaign_id, "scheduled")

    async def get_campaign_preview(self, campaign_id: int) -> dict[str, Any]:
        """Get campaign HTML preview."""
        return await self._request("GET", f"/api/campaigns/{campaign_id}/preview")

    async def test_campaign(
        self,
        campaign_id: int,
        subscribers: list[str],
    ) -> dict[str, Any]:
        """Send a test of the campaign to one or more subscriber emails.

        Listmonk's test endpoint validates the full campaign payload
        (name/subject/lists/body/messenger/content_type), so we fetch the
        saved campaign and merge those fields into the test request — same
        pattern as update_campaign.

        Note: recipients must already exist as subscribers in listmonk;
        the test handler looks them up by email and requires permission
        to access those subscriber records.
        """
        if not subscribers:
            raise ValueError("At least one existing subscriber email is required")
        current = (await self.get_campaign(campaign_id)).get("data", {})
        data = self._campaign_payload(current)
        data["subscribers"] = subscribers
        return await self._request(
            "POST", f"/api/campaigns/{campaign_id}/test", json_data=data
        )

    async def change_campaign_status(
        self, campaign_id: int, status: str
    ) -> dict[str, Any]:
        """Change a campaign's status (draft, scheduled, running, paused, cancelled)."""
        return await self._request(
            "PUT",
            f"/api/campaigns/{campaign_id}/status",
            json_data={"status": status},
        )

    async def archive_campaign(
        self,
        campaign_id: int,
        archive: bool,
        archive_template_id: int | None = None,
        archive_meta: dict[str, Any] | None = None,
        archive_slug: str | None = None,
    ) -> dict[str, Any]:
        """Toggle a campaign's archive flag and optionally update archive metadata."""
        data: dict[str, Any] = {"archive": archive}
        if archive_template_id is not None:
            data["archive_template_id"] = archive_template_id
        if archive_meta is not None:
            data["archive_meta"] = archive_meta
        if archive_slug is not None:
            data["archive_slug"] = archive_slug
        return await self._request(
            "PUT", f"/api/campaigns/{campaign_id}/archive", json_data=data
        )

    async def delete_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Delete a single campaign."""
        return await self._request("DELETE", f"/api/campaigns/{campaign_id}")

    async def delete_campaigns(self, campaign_ids: list[int]) -> dict[str, Any]:
        """Delete multiple campaigns by ID."""
        params = {"id": [str(cid) for cid in campaign_ids]}
        return await self._request("DELETE", "/api/campaigns", params=params)

    async def get_running_campaign_stats(self) -> dict[str, Any]:
        """Get stats for currently running campaigns."""
        return await self._request("GET", "/api/campaigns/running/stats")

    async def get_campaign_analytics(
        self,
        analytics_type: str,
        campaign_ids: list[int],
        from_date: str,
        to_date: str,
        interval: str = "day",
        unique: bool = False,
    ) -> dict[str, Any]:
        """Get campaign analytics within a required date range, including v7 unique counts."""
        if not campaign_ids:
            raise ValueError("At least one campaign ID is required")
        if analytics_type not in {"views", "clicks", "links", "bounces"}:
            raise ValueError("Invalid analytics type")
        params: dict[str, Any] = {
            "id": campaign_ids,
            "from": from_date,
            "to": to_date,
            "interval": interval,
            "unique": str(unique).lower(),
        }
        return await self._request(
            "GET", f"/api/campaigns/analytics/{analytics_type}", params=params
        )

    # Template Operations
    async def get_templates(self) -> dict[str, Any]:
        """Get all email templates."""
        return await self._request("GET", "/api/templates")

    async def get_template(self, template_id: int) -> dict[str, Any]:
        """Get template by ID."""
        return await self._request("GET", f"/api/templates/{template_id}")

    async def create_template(
        self,
        name: str,
        body: str,
        type: str = "campaign",
        is_default: bool = False,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """Create a new email template."""
        data = {"name": name, "body": body, "type": type, "is_default": is_default}
        if subject is not None:
            data["subject"] = subject
        result = await self._request("POST", "/api/templates", json_data=data)
        if is_default:
            await self.set_default_template(result["data"]["id"])
        return result

    async def update_template(
        self,
        template_id: int,
        name: str | None = None,
        body: str | None = None,
        is_default: bool | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing template.

        Fetches the current template first and merges changes, as Listmonk
        requires all fields in PUT requests.
        """
        # Fetch current template to get all existing values
        current = await self.get_template(template_id)
        template_data = current.get("data", {})

        # Build update data with current values as defaults
        # IMPORTANT: type must be included, otherwise Listmonk validates as transactional template
        data: dict[str, Any] = {
            "name": name if name is not None else template_data.get("name", ""),
            "type": template_data.get("type", "campaign"),
            "body": body if body is not None else template_data.get("body", ""),
            "is_default": is_default
            if is_default is not None
            else template_data.get("is_default", False),
        }

        # Transactional templates require a subject field in PUT requests
        current_subject = template_data.get("subject", "")
        if subject is not None:
            data["subject"] = subject
        elif current_subject:
            data["subject"] = current_subject

        if "body_source" in template_data and body is None:
            data["body_source"] = template_data["body_source"]
        result = await self._request(
            "PUT", f"/api/templates/{template_id}", json_data=data
        )
        if is_default:
            await self.set_default_template(template_id)
        return result

    async def delete_template(self, template_id: int) -> dict[str, Any]:
        """Delete a template."""
        return await self._request("DELETE", f"/api/templates/{template_id}")

    async def set_default_template(self, template_id: int) -> dict[str, Any]:
        """Mark a template as the default for its type."""
        return await self._request("PUT", f"/api/templates/{template_id}/default")

    async def preview_template_body(
        self,
        body: str,
        template_type: str = "campaign",
    ) -> dict[str, Any]:
        """Render a preview of a template body without saving it."""
        data = {"body": body, "template_type": template_type}
        return await self._request("POST", "/api/templates/preview", form_data=data)

    # Settings & Admin Operations
    async def get_settings(self) -> dict[str, Any]:
        """Get the full server settings document."""
        return await self._request("GET", "/api/settings")

    async def update_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Update the full server settings document.

        WARNING: GET /api/settings returns secret fields (passwords, tokens) masked
        as bullets ("•••"). PUTting that body back overwrites the real values with
        literal bullets. Strip secret-looking keys before calling this.
        """
        return await self._request("PUT", "/api/settings", json_data=settings)

    async def update_setting(self, key: str, value: Any) -> dict[str, Any]:
        """Update a single settings key (avoids the password-masking footgun).

        Listmonk's per-key settings handler reads the request body as a raw
        JSON value and writes it directly into the settings document — so
        the body must be the value itself (e.g. a JSON string for a string
        setting), NOT wrapped in {"value": ...}. Wrapping causes listmonk
        to store the whole object and breaks the field.
        """
        return await self._request(
            "PUT", f"/api/settings/{quote(key, safe='')}", json_data=value
        )

    async def test_smtp_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Send a test email through provided SMTP settings."""
        return await self._request(
            "POST", "/api/settings/smtp/test", json_data=settings
        )

    async def reload_app(self) -> dict[str, Any]:
        """Trigger a hot-reload of the Listmonk app."""
        return await self._request("POST", "/api/admin/reload")

    async def get_logs(self) -> dict[str, Any]:
        """Get recent server logs."""
        return await self._request("GET", "/api/logs")

    async def get_about_info(self) -> dict[str, Any]:
        """Get version / build / runtime info."""
        return await self._request("GET", "/api/about")

    async def get_dashboard_counts(self) -> dict[str, Any]:
        """Get dashboard counts (subscribers, lists, campaigns, etc)."""
        return await self._request("GET", "/api/dashboard/counts")

    async def get_dashboard_charts(self) -> dict[str, Any]:
        """Get dashboard chart data (campaign views, link clicks over time)."""
        return await self._request("GET", "/api/dashboard/charts")

    # Maintenance Operations
    async def gc_subscribers(self, gc_type: str) -> dict[str, Any]:
        """Garbage collect subscribers.

        Args:
            gc_type: One of "blocklisted", "orphan".
        """
        if gc_type not in {"blocklisted", "orphan"}:
            raise ValueError("gc_type must be blocklisted or orphan")
        return await self._request("DELETE", f"/api/maintenance/subscribers/{gc_type}")

    async def gc_campaign_analytics(
        self, analytics_type: str, before: str
    ) -> dict[str, Any]:
        """Delete views/clicks/all older than a required RFC3339 timestamp."""
        if analytics_type not in {"views", "clicks", "all"}:
            raise ValueError("analytics_type must be views, clicks, or all")
        return await self._request(
            "DELETE",
            f"/api/maintenance/analytics/{analytics_type}",
            params={"before_date": before},
        )

    async def gc_unconfirmed_subscriptions(self, before: str) -> dict[str, Any]:
        """Delete unconfirmed subscriptions older than an RFC3339 timestamp."""
        return await self._request(
            "DELETE",
            "/api/maintenance/subscriptions/unconfirmed",
            params={"before_date": before},
        )

    # Transactional Email
    async def send_transactional_email(
        self,
        subscriber_email: str,
        template_id: int,
        data: dict[str, Any] | None = None,
        content_type: str = "html",
    ) -> dict[str, Any]:
        """Send a transactional email."""
        payload = {
            "subscriber_email": subscriber_email,
            "template_id": template_id,
            "data": data or {},
            "content_type": content_type,
        }
        return await self._request("POST", "/api/tx", json_data=payload)

    # Media Operations
    async def get_media(
        self,
        page: int = 1,
        per_page: int = 20,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get paginated media; v7 supports search and tags."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if query:
            params["query"] = query
        if tags:
            params["tag"] = tags
        return await self._request("GET", "/api/media", params=params)

    async def upload_media(
        self, file_path: str, title: str | None = None
    ) -> dict[str, Any]:
        """Upload a media file.

        Args:
            file_path: Absolute path to the file to upload
            title: Optional title for the media file (defaults to filename)

        Returns:
            Dict containing the uploaded media data including URL
        """
        from pathlib import Path

        url = self._build_url("/api/media")

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ListmonkAPIError(f"File not found: {file_path}")

        # Determine content type from file extension
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }
        ext = file_path_obj.suffix.lower()
        content_type = content_types.get(ext, "application/octet-stream")

        # Use filename as title if not provided
        if title is None:
            title = file_path_obj.name

        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Prepare multipart form data
        files = {"file": (file_path_obj.name, file_content, content_type)}
        data = {}
        if title:
            data["title"] = title

        try:
            response = await self._get_client().post(url, files=files, data=data)
            return await self._handle_response(response)
        except httpx.RequestError as e:
            raise ListmonkAPIError(f"Media upload failed: {e}") from e

    async def update_media(self, media_id: int, title: str) -> dict[str, Any]:
        """Compatibility entry point for an unsupported operation."""
        raise ValueError(
            "Listmonk does not support media title changes. Use update_media_tags on v7 instead."
        )

    async def update_media_tags(self, media_id: int, tags: list[str]) -> dict[str, Any]:
        """Replace media tags (Listmonk v7+)."""
        return await self._request(
            "PUT", f"/api/media/{media_id}", json_data={"tags": tags}
        )

    async def delete_media(self, media_id: int) -> dict[str, Any]:
        """Delete a media file.

        Args:
            media_id: ID of the media file to delete
        """
        return await self._request("DELETE", f"/api/media/{media_id}")


async def create_client(config: Config) -> ListmonkClient:
    """Create and connect a Listmonk client."""
    client = ListmonkClient(config)
    await client.connect()
    return client
