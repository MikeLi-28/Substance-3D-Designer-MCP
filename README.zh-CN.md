# Substance-3D-Designer-MCP

**中文** | [English](README.md)

面向 Adobe Substance 3D Designer 的独立、安全型 Model Context Protocol Server。1.1.0 新增通用
authoring 能力，并把 MCP 运行时放在 Designer 进程外，严格隔离两套 Python 环境。

> **兼容状态：** Substance 3D Designer 16.0.3 是受支持基线。1.0.0 能力集已在该版本完成
> 真机验证；1.1.0 新增的 authoring 扩展尚未完成真机验证。

## 兼容性

| Substance Designer 版本 | 状态 |
|---|---|
| 16.0.3 | 受支持基线；1.1.0 authoring 扩展尚未完成真机验证 |
| 其他已发布的 16.x 版本 | 未验证；按运行时能力探测启用功能 |
| 更新的主版本 | 实验性且未验证 |

只有在真实 Substance Designer 安装环境中完成插件加载和 MCP 工具测试后，具体版本才会被标记为“已完整测试”。能力探测不能代替真实版本测试。

## 功能范围

- 读取 Application、Package、Graph、Selection、Node、Property 和能力矩阵。
- 搜索 Designer 当前已加载 Package 中的 Resource。
- 创建经过运行时验证的 Atomic Node，或实例化搜索结果返回的 Resource。
- 移动/删除明确节点，连接明确的运行时 Property，修改受支持的简单参数。
- 显式确认后，原地保存一个已有路径的 Package。
- 新建空 Package 和 Compositing Graph，不依赖当前选区。
- 查询运行时 Node Definition，读取包含明确连接的版本化 Graph Snapshot。
- 用真实 `SDUsage`/`SDValueUsage` metadata 创建 Output，而不是只返回一个 usage 字段。
- dry-run 并应用受限的增量 Graph Patch；检查定义、端口、类型、重复目标和环路，失败回滚。
- 导入本地 Bitmap、显式确认 Save As，并通过官方进程内 API 发布已保存 Package 为 SBSAR。

本项目不生成复杂材质配方，不爬取 Qt UI，不提供 Python/Shell 执行，不访问互联网、不上传遥测，
也不提供远程控制。

## 架构

```text
MCP Host
   | stdio
外部 Python 3.10+ MCP Server
   | 127.0.0.1 上的认证长度前缀 JSON
Designer Python Plugin
   | 命令白名单 + Qt 主线程派发
单一职责 Services + Compatibility 探测
   | 已核对的 Adobe Python API
Substance 3D Designer（真机验证版本：16.0.3）
```

外部进程绝不导入 `sd`；Bridge 只做传输；Adobe API 调用只存在于插件 Services 或兼容层。

## 安装

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\build_plugin.py
.\.venv\Scripts\python.exe scripts\install_plugin.py --target "C:\明确的\Designer用户插件目录"
```

安装脚本要求显式目标，拒绝写入 Adobe 安装核心目录，并会备份已有插件。手动 Plugin Manager
加载方法见 [installation.md](docs/installation.md)。

通用 MCP stdio 配置：

```json
{
  "mcpServers": {
    "substance-designer": {
      "command": "substance-designer-mcp",
      "args": []
    }
  }
}
```

## 工具与风险

- 只读：`sd_ping`、`sd_get_application_info`、`sd_get_capabilities`、`sd_list_packages`、
  `sd_get_active_graph`、`sd_list_graph_nodes`、`sd_get_selection`、`sd_get_node`、
  `sd_list_node_properties`、`sd_search_library`、`sd_list_node_definitions`、
  `sd_get_graph_snapshot`、`sd_validate_graph_patch`。
- 普通写入：`sd_create_node`、`sd_create_instance_node`、`sd_move_nodes`、
  `sd_connect_nodes`、`sd_disconnect_nodes`、`sd_set_node_parameter`、`sd_create_package`、
  `sd_create_graph`、`sd_open_graph`、`sd_create_graph_output`、`sd_apply_graph_patch`、
  `sd_import_bitmap`。
- 破坏性/高风险：`sd_delete_nodes`、`sd_save_package`、`sd_save_package_as`、
  `sd_export_package_sbsar`，都要求 `confirm: true`；路径必须绝对、父目录已存在，覆盖需显式开启。

不支持 Curve、Gradient 等尚未完整真机验证的复杂 SDValue，也不实现自动猜端口、任意代码执行
或静默路径覆盖。

## 配置

| 环境变量 | 默认值 |
| --- | --- |
| `SUBSTANCE_DESIGNER_MCP_SESSION_PATH` | `~/.substance-designer-mcp/session.json` |
| `SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH` | `~/.substance-designer-mcp/logs/plugin.log` |
| `SUBSTANCE_DESIGNER_MCP_CONNECT_TIMEOUT` | `5` 秒 |
| `SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT` | `5` 秒 |
| `SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT` | `30` 秒 |
| `SUBSTANCE_DESIGNER_MCP_LOG_LEVEL` | `INFO` |

必须在 Designer 导入插件前设置 Session 与插件日志路径变量，这样隔离测试不会覆盖用户的常规状态文件。

## 开发验证

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe scripts\build_plugin.py
```

SD API 事实只来自 Designer 内置 Python API Documentation。更详细的架构、协议、安全、兼容和
开发说明位于 [docs](docs/)。

## 许可证

MIT。Adobe 和 Substance 3D Designer 是 Adobe 的商标。本项目为独立开源项目，未获 Adobe
官方背书。
