import os
from pathlib import Path
import subprocess
import sys

import httpx
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from notify_bot_mcp.server import create_server

URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock-secret"


def factory(**kwargs):
    return httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"errcode": 0})
    ), **kwargs)


async def test_mcp_discovery_and_mock_send():
    async with Client(create_server(URL, factory)) as client:
        tools = await client.list_tools()
        tool = tools.tools[0] if hasattr(tools, "tools") else tools[0]
        assert tool.name == "send_message"
        assert tool.input_schema["required"] == ["content"]
        assert tool.annotations.idempotent_hint is False
        result = await client.call_tool("send_message", {"content": "测试"})
        assert not result.is_error
        assert "accepted" in str(result)
        result = await client.call_tool("send_message", {"content": " "})
        assert result.is_error
        assert "mock-secret" not in str(result)


async def test_stdio_roundtrip_without_sending():
    env = {**os.environ, "WECOM_WEBHOOK_URL": URL,
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "notify_bot_mcp"], env=env)
    async with Client(params) as client:
        tools = await client.list_tools()
        assert "send_message" in str(tools)
        result = await client.call_tool("send_message", {"content": ""})
        assert result.is_error
        assert "mock-secret" not in str(result)


def test_missing_config_exits_without_stdout():
    env = {**os.environ, "WECOM_WEBHOOK_URL": "",
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    result = subprocess.run([sys.executable, "-m", "notify_bot_mcp"], env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "WECOM_WEBHOOK_URL" in result.stderr
