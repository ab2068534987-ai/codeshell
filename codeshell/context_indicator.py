from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual._context import NoActiveAppError
from textual.widgets import Static

TRACK_STYLE = "#8b949e"
INDICATOR_WIDTH = 3
INDICATOR_HEIGHT = 1
EMPTY_SYMBOL = "○"
LOW_SYMBOL = EMPTY_SYMBOL
MEDIUM_SYMBOL = EMPTY_SYMBOL
HIGH_SYMBOL = EMPTY_SYMBOL
FULL_SYMBOL = EMPTY_SYMBOL


@dataclass(frozen=True)
class ContextUsage:
    used_tokens: int
    total_tokens: int
    percent: int | None
    state: str


def format_context_usage(used_tokens: int, total_tokens: int) -> ContextUsage:
    used = max(0, int(used_tokens))
    total = max(0, int(total_tokens))
    if total == 0:
        return ContextUsage(used_tokens=used, total_tokens=0, percent=None, state="unknown")

    percent = int(used / total * 100)
    percent = max(0, min(100, percent))
    if percent == 0:
        state = "empty"
    elif percent <= 25:
        state = "low"
    elif percent <= 50:
        state = "medium"
    elif percent <= 75:
        state = "high"
    else:
        state = "full"
    return ContextUsage(used_tokens=used, total_tokens=total, percent=percent, state=state)


def context_usage_symbol(percent: int | None) -> str:
    return EMPTY_SYMBOL


def context_usage_indicator_text(percent: int | None) -> Text:
    return Text(f" {context_usage_symbol(percent)} ", style=TRACK_STYLE, no_wrap=True)


def context_usage_ring(percent: int | None) -> Text:
    return context_usage_indicator_text(percent)


def context_usage_tooltip(usage: ContextUsage) -> str:
    if usage.percent is None:
        return "Context: unknown"
    return (
        "Context: "
        f"{usage.used_tokens:,} / {usage.total_tokens:,} tokens "
        f"({usage.percent}%)"
    )


class ContextUsageIndicator(Static):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "context-usage")
        super().__init__(context_usage_indicator_text(None), **kwargs)
        self.usage = format_context_usage(0, 0)
        self.rendered_symbol = context_usage_symbol(None)
        self.rendered_ring = context_usage_indicator_text(None)
        self.tooltip = context_usage_tooltip(self.usage)

    def update_usage(self, used_tokens: int, total_tokens: int) -> None:
        self.usage = format_context_usage(used_tokens, total_tokens)
        self.rendered_symbol = context_usage_symbol(self.usage.percent)
        self.rendered_ring = context_usage_indicator_text(self.usage.percent)
        self.tooltip = context_usage_tooltip(self.usage)
        try:
            self.update(self.rendered_ring)
        except NoActiveAppError:
            pass