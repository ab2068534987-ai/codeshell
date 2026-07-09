# 可视化 Diff 审阅 Plan

## 架构概览
新增 `codeshell.diff_review` 子系统，负责“生成预览变更 → 渲染 diff → 等待用户审批 → 应用变更”。Agent 在权限检查通过之后、真实工具写入之前调用该子系统。这样现有权限系统仍然负责“是否允许尝试该工具”，diff 审阅负责“是否允许应用这些具体文件变化”。

`EditFile` 和 `WriteFile` 使用直接预览：根据工具参数在内存中构造目标文件的新内容，生成 change set，用户批准后再写入真实文件。

`Bash` 使用隔离预览：复制当前工作区到临时预览目录，在预览目录中执行命令，比较预览目录执行前后的文件快照，得到 change set。用户批准后，不重新执行命令，而是把预览目录中的文件变更应用回真实工作区。这样用户批准的内容和实际落盘内容一致。

如果平台或命令无法安全预览，命令不会直接在真实工作区执行，而是返回明确错误。

## 核心数据结构

### FileSnapshot
记录某个文件在某一时刻的状态。

字段：
- `path: str`：相对工作区路径。
- `exists: bool`：文件是否存在。
- `sha256: str`：文件内容 hash；不存在时为空。
- `size: int`：文件大小。
- `is_binary: bool`：是否按二进制处理。
- `content: bytes | None`：小文本文件保留内容，用于生成 diff；大文件或二进制文件不保留完整内容。

### FileChange
表示一个文件变化。

字段：
- `path: str`：相对工作区路径。
- `kind: Literal["create", "modify", "delete"]`。
- `before: FileSnapshot`。
- `after: FileSnapshot`。
- `diff_text: str`：文本 diff；二进制或过大文件为空。
- `summary: str`：用于 UI 的单文件摘要。

### ChangeSet
一次工具调用产生的所有文件变化。

字段：
- `tool_name: str`。
- `description: str`：工具动作说明。
- `work_dir: str`。
- `changes: list[FileChange]`。
- `stdout: str`：预览命令输出；文件工具为空或简短说明。
- `is_preview_error: bool`。
- `error_message: str`。

方法：
- `has_changes() -> bool`
- `summary_text() -> str`
- `render_diff(max_lines: int) -> str`

### DiffReviewRequest
新增 AgentEvent，用于把 change set 交给 UI 审批。

字段：
- `tool_name: str`
- `description: str`
- `change_set: ChangeSet`
- `future: asyncio.Future[DiffReviewResponse]`

### DiffReviewResponse
枚举：
- `APPROVE`
- `DENY`

### DiffReviewManager
Agent 持有的审阅协调器。

方法：
- `supports(tool_name: str) -> bool`
- `prepare(tool, params, work_dir) -> ChangeSet`
- `apply(change_set) -> ToolResult`

职责：
- 为 `EditFile`、`WriteFile`、`Bash` 生成预览。
- 校验真实工作区在预览和应用之间没有变化。
- 应用批准后的文件变化。
- 拒绝没有 diff adapter 的写类工具，避免静默修改。

## 模块设计

### codeshell/diff_review/models.py
**职责：** 定义 `FileSnapshot`、`FileChange`、`ChangeSet`、`DiffReviewResponse`。

### codeshell/diff_review/snapshot.py
**职责：**
- 扫描工作区文件快照。
- 排除 `.git`、`.venv`、`node_modules`、`__pycache__` 等目录。
- 限制单文件读取大小。
- 判断文本/二进制。
- 比较两个快照生成 `FileChange` 列表。

### codeshell/diff_review/render.py
**职责：**
- 使用 `difflib.unified_diff` 生成文本 diff。
- 对二进制、大文件、编码异常文件生成摘要。
- 限制最大 diff 行数和最大字符数。

### codeshell/diff_review/apply.py
**职责：**
- 应用 `ChangeSet` 到真实工作区。
- 应用前校验每个文件当前 hash 与 `before.sha256` 一致。
- create/modify/delete 全部验证通过后再执行写入。
- 任意文件冲突时整体中止，不做部分应用。
- 写入后失效 FileCache、更新 FileStateCache、记录 FileHistory。

### codeshell/diff_review/manager.py
**职责：**
- 对外提供 `DiffReviewManager`。
- 为 `EditFile` 和 `WriteFile` 构造内存预览。
- 为 `Bash` 调用 Bash 预览后端。
- 将批准后的 `ChangeSet` 应用并返回统一 `ToolResult`。

### codeshell/diff_review/bash_preview.py
**职责：**
- 创建临时预览工作区。
- 复制真实工作区，排除大目录和缓存目录。
- 在预览工作区中执行命令并捕获输出。
- 执行前后比较快照，返回 `ChangeSet`。
- 优先使用 OS 沙箱限制写入只能发生在预览目录；没有安全沙箱且无法保证命令不会写真实工作区时，返回预览错误，不执行真实命令。

### codeshell/agent.py
**职责：**
- 新增 `DiffReviewRequest` AgentEvent。
- Agent 增加 `diff_review_manager: DiffReviewManager | None`。
- `_execute_tool()` 在权限确认之后、`tool.execute()` 之前：
  1. 校验参数。
  2. 如果工具需要 diff 审阅，调用 `prepare()`。
  3. 预览失败则返回错误。
  4. 无文件变化则返回预览命令输出或 no changes 结果。
  5. 有变化则 yield `DiffReviewRequest`。
  6. 用户拒绝则返回拒绝结果。
  7. 用户批准则调用 `apply()`。
- 非交互式 direct 执行路径遇到 diff-required 工具时返回错误，避免无 UI 时静默写入。

### codeshell/diff_dialog.py
**职责：**
- 新增 `InlineDiffReviewWidget`。
- 显示文件摘要、截断后的 unified diff、批准/拒绝选项。
- 支持键盘导航：上/下选择，Enter 确认，Escape 拒绝。

### codeshell/app.py
**职责：**
- 创建 `DiffReviewManager` 并注入 Agent。
- 处理 `DiffReviewRequest`，挂载 `InlineDiffReviewWidget`。
- 用户响应后设置 future，移除 widget，恢复输入框。

### codeshell/__main__.py / codeshell/remote.py
**职责：**
- 非 TUI `-p` 模式：遇到 diff 审阅请求默认拒绝，并输出“需要交互式 diff 审阅”。
- Web remote 模式：新增 diff review event 结构；第一版可以返回拒绝或复用现有 permission request 事件，后续再做 Web diff UI。

### codeshell/tools/edit_file.py / write_file.py / bash.py
**职责：**
- 保留原工具执行能力。
- 增加必要的预览辅助方法或让 `DiffReviewManager` 直接复用其参数模型。
- 工具本身不直接与 UI 交互。

## 模块交互

### EditFile / WriteFile
1. Agent 完成权限检查。
2. Agent 校验工具参数。
3. DiffReviewManager 读取真实文件当前内容，构造目标内容。
4. DiffReviewManager 生成 ChangeSet。
5. Agent yield DiffReviewRequest。
6. UI 展示 diff。
7. 用户批准后，DiffReviewManager 校验真实文件 hash 并应用变化。
8. Agent 返回 ToolResult 给模型。

### Bash
1. Agent 完成权限检查。
2. DiffReviewManager 创建预览工作区。
3. 复制真实工作区到预览目录。
4. 在预览目录执行命令，捕获 stdout。
5. 比较预览目录执行前后快照，生成 ChangeSet。
6. 如果无文件变化，直接返回 stdout。
7. 如果有文件变化，Agent yield DiffReviewRequest。
8. 用户批准后，应用预览目录中的变更到真实工作区。
9. 用户拒绝或真实工作区 hash 冲突时，不修改真实工作区。

## 文件组织
```text
codeshell/
├── agent.py                         — 新增 DiffReviewRequest 事件和执行流程接入
├── app.py                           — TUI 中处理 diff 审阅请求
├── diff_dialog.py                   — 内联 diff 审阅组件
├── diff_review/
│   ├── __init__.py
│   ├── models.py                    — FileSnapshot/FileChange/ChangeSet 等结构
│   ├── snapshot.py                  — 快照扫描、hash、文本/二进制判断
│   ├── render.py                    — unified diff 和摘要渲染
│   ├── apply.py                     — hash guard 和应用变更
│   ├── bash_preview.py              — Bash 隔离预览执行
│   └── manager.py                   — 对 Agent 暴露的统一审阅服务
├── tools/
│   ├── edit_file.py                 — 保留工具执行，配合 manager 预览
│   ├── write_file.py                — 保留工具执行，配合 manager 预览
│   └── bash.py                      — 暴露可复用命令执行函数，供预览后端使用
└── remote.py                        — diff review event 降级处理

tests/
├── test_diff_review.py              — 快照、diff、apply、冲突检测
├── test_diff_review_tools.py        — EditFile/WriteFile 审阅流程
├── test_diff_review_bash.py         — Bash 预览、批准、拒绝、失败
└── test_app_diff_review.py          — TUI widget 基础行为
```

## 技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 审阅位置 | 权限检查后、真实执行前 | 先保留现有权限语义，再增加文件级确认 |
| Bash 批准后行为 | 应用预览文件变化，不重新执行命令 | 保证实际落盘内容和用户看到的 diff 一致 |
| Bash 预览环境 | 临时工作区副本，优先 OS 沙箱限制写入 | 保护真实工作区，降低任意命令副作用 |
| 无法安全预览 | 阻止执行并返回错误 | 满足“不能静默直接修改真实工作区” |
| 冲突处理 | hash 不一致则整体中止 | 避免覆盖用户或外部进程的新改动 |
| 大文件/二进制 | 只显示摘要，不渲染全文 diff | 避免 UI 卡死和乱码 |
| 非交互模式 | 默认拒绝 diff-required 修改 | 没有用户确认时不能应用文件变化 |
| Plan Mode | 保持计划文件特殊放行，不引入额外 diff 审阅 | 不破坏现有计划审批流程 |

## Spec 覆盖
- F1/F2：由 manager 为 EditFile/WriteFile 构造预写入 ChangeSet。
- F3/F9/F11：由 bash_preview 的隔离预览和失败阻止实现。
- F4/F5/F6：由 snapshot/render 覆盖新增、修改、删除、二进制和摘要。
- F7/F8/F10：由 Agent 审阅事件和 apply hash guard 实现。
- F12：由 InlineDiffReviewWidget 提供批准/拒绝动作。
- F13：由 PathSandbox、快照路径校验和工作区相对路径约束实现。