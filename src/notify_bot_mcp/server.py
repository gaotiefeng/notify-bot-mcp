"""STDIO entry point; stdout belongs exclusively to MCP."""
import logging
import os
import sys
from collections.abc import Callable

import httpx
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .wecom import NotificationError, WeComSender, validate_webhook


def create_server(webhook: str, client_factory: Callable = httpx.AsyncClient) -> MCPServer:
    webhook = validate_webhook(webhook)
    server = MCPServer(
        "notify-bot-mcp", version="0.1.0",
        instructions="Send to the configured WeCom group only when the user explicitly requests it. Sending is an external side effect. Do not automatically retry uncertain results.",
    )

    @server.tool(
        name="send_message",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                                    idempotentHint=False, openWorldHint=True),
    )
    async def send_message(content: str) -> dict:
        """Send UTF-8 plain text (max 2048 bytes) to the configured WeCom group. Requires explicit user intent to send. Accepted does not mean read. Never automatically retry unknown delivery."""
        async with client_factory(timeout=10.0, follow_redirects=False, trust_env=False) as client:
            return await WeComSender(webhook, client).send(content)

    return server


def main() -> None:
    # HTTPX logs request URLs at INFO; never expose webhook credentials there.
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        server = create_server(os.environ.get("WECOM_WEBHOOK_URL", ""))
    except NotificationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    server.run(transport="stdio")
