# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-07-16

### Added

- 通过官方 API 新建空 Package 和 `SDSBSCompGraph`，并用结构化引用返回结果。
- 运行时 Node Definition 查询和版本化 Graph Snapshot，包含属性、连接和 preset。
- 正确写入 `SDUsage` / `SDValueUsage` 的通用 Output node 创建工具。
- 版本化 Graph Patch dry-run/apply：定义、资源、端口、类型、重复目标、环路和参数预检，
  运行时失败时回滚本次创建的全部节点。
- 受限 Bitmap 导入、确认式 Save As 和显式发布设置的进程内 SBSAR export。

### Security

- 所有新动作继续走命令白名单、插件侧校验、主线程派发和串行写入。
- 不加入材质 recipe、任意 Python、Shell、UI 抓取、端口猜测、网络访问或遥测。
- 文件路径必须绝对、父目录已存在；覆盖必须显式开启，Save As/SBSAR 还需 `confirm: true`。

### Compatibility

- Substance 3D Designer 16.0.3 是受支持基线。
- 1.1.0 新增 authoring 能力尚未完成真机验证。

## [1.0.0] - 2026-07-14

### Added

- 首个公开稳定版本。
- 初始外部 MCP server、认证回环 bridge、Designer 插件、聚焦服务、兼容性检测、测试、文档和打包。
- 支持 Designer 16.0.3 上的 Graph、选择、节点、属性、连接、参数和 Package 保存工作流。

### Fixed

- 重复连接按稳定节点 identifier 判断，不依赖 Adobe Python 包装对象身份。
- Package 卸载后不再读取已失效的 API handle。

### Compatibility

- Substance 3D Designer 16.0.3 是唯一完成真机验证的版本。
- 其他已发布的 Designer 16.x 版本预期兼容，但尚未逐版本测试；可用能力由运行时探测决定。
- 尚未发布的未来版本当前无法测试，项目不声明其受支持或已经验证。
- 运行时明确区分 `verified`、`untested`、`experimental` 和 `unsupported`，能力探测不等于
  真实版本验证。
