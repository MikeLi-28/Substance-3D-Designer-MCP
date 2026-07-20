# Contributing

Contributions must preserve the runtime and security boundaries documented in
[`docs/architecture.md`](docs/architecture.md) and [`docs/security-model.md`](docs/security-model.md).

1. Create a focused branch.
2. Use Adobe's bundled Python API documentation as the only source for Designer API claims.
3. Add a failing test, observe the expected failure, then implement the smallest passing change.
4. Run `pytest`, `ruff check .`, `ruff format --check .`, `mypy src`, package build, plugin build, and
   release verification.
5. Update compatibility claims only when they are supported by matching real-machine evidence.

Do not submit copied third-party Substance MCP code, arbitrary execution tools, UI scraping,
telemetry, or undocumented Adobe API assumptions.
