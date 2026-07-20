# Security Policy

## Supported versions

Security fixes are provided for the latest released project version. This policy refers to
`substance-designer-mcp` releases, not to Adobe application compatibility. Designer 16.0.3 is the
only real-machine-verified Designer version; other released 16.x versions are expected compatible
but not individually tested, and future versions are not claimed as supported or verified.

## Reporting a vulnerability

Do not open a public issue for token disclosure, authentication bypass, path overwrite, arbitrary
code execution, or remote-listener findings. Use the repository's private security advisory
channel and include reproduction steps, affected version, impact, and any proposed mitigation.

The project intentionally exposes no arbitrary Python, shell, terminal, or remote internet control.
The Designer bridge must bind only to `127.0.0.1`, authenticate before command execution, redact its
token, and require confirmation for destructive operations.
