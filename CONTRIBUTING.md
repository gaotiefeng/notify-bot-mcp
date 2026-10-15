# Contributing

Use Python 3.11+ and uv. Run `uv sync --locked`, then `uv run --locked pytest`.
Keep provider HTTP behavior in `wecom.py` and MCP registration in `server.py`.
New providers should not change the meaning of the existing WeCom tool.

Tests must mock delivery; never add production webhook URLs or network-sending
smoke tests to CI. Cover timeout ambiguity, business rejection and secret
redaction when changing the transport. Never print on stdout in the STDIO server.

The dependency lock is committed. Update it intentionally with `uv lock` and
run the tests after any SDK upgrade. Public API changes need README examples.
