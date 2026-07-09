from codeshell.commands.completion import CompletionPopup


def _render_text(popup: CompletionPopup) -> str:
    return str(popup.render())


def test_completion_popup_uses_limited_window_with_count() -> None:
    popup = CompletionPopup()
    pairs = [(f"/cmd{i}", f"/cmd{i}") for i in range(12)]

    popup.show_pairs(pairs)
    rendered = _render_text(popup)

    assert "1-8 / 12" in rendered
    assert "/cmd0" in rendered
    assert "/cmd7" in rendered
    assert "/cmd8" not in rendered
    assert popup.get_selected() == "/cmd0"


def test_completion_popup_scrolls_selected_item_into_view() -> None:
    popup = CompletionPopup()
    pairs = [(f"/cmd{i}", f"/cmd{i}") for i in range(12)]
    popup.show_pairs(pairs)

    for _ in range(11):
        popup.move_down()

    rendered = _render_text(popup)

    assert popup.get_selected() == "/cmd11"
    assert "5-12 / 12" in rendered
    assert "/cmd11" in rendered
    assert "/cmd0" not in rendered

    popup.move_up()
    assert popup.get_selected() == "/cmd10"
    assert "/cmd10" in _render_text(popup)


def test_completion_popup_hide_resets_scroll_state() -> None:
    popup = CompletionPopup()
    pairs = [(f"/cmd{i}", f"/cmd{i}") for i in range(12)]
    popup.show_pairs(pairs)

    for _ in range(11):
        popup.move_down()
    popup.hide()

    assert popup.get_selected() is None
    assert popup._visible_start == 0
    assert popup._cursor == 0
    assert popup._displays == []
    assert popup._values == []