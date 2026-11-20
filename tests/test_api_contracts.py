"""Request contracts checked against Listmonk v7.0.0-beta.2 handlers."""

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from listmonk_mcp.client import ListmonkAPIError, ListmonkClient


async def test_template_update_preserves_transactional_subject(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "id": 5,
        "name": "Receipt",
        "type": "tx",
        "subject": "Order {{ .Tx.Data.id }}",
        "body": "Old",
        "body_source": "visual source",
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": {**original, "body": "New"}})
    await client.update_template(5, body="New")
    payload = json.loads(httpx_mock.get_requests()[1].content)
    assert payload["subject"] == original["subject"]
    assert payload["type"] == "tx"
    assert payload["name"] == "Receipt"
    assert "body_source" not in payload


async def test_template_subject_override_and_default_endpoint(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        json={
            "data": {"name": "Receipt", "type": "tx", "subject": "Old", "body": "HTML"}
        }
    )
    httpx_mock.add_response(json={"data": {"id": 5}})
    httpx_mock.add_response(json={"data": True})
    await client.update_template(5, subject="New", is_default=True)
    requests = httpx_mock.get_requests()
    assert json.loads(requests[1].content)["subject"] == "New"
    assert requests[2].method == "PUT"
    assert requests[2].url.path == "/api/templates/5/default"


async def test_create_transactional_template(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": {"id": 5}})
    await client.create_template("Receipt", "Body", type="tx", subject="Order received")
    assert json.loads(httpx_mock.get_request().content)["subject"] == "Order received"


async def test_campaign_test_merges_full_saved_payload(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "subject": "News",
        "lists": [{"id": 7}],
        "body": "Hello",
        "from_email": "news@example.com",
        "content_type": "html",
        "messenger": "email",
        "template_id": 3,
        "headers": [{"X-Test": "yes"}],
        "media": [{"id": 9}],
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.test_campaign(42, ["reader@example.com"])
    req = httpx_mock.get_requests()[1]
    payload = json.loads(req.content)
    assert req.url.path == "/api/campaigns/42/test"
    assert payload == {
        **original,
        "lists": [7],
        "media": [9],
        "subscribers": ["reader@example.com"],
    }


async def test_campaign_update_preserves_other_fields(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "subject": "Original",
        "lists": [{"id": 7}],
        "body": "Hello",
        "from_email": "news@example.com",
        "content_type": "html",
        "messenger": "email",
        "tags": ["weekly"],
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.update_campaign(42, subject="New")
    assert json.loads(httpx_mock.get_requests()[1].content) == {
        **original,
        "subject": "New",
        "lists": [7],
    }


async def test_schedule_saves_send_time_before_changing_status(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        json={
            "data": {
                "name": "Weekly",
                "subject": "News",
                "lists": [{"id": 7}],
                "body": "Hi",
                "messenger": "email",
            }
        }
    )
    httpx_mock.add_response(json={"data": True})
    httpx_mock.add_response(json={"data": True})
    await client.schedule_campaign(42, "2030-01-01T12:00:00Z")
    requests = httpx_mock.get_requests()
    assert requests[1].url.path == "/api/campaigns/42"
    assert json.loads(requests[1].content)["send_at"] == "2030-01-01T12:00:00Z"
    assert requests[2].url.path == "/api/campaigns/42/status"
    assert json.loads(requests[2].content) == {"status": "scheduled"}


async def test_subscriber_updates_preserve_memberships(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": True})
    await client.update_subscriber(7, name="New")
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    assert json.loads(request.content) == {"name": "New"}


async def test_explicit_empty_lists_clear_memberships(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": True})
    await client.patch_subscriber(7, lists=[])
    assert json.loads(httpx_mock.get_request().content) == {"lists": []}


async def test_list_update_preserves_other_fields(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "type": "private",
        "optin": "double",
        "tags": ["news"],
        "status": "active",
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.update_list(7, description="New")
    assert json.loads(httpx_mock.get_requests()[1].content) == {
        **original,
        "description": "New",
    }


async def test_preview_uses_form_fields_and_returns_html(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        text="<html>Preview</html>", headers={"Content-Type": "text/html"}
    )
    result = await client.preview_template_body('<p>{{ template "content" . }}</p>')
    req = httpx_mock.get_request()
    assert req.headers["content-type"] == "application/x-www-form-urlencoded"
    assert b"template_type=campaign" in req.content
    assert result == {"data": "<html>Preview</html>"}


@pytest.mark.parametrize(
    "value", ["hello", ["Sender <sender@example.com>"], False, None, {"enabled": True}]
)
async def test_per_key_settings_sends_raw_json_value(
    client: ListmonkClient, httpx_mock: HTTPXMock, value: object
) -> None:
    httpx_mock.add_response(json={"data": True})
    await client.update_setting("app.from_email", value)
    assert json.loads(httpx_mock.get_request().content) == value


async def test_v7_analytics_date_interval_and_unique(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": []})
    await client.get_campaign_analytics(
        "views", [7, 8], "2026-01-01", "2026-12-31", interval="week", unique=True
    )
    params = httpx_mock.get_request().url.params
    assert params.get_list("id") == ["7", "8"]
    assert params["from"] == "2026-01-01"
    assert params["interval"] == "week"
    assert params["unique"] == "true"


@pytest.mark.parametrize(
    "method,args,path",
    [
        (
            "gc_campaign_analytics",
            ("views", "2026-01-01T00:00:00Z"),
            "/api/maintenance/analytics/views",
        ),
        (
            "gc_unconfirmed_subscriptions",
            ("2026-01-01T00:00:00Z",),
            "/api/maintenance/subscriptions/unconfirmed",
        ),
    ],
)
async def test_maintenance_requires_before_date(
    client: ListmonkClient, httpx_mock: HTTPXMock, method: str, args: tuple, path: str
) -> None:
    httpx_mock.add_response(json={"data": True})
    await getattr(client, method)(*args)
    req = httpx_mock.get_request()
    assert req.url.path == path
    assert req.url.params["before_date"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize("method", ["delete_bounces", "blocklist_bounced_subscribers"])
async def test_empty_bounce_ids_never_implicitly_target_everyone(
    client: ListmonkClient, method: str
) -> None:
    with pytest.raises(ValueError, match="all=True"):
        await getattr(client, method)([])


async def test_blocklist_bounces_uses_query_ids(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": True})
    await client.blocklist_bounced_subscribers([7, 8])
    assert httpx_mock.get_request().url.params.get_list("id") == ["7", "8"]
    assert httpx_mock.get_request().content == b""


async def test_import_multipart_upload(
    client: ListmonkClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    csv = tmp_path / "subscribers.csv"
    csv.write_text("email,name\nreader@example.com,Reader\n")
    httpx_mock.add_response(json={"data": True})
    await client.import_subscribers(
        str(csv), list_ids=[7], subscription_status="unconfirmed"
    )
    req = httpx_mock.get_request()
    assert "multipart/form-data; boundary=" in req.headers["content-type"]
    assert b'"lists": [7]' in req.content
    assert b'"subscription_status": "unconfirmed"' in req.content
    assert b"reader@example.com" in req.content


async def test_non_json_http_error_is_reported(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(status_code=502, text="Bad gateway")
    with pytest.raises(ListmonkAPIError, match="HTTP 502") as exc:
        await client.health_check()
    assert exc.value.status_code == 502


async def test_v6_subscriber_fallback_preserves_required_fields(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(status_code=404, json={"message": "Unknown API endpoint"})
    httpx_mock.add_response(
        json={
            "data": {
                "email": "reader@example.com",
                "name": "Original",
                "status": "enabled",
                "attribs": {"city": "Pune"},
                "lists": [{"id": 7}],
            }
        }
    )
    httpx_mock.add_response(json={"data": True})
    await client.update_subscriber(7, name="New")
    req = httpx_mock.get_requests()[-1]
    assert req.method == "PUT"
    assert json.loads(req.content) == {
        "email": "reader@example.com",
        "name": "New",
        "status": "enabled",
        "attribs": {"city": "Pune"},
        "lists": [7],
    }


async def test_v7_media_tags(client: ListmonkClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"data": {"id": 7, "tags": ["news"]}})
    await client.update_media_tags(7, ["news"])
    req = httpx_mock.get_request()
    assert req.url.path == "/api/media/7"
    assert json.loads(req.content) == {"tags": ["news"]}


async def test_unsupported_media_title_does_not_report_success(
    client: ListmonkClient,
) -> None:
    with pytest.raises(ValueError, match="does not support"):
        await client.update_media(7, "New title")


async def test_campaign_create_sends_from_email(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": {"id": 42}})
    await client.create_campaign(
        "Weekly", "News", [7], from_email="Shop Team <shop@example.com>"
    )
    payload = json.loads(httpx_mock.get_request().content)
    assert payload["from_email"] == "Shop Team <shop@example.com>"


async def test_campaign_create_without_from_email_uses_server_default(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": {"id": 42}})
    await client.create_campaign("Weekly", "News", [7])
    assert "from_email" not in json.loads(httpx_mock.get_request().content)


async def test_campaign_update_overrides_from_email(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "subject": "News",
        "lists": [{"id": 7}],
        "body": "Hello",
        "from_email": "news@example.com",
        "content_type": "html",
        "messenger": "email",
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.update_campaign(42, from_email="Shop Team <shop@example.com>")
    assert json.loads(httpx_mock.get_requests()[1].content) == {
        **original,
        "from_email": "Shop Team <shop@example.com>",
        "lists": [7],
    }


async def test_campaign_create_sends_messenger_and_altbody(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": {"id": 42}})
    await client.create_campaign(
        "Weekly", "News", [7], messenger="bulk", altbody="Plain news"
    )
    payload = json.loads(httpx_mock.get_request().content)
    assert payload["messenger"] == "bulk"
    assert payload["altbody"] == "Plain news"


async def test_campaign_create_defaults_to_email_messenger_without_altbody(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json={"data": {"id": 42}})
    await client.create_campaign("Weekly", "News", [7])
    payload = json.loads(httpx_mock.get_request().content)
    assert payload["messenger"] == "email"
    assert "altbody" not in payload


async def test_campaign_update_overrides_messenger_and_altbody(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "subject": "News",
        "lists": [{"id": 7}],
        "body": "<p>Hello</p>",
        "altbody": "Hello",
        "from_email": "news@example.com",
        "content_type": "html",
        "messenger": "email",
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.update_campaign(42, messenger="bulk", altbody="Hello again")
    assert json.loads(httpx_mock.get_requests()[1].content) == {
        **original,
        "messenger": "bulk",
        "altbody": "Hello again",
        "lists": [7],
    }


async def test_campaign_update_keeps_messenger_and_altbody_when_omitted(
    client: ListmonkClient, httpx_mock: HTTPXMock
) -> None:
    original = {
        "name": "Weekly",
        "subject": "News",
        "lists": [{"id": 7}],
        "body": "<p>Hello</p>",
        "altbody": "Hello",
        "content_type": "html",
        "messenger": "bulk",
    }
    httpx_mock.add_response(json={"data": original})
    httpx_mock.add_response(json={"data": True})
    await client.update_campaign(42, subject="Fresh news")
    payload = json.loads(httpx_mock.get_requests()[1].content)
    assert payload["messenger"] == "bulk"
    assert payload["altbody"] == "Hello"
    assert payload["subject"] == "Fresh news"
