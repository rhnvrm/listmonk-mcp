"""Listmonk API client abstraction using httpx."""

import asyncio
from typing import Any
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Response

from .config import Config


class ListmonkAPIError(Exception):
    """Base exception for Listmonk API errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ListmonkClient:
    """Async HTTP client for Listmonk API operations."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.url.rstrip('/')
        self._client: AsyncClient | None = None

    async def __aenter__(self) -> "ListmonkClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
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
                "User-Agent": "Listmonk-MCP-Server/0.1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"token {auth_token}"
            }
        )

        # Test connection with health check
        await self.health_check()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> AsyncClient:
        """Get the HTTP client, raising error if not connected."""
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first or use as async context manager.")
        return self._client

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip('/'))

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        retry_count: int = 0
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic and error handling."""
        client = self._get_client()
        url = self._build_url(endpoint)

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )

            return await self._handle_response(response)

        except httpx.RequestError as e:
            if retry_count < self.config.max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._request(method, endpoint, params, json_data, retry_count + 1)

            raise ListmonkAPIError(f"Request failed: {str(e)}") from e

    async def _handle_response(self, response: Response) -> dict[str, Any]:
        """Handle HTTP response and extract data."""
        try:
            response_data = response.json()
        except Exception:
            response_data = {"text": response.text}

        if response.is_success:
            return response_data  # type: ignore[no-any-return]

        # Handle API errors
        error_message = response_data.get("message", f"HTTP {response.status_code}")
        raise ListmonkAPIError(
            message=error_message,
            status_code=response.status_code,
            response=response_data
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
        query: str | None = None
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
        params = {"query": f"subscribers.email = '{email}'"}
        response = await self._request("GET", "/api/subscribers", params=params)

        if response.get("data", {}).get("results"):
            return {"data": response["data"]["results"][0]}
        else:
            raise ListmonkAPIError(f"Subscriber with email {email} not found", status_code=404)

    async def create_subscriber(
        self,
        email: str,
        name: str,
        status: str = "enabled",
        lists: list[int] | None = None,
        attribs: dict[str, Any] | None = None,
        preconfirm_subscriptions: bool = False
    ) -> dict[str, Any]:
        """Create a new subscriber."""
        data = {
            "email": email,
            "name": name,
            "status": status,
            "lists": lists or [],
            "attribs": attribs or {},
            "preconfirm_subscriptions": preconfirm_subscriptions
        }
        return await self._request("POST", "/api/subscribers", json_data=data)

    async def update_subscriber(
        self,
        subscriber_id: int,
        email: str | None = None,
        name: str | None = None,
        status: str | None = None,
        lists: list[int] | None = None,
        attribs: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Update an existing subscriber."""
        data: dict[str, Any] = {}
        if email is not None:
            data["email"] = email
        if name is not None:
            data["name"] = name
        if status is not None:
            data["status"] = status
        if lists is not None:
            data["lists"] = lists
        if attribs is not None:
            data["attribs"] = attribs

        return await self._request("PUT", f"/api/subscribers/{subscriber_id}", json_data=data)

    async def delete_subscriber(self, subscriber_id: int) -> dict[str, Any]:
        """Delete a subscriber."""
        return await self._request("DELETE", f"/api/subscribers/{subscriber_id}")

    async def set_subscriber_status(self, subscriber_id: int, status: str) -> dict[str, Any]:
        """Set subscriber status (enabled, disabled, blocklisted)."""
        data = {"status": status}
        return await self._request("PUT", f"/api/subscribers/{subscriber_id}", json_data=data)

    # List Operations
    async def get_lists(self) -> dict[str, Any]:
        """Get all mailing lists."""
        return await self._request("GET", "/api/lists")

    async def get_list(self, list_id: int) -> dict[str, Any]:
        """Get mailing list by ID."""
        return await self._request("GET", f"/api/lists/{list_id}")

    async def create_list(
        self,
        name: str,
        type: str = "public",
        optin: str = "single",
        tags: list[str] | None = None,
        description: str | None = None
    ) -> dict[str, Any]:
        """Create a new mailing list."""
        data = {
            "name": name,
            "type": type,
            "optin": optin,
            "tags": tags or [],
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
        description: str | None = None
    ) -> dict[str, Any]:
        """Update an existing mailing list."""
        data: dict[str, Any] = {}
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

    async def get_list_subscribers(self, list_id: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        """Get subscribers for a specific list."""
        params = {"page": page, "per_page": per_page, "list_id": list_id}
        return await self._request("GET", "/api/subscribers", params=params)

    # Campaign Operations
    async def get_campaigns(
        self,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None
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
        tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Create a new campaign."""
        data: dict[str, Any] = {
            "name": name,
            "subject": subject,
            "lists": lists,
            "type": type,
            "content_type": content_type,
            "tags": tags or []
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
        tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Update an existing campaign.

        If lists is not provided, fetches the current campaign's lists to preserve them.
        """
        # If lists not provided, fetch current campaign to get existing lists
        if lists is None:
            current = await self.get_campaign(campaign_id)
            campaign_data = current.get("data", {})
            current_lists = campaign_data.get("lists", [])
            lists = [lst.get("id") for lst in current_lists if lst.get("id")]

        data: dict[str, Any] = {"lists": lists}
        if name is not None:
            data["name"] = name
        if subject is not None:
            data["subject"] = subject
        if body is not None:
            data["body"] = body
        if tags is not None:
            data["tags"] = tags

        return await self._request("PUT", f"/api/campaigns/{campaign_id}", json_data=data)

    async def send_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Send a campaign immediately."""
        return await self._request("PUT", f"/api/campaigns/{campaign_id}/status", json_data={"status": "running"})

    async def schedule_campaign(self, campaign_id: int, send_at: str) -> dict[str, Any]:
        """Schedule a campaign for future delivery."""
        data = {"status": "scheduled", "send_at": send_at}
        return await self._request("PUT", f"/api/campaigns/{campaign_id}/status", json_data=data)

    async def get_campaign_preview(self, campaign_id: int) -> dict[str, Any]:
        """Get campaign HTML preview."""
        return await self._request("GET", f"/api/campaigns/{campaign_id}/preview")

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
        is_default: bool = False
    ) -> dict[str, Any]:
        """Create a new email template."""
        data = {
            "name": name,
            "body": body,
            "type": type,
            "is_default": is_default
        }
        return await self._request("POST", "/api/templates", json_data=data)

    async def update_template(
        self,
        template_id: int,
        name: str | None = None,
        body: str | None = None,
        is_default: bool | None = None
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
            "is_default": is_default if is_default is not None else template_data.get("is_default", False),
        }

        return await self._request("PUT", f"/api/templates/{template_id}", json_data=data)

    async def delete_template(self, template_id: int) -> dict[str, Any]:
        """Delete a template."""
        return await self._request("DELETE", f"/api/templates/{template_id}")

    # Transactional Email
    async def send_transactional_email(
        self,
        subscriber_email: str,
        template_id: int,
        data: dict[str, Any] | None = None,
        content_type: str = "html"
    ) -> dict[str, Any]:
        """Send a transactional email."""
        payload = {
            "subscriber_email": subscriber_email,
            "template_id": template_id,
            "data": data or {},
            "content_type": content_type
        }
        return await self._request("POST", "/api/tx", json_data=payload)

    # Media Operations
    async def get_media(self) -> dict[str, Any]:
        """Get all media files."""
        return await self._request("GET", "/api/media")

    async def upload_media(self, file_path: str, title: str | None = None) -> dict[str, Any]:
        """Upload a media file.

        Args:
            file_path: Absolute path to the file to upload
            title: Optional title for the media file (defaults to filename)

        Returns:
            Dict containing the uploaded media data including URL
        """
        import os
        from pathlib import Path

        client = self._get_client()
        url = self._build_url("/api/media")

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ListmonkAPIError(f"File not found: {file_path}")

        # Determine content type from file extension
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
        }
        ext = file_path_obj.suffix.lower()
        content_type = content_types.get(ext, 'application/octet-stream')

        # Use filename as title if not provided
        if title is None:
            title = file_path_obj.name

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Prepare multipart form data
        files = {
            'file': (file_path_obj.name, file_content, content_type)
        }
        data = {}
        if title:
            data['title'] = title

        try:
            # Create a new client without Content-Type header for multipart upload
            # The client will automatically set multipart/form-data with boundary
            upload_client = AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"token {self.config.username}:{self.config.password}",
                    "User-Agent": "Listmonk-MCP-Server/0.1.0",
                    "Accept": "application/json",
                    # No Content-Type - will be set automatically by httpx for multipart
                }
            )

            response = await upload_client.post(url, files=files, data=data)
            await upload_client.aclose()
            return await self._handle_response(response)

        except httpx.RequestError as e:
            raise ListmonkAPIError(f"Media upload failed: {str(e)}") from e

    async def update_media(self, media_id: int, title: str) -> dict[str, Any]:
        """Update media file metadata (rename).

        Args:
            media_id: ID of the media file
            title: New title for the media file
        """
        data = {"title": title}
        return await self._request("PUT", f"/api/media/{media_id}", json_data=data)

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
