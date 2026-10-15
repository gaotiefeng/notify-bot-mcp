"""WeCom transport. Never include credentials or upstream bodies in errors."""
from urllib.parse import parse_qs, urlsplit

import httpx


class NotificationError(Exception):
    """A sanitized error safe to expose to the MCP client."""


def validate_webhook(value: str) -> str:
    try:
        url = urlsplit(value)
        query = parse_qs(url.query, keep_blank_values=True)
        valid = (
            url.scheme == "https"
            and url.netloc == "qyapi.weixin.qq.com"
            and url.path == "/cgi-bin/webhook/send"
            and not url.fragment
            and set(query) == {"key"}
            and len(query["key"]) == 1
            and bool(query["key"][0].strip())
            and not any(c.isspace() or ord(c) < 32 for c in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise NotificationError("Invalid WECOM_WEBHOOK_URL; use the official HTTPS group bot send endpoint with one key.")
    return value


def validate_content(content: str) -> None:
    if not isinstance(content, str) or not content.strip():
        raise NotificationError("content must contain non-whitespace text.")
    try:
        size = len(content.encode("utf-8"))
    except UnicodeError:
        raise NotificationError("content must be valid UTF-8 text.") from None
    if size > 2048:
        raise NotificationError("content exceeds the 2048-byte UTF-8 text limit.")


class WeComSender:
    def __init__(self, webhook: str, client: httpx.AsyncClient):
        self._webhook = validate_webhook(webhook)
        self._client = client

    async def send(self, content: str) -> dict:
        validate_content(content)
        try:
            response = await self._client.post(
                self._webhook,
                json={"msgtype": "text", "text": {"content": content}},
                follow_redirects=False,
            )
        except httpx.RequestError:
            raise NotificationError("Transport failure; delivery is unknown. Check the group before retrying.") from None
        if response.status_code != 200:
            raise NotificationError(f"WeCom HTTP {response.status_code}; delivery is unconfirmed. No automatic retry.")
        try:
            data = response.json()
        except ValueError:
            raise NotificationError("Invalid WeCom response; delivery is unknown.") from None
        if not isinstance(data, dict) or type(data.get("errcode")) is not int:
            raise NotificationError("Missing or invalid WeCom errcode; delivery is unknown.")
        if data["errcode"] != 0:
            raise NotificationError(f"WeCom rejected the message (errcode={data['errcode']}).")
        return {"status": "accepted", "provider": "wecom", "errcode": 0,
                "message": "WeCom accepted the message; this is not a read receipt."}
