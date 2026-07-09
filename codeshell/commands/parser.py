from __future__ import annotations

from codeshell.commands.registry import CommandRegistry

MAX_DESCRIPTION_CHARS = 18

SHORT_DESCRIPTIONS = {
    "clear": "清除对话历史",
    "code-spec": "规范驱动开发流程",
    "compact": "压缩上下文",
    "doctor": "环境诊断",
    "frontend-design": "前端界面设计",
    "greeting-helper": "生成问候语",
    "help": "显示帮助信息",
    "mcp": "查看 MCP 状态",
    "memory": "管理记忆",
    "permission": "管理权限",
    "plan": "切换 Plan 模式",
    "rewind": "回退到历史检查点",
    "sandbox": "管理沙箱",
    "session": "管理会话",
    "skill": "管理技能",
    "skill-creator": "创建或优化技能",
    "status": "显示状态信息",
}


def parse_command(text: str) -> tuple[str, str, bool]:
    text = text.strip()
    if not text.startswith("/"):
        return "", "", False
    text = text[1:]
    if not text:
        return "", "", True
    parts = text.split(None, 1)
    name = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return name, args, True


def _escape_markup(text: str) -> str:
    return text.replace("[", "\\[")


def _short_description(name: str, description: str) -> str:
    suffix = ""
    desc = description.strip()
    if desc.endswith("[技能]"):
        suffix = " [技能]"
        desc = desc.removesuffix("[技能]").strip()
    elif desc.endswith("[skill]"):
        suffix = " [技能]"
        desc = desc.removesuffix("[skill]").strip()

    desc = SHORT_DESCRIPTIONS.get(name, desc)
    desc = " ".join(desc.split())
    if len(desc) > MAX_DESCRIPTION_CHARS:
        desc = desc[:MAX_DESCRIPTION_CHARS].rstrip() + "…"
    return _escape_markup(desc + suffix)


def complete(registry: CommandRegistry, prefix: str) -> list[tuple[str, str]]:
    """Return matching commands as (display_text, command_value) pairs."""
    prefix = prefix.lstrip("/")
    seen: set[str] = set()
    matches: list[tuple[str, str]] = []
    for cmd in registry.list_commands():
        if cmd.name in seen:
            continue
        if cmd.name.startswith(prefix) or any(a.startswith(prefix) for a in cmd.aliases):
            seen.add(cmd.name)
            desc = _short_description(cmd.name, cmd.description)
            display = f"/{cmd.name:<16} - {desc}"
            matches.append((display, "/" + cmd.name))
    matches.sort(key=lambda x: x[1])
    return matches