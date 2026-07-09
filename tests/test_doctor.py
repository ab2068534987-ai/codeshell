from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from codeshell.commands.handlers import register_all_commands
from codeshell.commands.handlers.doctor import handle_doctor
from codeshell.commands.parser import complete
from codeshell.commands.registry import CommandContext, CommandRegistry
from codeshell.config import AppConfig, MCPServerConfig, ProviderConfig, SandboxAppConfig


class MockUI:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self._mcp_server_info = "context7 connected"

    def add_system_message(self, text: str) -> None:
        self.messages.append(text)

    def send_user_message(self, text: str) -> None:
        pass

    def set_plan_mode(self, enabled: bool) -> None:
        pass

    def get_token_count(self) -> tuple[int, int]:
        return 10, 2

    def refresh_status(self) -> None:
        pass


@dataclass
class MockMeta:
    id: str = "session_test"
    message_count: int = 3


@dataclass
class MockSession:
    meta: MockMeta = field(default_factory=MockMeta)


class MockRegistry:
    def list_tools(self):
        return [SimpleNamespace(name="ReadFile"), SimpleNamespace(name="Bash")]

    def is_enabled(self, name: str) -> bool:
        return True


class MockAgent:
    def __init__(self, work_dir: str) -> None:
        self.work_dir = work_dir
        self.permission_mode = SimpleNamespace(value="default")
        self.registry = MockRegistry()


@pytest.mark.asyncio
async def test_doctor_outputs_diagnostics_and_redacts_api_key(tmp_path: Path) -> None:
    (tmp_path / ".codeshell" / "sessions").mkdir(parents=True)
    (tmp_path / ".codeshell" / "skills").mkdir()
    (tmp_path / ".codeshell" / "memory").mkdir()
    (tmp_path / ".codeshell" / "config.yaml").write_text("providers: []\n", encoding="utf-8")
    (tmp_path / ".codeshell" / "skills" / "demo").mkdir()

    provider = ProviderConfig(
        name="test-provider",
        protocol="openai-compat",
        base_url="https://example.com/v1",
        model="qwen-plus",
        api_key="secret-key-123",
    )
    app_config = AppConfig(
        providers=[provider],
        mcp_servers=[MCPServerConfig(name="context7", command="npx")],
        sandbox=SandboxAppConfig(enabled=True, auto_allow=False, network_enabled=False),
    )
    ui = MockUI()
    ctx = CommandContext(
        args="",
        agent=MockAgent(str(tmp_path)),
        conversation=None,
        session=MockSession(),
        session_manager=None,
        memory_manager=None,
        ui=ui,
        config={"app_config": app_config},
    )

    await handle_doctor(ctx)

    report = ui.messages[-1]
    assert "CodeShell 环境诊断" in report
    assert "Python" in report
    assert "工作目录" in report
    assert "配置文件" in report
    assert "Provider" in report
    assert "MCP" in report
    assert "权限模式" in report
    assert "会话" in report
    assert "Skills" in report
    assert "secret-key-123" not in report
    assert "已配置（配置文件，已隐藏）" in report


def test_doctor_command_is_registered_and_completes() -> None:
    registry = CommandRegistry()
    register_all_commands(registry)

    assert registry.find("doctor") is not None
    matches = complete(registry, "/doc")

    assert matches == [("/doctor           - 环境诊断", "/doctor")]