import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError
from typer.testing import CliRunner

import listmonk_mcp.server as server
from listmonk_mcp.client import ListmonkAPIError, ListmonkClient
from listmonk_mcp.config import Config, load_config
from listmonk_mcp.exceptions import safe_execute_async


def test_cli_help_and_version_work_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("URL", "USERNAME", "PASSWORD"):
        monkeypatch.delenv(f"LISTMONK_MCP_{name}", raising=False)
    runner = CliRunner()
    for arg in ("--help", "--version"):
        result = runner.invoke(server.cli_app, [arg])
        assert result.exit_code == 0, result.output
    assert "0.2.0" in runner.invoke(server.cli_app, ["--version"]).output


def test_explicit_env_file_is_respected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("URL", "USERNAME", "PASSWORD"):
        monkeypatch.delenv(f"LISTMONK_MCP_{name}", raising=False)
    env = tmp_path / "custom.env"
    env.write_text(
        "LISTMONK_MCP_URL=https://example.com\nLISTMONK_MCP_USERNAME=api\nLISTMONK_MCP_PASSWORD=secret\n"
    )
    cfg = load_config(str(env))
    assert cfg.url == "https://example.com"
    assert "secret" not in repr(cfg)
    with pytest.raises(ValueError, match="not found"):
        load_config(str(tmp_path / "missing.env"))


def test_configuration_errors_hide_credentials() -> None:
    with pytest.raises(ValidationError) as exc:
        Config(url="invalid", username="api", password="very-secret", timeout=-1)
    assert "very-secret" not in str(exc.value)


async def test_production_server_retains_resources_and_tools() -> None:
    production = server.create_production_server()
    assert production is server.mcp
    assert len(await production.list_tools()) >= 70
    assert len(await production.list_resources()) >= 5
    assert len(await production.list_resource_templates()) >= 5


async def test_failed_connect_closes_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = Config(
        url="http://127.0.0.1:1", username="api", password="secret", max_retries=0
    )
    c = ListmonkClient(cfg)
    health = AsyncMock(side_effect=ListmonkAPIError("unreachable"))
    monkeypatch.setattr(c, "health_check", health)
    with pytest.raises(ListmonkAPIError):
        await c.connect()
    assert c._client is None


@pytest.mark.parametrize(
    "method,expected", [("GET", 3), ("POST", 1), ("PUT", 1), ("DELETE", 1)]
)
async def test_only_reads_are_retried(
    method: str, expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        raise httpx.ReadTimeout("response lost", request=request)

    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    cfg = Config(
        url="https://example.com", username="api", password="secret", max_retries=2
    )
    c = ListmonkClient(cfg)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        c._client = http
        with pytest.raises(ListmonkAPIError):
            await c._request(method, "/api/campaigns")
    assert count == expected


async def test_api_errors_are_mcp_tool_errors() -> None:
    with pytest.raises(ToolError, match="Forbidden"):
        await safe_execute_async(
            AsyncMock(side_effect=ListmonkAPIError("Forbidden", status_code=403))
        )


async def test_unexpected_errors_do_not_leak_tracebacks_to_client() -> None:
    with pytest.raises(ToolError) as exc:
        await safe_execute_async(AsyncMock(side_effect=RuntimeError("internal secret")))
    assert "internal secret" not in str(exc.value)
    assert "Traceback" not in str(exc.value)
