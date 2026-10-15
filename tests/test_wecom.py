import json

import httpx
import pytest

from notify_bot_mcp.wecom import NotificationError, WeComSender, validate_webhook, validate_content

URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-secret"


@pytest.mark.parametrize("url", ["", "http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a",
    "https://evil.test/cgi-bin/webhook/send?key=a", URL + "&key=b", URL + "#fragment",
    URL + "&other=x", URL.replace("test-secret", ""), URL.replace("send", "upload_media"),
    URL.replace("qyapi", "user:password@qyapi"), URL + "\n"])
def test_invalid_url_is_sanitized(url):
    with pytest.raises(NotificationError) as error:
        validate_webhook(url)
    assert "test-secret" not in str(error.value)


def test_valid_url():
    assert validate_webhook(URL) == URL


@pytest.mark.parametrize("text", ["", " \n\t", "a" * 2049, "中" * 683, "\ud800"])
def test_bad_content(text):
    with pytest.raises(NotificationError):
        validate_content(text)


def test_byte_boundary():
    validate_content("a" * 2048)
    validate_content("中" * 682 + "ab")


async def test_success_payload_and_one_request():
    requests = []
    def handler(request):
        requests.append(request)
        assert json.loads(request.content) == {"msgtype": "text", "text": {"content": "测试\n消息"}}
        return httpx.Response(200, json={"errcode": 0, "errmsg": "ok"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await WeComSender(URL, client).send("测试\n消息")
    assert result["status"] == "accepted"
    assert len(requests) == 1


@pytest.mark.parametrize("status,body,expected", [
    (200, '{"errcode":93000,"errmsg":"test-secret"}', "rejected"),
    (200, 'not json test-secret', "unknown"),
    (200, '[]', "unknown"),
    (200, '{"errcode":false}', "unknown"),
    (200, '{"errcode":"0"}', "unknown"),
    (200, '{}', "unknown"),
    (302, '', "HTTP 302"),
    (429, 'test-secret', "HTTP 429"),
    (500, 'test-secret', "HTTP 500"),
])
async def test_failures_no_retry_or_secret(status, body, expected):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=body, headers={"Location": "https://evil.test"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        with pytest.raises(NotificationError, match=expected) as error:
            await WeComSender(URL, client).send("hello")
    assert "test-secret" not in str(error.value)
    assert len(calls) == 1


async def test_timeout_is_unknown_and_not_retried():
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout(URL, request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NotificationError, match="unknown") as error:
            await WeComSender(URL, client).send("hello")
    assert "test-secret" not in str(error.value)
    assert len(calls) == 1


async def test_invalid_content_never_sends():
    def handler(request):
        pytest.fail("Unexpected outbound request")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NotificationError):
            await WeComSender(URL, client).send(" ")
