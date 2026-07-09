# 可视化 Diff 审阅 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 新建 | `codeshell/diff_review/__init__.py` | 导出 diff review 子系统核心类型 |
| 新建 | `codeshell/diff_review/models.py` | 定义 FileSnapshot、FileChange、ChangeSet、DiffReviewResponse |
| 新建 | `codeshell/diff_review/render.py` | 生成 unified diff、二进制/大文件摘要、截断输出 |
| 新建 | `codeshell/diff_review/snapshot.py` | 扫描工作区快照、hash、文本/二进制判断、比较快照 |
| 新建 | `codeshell/diff_review/apply.py` | 校验 hash 并应用 create/modify/delete 变更 |
| 新建 | `codeshell/diff_review/bash_preview.py` | 临时预览工作区执行 Bash 并生成 ChangeSet |
| 新建 | `codeshell/diff_review/manager.py` | 统一协调 EditFile、WriteFile、Bash 的预览和应用 |
| 新建 | `codeshell/diff_dialog.py` | Textual 内联 diff 审阅组件 |
| 修改 | `codeshell/agent.py` | 新增 DiffReviewRequest 事件并接入工具执行流程 |
| 修改 | `codeshell/app.py` | 创建 manager、处理 diff 审阅 UI 事件 |
| 修改 | `codeshell/__main__.py` | 非 TUI 模式遇到 diff 审阅时拒绝并说明 |
| 修改 | `codeshell/remote.py` | remote 模式处理 diff 审阅事件的降级行为 |
| 修改 | `codeshell/tools/bash.py` | 抽出可复用命令执行函数，供预览后端使用 |
| 修改 | `codeshell/styles.tcss` | 添加 diff 审阅内联组件样式 |
| 新建 | `tests/test_diff_review.py` | 测试快照、diff 渲染、应用、冲突检测 |
| 新建 | `tests/test_diff_review_tools.py` | 测试 EditFile/WriteFile 审阅流程 |
| 新建 | `tests/test_diff_review_bash.py` | 测试 Bash 预览、批准、拒绝、失败 |
| 新建 | `tests/test_app_diff_review.py` | 测试 diff 审阅 widget 基础行为 |

## T1: 定义 diff review 数据模型
**文件：** `codeshell/diff_review/models.py`、`codeshell/diff_review/__init__.py`  
**依赖：** 无

步骤：
1. 定义 `FileSnapshot` dataclass，包含 path、exists、sha256、size、is_binary、content。
2. 定义 `FileChange` dataclass，包含 path、kind、before、after、diff_text、summary。
3. 定义 `ChangeSet` dataclass，包含 tool_name、description、work_dir、changes、stdout、is_preview_error、error_message。
4. 为 `ChangeSet` 实现 `has_changes()`、`summary_text()`、`render_diff(max_lines)`。
5. 定义 `DiffReviewResponse` 枚举：APPROVE、DENY。
6. 在 `__init__.py` 导出核心类型。

验证：运行 `uv run pytest tests/test_diff_review.py -q`，预期至少模型相关用例通过；若测试文件尚未创建，先运行 `uv run python -c "from codeshell.diff_review import ChangeSet, DiffReviewResponse; print('ok')"`。

## T2: 实现 diff 渲染
**文件：** `codeshell/diff_review/render.py`  
**依赖：** T1

步骤：
1. 定义最大文本文件读取阈值、最大 diff 行数、最大 diff 字符数常量。
2. 实现文本 bytes 到行列表的安全解码。
3. 使用 `difflib.unified_diff` 生成 create/modify/delete 的统一 diff。
4. 对二进制、超大文件、编码异常文件生成摘要文本。
5. 实现 diff 截断，保留“已截断”提示。

验证：`uv run pytest tests/test_diff_review.py -q`，期望文本 diff、二进制摘要、截断测试通过。

## T3: 实现快照扫描和比较
**文件：** `codeshell/diff_review/snapshot.py`  
**依赖：** T1, T2

步骤：
1. 实现 `snapshot_file(root, rel_path)`，生成单文件快照。
2. 实现 `snapshot_tree(root)`，递归扫描工作区。
3. 排除 `.git`、`.venv`、`node_modules`、`__pycache__`、`.tox`、`.mypy_cache` 等目录。
4. 路径统一为 POSIX 风格相对路径。
5. 实现 `compare_snapshots(before, after)`，生成 FileChange 列表。
6. 为每个 FileChange 填充 diff_text 和 summary。

验证：`uv run pytest tests/test_diff_review.py -q`，期望新增、修改、删除、空文件变化测试通过。

## T4: 实现安全应用变更
**文件：** `codeshell/diff_review/apply.py`  
**依赖：** T1, T3

步骤：
1. 实现路径解析，确保目标路径位于真实工作区内。
2. 实现 `validate_no_conflicts(change_set)`：检查真实文件当前 hash 与 before 一致。
3. 实现两阶段应用：先全部校验，再执行写入/删除。
4. 支持 create、modify、delete。
5. 应用后调用可选 cache invalidate、file_state_cache update、file_history track_edit。
6. 冲突时返回错误，不做部分应用。

验证：`uv run pytest tests/test_diff_review.py -q`，期望批准应用和外部修改冲突测试通过。

## T5: 为文件工具实现预览 manager
**文件：** `codeshell/diff_review/manager.py`  
**依赖：** T1-T4

步骤：
1. 定义 `DiffReviewManager` 构造参数：file_cache、file_state_cache、file_history。
2. 实现 `supports(tool_name)`，第一批支持 EditFile、WriteFile、Bash。
3. 实现 `prepare_edit_file(params, work_dir)`：复用 old_string 唯一性规则，构造修改后的内容。
4. 实现 `prepare_write_file(params, work_dir)`：构造创建/覆盖后的内容。
5. 实现 `prepare(tool, params, work_dir)` 分发逻辑。
6. 实现 `apply(change_set)` 调用 apply 模块。
7. 保持原 `EditFile`/`WriteFile` 错误语义：找不到 old_string、多次出现、读取失败均返回预览错误。

验证：`uv run pytest tests/test_diff_review_tools.py -q`，期望 EditFile/WriteFile 预览、批准、拒绝的 manager 层测试通过。

## T6: 抽出 Bash 可复用执行函数
**文件：** `codeshell/tools/bash.py`  
**依赖：** 无

步骤：
1. 抽出内部 async 函数 `run_shell_command(command, timeout, cwd, sandbox=None, sandbox_config=None)`。
2. 保持现有 Bash.execute 输出和 exit code 语义不变。
3. 让 `Bash.execute()` 调用该函数。
4. 不改变现有公开参数模型。

验证：`uv run pytest tests/test_permissions.py tests/test_agent.py -q`，期望既有 Bash 行为相关测试不回归。

## T7: 实现 Bash 预览后端
**文件：** `codeshell/diff_review/bash_preview.py`、`codeshell/diff_review/manager.py`  
**依赖：** T3, T6

步骤：
1. 创建临时预览目录。
2. 复制真实工作区到预览目录，排除大目录和缓存目录。
3. 对预览目录执行命令，工作目录设置为预览目录。
4. 执行前后分别调用 `snapshot_tree()`。
5. 比较得到 ChangeSet，并保存预览目录 after 文件来源信息，供 apply 使用。
6. 对预览失败、超时、复制失败返回 preview error。
7. 第一版不允许命令写出预览目录之外；无法保证时返回错误。

验证：`uv run pytest tests/test_diff_review_bash.py -q`，期望 Bash 创建、修改、删除文件的预览测试通过。

## T8: 接入 Agent 事件流
**文件：** `codeshell/agent.py`  
**依赖：** T5, T7

步骤：
1. 新增 `DiffReviewRequest` dataclass 和 AgentEvent union 成员。
2. Agent 构造函数增加 `diff_review_manager` 可选参数。
3. `_execute_tool()` 在权限确认后先校验 params。
4. 若 manager 支持该工具，调用 `prepare()`。
5. 预览错误直接返回 ToolResult 错误。
6. 无文件变化时返回 stdout/no changes。
7. 有变化时 yield `DiffReviewRequest`，等待 future。
8. 用户拒绝时返回拒绝 ToolResult。
9. 用户批准时调用 manager.apply()，返回应用结果。
10. `_execute_tool_direct()` 遇到需要 diff 审阅的工具时返回错误。

验证：`uv run pytest tests/test_diff_review_tools.py tests/test_diff_review_bash.py tests/test_agent.py -q`，期望 Agent 层审批流测试通过且既有 agent 测试不回归。

## T9: 实现 Textual diff 审阅组件
**文件：** `codeshell/diff_dialog.py`、`codeshell/styles.tcss`  
**依赖：** T1, T2

步骤：
1. 实现 `InlineDiffReviewWidget`。
2. 显示标题、工具名、文件摘要、截断后的 diff。
3. 显示两个操作：Approve changes、Reject changes。
4. 支持 up/down、enter、escape。
5. 样式与现有 permission/askuser 内联组件一致。

验证：`uv run pytest tests/test_app_diff_review.py -q`，期望 widget 渲染和响应事件测试通过。

## T10: 接入 App UI
**文件：** `codeshell/app.py`  
**依赖：** T8, T9

步骤：
1. 创建 `DiffReviewManager` 并传入 Agent。
2. 在事件循环中处理 `DiffReviewRequest`。
3. 挂载 `InlineDiffReviewWidget`，禁用输入框。
4. 响应 widget 事件，设置 future，移除 widget，恢复输入框。
5. 确保批准/拒绝后原工具调用继续返回 ToolResult。

验证：`uv run pytest tests/test_app_diff_review.py tests/test_agent.py -q`，期望 TUI 事件接入测试通过。

## T11: 接入非 TUI 和 remote 降级
**文件：** `codeshell/__main__.py`、`codeshell/remote.py`  
**依赖：** T8

步骤：
1. `__main__.py` 遇到 DiffReviewRequest 时设置 DENY，并输出说明。
2. stream-json 模式输出 diff_review_required 事件或 error 事件。
3. `remote.py` 遇到 DiffReviewRequest 时广播 diff review 事件；第一版无 Web 审阅 UI 时默认拒绝或等待客户端响应，按现有 remote 权限机制实现最小可用行为。
4. 确保不会在无交互场景自动应用文件变更。

验证：`uv run pytest tests/test_diff_review_tools.py tests/test_diff_review_bash.py -q`，并补充非交互拒绝测试。

## T12: 补齐测试和回归
**文件：** `tests/test_diff_review.py`、`tests/test_diff_review_tools.py`、`tests/test_diff_review_bash.py`、`tests/test_app_diff_review.py`、必要时更新既有测试  
**依赖：** T1-T11

步骤：
1. 覆盖 EditFile 修改批准前/后行为。
2. 覆盖 WriteFile 创建和覆盖 diff。
3. 覆盖 Bash 创建、修改、删除文件预览。
4. 覆盖拒绝后真实工作区不变。
5. 覆盖预览执行失败后真实工作区不变。
6. 覆盖 hash 冲突阻止应用。
7. 覆盖二进制摘要。
8. 覆盖 slash/TUI 不受影响的关键回归。

验证：`uv run pytest tests/test_diff_review.py tests/test_diff_review_tools.py tests/test_diff_review_bash.py tests/test_app_diff_review.py -q` 通过。

## T13: 全量验证
**文件：** 全项目  
**依赖：** T12

步骤：
1. 运行 diff review 局部测试。
2. 运行 agent/permission/app 相关测试。
3. 运行全量测试。
4. 如有失败，修复后重跑对应测试。

验证：
- `uv run pytest tests/test_diff_review.py tests/test_diff_review_tools.py tests/test_diff_review_bash.py tests/test_app_diff_review.py -q` 通过。
- `uv run pytest tests/test_agent.py tests/test_permissions.py tests/test_app.py -q` 通过。
- `uv run pytest -q` 通过。

## 执行顺序
```text
T1 → T2 → T3 → T4 → T5
                    ↘
T6 → T7 --------------→ T8 → T9 → T10 → T11 → T12 → T13
```