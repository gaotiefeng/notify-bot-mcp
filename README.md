# notify-bot-mcp

An MCP server for sending notifications to chat bots. Starting with WeCom.

通过 MCP 向**一个预先配置的企业微信群机器人**发送纯文本消息。Python 3.11+，官方 MCP Python SDK 2.3.0，STDIO 传输。无需模型 API Key。

## 安装与运行

安装 [uv](https://docs.astral.sh/uv/)，克隆本仓库后执行：

```bash
uv sync --locked
cp .env.example .env
```

在本地 `.env` 中填写机器人 Webhook（不要提交真实 key），运行：

```bash
uv run --env-file .env notify-bot-mcp
```

这是 STDIO 服务，会等待 MCP 客户端输入，不会打开网页或自动发送消息。`.env` 由 `uv --env-file` 显式加载；Python 服务自身只读取环境变量。

## MCP 客户端配置

支持 `mcpServers` 配置的客户端可参考以下示例；将路径替换成实际绝对路径。若图形客户端找不到 uv，使用 `command -v uv` 返回的绝对路径。

```json
{
  "mcpServers": {
    "notify-bot": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/notify-bot-mcp",
        "run", "--locked", "--env-file", "/absolute/path/notify-bot-mcp/.env",
        "notify-bot-mcp"
      ]
    }
  }
}
```

每个服务实例对应一个机器人。确保用户知道配置的是哪个群，并在客户端确认目标与消息内容后调用工具。工具描述和 annotations 是提示，不是服务器端权限校验；本版本不提供公网端点。

## 工具

`send_message(content: str)` 只接收内容，不接受任意 URL。

```json
{"content": "发布完成：新增用户导出功能。"}
```

成功返回 `status: accepted`、`provider: wecom` 和 `errcode: 0`，表示平台受理，**不是已读回执**。失败返回 MCP 工具错误。空白或超过 2048 UTF-8 字节的文本拒绝发送；不会自动截断或拆分。

## 行为边界

- 仅允许 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...`，不跟随重定向。
- 单次 HTTP 操作配置 10 秒超时；没有自动重试、去重或持久化队列。
- 超时、网络错误、异常响应意味着投递可能不确定：先检查群消息，再决定是否重试。
- 不记录内容、Webhook 或平台原始错误正文。日志走 stderr，stdout 留给协议。
- HTTP 客户端不读取代理环境变量（`trust_env=False`），需要直连企业微信端点。
- 暂不支持 Markdown、@成员、文件、多群、钉钉或飞书。

## 开发和测试

```bash
uv sync --locked
uv run --locked pytest
```

测试使用 httpx MockTransport，覆盖发送载荷、UTF-8 边界、平台错误、超时、重定向、配置与密钥脱敏，并验证 MCP 内存会话及真实 STDIO 子进程。STDIO 测试仅提交无效内容，不向企业微信发送请求。

真实群测试需由使用者配置自己的测试机器人，并明确发送内容。当前模拟验证不代表真实平台联调已完成。

```text
src/notify_bot_mcp/
  server.py   MCP 工具注册与入口
  wecom.py    校验、HTTP 发送、响应处理
tests/        发送层与 MCP 协议测试
```

## 参考与许可

- [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [企业微信群机器人文档](https://developer.work.weixin.qq.com/document/path/91770)

MIT License. 本项目为独立开源工具，不是企业微信官方产品。仓库源码可本地安装；尚未声明在 PyPI 发布。
