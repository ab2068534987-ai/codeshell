# CodeShell

CodeShell 是一个运行在终端里的 AI coding assistant。它支持多模型 provider、工具调用、MCP、会话恢复、权限控制、上下文管理、自动压缩、已应用 diff 展示、Skill 和子 Agent 等能力。

## 功能特性

- 终端交互界面：基于 Textual 的 TUI，直接在命令行内使用。
- 多模型接入：支持 `anthropic`、`openai`、`openai-compat` 协议。
- 工具调用：支持文件读写、搜索、命令执行、任务管理、worktree 等常用 coding agent 能力。
- MCP 扩展：可在配置文件中接入外部 MCP server。
- 会话管理：支持查看历史会话、恢复会话和新建会话。
- 上下文管理：显示上下文窗口使用量，并在接近阈值时进行压缩。
- 权限与沙箱：支持权限模式、规则和 sandbox 控制。
- Diff 展示：文件修改会自动应用，并在完成后展示已应用 diff。
- Skill：支持通过 skill 扩展固定工作流和专项能力。

## 环境要求

- Python 3.11 或更高版本
- uv
- Git
- Node.js / npm：仅在使用 `npx` 类型 MCP server 时需要

## 安装依赖

在项目根目录执行：

```powershell
uv sync
```

## 配置模型

创建本地配置文件 `.codeshell/config.yaml`。该文件可以包含 API Key，默认不应提交到 Git。

OpenAI compatible / 阿里云百炼兼容接口示例：

```yaml
providers:
  - name: qwen-bailian
    protocol: openai-compat
    base_url: https://your-endpoint/compatible-mode/v1
    api_key: "your-api-key"
    model: qwen-plus
    context_window: 131072
    max_output_tokens: 8192

permission_mode: default

mcp_servers:
  - name: context7
    command: npx
    args: ["-y", "@upstash/context7-mcp"]
```

字段说明：

- `name`：provider 名称，用于区分不同模型配置。
- `protocol`：接口协议，支持 `anthropic`、`openai`、`openai-compat`。
- `base_url`：模型服务的 API 地址。
- `api_key`：模型服务 API Key。建议只放在本地配置或环境变量中。
- `model`：模型名称，以服务商控制台显示为准。
- `context_window`：模型真实上下文窗口大小。这个值只影响 CodeShell 的上下文管理和显示，不会提升模型本身能力。
- `max_output_tokens`：单次回复允许的最大输出 token 数。
- `mcp_servers`：需要接入的 MCP server 列表。

## 运行

启动交互式界面：

```powershell
uv run codeshell
```

执行单次 prompt：

```powershell
uv run python -m codeshell -p "你好，测试一下连接"
```

查看帮助：

```powershell
uv run python -m codeshell --help
```

## 常用 Slash Commands

- `/help`：查看命令帮助。
- `/doctor`：检查配置、provider、环境和 MCP 状态。
- `/status`：查看当前运行状态。
- `/session list`：查看历史会话。
- `/session resume <id|序号>`：恢复历史会话。
- `/session new`：开始新会话。
- `/compact`：手动压缩当前上下文。
- `/memory`：查看或管理记忆。
- `/mcp`：查看 MCP server 状态。
- `/permission`：查看或调整权限规则。
- `/sandbox`：查看或切换沙箱模式。
- `/skill`：查看和管理 skills。
- `/tasks`：查看后台任务。
- `/worktree`：管理 Git worktree。

在界面输入 `/` 可以打开 slash command 菜单。

## 会话与上下文

CodeShell 会把会话记录保存在本地 `.codeshell/sessions/` 下。重新进入项目后，可以通过 `/session list` 查看历史会话，并通过 `/session resume <id|序号>` 恢复。

上下文窗口用量会根据当前会话内容和工具输出估算。`context_window` 应设置为当前模型真实支持的上下文窗口大小，否则显示比例和压缩触发点会不准确。

## 开发与测试

运行全部测试：

```powershell
uv run pytest
```

运行指定测试：

```powershell
uv run pytest tests/test_context_indicator.py -q
```

## 安全说明

- 不要提交 `.codeshell/config.yaml`。
- 不要提交 API Key、`.env`、会话 JSONL、日志或虚拟环境目录。
- 仓库 `.gitignore` 已忽略 `.codeshell/`、`.venv/`、`.pytest_cache/`、`.env*` 等本地文件。
- 如果需要共享配置示例，请使用占位符，不要使用真实密钥。

## 目录结构

```text
codeshell-python/
├── codeshell/          # 主程序代码
├── tests/              # 测试代码
├── pyproject.toml      # 项目元数据、依赖和命令入口
├── uv.lock             # uv 锁文件
└── README.md           # 项目说明
```

## License

当前仓库尚未声明 License。
