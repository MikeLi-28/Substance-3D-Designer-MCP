# Compatibility

## Version status

The following status model applies to project release `1.1.0`.

| Substance Designer version | Verification status | Compatibility status | Startup policy |
| --- | --- | --- | --- |
| 16.0.3 | `verified` | `supported` | Starts normally; capabilities are still probed |
| Other released 16.x versions | `untested` | `capability_detected` | Starts when required capabilities exist and reports a warning |
| Unknown newer major versions | `untested` | `experimental` | May start experimentally through capability detection and reports a warning |
| Versions below 16 or unrecognized versions | `untested` | `unsupported` | Not claimed as supported; capability results remain available for diagnosis |

Designer 16.0.3 is the only version fully tested on a real installation. Other released 16.x
versions are expected to be compatible but have not been individually tested. Future Designer
versions are not currently testable and are not claimed as supported or verified.

## Compatibility mechanism

The compatibility layer combines three separate mechanisms:

```text
Version detection
+
Runtime capability detection
+
Compatibility adapter
```

Version detection classifies the running Designer version. Runtime capability detection checks the
actual managers, graph objects, node methods, and package save methods exposed by that process. The
Compatibility adapter contains version and API differences without spreading them through the
bridge or MCP tools. A missing API disables only the affected capability; tools that require it
return `UNSUPPORTED_CAPABILITY` without crashing the whole plugin.

Capability detection means the project can identify whether a required API is present.

It does not prove that an untested Designer version is fully compatible.

能力探测只能确认当前运行环境中是否存在所需 API，不能证明一个未经测试的 Designer 版本完全兼容。

Every compatibility result includes `designer_version`, `verification_status`,
`compatibility_status`, `verified_versions`, `warning`, and the per-feature capability map.
Availability and real-machine verification remain separate fields.

## Release coverage

The `1.0.0` capability baseline is real-machine verified on Designer 16.0.3. Authoring extensions
introduced in `1.1.0` are available on that version but are reported as not real-machine verified.
The capability response exposes this distinction per feature.
