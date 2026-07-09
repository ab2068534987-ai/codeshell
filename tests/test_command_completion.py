from unittest.mock import AsyncMock

from codeshell.commands.parser import complete
from codeshell.commands.registry import Command, CommandRegistry, CommandType


def _command(name: str, description: str | None = None) -> Command:
    return Command(
        name=name,
        description=description or f"Test {name}",
        type=CommandType.LOCAL,
        handler=AsyncMock(),
    )


def test_complete_returns_all_matches_without_menu_limit() -> None:
    registry = CommandRegistry()
    for i in range(12):
        registry.register_sync(_command(f"cmd{i:02d}"))

    matches = complete(registry, "/")
    values = [value for _, value in matches]

    assert len(matches) == 12
    assert values[0] == "/cmd00"
    assert values[-1] == "/cmd11"


def test_complete_shortens_long_description_for_menu() -> None:
    registry = CommandRegistry()
    long_description = "This is a long command description that should not occupy multiple rows in the slash menu"
    registry.register_sync(_command("longdesc", long_description))

    matches = complete(registry, "/long")

    assert len(matches) == 1
    assert "This is a long com…" in matches[0][0]
    assert long_description not in matches[0][0]


def test_complete_uses_chinese_short_description_for_known_commands() -> None:
    registry = CommandRegistry()
    registry.register_sync(_command("rewind", "Rewind to a previous checkpoint"))
    registry.register_sync(_command("skill-creator", "Create new skills, modify and improve existing skills. [技能]"))

    displays = {value: display for display, value in complete(registry, "/")}

    assert displays["/rewind"].endswith("回退到历史检查点")
    assert displays["/skill-creator"].endswith("创建或优化技能 \\[技能]")