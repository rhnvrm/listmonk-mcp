import httpx
import pytest

from listmonk_mcp.client import ListmonkClient
from listmonk_mcp.config import Config


@pytest.mark.asyncio
async def test_get_lists_sends_pagination_and_filters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "results": [{"id": 7, "name": "Weekly News"}],
                    "total": 588,
                    "page": 3,
                    "per_page": 500,
                }
            },
        )

    config = Config(
        url="https://listmonk.example",
        username="api-user",
        password="api-token",
        max_retries=0,
    )
    client = ListmonkClient(config)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client._client = http_client
        result = await client.get_lists(
            page=3,
            per_page=500,
            query="Weekly",
            status="active",
            minimal=True,
            tags=["newsletter", "weekly"],
            order_by="name",
            order="ASC",
        )

    assert result["data"]["total"] == 588
    assert len(requests) == 1
    params = requests[0].url.params
    assert params["page"] == "3"
    assert params["per_page"] == "500"
    assert params["query"] == "Weekly"
    assert params["status"] == "active"
    assert params["minimal"] == "true"
    assert params.get_list("tag") == ["newsletter", "weekly"]
    assert params["order_by"] == "name"
    assert params["order"] == "ASC"


@pytest.mark.asyncio
async def test_get_lists_supports_a_response_with_no_results() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": {
                    "results": [],
                    "total": 0,
                    "page": 1,
                    "per_page": 100,
                }
            },
        )

    config = Config(
        url="https://listmonk.example",
        username="api-user",
        password="api-token",
        max_retries=0,
    )
    client = ListmonkClient(config)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client._client = http_client
        result = await client.get_lists(page=1, query="missing")

    assert result["data"]["total"] == 0
    assert requests[0].url.params["per_page"] == "100"
