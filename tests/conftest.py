from collections.abc import AsyncIterator

import httpx
import pytest

from listmonk_mcp.client import ListmonkClient
from listmonk_mcp.config import Config


@pytest.fixture
async def client() -> AsyncIterator[ListmonkClient]:
    config = Config(
        url="https://listmonk.example",
        username="api",
        password="test-token",
        max_retries=0,
    )
    c = ListmonkClient(config)
    async with httpx.AsyncClient() as http:
        c._client = http
        yield c
