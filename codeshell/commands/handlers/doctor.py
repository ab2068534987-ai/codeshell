from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codeshell.commands.registry import Command, CommandContext, CommandType


@dataclass
class DoctorCheck:
    level: str
    title: str
    detail: str
    suggestion: str = ""


def _is_venv() -> bool:
    return bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix


def _status_icon(level: str) -> str:
    return {
        "OK": "[OK]",
        "WARN": "[WARN]",
        "ERROR": "[ERROR]",
    }.get(level, "[INFO]")


def _add(checks: list[DoctorCheck], level: str, title: str, detail: str, suggestion: str = "") -> None:
    checks.append(DoctorCheck(level, title, detail, suggestion))


def _config_paths(work_dir: Path) -> list[Path]:
    return [
        Path.home() / ".codeshell" / "config.yaml",
        work_dir / ".codeshell" / "config.yaml",
        work_dir / ".codeshell" / "config.local.yaml",
    ]


def _get_app_config(ctx: CommandContext) -> Any:
    config = ctx.config
    if isinstance(config, dict):
        return config.get("app_config") or config.get("config")
    return config


def _provider_key_state(provider: Any) -> str:
    configured = bool(getattr(provider, "api_key", ""))
    resolved = ""
    try:
        resolved = provider.resolve_api_key()
    except Exception:
        resolved = getattr(provider, "api_key", "") or ""
    if configured:
        return "已配置（配置文件，已隐藏）" if resolved else "配置文件字段为空"
    return "已配置（环境变量，已隐藏）" if resolved else "未配置"


def _collect_checks(ctx: CommandContext) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    work_dir = Path(getattr(ctx.agent, "work_dir", os.getcwd()) if ctx.agent else os.getcwd())
    app_config = _get_app_config(ctx)

    _add(checks, "OK", "Python", sys.version.split()[0])
    if _is_venv():
        venv = os.environ.get("VIRTUAL_ENV", sys.prefix)
        _add(checks, "OK", "虚拟环境", str(venv))
    else:
        _add(checks, "WARN", "虚拟环境", "未检测到虚拟环境", "建议使用 uv sync 创建并使用项目虚拟环境")

    _add(checks, "OK" if work_dir.exists() else "ERROR", "工作目录", str(work_dir))

    existing_configs = [p for p in _config_paths(work_dir) if p.exists()]
    if existing_configs:
        _add(checks, "OK", "配置文件", ", ".join(str(p) for p in existing_configs))
    else:
        _add(checks, "ERROR", "配置文件", "未找到 config.yaml", "请创建 .codeshell/config.yaml 或 ~/.codeshell/config.yaml")

    providers = list(getattr(app_config, "providers", []) or [])
    if providers:
        _add(checks, "OK", "Provider", f"已配置 {len(providers)} 个")
        for provider in providers:
            name = getattr(provider, "name", "unknown")
            protocol = getattr(provider, "protocol", "unknown")
            model = getattr(provider, "model", "unknown")
            base_url = getattr(provider, "base_url", "") or "未设置"
            key_state = _provider_key_state(provider)
            level = "OK" if not key_state.startswith("未配置") else "WARN"
            _add(
                checks,
                level,
                f"Provider:{name}",
                f"protocol={protocol}, model={model}, base_url={base_url}, api_key={key_state}",
                "如需调用模型，请配置 api_key 或对应环境变量" if level == "WARN" else "",
            )
    else:
        _add(checks, "ERROR", "Provider", "未配置 provider", "请在 config.yaml 中配置 providers")

    mcp_servers = list(getattr(app_config, "mcp_servers", []) or [])
    if mcp_servers:
        _add(checks, "OK", "MCP 配置", f"已配置 {len(mcp_servers)} 个服务器")
    else:
        _add(checks, "WARN", "MCP 配置", "未配置 MCP 服务器")

    mcp_info = getattr(ctx.ui, "_mcp_server_info", "")
    if mcp_info:
        _add(checks, "OK", "MCP 运行时", str(mcp_info).strip())
    elif mcp_servers:
        _add(checks, "WARN", "MCP 运行时", "未检测到已连接服务器", "启动后等待连接，或使用 /mcp 查看详细状态")
    else:
        _add(checks, "OK", "MCP 运行时", "无 MCP 服务器需要连接")

    mode = getattr(getattr(ctx.agent, "permission_mode", None), "value", None) or "unknown"
    _add(checks, "OK", "权限模式", str(mode))

    sandbox = getattr(app_config, "sandbox", None)
    if sandbox is not None:
        enabled = getattr(sandbox, "enabled", False)
        auto_allow = getattr(sandbox, "auto_allow", False)
        network = getattr(sandbox, "network_enabled", False)
        _add(checks, "OK", "Sandbox", f"enabled={enabled}, auto_allow={auto_allow}, network={network}")
    else:
        _add(checks, "WARN", "Sandbox", "未读取到 sandbox 配置")

    if ctx.session:
        meta = ctx.session.meta
        _add(checks, "OK", "会话", f"{meta.id}，消息数 {meta.message_count}")
    else:
        _add(checks, "WARN", "会话", "当前没有活动会话")

    codeshell_dir = work_dir / ".codeshell"
    for rel in ["sessions", "skills", "memory"]:
        path = codeshell_dir / rel
        _add(checks, "OK" if path.exists() else "WARN", f"目录:{rel}", str(path) if path.exists() else "不存在")

    skills_dir = codeshell_dir / "skills"
    if skills_dir.is_dir():
        skill_count = sum(1 for p in skills_dir.iterdir() if p.is_dir() or p.suffix == ".md")
        _add(checks, "OK", "Skills", f"发现 {skill_count} 个")
    else:
        _add(checks, "WARN", "Skills", "未找到 skills 目录")

    if ctx.agent:
        try:
            enabled_tools = [t for t in ctx.agent.registry.list_tools() if ctx.agent.registry.is_enabled(t.name)]
            _add(checks, "OK", "工具", f"已启用 {len(enabled_tools)} 个")
        except Exception as exc:
            _add(checks, "WARN", "工具", f"无法读取工具状态：{exc}")
    else:
        _add(checks, "WARN", "工具", "agent 未初始化")

    return checks


def _format_report(checks: list[DoctorCheck]) -> str:
    errors = sum(1 for c in checks if c.level == "ERROR")
    warnings = sum(1 for c in checks if c.level == "WARN")
    lines = [
        "CodeShell 环境诊断",
        "------------------",
        f"摘要: {errors} 个错误，{warnings} 个警告",
        "",
    ]
    for check in checks:
        lines.append(f"{_status_icon(check.level)} {check.title}: {check.detail}")
        if check.suggestion:
            lines.append(f"      建议: {check.suggestion}")
    return "\n".join(lines)


async def handle_doctor(ctx: CommandContext) -> None:
    checks = _collect_checks(ctx)
    ctx.ui.add_system_message(_format_report(checks))


DOCTOR_COMMAND = Command(
    name="doctor",
    aliases=[],
    description="环境诊断",
    usage="/doctor",
    type=CommandType.LOCAL,
    handler=handle_doctor,
)