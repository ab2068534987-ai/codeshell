from __future__ import annotations

from rich.cells import cell_len

from codeshell.context_indicator import (
    ContextUsageIndicator,
    EMPTY_SYMBOL,
    FULL_SYMBOL,
    HIGH_SYMBOL,
    INDICATOR_HEIGHT,
    INDICATOR_WIDTH,
    LOW_SYMBOL,
    MEDIUM_SYMBOL,
    TRACK_STYLE,
    context_usage_indicator_text,
    context_usage_ring,
    context_usage_symbol,
    context_usage_tooltip,
    format_context_usage,
)


def test_format_unknown_when_total_is_zero() -> None:
    usage = format_context_usage(100, 0)

    assert usage.used_tokens == 100
    assert usage.total_tokens == 0
    assert usage.percent is None
    assert usage.state == "unknown"
    assert context_usage_symbol(usage.percent) == EMPTY_SYMBOL
    assert context_usage_tooltip(usage) == "Context: unknown"


def test_format_clamps_negative_values() -> None:
    usage = format_context_usage(-10, -1)

    assert usage.used_tokens == 0
    assert usage.total_tokens == 0
    assert usage.percent is None


def test_format_context_usage_percent_and_state() -> None:
    cases = [
        (0, 1_000_000, 0, "empty", EMPTY_SYMBOL),
        (250_000, 1_000_000, 25, "low", LOW_SYMBOL),
        (500_000, 1_000_000, 50, "medium", MEDIUM_SYMBOL),
        (750_000, 1_000_000, 75, "high", HIGH_SYMBOL),
        (900_000, 1_000_000, 90, "full", FULL_SYMBOL),
        (1_200_000, 1_000_000, 100, "full", FULL_SYMBOL),
    ]

    for used, total, percent, state, symbol in cases:
        usage = format_context_usage(used, total)
        assert usage.percent == percent
        assert usage.state == state
        assert context_usage_symbol(usage.percent) == symbol


def test_context_usage_indicator_text_uses_single_real_circle() -> None:
    empty = context_usage_indicator_text(0)
    active = context_usage_indicator_text(50)

    assert empty.plain == f" {EMPTY_SYMBOL} "
    assert active.plain == f" {EMPTY_SYMBOL} "
    assert len(empty.plain.splitlines()) == INDICATOR_HEIGHT
    assert cell_len(empty.plain) == INDICATOR_WIDTH
    assert len(active.plain.splitlines()) == INDICATOR_HEIGHT
    assert cell_len(active.plain) == INDICATOR_WIDTH
    assert "\u20dd" not in empty.plain
    assert "\u20dd" not in active.plain
    assert str(empty.style) == TRACK_STYLE
    assert str(active.style) == TRACK_STYLE


def test_context_usage_ring_keeps_compatibility_alias() -> None:
    assert context_usage_ring(50).plain == context_usage_indicator_text(50).plain


def test_tooltip_uses_token_totals_and_percent() -> None:
    usage = format_context_usage(12_345, 1_000_000)

    assert context_usage_tooltip(usage) == "Context: 12,345 / 1,000,000 tokens (1%)"


def test_indicator_initializes_and_updates() -> None:
    indicator = ContextUsageIndicator()

    assert indicator.rendered_symbol == EMPTY_SYMBOL
    assert indicator.tooltip == "Context: unknown"

    indicator.update_usage(500_000, 1_000_000)

    assert indicator.usage.percent == 50
    assert indicator.rendered_symbol == EMPTY_SYMBOL
    assert indicator.rendered_ring.plain == context_usage_indicator_text(50).plain
    assert indicator.tooltip == "Context: 500,000 / 1,000,000 tokens (50%)"