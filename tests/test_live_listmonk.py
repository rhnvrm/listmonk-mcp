"""Opt-in integration tests. Run only against a disposable Listmonk installation.

LISTMONK_TEST_URL=http://127.0.0.1:19000
LISTMONK_TEST_ADMIN_USER=test-admin
LISTMONK_TEST_ADMIN_PASSWORD=test-password
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from aiosmtpd.controller import Controller
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from listmonk_mcp.client import ListmonkClient
from listmonk_mcp.config import Config

pytestmark = pytest.mark.skipif(
    not os.environ.get("LISTMONK_TEST_URL"),
    reason="Requires a disposable Listmonk instance",
)


@pytest.fixture
async def live_client() -> AsyncIterator[ListmonkClient]:
    url = os.environ["LISTMONK_TEST_URL"]
    async with httpx.AsyncClient(base_url=url, follow_redirects=True) as admin:
        await admin.post(
            "/admin/login",
            data={
                "username": os.environ["LISTMONK_TEST_ADMIN_USER"],
                "password": os.environ["LISTMONK_TEST_ADMIN_PASSWORD"],
            },
        )
        response = await admin.get("/api/users")
        response.raise_for_status()
        user = response.json()["data"][0]
        role_id = user.get("user_role_id") or user["user_role"]["id"]
        username = f"mcp-test-{uuid4().hex[:8]}"
        response = await admin.post(
            "/api/users",
            json={
                "username": username,
                "name": username,
                "type": "api",
                "status": "enabled",
                "user_role_id": role_id,
            },
        )
        response.raise_for_status()
        api = response.json()["data"]
        config = Config(
            url=url, username=username, password=api["password"], max_retries=0
        )
        try:
            async with ListmonkClient(config) as client:
                yield client
        finally:
            await admin.delete(f"/api/users/{api['id']}")


async def test_live_campaign_workflow(
    live_client: ListmonkClient, tmp_path: Path
) -> None:
    c = live_client
    lst = (
        await c.create_list("MCP integration", type="private", tags=["integration"])
    )["data"]
    lid = lst["id"]
    await c.update_list(lid, description="Preserve original fields")
    assert (await c.get_list(lid))["data"]["type"] == "private"
    found = (await c.get_lists(query="MCP integration", per_page=1))["data"]
    assert found["total"] >= 1
    sub = (
        await c.create_subscriber(
            f"mcp-{uuid4().hex[:8]}@example.com",
            "Original",
            lists=[lid],
            preconfirm_subscriptions=True,
        )
    )["data"]
    sid = sub["id"]
    await c.update_subscriber(sid, name="Updated")
    updated = (await c.get_subscriber(sid))["data"]
    assert updated["name"] == "Updated"
    assert lid in [item["id"] for item in updated["lists"]]
    await c.get_subscriber_activity(sid)
    await c.get_subscriber_bounces(sid)
    template = (
        await c.create_template(
            "MCP tx", "<p>Thanks</p>", type="tx", subject="Original"
        )
    )["data"]
    tid = template["id"]
    await c.update_template(tid, body="<p>Updated</p>")
    assert (await c.get_template(tid))["data"]["subject"] == "Original"
    await c.update_template(tid, subject="Updated")
    assert (await c.get_template(tid))["data"]["subject"] == "Updated"
    preview = await c.preview_template_body('<html>{{ template "content" . }}</html>')
    assert "<html" in preview["data"].lower()
    campaign = (
        await c.create_campaign(
            "MCP campaign", "Original", [lid], body="<p>Hello</p>", content_type="html"
        )
    )["data"]
    cid = campaign["id"]
    await c.update_campaign(cid, subject="Updated")
    saved = (await c.get_campaign(cid))["data"]
    assert saved["subject"] == "Updated"
    assert saved["body"] == "<p>Hello</p>"
    assert saved["messenger"] == "email"
    await c.get_campaign_preview(cid)
    date = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    await c.schedule_campaign(cid, date)
    scheduled = (await c.get_campaign(cid))["data"]
    assert scheduled["status"] == "scheduled"
    assert scheduled["send_at"] is not None
    await c.change_campaign_status(cid, "draft")
    await c.get_campaign_analytics(
        "views", [cid], "2020-01-01", "2030-01-01", interval="week", unique=True
    )
    # Use an in-process mail sink; no mail leaves this disposable instance.
    messages: list[bytes] = []

    class Sink:
        async def handle_DATA(self, server, session, envelope):
            messages.append(envelope.content)
            return "250 OK"

    smtp = Controller(
        Sink(),
        hostname="127.0.0.1",
        port=int(os.environ.get("LISTMONK_TEST_SMTP_PORT", "11025")),
    )
    smtp.start()
    try:
        settings = (await c.get_settings())["data"]
        servers = settings["smtp"]
        servers[0].update(
            {
                "host": "127.0.0.1",
                "port": smtp.port,
                "auth_protocol": "none",
                "tls_type": "none",
                "username": "",
                "password": "",
                "enabled": True,
            }
        )
        await c.update_setting("smtp", servers)
        # Listmonk schedules a reload 500ms after a settings update.
        await asyncio.sleep(2)
        await c.test_campaign(cid, [sub["email"]])
        for _ in range(50):
            if messages:
                break
            await asyncio.sleep(0.1)
        assert messages, "Campaign test did not reach the local SMTP sink"
        assert sub["email"].encode() in messages[0]
        await c.send_transactional_email(sub["email"], tid)
        for _ in range(50):
            if len(messages) >= 2:
                break
            await asyncio.sleep(0.1)
        assert len(messages) >= 2, "Transactional message did not reach the SMTP sink"
    finally:
        smtp.stop()
    csv = tmp_path / "subscribers.csv"
    csv.write_text(f"email,name\nimport-{uuid4().hex[:8]}@example.com,Imported\n")
    await c.import_subscribers(
        str(csv), list_ids=[lid], subscription_status="unconfirmed"
    )
    for _ in range(50):
        status = (await c.get_import_status())["data"]
        if status.get("status") != "importing":
            break
        await asyncio.sleep(0.1)
    await c.get_import_logs()
    image = tmp_path / "mcp.svg"
    image.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>'
    )
    media = (await c.upload_media(str(image)))["data"]
    mid = media["id"]
    media_page = (await c.get_media())["data"]
    assert any(item["id"] == mid for item in media_page["results"])
    about = await c.get_about_info()
    about = about.get("data", about)
    if about["version"].lstrip("v").startswith("7."):
        tagged = (await c.update_media_tags(mid, ["integration"]))["data"]
        assert "integration" in tagged["tags"]
    await c.delete_media(mid)
    await c.get_bounces()
    await c.get_dashboard_counts()
    await c.get_dashboard_charts()
    await c.get_about_info()
    settings = (await c.get_settings())["data"]
    # Preserve each server version's native string/array representation.
    await c.update_setting("app.from_email", settings["app.from_email"])
    await c.gc_campaign_analytics("views", "2000-01-01T00:00:00Z")
    await c.gc_unconfirmed_subscriptions("2000-01-01T00:00:00Z")
    await c.delete_campaign(cid)
    await c.delete_template(tid)
    await c.delete_subscriber(sid)
    await c.delete_list(lid)


async def test_live_mcp_stdio_tools_and_resources(live_client: ListmonkClient) -> None:
    cfg = live_client.config
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "listmonk_mcp.server"],
        env={
            **os.environ,
            "LISTMONK_MCP_URL": cfg.url,
            "LISTMONK_MCP_USERNAME": cfg.username,
            "LISTMONK_MCP_PASSWORD": cfg.password,
        },
    )
    async with asyncio.timeout(30):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert {
                    "test_campaign",
                    "search_mailing_lists",
                    "update_template",
                    "get_campaign_analytics",
                } <= names
                result = await session.call_tool(
                    "get_mailing_lists", {"page": 1, "per_page": 2}
                )
                assert not result.isError
                media = await session.call_tool(
                    "get_media_list", {"page": 1, "per_page": 2}
                )
                assert not media.isError
                resources = await session.list_resources()
                assert "listmonk://lists" in {str(r.uri) for r in resources.resources}
                templates = await session.list_resource_templates()
                assert "listmonk://subscriber/{subscriber_id}" in {
                    t.uriTemplate for t in templates.resourceTemplates
                }
                resource = await session.read_resource("listmonk://lists")
                assert resource.contents
                error = await session.call_tool(
                    "get_campaign", {"campaign_id": 2147483647}
                )
                assert error.isError
