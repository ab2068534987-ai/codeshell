# 可视化 Diff 审阅 Checklist

> 每一项都必须通过运行代码、观察行为或检查测试结果验证；重点验证真实工作区是否在批准前保持不变。

## 实现完整性
- [ ] `EditFile` 修改已有文件时会产生 diff 审阅请求（验证：运行 EditFile 审阅测试，观察事件类型为 DiffReviewRequest）。
- [ ] `WriteFile` 创建新文件时会产生新增文件 diff（验证：运行 WriteFile 创建测试，diff 中包含新文件路径和新增内容）。
- [ ] `WriteFile` 覆盖已有文件时会产生旧内容到新内容的 diff（验证：运行 WriteFile 覆盖测试，diff 中同时出现删除行和新增行）。
- [ ] `Bash` 修改工作区文件时先在预览环境执行（验证：运行 Bash 修改测试，批准前真实文件内容不变）。
- [ ] `Bash` 创建和删除工作区文件时都能被快照比较捕获（验证：运行 Bash create/delete 测试，ChangeSet 包含 create/delete）。
- [ ] 二进制文件变化显示摘要而不是乱码全文（验证：运行二进制文件测试，输出包含 binary/二进制摘要且无原始不可读内容）。

## 审批行为
- [ ] 用户批准 `EditFile` diff 后，真实文件内容变为 diff 中的新内容（验证：批准测试后读取文件内容）。
- [ ] 用户拒绝 `EditFile` diff 后，真实文件内容保持旧内容（验证：拒绝测试后读取文件内容）。
- [ ] 用户批准 `WriteFile` 新建 diff 后，新文件被创建且内容一致（验证：批准测试后读取新文件）。
- [ ] 用户拒绝 `WriteFile` 新建 diff 后，新文件不存在（验证：拒绝测试后检查路径不存在）。
- [ ] 用户批准 `Bash` diff 后，真实工作区应用预览文件变化（验证：批准测试后读取真实文件）。
- [ ] 用户拒绝 `Bash` diff 后，真实工作区不变（验证：拒绝测试后比较文件 hash）。

## 安全与边界
- [ ] 预览执行失败时真实工作区不变（验证：运行失败命令测试，检查文件 hash 未变化）。
- [ ] 预览后真实文件被外部修改时阻止应用（验证：构造 hash 冲突，期望 ToolResult 为错误且文件保留外部修改）。
- [ ] diff 应用不会写出工作区之外（验证：路径越界测试返回错误）。
- [ ] 无法安全预览的写操作不会直接修改真实工作区（验证：对应测试返回错误且文件不变）。
- [ ] Plan Mode 原有计划文件流程不被破坏（验证：运行现有 plan/agent 测试）。
- [ ] 非交互 `-p` 模式不会自动批准 diff 审阅（验证：非 TUI 测试返回需要交互式 diff 审阅或拒绝信息）。

## UI 集成
- [ ] TUI 中 diff 审阅组件显示文件摘要（验证：widget 测试包含 create/modify/delete 路径）。
- [ ] TUI 中 diff 审阅组件显示截断后的 unified diff（验证：widget 测试包含 `---`、`+++`、`@@` 或截断提示）。
- [ ] TUI 中 diff 审阅组件提供批准和拒绝动作（验证：enter 发送 APPROVE，escape 发送 DENY）。
- [ ] diff 审阅期间输入框禁用，响应后恢复（验证：App 事件测试检查 disabled 状态变化）。

## 集成
- [ ] Agent 在权限确认之后触发 diff 审阅（验证：默认权限下先出现 PermissionRequest，再出现 DiffReviewRequest）。
- [ ] acceptEdits/bypassPermissions 仍会触发 diff 审阅，不会绕过文件级确认（验证：权限模式测试中仍出现 DiffReviewRequest）。
- [ ] 拒绝 diff 后 ToolResult 返回错误并写入对话工具结果（验证：Agent 测试检查 ToolResultEvent.is_error 为 True）。
- [ ] 批准 diff 后 ToolResult 返回成功并写入对话工具结果（验证：Agent 测试检查 ToolResultEvent.is_error 为 False）。
- [ ] 现有 `/doctor`、slash completion、banner、权限命令测试不回归（验证：运行相关测试）。

## 测试命令
- [ ] `uv run pytest tests/test_diff_review.py -q` 通过。
- [ ] `uv run pytest tests/test_diff_review_tools.py -q` 通过。
- [ ] `uv run pytest tests/test_diff_review_bash.py -q` 通过。
- [ ] `uv run pytest tests/test_app_diff_review.py -q` 通过。
- [ ] `uv run pytest tests/test_agent.py tests/test_permissions.py tests/test_app.py -q` 通过。
- [ ] `uv run pytest -q` 通过。

## 端到端场景
- [ ] 场景 1：Agent 请求修改已有文本文件 → 用户看到 diff → 用户批准 → 文件按 diff 修改（验证：端到端测试或手动运行后读取文件）。
- [ ] 场景 2：Agent 请求创建新文件 → 用户看到新增文件 diff → 用户拒绝 → 文件没有创建（验证：端到端测试或手动运行后检查路径）。
- [ ] 场景 3：Agent 请求执行会修改文件的 Bash 命令 → 预览环境生成 diff → 用户批准 → 真实工作区应用同样文件变化（验证：端到端测试或手动运行后读取文件）。
- [ ] 场景 4：预览后用户或外部进程改动目标文件 → 用户批准旧 diff → 系统阻止应用并提示重新执行（验证：冲突测试）。